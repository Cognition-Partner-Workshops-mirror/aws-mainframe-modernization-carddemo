# COBOL Copybook → PySpark Type-Mapping Notes

This document describes the type-mapping decisions made when translating
COBOL copybook field definitions into PySpark DataFrame schemas for the
CardDemo application.

---

## Copybooks Covered

| Copybook | Record Name | RECLN | Source File |
|---|---|---|---|
| `CVACT01Y.cpy` | ACCOUNT-RECORD | 300 | `app/data/ASCII/acctdata.txt` |
| `CUSTREC.cpy` | CUSTOMER-RECORD | 500 | `app/data/ASCII/custdata.txt` |
| `CVACT02Y.cpy` | CARD-RECORD | 150 | `app/data/ASCII/carddata.txt` |

---

## General Approach

1. **Fixed-width parsing** — Each data file is read with `spark.read.text()`
   and fields are extracted via `F.substring(col, offset, length)` using
   1-based byte offsets derived directly from the copybook.

2. **FILLER fields** — Every copybook includes a trailing `FILLER` that pads
   the record to its declared length.  FILLER columns are extracted during
   parsing but immediately dropped from the final DataFrame.

3. **Field naming** — COBOL hyphens (`-`) are replaced with underscores
   (`_`) to produce valid PySpark column names.  Original COBOL names
   (including the `EXPIRAION` typo in CVACT01Y and CVACT02Y) are preserved
   to maintain traceability back to the copybook.

---

## Type-Mapping Rules

### `PIC X(n)` → `StringType`

All alphanumeric COBOL fields map to PySpark `StringType`.  Trailing spaces
(the COBOL default pad character) are removed with `F.trim()`.

**Examples:** `ACCT-ACTIVE-STATUS PIC X(01)`, `CUST-FIRST-NAME PIC X(25)`,
`CARD-NUM PIC X(16)`.

### `PIC 9(n)` (unsigned numeric, DISPLAY) → `StringType`

Unsigned numeric fields are mapped to `StringType` rather than a numeric
type.  This preserves **leading zeros**, which is critical for:

- **Identifiers** — `ACCT-ID PIC 9(11)` stores values like `00000000001`.
  Casting to `LongType` would discard the leading zeros, breaking downstream
  joins that rely on the fixed-width representation.
- **SSN** — `CUST-SSN PIC 9(09)` may begin with `0`.
- **CVV codes** — `CARD-CVV-CD PIC 9(03)` can be `007`.

**Exception — FICO score:** `CUST-FICO-CREDIT-SCORE PIC 9(03)` is cast to
`IntegerType` because it represents a true numeric value (credit score
300–850) where leading-zero preservation is unnecessary and numeric
comparisons / aggregations are expected.

### `PIC S9(n)V99` (signed zoned decimal, DISPLAY) → `DecimalType(12, 2)`

Signed numeric fields with an implied decimal point (`V99`) use COBOL's
**zoned-decimal / DISPLAY** format.  In the ASCII data files the sign is
encoded as an **overpunch character** in the last byte:

| Last byte | Digit | Sign |
|---|---|---|
| `{` | 0 | + |
| `A`–`I` | 1–9 | + |
| `}` | 0 | − |
| `J`–`R` | 1–9 | − |

A pure Spark SQL expression (`_decode_signed_col`) built from chained
`F.when()` calls translates the overpunch byte into an explicit sign and
inserts the decimal point at the position indicated by the `V` clause.
This avoids Python UDF serialization overhead and keeps execution in the JVM.

**Example:** raw `00000001940{` → sign `+`, digits `000000019400`,
with `V99` → `+0000000194.00`.  The result is cast to
`DecimalType(12, 2)` (10 integer digits + 2 decimal digits).

This mapping is used for all five monetary fields in `CVACT01Y.cpy`:
`ACCT-CURR-BAL`, `ACCT-CREDIT-LIMIT`, `ACCT-CASH-CREDIT-LIMIT`,
`ACCT-CURR-CYC-CREDIT`, `ACCT-CURR-CYC-DEBIT`.

### `COMP-3` (packed decimal) → `DecimalType` *(not present in these copybooks)*

None of the three copybooks in scope use `COMP-3` (packed decimal).  If
encountered in other CardDemo copybooks, `COMP-3` fields would be handled as
follows:

- Each byte stores two BCD digits; the low nibble of the last byte carries
  the sign (`0xC` = positive, `0xD` = negative, `0xF` = unsigned).
- A `PIC S9(7)V99 COMP-3` field occupies `ceil((7+2+1)/2) = 5` bytes.
- The raw bytes must be decoded from binary (not ASCII text), so
  `spark.read.format("binaryFile")` or a custom InputFormat would be
  required instead of `spark.read.text()`.
- The decoded value would map to `DecimalType(9, 2)`.

### `COMP` / `COMP-4` (binary integer) → `LongType` / `IntegerType` *(not present)*

Binary integer fields are also absent from these copybooks.  If present:

- `PIC S9(4) COMP` → 2 bytes → `ShortType` or `IntegerType`
- `PIC S9(9) COMP` → 4 bytes → `IntegerType`
- `PIC S9(18) COMP` → 8 bytes → `LongType`

---

## Date Handling

Date fields (`ACCT-OPEN-DATE`, `ACCT-EXPIRAION-DATE`, `ACCT-REISSUE-DATE`,
`CARD-EXPIRAION-DATE`, `CUST-DOB-YYYYMMDD`) are declared as `PIC X(10)` in
the copybooks and stored as `YYYY-MM-DD` strings in the data files.

They are kept as `StringType` in the parsed DataFrames to avoid timezone
ambiguity.  Downstream consumers can cast to `DateType` with:

```python
F.to_date(F.col("ACCT_OPEN_DATE"), "yyyy-MM-dd")
```

---

## Byte-Offset Verification

The sum of all field lengths in each copybook matches the declared record
length:

| Copybook | Field lengths | RECLN |
|---|---|---|
| CVACT01Y | 11+1+12+12+12+10+10+10+12+12+10+10+178 | **300** |
| CUSTREC | 9+25+25+25+50+50+50+2+3+10+15+15+9+20+10+10+1+3+168 | **500** |
| CVACT02Y | 16+11+3+50+10+1+59 | **150** |

Each raw data file was verified to contain lines of exactly the expected
byte width (300, 500, and 150 respectively).

---

## Artifacts Produced

```
pyspark_copybook_parsers/
├── parsers/
│   ├── parse_acctdata.py      # CVACT01Y → acctdata.txt
│   ├── parse_custdata.py      # CUSTREC  → custdata.txt
│   └── parse_carddata.py      # CVACT02Y → carddata.txt
├── schemas/
│   ├── CVACT01Y_account_schema.json
│   ├── CUSTREC_customer_schema.json
│   └── CVACT02Y_card_schema.json
├── validation/
│   ├── validate_acctdata.py
│   ├── validate_custdata.py
│   └── validate_carddata.py
└── COPYBOOK_PARSING_NOTES.md  (this file)
```
