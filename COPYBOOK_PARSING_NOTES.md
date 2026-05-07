# COBOL Copybook Parsing Notes

## Overview

This document describes the type-mapping decisions and parsing logic used to convert
COBOL copybook record layouts into PySpark DataFrames for the CardDemo application.

Three copybooks are processed:

| Copybook | Record | Length | Data File |
|----------|--------|--------|-----------|
| `CVACT01Y.cpy` | ACCOUNT-RECORD | 300 bytes | `acctdata.txt` |
| `CUSTREC.cpy` | CUSTOMER-RECORD | 500 bytes | `custdata.txt` |
| `CVACT02Y.cpy` | CARD-RECORD | 150 bytes | `carddata.txt` |

---

## Type-Mapping Decisions

### PIC 9(n) → LongType / IntegerType

Unsigned numeric fields (`PIC 9(n)`) are stored as display (zoned) numerics — one
ASCII digit per byte with no sign encoding.

- **PIC 9(11)** → `LongType` (exceeds 32-bit int range)
- **PIC 9(09)** → `LongType` (SSN and IDs can exceed IntegerType's safe usage for leading zeros)
- **PIC 9(03)** → `IntegerType` (small values like CVV, FICO score)

### PIC X(n) → StringType

Alphanumeric fields are mapped directly to `StringType`. Values are right-padded with
spaces in the fixed-width file and trimmed during parsing.

### PIC S9(n)V99 → DecimalType(precision, scale)

Signed numeric fields with implied decimal point use **zoned decimal** representation
in the ASCII data files. The sign is encoded in the **last byte** using the standard
EBCDIC-to-ASCII overpunch mapping:

| Last Char | Sign | Digit |
|-----------|------|-------|
| `{` | + | 0 |
| `A`–`I` | + | 1–9 |
| `}` | - | 0 |
| `J`–`R` | - | 1–9 |

For `PIC S9(10)V99`:
- Total length: 12 bytes (10 integer digits + 2 decimal digits, sign in last byte)
- PySpark type: `DecimalType(12, 2)`
- The `V` (implied decimal point) means no actual decimal character exists in the data;
  the last 2 digits represent cents

**Example**: `00000001940{` → digits = `000000019400`, sign = positive → 194.00

### COMP-3 (Packed Decimal) → DecimalType

COMP-3 fields are **not present** in these three copybooks. If encountered in other
CardDemo copybooks, the mapping would be:

- Each byte stores two BCD digits (4 bits each)
- The last nibble encodes the sign (C=positive, D=negative, F=unsigned)
- Storage: `ceil((n + 1) / 2)` bytes for `PIC S9(n)V99 COMP-3`
- PySpark type: `DecimalType(precision, scale)`

### FILLER → StringType (excluded from output)

FILLER fields are parsed to maintain correct byte offsets but excluded from the
final DataFrame display and validation output.

---

## Fixed-Width Parsing Strategy

1. **Read as text**: Each line in the ASCII data file represents one complete record
2. **Substring extraction**: Fields are extracted using byte offset and length from
   the copybook layout
3. **Type conversion**: Applied per field type:
   - Numeric: `int()` on raw substring
   - Signed decimal: Overpunch decode + implied decimal division
   - String: `strip()` to remove padding
4. **DataFrame creation**: Parsed dictionaries are converted to a PySpark DataFrame
   with an explicit schema

---

## Data File Format

The ASCII data files use:
- **Fixed record length** (no delimiters between fields)
- **Newline-terminated** records (LF)
- **Space-padded** alphanumeric fields (right-padded)
- **Zero-padded** numeric fields (left-padded)
- **Overpunch-encoded** signed fields (last byte carries sign)

---

## Validation Approach

Each parser produces a JSON validation file containing:
- Source file path and associated copybook
- Record length in bytes
- Raw line count from the file
- Parsed row count from the DataFrame
- Boolean flag indicating count match
- First 5 parsed records as sample data for manual verification

---

## Field Offset Verification

### ACCOUNT-RECORD (300 bytes)
```
ACCT-ID                 :   0 + 11  =  11
ACCT-ACTIVE-STATUS      :  11 +  1  =  12
ACCT-CURR-BAL           :  12 + 12  =  24
ACCT-CREDIT-LIMIT       :  24 + 12  =  36
ACCT-CASH-CREDIT-LIMIT  :  36 + 12  =  48
ACCT-OPEN-DATE          :  48 + 10  =  58
ACCT-EXPIRAION-DATE     :  58 + 10  =  68
ACCT-REISSUE-DATE       :  68 + 10  =  78
ACCT-CURR-CYC-CREDIT    :  78 + 12  =  90
ACCT-CURR-CYC-DEBIT     :  90 + 12  = 102
ACCT-ADDR-ZIP           : 102 + 10  = 112
ACCT-GROUP-ID           : 112 + 10  = 122
FILLER                  : 122 +178  = 300  ✓
```

### CUSTOMER-RECORD (500 bytes)
```
CUST-ID                 :   0 +  9  =   9
CUST-FIRST-NAME         :   9 + 25  =  34
CUST-MIDDLE-NAME        :  34 + 25  =  59
CUST-LAST-NAME          :  59 + 25  =  84
CUST-ADDR-LINE-1        :  84 + 50  = 134
CUST-ADDR-LINE-2        : 134 + 50  = 184
CUST-ADDR-LINE-3        : 184 + 50  = 234
CUST-ADDR-STATE-CD      : 234 +  2  = 236
CUST-ADDR-COUNTRY-CD    : 236 +  3  = 239
CUST-ADDR-ZIP           : 239 + 10  = 249
CUST-PHONE-NUM-1        : 249 + 15  = 264
CUST-PHONE-NUM-2        : 264 + 15  = 279
CUST-SSN                : 279 +  9  = 288
CUST-GOVT-ISSUED-ID     : 288 + 20  = 308
CUST-DOB-YYYYMMDD       : 308 + 10  = 318
CUST-EFT-ACCOUNT-ID     : 318 + 10  = 328
CUST-PRI-CARD-HOLDER-IND: 328 +  1  = 329
CUST-FICO-CREDIT-SCORE  : 329 +  3  = 332
FILLER                  : 332 +168  = 500  ✓
```

### CARD-RECORD (150 bytes)
```
CARD-NUM                :   0 + 16  =  16
CARD-ACCT-ID            :  16 + 11  =  27
CARD-CVV-CD             :  27 +  3  =  30
CARD-EMBOSSED-NAME      :  30 + 50  =  80
CARD-EXPIRAION-DATE     :  80 + 10  =  90
CARD-ACTIVE-STATUS      :  90 +  1  =  91
FILLER                  :  91 + 59  = 150  ✓
```

---

## References

- [IBM COBOL PIC Clause Documentation](https://www.ibm.com/docs/en/cobol-zos/6.4?topic=clause-picture)
- [Zoned Decimal / Overpunch Encoding](https://www.ibm.com/docs/en/i/7.5?topic=data-zoned-decimal-format)
- AWS CardDemo Application: `app/cpy/` directory
