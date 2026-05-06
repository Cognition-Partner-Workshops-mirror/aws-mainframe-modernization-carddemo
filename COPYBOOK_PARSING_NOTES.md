# COBOL Copybook → PySpark Type-Mapping Notes

This document explains how each COBOL PIC clause in the CardDemo copybooks was
mapped to a PySpark data type and how the fixed-width ASCII data files were
parsed.

---

## Copybook/Data-File Pairings

| Copybook         | Record Name       | Record Length | Data File                     |
|------------------|-------------------|:------------:|-------------------------------|
| `CVACT01Y.cpy`   | ACCOUNT-RECORD    | 300          | `app/data/ASCII/acctdata.txt` |
| `CUSTREC.cpy`    | CUSTOMER-RECORD   | 500          | `app/data/ASCII/custdata.txt` |
| `CVACT02Y.cpy`   | CARD-RECORD       | 150          | `app/data/ASCII/carddata.txt` |

---

## Type-Mapping Decisions

### `PIC X(n)` → `StringType`

Alphanumeric fields are mapped directly to PySpark `StringType`. After
extraction via `substring()` the values are trimmed of trailing spaces using
`trim()`.

**Examples:** `ACCT-ACTIVE-STATUS PIC X(01)`, `CUST-FIRST-NAME PIC X(25)`,
`CARD-NUM PIC X(16)`.

### `PIC 9(n)` (unsigned numeric) → `LongType` or `IntegerType`

Unsigned display-numeric fields contain only the digit characters `0–9` and
are cast to:
- **`LongType`** when the field width exceeds 9 digits (e.g., `ACCT-ID PIC
  9(11)`, `CUST-SSN PIC 9(09)`).
- **`IntegerType`** when the field width is ≤ 4 digits (e.g., `CARD-CVV-CD PIC
  9(03)`, `CUST-FICO-CREDIT-SCORE PIC 9(03)`).

Leading zeros are naturally dropped during the numeric cast.

### `PIC S9(n)V99` (signed zoned decimal) → `DecimalType(12, 2)`

Signed zoned-decimal fields store:
1. **Sign** — embedded in the last byte as an ASCII overpunch character.
2. **Implied decimal** — the `V99` clause means 2 decimal places; no literal
   `.` appears in the data.

The field width equals `n + 2` bytes (10 integer digits + 2 fractional digits
for `PIC S9(10)V99` → 12 bytes).

#### ASCII Overpunch Decoding

When EBCDIC data is transferred to ASCII, the sign+last-digit combination is
represented as:

| Digit | Positive | Negative |
|:-----:|:--------:|:--------:|
|   0   |    `{`   |    `}`   |
|   1   |    `A`   |    `J`   |
|   2   |    `B`   |    `K`   |
|   3   |    `C`   |    `L`   |
|   4   |    `D`   |    `M`   |
|   5   |    `E`   |    `N`   |
|   6   |    `F`   |    `O`   |
|   7   |    `G`   |    `P`   |
|   8   |    `H`   |    `Q`   |
|   9   |    `I`   |    `R`   |

A Spark UDF (`decode_zoned_decimal` in `cobol_utils.py`) extracts the digit
from the overpunch character, reconstructs the full digit string, applies the
sign, and inserts the implied decimal point before casting to
`DecimalType(12, 2)`.

**Example:** raw bytes `00000001940{` → digits `000000019400` → decimal
`194.00` (positive, from `{` = +0).

### COMP-3 (Packed Decimal)

The CardDemo ASCII data files in this repository do not contain COMP-3
(packed-decimal / BCD) fields. If COMP-3 fields were present, the recommended
mapping would be:

- **`COMP-3 PIC S9(n)V9(m)`** → `DecimalType(n + m, m)`
- Each byte stores two BCD digits (high nibble, low nibble), with the low
  nibble of the last byte encoding the sign (`0xC` = positive, `0xD` =
  negative, `0xF` = unsigned).
- A packed field of `PIC S9(n)` occupies `⌈(n + 1) / 2⌉` bytes.
- Parsing would require reading raw bytes (not text lines) and decoding each
  nibble pair.

### FILLER Fields

Every copybook includes a trailing `FILLER` field that pads the record to its
declared length. These are extracted as `StringType` for completeness but are
dropped from the final DataFrames and CSV outputs since they carry no business
data.

---

## Parsing Approach

1. **Read as text** — `spark.read.text(path)` reads each fixed-length line into
   a single `value` column.
2. **Slice columns** — `substring(col("value"), offset, length)` extracts each
   field using 1-based byte offsets derived from the cumulative field widths in
   the copybook.
3. **Type conversion** — string fields are trimmed, unsigned numerics are cast
   to `LongType`/`IntegerType`, and signed zoned-decimal fields are decoded via
   the `decode_zoned_decimal` UDF and cast to `DecimalType(12, 2)`.

---

## Validation Summary

All three datasets passed validation:

| Dataset   | Raw Lines | PySpark Rows | Row Match | Record Length | Nulls |
|-----------|:---------:|:------------:|:---------:|:-------------:|:-----:|
| Account   |    50     |      50      |   PASS    |   PASS (300)  | NONE  |
| Customer  |    50     |      50      |   PASS    |   PASS (500)  | NONE  |
| Card      |    50     |      50      |   PASS    |   PASS (150)  | NONE  |

See `pyspark_parsers/validation/validation_report.txt` for the full report and
`pyspark_parsers/validation/*.csv` for the parsed output.

---

## File Inventory

```
pyspark_parsers/
├── schemas/
│   ├── cvact01y_account_schema.json   # Account field layout
│   ├── custrec_customer_schema.json   # Customer field layout
│   └── cvact02y_card_schema.json      # Card field layout
├── scripts/
│   ├── cobol_utils.py                 # Zoned-decimal decoding utility
│   ├── parse_acctdata.py              # Account parser
│   ├── parse_custdata.py              # Customer parser
│   ├── parse_carddata.py              # Card parser
│   └── validate_all.py               # Consolidated validation runner
└── validation/
    ├── validation_report.txt          # Full validation output
    ├── acctdata_parsed.csv            # Parsed account data
    ├── custdata_parsed.csv            # Parsed customer data
    └── carddata_parsed.csv            # Parsed card data
```
