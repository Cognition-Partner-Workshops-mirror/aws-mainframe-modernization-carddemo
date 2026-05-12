# COBOL Copybook → PySpark Parsing Notes

This document describes the type-mapping decisions, parsing strategies, and conventions
used when converting COBOL copybook field definitions to PySpark DataFrame schemas.

## Copybooks Processed

| Copybook       | Record Name       | Record Length | Data File       | Row Count |
|----------------|-------------------|---------------|-----------------|-----------|
| `CVACT01Y.cpy` | ACCOUNT-RECORD    | 300 bytes     | `acctdata.txt`  | 50        |
| `CUSTREC.cpy`  | CUSTOMER-RECORD   | 500 bytes     | `custdata.txt`  | 50        |
| `CVACT02Y.cpy` | CARD-RECORD       | 150 bytes     | `carddata.txt`  | 50        |

## Type-Mapping Decisions

### PIC X(n) → StringType

**Decision:** All `PIC X(n)` (alphanumeric) fields map to `StringType`.

**Rationale:** `PIC X` fields contain arbitrary characters—names, addresses, dates as
formatted strings, status flags, etc. `StringType` is the natural PySpark equivalent.
Values are right-trimmed of trailing spaces during parsing to remove COBOL padding.

**Examples:**
- `ACCT-ACTIVE-STATUS PIC X(01)` → `StringType` (values: `"Y"`, `"N"`)
- `ACCT-OPEN-DATE PIC X(10)` → `StringType` (values: `"2014-11-20"`)
- `CUST-FIRST-NAME PIC X(25)` → `StringType` (values: `"Immanuel"`)

### PIC 9(n) (Identifiers / Codes) → StringType

**Decision:** `PIC 9(n)` fields that represent identifiers, codes, or sensitive numbers
are mapped to `StringType` to **preserve leading zeros**.

**Rationale:** Fields like account IDs (`00000000001`), SSNs (`020973888`), and CVV codes
(`028`) contain leading zeros that carry semantic meaning. Casting these to numeric types
would silently strip leading zeros and corrupt the data.

**Examples:**
- `ACCT-ID PIC 9(11)` → `StringType` (e.g., `"00000000001"`)
- `CUST-ID PIC 9(09)` → `StringType` (e.g., `"000000001"`)
- `CUST-SSN PIC 9(09)` → `StringType` (e.g., `"020973888"`)
- `CARD-CVV-CD PIC 9(03)` → `StringType` (e.g., `"028"`)
- `CARD-ACCT-ID PIC 9(11)` → `StringType` (e.g., `"00000000050"`)

### PIC 9(n) (Numeric Values) → IntegerType

**Decision:** `PIC 9(n)` fields that represent true numeric values (scores, counts)
are mapped to `IntegerType`.

**Rationale:** These fields have numeric semantics where leading zeros are padding,
not data. Casting to `IntegerType` enables numeric operations (aggregation, filtering).

**Examples:**
- `CUST-FICO-CREDIT-SCORE PIC 9(03)` → `IntegerType` (values: `274`, `616`)

### PIC S9(n)V99 → DecimalType(n+2, 2)

**Decision:** Signed zoned-decimal fields with an implied decimal point map to
`DecimalType(12, 2)` for `PIC S9(10)V99`.

**Rationale:**
- The `S` prefix indicates a signed value (positive or negative).
- `V99` is an implied decimal point — the last 2 digits represent cents/fractions,
  but no decimal point character appears in the stored data.
- In ASCII display format, the sign is encoded as an **overpunch** on the last byte
  of the field.
- `DecimalType` provides exact precision for financial values (no floating-point drift).
- `precision=12` accommodates `9(10)` (10 integer digits) + `V99` (2 fractional digits).

**Examples:**
- `ACCT-CURR-BAL PIC S9(10)V99` → `DecimalType(12, 2)` (e.g., `194.00`)
- `ACCT-CREDIT-LIMIT PIC S9(10)V99` → `DecimalType(12, 2)` (e.g., `2020.00`)

### COMP-3 (Packed Decimal) → DecimalType *(not present in these copybooks)*

**Decision:** If `COMP-3` fields were encountered, they would map to `DecimalType`.

**Rationale:** `COMP-3` (packed decimal) stores two digits per byte plus a sign nibble
in the last byte. In EBCDIC files, each byte encodes two BCD digits (0–9), with the
final nibble being the sign (`0xC` = positive, `0xD` = negative, `0xF` = unsigned).
The PySpark equivalent is `DecimalType(precision, scale)`, where:
- `precision` = total digits defined in the PIC clause
- `scale` = digits after the implied decimal (`V`)

**Note:** The ASCII data files in this project do not contain `COMP-3` fields.
All signed fields use zoned-decimal (display) format with sign overpunch encoding.
If migrating from EBCDIC source, a byte-level unpacking step would be needed before
the PySpark parsing stage.

### FILLER → Excluded

**Decision:** `FILLER` fields are excluded from the PySpark DataFrame.

**Rationale:** COBOL `FILLER` reserves space within the fixed-width record but carries
no business data. Including it would add unused columns and inflate memory usage.
The field definitions are documented in the JSON schemas for completeness.

## Sign Overpunch Decoding

COBOL stores the sign of a signed zoned-decimal field by overwriting the last byte
with a special character that encodes both the sign and the digit value:

| Positive  | Char | Digit | Negative  | Char | Digit |
|-----------|------|-------|-----------|------|-------|
| `{`       | +0   | 0     | `}`       | -0   | 0     |
| `A`       | +1   | 1     | `J`       | -1   | 1     |
| `B`       | +2   | 2     | `K`       | -2   | 2     |
| `C`       | +3   | 3     | `L`       | -3   | 3     |
| `D`       | +4   | 4     | `M`       | -4   | 4     |
| `E`       | +5   | 5     | `N`       | -5   | 5     |
| `F`       | +6   | 6     | `O`       | -6   | 6     |
| `G`       | +7   | 7     | `P`       | -7   | 7     |
| `H`       | +8   | 8     | `Q`       | -8   | 8     |
| `I`       | +9   | 9     | `R`       | -9   | 9     |

**Example:** `00000001940{` → digits `000000019400`, sign `+` → value `+194.00`

The decoding logic lives in `pyspark/cobol_utils.py` and is reusable for any
COBOL fixed-width file with signed zoned-decimal fields.

### Observation on Current Data

All 250 signed field values across 50 account records use the `{` overpunch
character (positive zero), indicating all monetary values in the test dataset are
positive. The parser handles both positive and negative overpunches correctly.

## Parsing Strategy

### Fixed-Width Extraction

All data files are parsed using PySpark's `spark.read.text()` to read raw lines,
then `F.col("value").substr(offset + 1, length)` to extract each field by byte
position. PySpark `substr` is 1-indexed, so we add 1 to the 0-based COBOL offsets.

### String Trimming

All extracted fields are passed through `F.trim()` to remove trailing whitespace
padding that COBOL uses to fill fixed-width fields. This is particularly important
for `PIC X` fields like names and addresses.

### Data File Format

- **Encoding:** ASCII (the `app/data/ASCII/` directory contains ASCII-encoded versions)
- **Record terminator:** Each record is followed by a newline character (`\n`)
- **No header row:** Data files contain only data records

## Generated Artifacts

```
pyspark/
├── cobol_utils.py                     # Shared sign-overpunch decoder and utilities
├── parse_acctdata.py                  # CVACT01Y.cpy → acctdata.txt parser
├── parse_custdata.py                  # CUSTREC.cpy  → custdata.txt parser
├── parse_carddata.py                  # CVACT02Y.cpy → carddata.txt parser
├── schemas/
│   ├── CVACT01Y_schema.json           # Account record JSON schema
│   ├── CUSTREC_schema.json            # Customer record JSON schema
│   └── CVACT02Y_schema.json           # Card record JSON schema
└── validation/
    ├── acctdata_validation.txt        # Account parsing validation output
    ├── custdata_validation.txt        # Customer parsing validation output
    └── carddata_validation.txt        # Card parsing validation output
```

## Validation Summary

| Data File       | Raw Rows | Parsed Rows | Match | Notes |
|-----------------|----------|-------------|-------|-------|
| `acctdata.txt`  | 50       | 50          | Yes   | All balances parsed as `DecimalType(12,2)` |
| `custdata.txt`  | 50       | 50          | Yes   | FICO scores cast to `IntegerType` (range 1–793) |
| `carddata.txt`  | 50       | 50          | Yes   | All card numbers are 16 characters |

## Known Copybook Quirks

1. **Typo in field name:** Both `CVACT01Y.cpy` and `CVACT02Y.cpy` spell expiration
   as `EXPIRAION` (missing 'T'). The PySpark column names preserve this original
   spelling for traceability.

2. **Tab characters in CUSTREC.cpy:** The copybook source file uses tab characters
   for indentation (instead of standard COBOL spaces), which causes compilation
   failures with GnuCOBOL's strict parser. This does not affect PySpark parsing
   since we derive the schema manually from the field definitions.

3. **ACCT-ADDR-ZIP values:** Account records contain `A000000000` as the ZIP code,
   which appears to be test/placeholder data rather than a valid postal code.
