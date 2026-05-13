# COBOL Copybook to PySpark Type-Mapping Notes

## Overview

This document describes the type-mapping decisions made when converting COBOL copybook field
definitions to PySpark DataFrame schemas. Three copybooks are covered:

| Copybook      | Record Name      | Record Length | Data File              |
|---------------|------------------|--------------|------------------------|
| CVACT01Y.cpy  | ACCOUNT-RECORD   | 300 bytes    | acctdata.txt           |
| CUSTREC.cpy   | CUSTOMER-RECORD  | 500 bytes    | custdata.txt           |
| CVACT02Y.cpy  | CARD-RECORD      | 150 bytes    | carddata.txt           |

## Type-Mapping Rules

### PIC X(n) → StringType

- **Decision**: All `PIC X(n)` fields map to `StringType` in PySpark.
- **Rationale**: `PIC X` defines alphanumeric data that can contain any character.
  Dates stored as `PIC X(10)` (e.g., `YYYY-MM-DD`) are kept as strings to preserve
  the original format. Downstream consumers can cast to `DateType` as needed.
- **Trimming**: Leading and trailing spaces are trimmed during parsing since COBOL
  pads alphanumeric fields with trailing spaces.

### PIC 9(n) (Unsigned) → LongType or IntegerType

- **Decision**: Unsigned numeric fields (`PIC 9(n)`) map to `LongType` for fields
  with more than 9 digits, `IntegerType` for fields with ≤ 9 digits.
- **Rationale**: COBOL stores these as ASCII character digits (`'0'`-`'9'`) in DISPLAY
  usage. Simple cast to integer type after trimming is sufficient.
- **Special case**: `CARD-NUM` (PIC X(16)) is kept as `StringType` despite containing
  only digits because it's a card number identifier and leading zeros are significant.
- **Examples**:
  - `PIC 9(11)` → `LongType` (ACCT-ID, CARD-ACCT-ID)
  - `PIC 9(09)` → `LongType` (CUST-ID, CUST-SSN)
  - `PIC 9(03)` → `IntegerType` (CARD-CVV-CD, CUST-FICO-CREDIT-SCORE)

### PIC S9(n)V99 (Signed with Implied Decimal) → DecimalType(12, 2)

- **Decision**: Signed numeric fields with implied decimal places map to
  `DecimalType(precision, scale)` where precision = total digits and scale = decimal places.
- **Rationale**: `PIC S9(10)V99` has 10 integer digits + 2 decimal digits = 12 total
  digits with 2 decimal places → `DecimalType(12, 2)`.
- **Overpunch decoding**: In ASCII-format COBOL data files (DISPLAY usage), the sign is
  encoded in the last byte using overpunch notation:
  - Positive: `{`=0, `A`=1, `B`=2, `C`=3, `D`=4, `E`=5, `F`=6, `G`=7, `H`=8, `I`=9
  - Negative: `}`=0, `J`=1, `K`=2, `L`=3, `M`=4, `N`=5, `O`=6, `P`=7, `Q`=8, `R`=9
- **Example**: `00000001940{` → digits `000000019400`, sign positive → `+194.00`

### COMP-3 (Packed Decimal) → DecimalType

- **Decision**: If COMP-3 fields were present, they would map to `DecimalType`.
- **Rationale**: COMP-3 stores two digits per byte (BCD encoding) with the sign in the
  last nibble. Each byte contains two decimal digits except the last byte which has one
  digit and a sign nibble (C=positive, D=negative, F=unsigned).
- **Note**: None of the three copybooks in this exercise use COMP-3. This mapping is
  documented for completeness since it's referenced in the task specification.
- **Formula**: Storage size = `CEIL((n + 1) / 2)` bytes for PIC S9(n) COMP-3.

### FILLER → Excluded from Output

- **Decision**: FILLER fields are parsed but excluded from the final DataFrame output.
- **Rationale**: FILLER is padding to reach the record length boundary. It contains no
  business data and would clutter the output schema.

## Implied Decimal Point (V)

COBOL's `V` denotes an implied (virtual) decimal point — no actual decimal character exists
in the stored data. The position of `V` determines how many trailing digits represent the
fractional part.

- `PIC S9(10)V99`: 12 bytes stored, last 2 digits are cents → divide raw integer by 100
- Our PySpark implementation inserts the decimal point programmatically after decoding.

## Data Format Notes

### ASCII vs EBCDIC

The data files in `app/data/ASCII/` are ASCII-encoded. The same data also exists in
`app/data/EBCDIC/` in EBCDIC encoding. Our parsers target the ASCII files only.

Key differences:
- ASCII overpunch uses `{`, `A`-`I` for positive and `}`, `J`-`R` for negative
- EBCDIC overpunch uses different hex values for the zone nibble

### Fixed-Width Record Layout

Each line in the data file is exactly the record length specified in the copybook:
- `acctdata.txt`: 300 bytes per line
- `custdata.txt`: 500 bytes per line
- `carddata.txt`: 150 bytes per line

Records are newline-delimited (`\n`), which is NOT part of the record itself.
PySpark's `spark.read.text()` handles the newline separation naturally.

### Field Name Conventions

- COBOL names use hyphens (e.g., `ACCT-CURR-BAL`)
- PySpark column names use underscores (e.g., `ACCT_CURR_BAL`)
- Original typos in copybook field names are preserved (e.g., `EXPIRAION` not `EXPIRATION`)

## Validation Approach

The validation script (`generated/pyspark/validate_all.py`) verifies:

1. **Row count parity**: Parsed DataFrame row count matches raw file line count
2. **Record length**: Each raw line matches the expected byte length
3. **Sample value assertions**: First-record field values are manually verified against
   the raw data by visual inspection of the fixed-width layout
4. **Type correctness**: All numeric fields parse without null (no conversion errors)

## Generated Artifacts

```
generated/
├── pyspark/
│   ├── parse_acctdata.py     # CVACT01Y.cpy → acctdata.txt parser
│   ├── parse_custdata.py     # CUSTREC.cpy → custdata.txt parser
│   ├── parse_carddata.py     # CVACT02Y.cpy → carddata.txt parser
│   └── validate_all.py       # Cross-validation script for all three
├── schemas/
│   ├── CVACT01Y_schema.json  # JSON schema for ACCOUNT-RECORD
│   ├── CUSTREC_schema.json   # JSON schema for CUSTOMER-RECORD
│   └── CVACT02Y_schema.json  # JSON schema for CARD-RECORD
└── validation/
    └── validation_report.txt # Output from validate_all.py
```
