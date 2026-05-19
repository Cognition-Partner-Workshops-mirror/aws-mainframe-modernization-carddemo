# COBOL Copybook → PySpark Type-Mapping Notes

This document describes the type-mapping decisions made when converting
COBOL copybook field definitions to PySpark column types for fixed-width
file parsing.

---

## Copybooks Processed

| Copybook | Record Name | Record Length | Data File |
|-----------|-------------|---------------|-----------|
| `CVACT01Y.cpy` | ACCOUNT-RECORD | 300 bytes | `app/data/ASCII/acctdata.txt` |
| `CUSTREC.cpy` | CUSTOMER-RECORD | 500 bytes | `app/data/ASCII/custdata.txt` |
| `CVACT02Y.cpy` | CARD-RECORD | 150 bytes | `app/data/ASCII/carddata.txt` |

---

## Type-Mapping Rules

### 1. `PIC X(n)` → `StringType`

Alphanumeric fields are mapped directly to PySpark `StringType`.
Values are right-padded with spaces in the fixed-width file; the parser
applies `trim()` to strip trailing whitespace.

**Examples:**
- `ACCT-ACTIVE-STATUS  PIC X(01)` → `StringType` (single-char flag: Y/N)
- `ACCT-OPEN-DATE      PIC X(10)` → `StringType` (date as YYYY-MM-DD text)
- `CARD-EMBOSSED-NAME  PIC X(50)` → `StringType` (name string)

**Date fields note:** Date fields (`PIC X(10)`) are kept as `StringType`
rather than converted to `DateType` because the copybook treats them as
plain alphanumeric text. Downstream consumers can cast to date types
as needed.

---

### 2. `PIC 9(n)` (unsigned zoned decimal) → `LongType` or `IntegerType`

Unsigned numeric display fields contain only ASCII digit characters
(`0`–`9`). They are cast to numeric PySpark types based on the
number of digits:

| Digits | PySpark Type | Rationale |
|--------|-------------|-----------|
| ≤ 9 | `IntegerType` | Fits within 32-bit signed integer range |
| 10–18 | `LongType` | Requires 64-bit signed integer |

**Exceptions — preserving leading zeros:**

Some `PIC 9(n)` fields are intentionally kept as `StringType` when
leading zeros carry semantic meaning:

- `CUST-SSN PIC 9(09)` → `StringType` — SSNs like `020973888` must
  retain the leading zero
- `CARD-CVV-CD PIC 9(03)` → `StringType` — CVV codes like `028` or
  `003` must retain leading zeros

**Examples of numeric casting:**
- `ACCT-ID PIC 9(11)` → `LongType` (11-digit account ID)
- `CUST-FICO-CREDIT-SCORE PIC 9(03)` → `IntegerType` (3-digit score,
  leading zeros are not meaningful for a numeric score)

---

### 3. `PIC S9(n)V99` (signed zoned decimal with implied decimal) → `DecimalType(n+2, 2)`

Signed zoned-decimal DISPLAY fields use the **trailing overpunch**
convention to encode the sign in the last byte of the field.

**Storage format:**
- Total bytes = integer digits + decimal digits (the `V` is implied,
  not stored)
- The last byte is a sign-overpunch character instead of a plain digit

**Overpunch mapping (EBCDIC-to-ASCII convention):**

| Last Char | Sign | Digit |
|-----------|------|-------|
| `{` | + | 0 |
| `A`–`I` | + | 1–9 |
| `}` | − | 0 |
| `J`–`R` | − | 1–9 |

**Example decode:**
```
Raw field:    00000001940{
Last char:    { → positive, digit 0
Digit string: 000000019400
V99 applied:  0000000194.00
Result:       194.00
```

**PySpark mapping:**
- `PIC S9(10)V99` → `DecimalType(12, 2)` — 12 total digits, 2 decimal places
- A custom UDF (`cobol_utils.make_signed_decimal_udf`) decodes the
  overpunch character, reconstructs the digit string, inserts the
  implied decimal point, and applies the sign
- The decoded string is then cast to `DecimalType`

**Fields using this mapping (all in CVACT01Y.cpy):**
- `ACCT-CURR-BAL`
- `ACCT-CREDIT-LIMIT`
- `ACCT-CASH-CREDIT-LIMIT`
- `ACCT-CURR-CYC-CREDIT`
- `ACCT-CURR-CYC-DEBIT`

---

### 4. `COMP-3` (packed decimal) → `DecimalType` *(not present in these copybooks)*

COMP-3 fields store two digits per byte (BCD encoding) with the sign
in the trailing nibble. None of the three copybooks processed here use
COMP-3, but the recommended mapping would be:

| COBOL PIC | PySpark Type | Notes |
|-----------|-------------|-------|
| `PIC S9(n) COMP-3` | `DecimalType(n, 0)` | Integer packed decimal |
| `PIC S9(n)V9(m) COMP-3` | `DecimalType(n+m, m)` | Packed decimal with implied decimal |

**Byte length formula:** `CEIL((n + 1) / 2)` where `n` is total digit
count (the `+1` accounts for the sign nibble).

COMP-3 fields require binary-level parsing (nibble extraction) rather
than character-level substring slicing. An EBCDIC-to-ASCII conversion
step is also typically required if the source data is in EBCDIC encoding.

---

### 5. `FILLER` → `StringType` (excluded from analysis)

FILLER fields are padding bytes with no business meaning. They are
extracted as `StringType` for completeness and record-length validation
but are typically dropped in downstream processing.

---

## Parsing Approach

### Fixed-Width File Reading

PySpark does not have a built-in fixed-width file reader. The approach
used here:

1. Read the file as plain text via `spark.read.text()` — each line
   becomes a single `value` column
2. Use `col("value").substr(offset + 1, length)` to slice each field
   (PySpark `substr` is 1-based)
3. Apply type conversions and trimming after slicing

### Sign Overpunch Handling

A Python UDF (`cobol_utils.make_signed_decimal_udf`) is used because
PySpark's built-in SQL functions cannot directly decode COBOL overpunch
characters. The UDF:

1. Extracts the last character of the raw field
2. Looks up the sign and digit value in the overpunch mapping table
3. Reconstructs the full digit string
4. Inserts the implied decimal point
5. Returns a signed decimal string suitable for `DecimalType` casting

The `cobol_utils.py` module is shipped to Spark workers via
`spark.sparkContext.addPyFile()`.

---

## Validation Summary

All three parsers were validated against their respective data files:

| Copybook | Data File | Raw Lines | Parsed Rows | Match | Bad Lengths | Nulls |
|-----------|-----------|-----------|-------------|-------|-------------|-------|
| CVACT01Y.cpy | acctdata.txt | 50 | 50 | ✓ | 0 | None |
| CUSTREC.cpy | custdata.txt | 50 | 50 | ✓ | 0 | None |
| CVACT02Y.cpy | carddata.txt | 50 | 50 | ✓ | 0 | None |

Detailed validation reports (including sample rows and numeric
summaries) are in `pyspark_parsing/validation/`.

---

## File Inventory

```
pyspark_parsing/
├── COPYBOOK_PARSING_NOTES.md          # This document
├── schemas/
│   ├── cvact01y_schema.json           # ACCOUNT-RECORD field layout
│   ├── custrec_schema.json            # CUSTOMER-RECORD field layout
│   └── cvact02y_schema.json           # CARD-RECORD field layout
├── scripts/
│   ├── cobol_utils.py                 # Shared overpunch decoding utilities
│   ├── parse_acctdata.py              # PySpark parser for acctdata.txt
│   ├── parse_custdata.py              # PySpark parser for custdata.txt
│   └── parse_carddata.py              # PySpark parser for carddata.txt
└── validation/
    ├── acctdata_validation.json       # Validation output for acctdata
    ├── custdata_validation.json       # Validation output for custdata
    └── carddata_validation.json       # Validation output for carddata
```
