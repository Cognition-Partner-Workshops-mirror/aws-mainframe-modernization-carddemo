# COBOL Copybook Parsing Notes

## Overview

This directory contains PySpark scripts, JSON schemas, and validation output for
parsing three CardDemo fixed-width data files using layouts derived from COBOL
copybooks.

| Copybook | Data File | Record Length | Record Name |
|---|---|---|---|
| `CVACT01Y.cpy` | `acctdata.txt` | 300 bytes | ACCOUNT-RECORD |
| `CUSTREC.cpy` | `custdata.txt` | 500 bytes | CUSTOMER-RECORD |
| `CVACT02Y.cpy` | `carddata.txt` | 150 bytes | CARD-RECORD |

---

## Type-Mapping Decisions

### PIC X(n) &rarr; `StringType`

All alphanumeric COBOL fields (`PIC X(n)`) are mapped to PySpark `StringType`.
Values are right-trimmed to remove padding spaces. No further transformation is
applied because these fields carry free-form text (names, addresses, dates stored
as strings, status flags).

### PIC 9(n) &rarr; `LongType` or `IntegerType`

Unsigned numeric display fields are cast to `LongType` when the precision exceeds
9 digits (e.g. `PIC 9(11)` for account and card-account IDs, `PIC 9(09)` for
customer IDs and SSNs) and to `IntegerType` for smaller fields (e.g. `PIC 9(03)`
for CVV codes and FICO scores). The choice avoids integer overflow that would
occur with `IntegerType` on 11-digit values.

### PIC S9(n)V99 &rarr; `DecimalType(n+2, 2)`

Signed numeric fields with an implied decimal point (`V99`) appear only in
`CVACT01Y.cpy` (balances, limits, cycle amounts). These are mapped to
`DecimalType(12, 2)`:

- **S (sign):** In the ASCII export the sign is encoded as an EBCDIC-style
  zoned-decimal *trailing overpunch* on the last byte of the field:
  - Positive: `{` = 0, `A`..`I` = 1..9
  - Negative: `}` = 0, `J`..`R` = 1..9
  
  A PySpark UDF (`decode_signed_numeric`) decodes the overpunch character, strips
  the sign, and reconstructs the numeric value.

- **V (implied decimal):** COBOL's `V` does not occupy a byte in the data;
  instead the last two digits of the field represent cents. The UDF inserts the
  decimal point at the correct position (e.g., `00000001940{` &rarr; `194.00`).

- **DecimalType vs. DoubleType:** `DecimalType` is chosen over `DoubleType` to
  preserve exact decimal precision for financial amounts.

### COMP-3 (Packed Decimal) &rarr; `DecimalType`

No COMP-3 fields appear in the three copybooks processed here. If COMP-3 fields
were encountered, each would occupy `ceil((n+1)/2)` bytes in binary-packed BCD
format and would be mapped to `DecimalType` with appropriate precision/scale. A
byte-level unpacking routine (reading nibbles) would be required instead of the
text-based substring approach used for display-numeric fields.

### FILLER Fields

Every copybook ends with a `FILLER PIC X(nnn)` that pads the record to its
declared length. FILLER columns are extracted during parsing to confirm total
record width but are dropped from the final DataFrame and validation output since
they carry no business data.

---

## Zoned-Decimal Overpunch Reference

The data files are ASCII exports of EBCDIC fixed-width records. COBOL stores the
sign of a `PIC S9(...)` field in the *zone nibble* of the last byte. After
EBCDIC-to-ASCII conversion the trailing byte becomes one of these characters:

| Last Char | Digit | Sign |
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
| `}` | 0 | - |
| `J` | 1 | - |
| `K` | 2 | - |
| `L` | 3 | - |
| `M` | 4 | - |
| `N` | 5 | - |
| `O` | 6 | - |
| `P` | 7 | - |
| `Q` | 8 | - |
| `R` | 9 | - |

---

## Byte-Offset Verification

Each schema JSON includes the byte offset of every field. The offsets were
validated by confirming:

- **CVACT01Y:** 11+1+12+12+12+10+10+10+12+12+10+10+178 = **300**
- **CUSTREC:** 9+25+25+25+50+50+50+2+3+10+15+15+9+20+10+10+1+3+168 = **500**
- **CVACT02Y:** 16+11+3+50+10+1+59 = **150**

---

## Validation Summary

All three parsers were executed against the feed files with the following results:

| File | Raw Lines | Parsed Rows | Match |
|---|---|---|---|
| `acctdata.txt` | 50 | 50 | Yes |
| `custdata.txt` | 50 | 50 | Yes |
| `carddata.txt` | 50 | 50 | Yes |

Sample rows for each file are captured in the `validation/` directory as JSON
files for downstream comparison.

---

## Directory Structure

```
copybook_parsing/
  COPYBOOK_PARSING_NOTES.md    # This file
  schemas/
    CVACT01Y_schema.json       # Account record JSON schema
    CUSTREC_schema.json        # Customer record JSON schema
    CVACT02Y_schema.json       # Card record JSON schema
  scripts/
    parse_acctdata.py          # PySpark parser for acctdata.txt
    parse_custdata.py          # PySpark parser for custdata.txt
    parse_carddata.py          # PySpark parser for carddata.txt
  validation/
    acctdata_validation.json   # Row-count + sample validation for accounts
    custdata_validation.json   # Row-count + sample validation for customers
    carddata_validation.json   # Row-count + sample validation for cards
```
