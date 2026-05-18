# COBOL Copybook → PySpark Parsing Notes

This document describes the type-mapping decisions, parsing strategy, and
assumptions made when converting COBOL copybook record layouts to PySpark
DataFrames for the CardDemo application.

---

## Copybooks Processed

| Copybook       | Record Name      | Length | Data File           |
|----------------|------------------|--------|---------------------|
| `CVACT01Y.cpy` | ACCOUNT-RECORD   | 300 B  | `acctdata.txt`      |
| `CUSTREC.cpy`  | CUSTOMER-RECORD  | 500 B  | `custdata.txt`      |
| `CVACT02Y.cpy` | CARD-RECORD      | 150 B  | `carddata.txt`      |

---

## Type-Mapping Decisions

### PIC X(n) → `StringType`

All alphanumeric COBOL fields (`PIC X(n)`) are mapped to PySpark `StringType`.
Trailing spaces (the COBOL padding character) are stripped via `F.trim()` during
parsing. Leading spaces are also stripped since COBOL left-pads are uncommon for
`PIC X` fields.

**Affected fields:** status flags, dates, names, addresses, zip codes, phone
numbers, government IDs, etc.

### PIC 9(n) → `LongType` or `IntegerType`

Unsigned numeric display fields (`PIC 9(n)`) are cast directly to integer types.
The choice between `LongType` and `IntegerType` is based on the digit count:

| Digits | PySpark Type    | Rationale                                      |
|--------|-----------------|------------------------------------------------|
| ≤ 9    | `IntegerType`\* | Fits comfortably in a 32-bit signed integer    |
| > 9    | `LongType`      | Exceeds `Integer.MAX_VALUE` (2,147,483,647)    |

\* Exception: `PIC 9(09)` fields like `CUST-ID` and `CUST-SSN` use `LongType`
because 9-digit values can approach the 32-bit signed limit (max 999,999,999 vs
2,147,483,647). `PIC 9(03)` fields (FICO score, CVV) use `IntegerType`.

These fields contain ASCII digit characters (`'0'`–`'9'`) with no sign or
decimal point, so a direct `cast("long")` in PySpark is sufficient.

### PIC S9(n)V99 → `DecimalType(n+2, 2)`

Signed numeric display fields with an implied decimal point require special
handling:

1. **Storage:** `PIC S9(10)V99` occupies 12 bytes in DISPLAY format
   (10 integer digits + 2 decimal digits). The `V` is an *implied* decimal —
   it does not occupy storage.

2. **Sign encoding (ASCII overpunch):** The sign is embedded in the **zone
   nibble of the last byte** using the standard ASCII overpunch convention:

   | Last Byte | Digit | Sign     |
   |-----------|-------|----------|
   | `{`       | 0     | Positive |
   | `A`–`I`   | 1–9   | Positive |
   | `}`       | 0     | Negative |
   | `J`–`R`   | 1–9   | Negative |

   Example: `00000001940{` → digits `000000019400`, sign = positive →
   with V99 → `+194.00`

3. **PySpark mapping:** `DecimalType(12, 2)` — precision 12 (total digits),
   scale 2 (digits after decimal). This preserves exact decimal arithmetic
   for financial amounts without floating-point rounding errors.

4. **Implementation:** A PySpark UDF (`decode_signed_zoned_decimal`) handles
   the overpunch decoding. The module `cobol_utils.py` is distributed to Spark
   workers via `spark.sparkContext.addPyFile()`.

**Affected fields (CVACT01Y only):**
- `ACCT-CURR-BAL`
- `ACCT-CREDIT-LIMIT`
- `ACCT-CASH-CREDIT-LIMIT`
- `ACCT-CURR-CYC-CREDIT`
- `ACCT-CURR-CYC-DEBIT`

### COMP-3 (Packed Decimal) → `DecimalType`

**Not present in these three copybooks.** If COMP-3 fields are encountered in
other CardDemo copybooks (e.g., transaction records), the mapping would be:

- **Storage:** Each digit pair occupies one byte; the last nibble is the sign
  (C=positive, D=negative, F=unsigned).
- **PySpark type:** `DecimalType(p, s)` where `p` = total digits, `s` = implied
  decimal scale.
- **Parsing:** Requires byte-level unpacking (not character-level like DISPLAY
  format). A dedicated binary UDF would be needed.

### FILLER → Excluded

COBOL `FILLER` fields are padding bytes used to reach the declared record
length. They are **not included** in the output PySpark DataFrames but are
documented in the JSON schema files for completeness (with byte offset and
length).

---

## Parsing Strategy

### Fixed-Width Record Extraction

Each data file is read as a text file (one line per record) using
`spark.read.text()`. Fields are extracted using `F.substring()` with
1-indexed positions derived from the copybook byte offsets:

```
pyspark_start_position = cobol_byte_offset + 1
```

This approach avoids external fixed-width libraries and works reliably
with PySpark's built-in string functions.

### Data Format Assumptions

1. **ASCII encoding:** The data files in `app/data/ASCII/` are already in
   ASCII (not EBCDIC). No character-set conversion is needed.

2. **Newline-delimited:** Each record is terminated by a newline character
   (`\n`), which is **not** counted in the record length.

3. **No record-type indicators:** All records in each file share the same
   layout (no multi-format files or record-type discriminators).

4. **Consistent record lengths:** Every line is exactly the copybook-declared
   length (verified: acctdata=300, custdata=500, carddata=150).

---

## Validation Summary

All three data files were successfully parsed with matching row counts:

| File            | Raw Lines | Parsed Rows | Match |
|-----------------|-----------|-------------|-------|
| `acctdata.txt`  | 50        | 50          | PASS  |
| `custdata.txt`  | 50        | 50          | PASS  |
| `carddata.txt`  | 50        | 50          | PASS  |

Sample values were cross-checked against manual `cut` extraction from the
raw files to confirm correct field alignment and type conversion.

---

## Field-Name Conventions

COBOL names use hyphens (`ACCT-ID`); PySpark column names use underscores
(`ACCT_ID`). The original COBOL names (including deliberate typos like
`ACCT-EXPIRAION-DATE`) are preserved in the JSON schema's `cobol_name` field
for traceability. The PySpark column names mirror the COBOL names with
`s/-/_/g` substitution.

---

## Project Structure

```
pyspark_copybook_parser/
├── COPYBOOK_PARSING_NOTES.md          ← This file
├── schemas/
│   ├── CVACT01Y_schema.json           ← Account record JSON schema
│   ├── CUSTREC_schema.json            ← Customer record JSON schema
│   └── CVACT02Y_schema.json           ← Card record JSON schema
├── scripts/
│   ├── __init__.py
│   ├── cobol_utils.py                 ← Shared utilities (overpunch decoding, parsing)
│   ├── parse_acctdata.py              ← PySpark parser for account data
│   ├── parse_custdata.py              ← PySpark parser for customer data
│   └── parse_carddata.py              ← PySpark parser for card data
└── validation/
    ├── acctdata_validation.txt         ← Validation output for account data
    ├── custdata_validation.txt         ← Validation output for customer data
    └── carddata_validation.txt         ← Validation output for card data
```

---

## Running the Parsers

```bash
# Install PySpark (if not already installed)
pip install pyspark

# Run individual parsers (from repo root)
python pyspark_copybook_parser/scripts/parse_acctdata.py
python pyspark_copybook_parser/scripts/parse_custdata.py
python pyspark_copybook_parser/scripts/parse_carddata.py
```

Each script:
1. Reads the corresponding JSON schema
2. Parses the fixed-width data file
3. Applies type conversions (including overpunch decoding for signed decimals)
4. Writes a validation report to `validation/`
5. Prints the DataFrame schema and sample rows to stdout
