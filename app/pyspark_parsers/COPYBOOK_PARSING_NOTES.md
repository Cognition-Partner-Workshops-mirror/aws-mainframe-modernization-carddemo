# COBOL Copybook → PySpark Type-Mapping Notes

This document describes how COBOL PIC clauses from the CardDemo copybooks were
mapped to PySpark data types, including special handling for signed
zoned-decimal fields.

---

## 1. Copybooks Analysed

| Copybook | Record Name | Record Length | Data File |
|---|---|---|---|
| `CVACT01Y.cpy` | `ACCOUNT-RECORD` | 300 bytes | `acctdata.txt` |
| `CUSTREC.cpy` | `CUSTOMER-RECORD` | 500 bytes | `custdata.txt` |
| `CVACT02Y.cpy` | `CARD-RECORD` | 150 bytes | `carddata.txt` |

---

## 2. General Type-Mapping Rules

| COBOL PIC Clause | COBOL Category | PySpark Type | Rationale |
|---|---|---|---|
| `PIC 9(n)` | Unsigned numeric display | `LongType` | Pure digit string; safe to cast directly. `LongType` chosen over `IntegerType` because IDs like `ACCT-ID` are 11 digits, exceeding `int32` range. |
| `PIC X(n)` | Alphanumeric | `StringType` | Direct 1:1 mapping; trailing spaces are trimmed after extraction. |
| `PIC S9(n)V99` | Signed numeric display with implied decimal | `DecimalType(n+2, 2)` | The `S` sign is encoded as a *sign overpunch* on the last byte. The `V` is an implied (virtual) decimal point — it occupies no physical storage. The field uses `n+2` total digits with 2 fractional digits. `DecimalType` preserves exact decimal arithmetic, avoiding `float`/`double` rounding. |
| `FILLER` | Padding | `StringType` (dropped) | Filler bytes pad the record to its declared length. They are extracted during parsing but **excluded** from the final DataFrame. |

### Why not `IntegerType` for `PIC 9(n)`?

`PIC 9(11)` can hold values up to 99,999,999,999 which exceeds the signed
32-bit integer maximum of 2,147,483,647.  `LongType` (64-bit) accommodates
all values.

### Why `DecimalType` instead of `DoubleType` for monetary fields?

Financial data requires exact decimal representation.  `DoubleType` (IEEE 754)
introduces binary floating-point rounding errors (e.g., `0.1 + 0.2 ≠ 0.3`).
`DecimalType(12, 2)` mirrors the COBOL precision exactly: 10 integer digits
plus 2 fractional digits.

---

## 3. Sign-Overpunch Decoding (PIC S9 DISPLAY Format)

### Background

In IBM mainframe COBOL, `PIC S9(n)` fields in `USAGE DISPLAY` (the default)
store the algebraic sign by *overpunching* the zone nibble of the **last byte**.
When data is exported from EBCDIC to ASCII, the overpunch characters are
preserved using the following conventional mapping:

| Last-byte Character | Digit Value | Sign |
|---|---|---|
| `{` | 0 | + |
| `A` | 1 | + |
| `B` | 2 | + |
| `C` | 3 | + |
| `D` | 4 | + |
| `E` | 5 | + |
| `F` | 6 | + |
| `G` | 7 | + |
| `H` | 8 | + |
| `I` | 9 | + |
| `}` | 0 | − |
| `J` | 1 | − |
| `K` | 2 | − |
| `L` | 3 | − |
| `M` | 4 | − |
| `N` | 5 | − |
| `O` | 6 | − |
| `P` | 7 | − |
| `Q` | 8 | − |
| `R` | 9 | − |

### Decoding Algorithm (implemented in `parse_acctdata.py`)

```text
1. Extract the last character of the raw field.
2. Look it up in the positive or negative overpunch map.
3. Replace the last character with the resolved digit.
4. Prepend '-' if the map was negative.
5. Insert the implied decimal point at position (length − scale).
6. Cast the resulting string to DecimalType.
```

### Fields requiring sign-overpunch decoding

Only `CVACT01Y.cpy` (ACCOUNT-RECORD) contains signed numeric fields:

- `ACCT-CURR-BAL` — PIC S9(10)V99
- `ACCT-CREDIT-LIMIT` — PIC S9(10)V99
- `ACCT-CASH-CREDIT-LIMIT` — PIC S9(10)V99
- `ACCT-CURR-CYC-CREDIT` — PIC S9(10)V99
- `ACCT-CURR-CYC-DEBIT` — PIC S9(10)V99

The other two copybooks (`CUSTREC.cpy`, `CVACT02Y.cpy`) use only `PIC 9(n)` or
`PIC X(n)`, so no sign decoding is needed.

---

## 4. COMP-3 (Packed Decimal) — Not Applicable Here

`COMP-3` (packed BCD) stores two digits per byte with the sign in the trailing
nibble.  **None of the three CardDemo copybooks use COMP-3.**  If COMP-3 fields
were present, the recommended mapping would be:

| COBOL | PySpark | Notes |
|---|---|---|
| `PIC S9(n)V99 COMP-3` | `DecimalType(n+2, 2)` | Requires unpacking: each byte contributes two BCD digits except the last byte whose low nibble is the sign (C=+, D=−, F=unsigned). Physical storage = `ceil((n + 2 + 1) / 2)` bytes. |

---

## 5. CARD-NUM Kept as StringType

Although `CARD-NUM` looks numeric, it is declared `PIC X(16)` (alphanumeric)
in the copybook.  It is intentionally kept as `StringType` to:

- Preserve leading zeros (e.g., `0500024453765740`)
- Match the copybook's declared type
- Avoid numeric overflow (16-digit numbers exceed `LongType` range)

---

## 6. Date Fields Kept as StringType

All date fields (`ACCT-OPEN-DATE`, `ACCT-EXPIRAION-DATE`, `ACCT-REISSUE-DATE`,
`CARD-EXPIRAION-DATE`, `CUST-DOB-YYYYMMDD`) are declared `PIC X(10)` and
stored as `YYYY-MM-DD` strings.  They are kept as `StringType` rather than
cast to `DateType` because:

- The copybook declares them as alphanumeric (`PIC X`), not numeric
- Downstream consumers may expect the original string format
- Casting to `DateType` can be done as a post-processing step if needed

---

## 7. Copybook Typos Preserved

The original copybooks contain the misspelling `EXPIRAION` (missing the 't'
in "EXPIRATION").  The generated field names and JSON schemas preserve this
spelling to maintain traceability back to the source copybook definitions.

---

## 8. Validation Strategy

Each parser script includes a `validate()` function that:

1. **Row-count comparison** — Verifies that the parsed DataFrame has the same
   number of rows as lines in the raw text file.
2. **Sample-value inspection** — Prints the first 5 rows with all field values
   for manual review.
3. **Null-count audit** — Reports the number of NULL values per column to
   detect parsing failures (e.g., bad sign-overpunch characters, unexpected
   field-width misalignment).

Validation output is written to `validation_<filename>.txt` alongside the
parser scripts.
