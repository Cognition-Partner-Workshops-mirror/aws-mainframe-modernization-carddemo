# COBOL Copybook Parsing Notes

## Overview

This document describes the type-mapping decisions and parsing strategy used to convert
COBOL copybook-defined fixed-width data files into PySpark DataFrames. Three copybook/data
pairs from the CardDemo application are covered:

| Copybook       | Record Name      | Record Length | Data File                      |
|----------------|------------------|---------------|--------------------------------|
| `CVACT01Y.cpy` | ACCOUNT-RECORD   | 300 bytes     | `app/data/ASCII/acctdata.txt`  |
| `CUSTREC.cpy`  | CUSTOMER-RECORD  | 500 bytes     | `app/data/ASCII/custdata.txt`  |
| `CVACT02Y.cpy` | CARD-RECORD      | 150 bytes     | `app/data/ASCII/carddata.txt`  |

---

## COBOL PIC Clause → PySpark Type Mappings

### 1. `PIC 9(n)` → `LongType` or `IntegerType`

**COBOL semantics:** Unsigned numeric display field. Each digit occupies one byte in
the ASCII representation (zoned decimal without sign).

**PySpark mapping:**
- `PIC 9(n)` where `n > 9` → `LongType` (to avoid 32-bit integer overflow)
- `PIC 9(n)` where `n ≤ 9` → `LongType` for IDs (e.g. `ACCT-ID`, `CUST-ID`) to ensure
  consistency, or `IntegerType` for small values like `CUST-FICO-CREDIT-SCORE` (PIC 9(03))
  and `CARD-CVV-CD` (PIC 9(03))

**Rationale:** COBOL `PIC 9(11)` can store values up to 99,999,999,999 which exceeds
Java's `Integer.MAX_VALUE` (2,147,483,647). Using `LongType` avoids overflow for large
account/customer identifiers.

**Conversion:** Direct `cast()` from the substring, since the ASCII representation is
already a valid numeric string (e.g., `"00000000001"` → `1`).

### 2. `PIC S9(m)V9(n)` → `DecimalType(m+n, n)`

**COBOL semantics:** Signed numeric display with an implied decimal point. In DISPLAY
format (no COMP/COMP-3 usage clause), the sign is stored as a **trailing overpunch** on
the last byte. The `V` is a virtual decimal point—it does not occupy storage.

**Storage size:** `m + n` bytes (one byte per digit; sign is embedded in the last byte).

**PySpark mapping:** `DecimalType(precision, scale)` where:
- `precision = m + n` (total number of digits)
- `scale = n` (number of digits after the implied decimal)

For example, `PIC S9(10)V99` → `DecimalType(12, 2)`.

**Rationale:** `DecimalType` preserves exact decimal precision, which is critical for
financial data (account balances, credit limits). Using `DoubleType` would introduce
floating-point rounding errors that are unacceptable for monetary values.

**Trailing Overpunch Decoding (ASCII convention):**

The last byte of a signed zoned-decimal field encodes both a digit and the sign:

| Character | Digit | Sign     |
|-----------|-------|----------|
| `{`       | 0     | Positive |
| `A`–`I`   | 1–9   | Positive |
| `}`       | 0     | Negative |
| `J`–`R`   | 1–9   | Negative |

Example: `00000001940{` → digits = `000000019400`, sign = positive → `+194.00`

**Implementation:** A Python UDF (`decode_signed_zoned_decimal`) in `cobol_parser_utils.py`
handles the overpunch decoding, then the result is cast to `DecimalType`.

### 3. `PIC X(n)` → `StringType`

**COBOL semantics:** Alphanumeric field. Each character occupies one byte. Fields are
right-padded with spaces to fill the declared length.

**PySpark mapping:** `StringType`, with `rtrim()` applied to strip trailing padding spaces.

**Rationale:** This is the natural mapping for COBOL alphanumeric fields. Date fields
(e.g., `ACCT-OPEN-DATE PIC X(10)`) are kept as strings because the copybook does not
enforce a date format—validation can be applied downstream.

### 4. `FILLER` → `StringType` (excluded from analytics)

**COBOL semantics:** Unnamed padding bytes used to align the record to a fixed length.
FILLER fields have no business meaning.

**PySpark mapping:** Parsed as `StringType` for completeness, then dropped from the
analytical DataFrame. Retained in the schema definition and JSON metadata for
documentation and round-trip fidelity.

---

## COMP-3 (Packed Decimal) Considerations

**Note:** The three copybooks analyzed (`CVACT01Y.cpy`, `CUSTREC.cpy`, `CVACT02Y.cpy`)
do **not** use `COMP-3` (packed decimal) storage. All numeric fields use the default
`DISPLAY` usage, where each digit occupies one byte.

If COMP-3 fields were encountered, the mapping would be:

| COBOL                | Storage         | PySpark              |
|----------------------|-----------------|----------------------|
| `PIC S9(m)V9(n) COMP-3` | `ceil((m+n+1)/2)` bytes | `DecimalType(m+n, n)` |

COMP-3 stores two digits per byte (BCD encoding) plus a trailing sign nibble. Parsing
COMP-3 from an ASCII flat file would require byte-level binary extraction rather than
string slicing. The utility module (`cobol_parser_utils.py`) currently handles only
DISPLAY format; COMP-3 support would require binary file reading (e.g., reading the file
in binary mode and unpacking nibbles).

---

## Byte Offset Calculations

Offsets are computed by cumulatively summing field lengths starting from byte 0. The
`V` (implied decimal) in `PIC S9(m)V9(n)` does **not** consume a byte—it is virtual.

### ACCOUNT-RECORD (300 bytes)

| Field                  | PIC Clause       | Offset | Length | Cumulative |
|------------------------|------------------|--------|--------|------------|
| ACCT-ID                | PIC 9(11)        | 0      | 11     | 11         |
| ACCT-ACTIVE-STATUS     | PIC X(01)        | 11     | 1      | 12         |
| ACCT-CURR-BAL          | PIC S9(10)V99    | 12     | 12     | 24         |
| ACCT-CREDIT-LIMIT      | PIC S9(10)V99    | 24     | 12     | 36         |
| ACCT-CASH-CREDIT-LIMIT | PIC S9(10)V99    | 36     | 12     | 48         |
| ACCT-OPEN-DATE         | PIC X(10)        | 48     | 10     | 58         |
| ACCT-EXPIRAION-DATE    | PIC X(10)        | 58     | 10     | 68         |
| ACCT-REISSUE-DATE      | PIC X(10)        | 68     | 10     | 78         |
| ACCT-CURR-CYC-CREDIT   | PIC S9(10)V99    | 78     | 12     | 90         |
| ACCT-CURR-CYC-DEBIT    | PIC S9(10)V99    | 90     | 12     | 102        |
| ACCT-ADDR-ZIP          | PIC X(10)        | 102    | 10     | 112        |
| ACCT-GROUP-ID          | PIC X(10)        | 112    | 10     | 122        |
| FILLER                 | PIC X(178)       | 122    | 178    | **300**    |

### CUSTOMER-RECORD (500 bytes)

| Field                    | PIC Clause   | Offset | Length | Cumulative |
|--------------------------|--------------|--------|--------|------------|
| CUST-ID                  | PIC 9(09)    | 0      | 9      | 9          |
| CUST-FIRST-NAME          | PIC X(25)    | 9      | 25     | 34         |
| CUST-MIDDLE-NAME         | PIC X(25)    | 34     | 25     | 59         |
| CUST-LAST-NAME           | PIC X(25)    | 59     | 25     | 84         |
| CUST-ADDR-LINE-1         | PIC X(50)    | 84     | 50     | 134        |
| CUST-ADDR-LINE-2         | PIC X(50)    | 134    | 50     | 184        |
| CUST-ADDR-LINE-3         | PIC X(50)    | 184    | 50     | 234        |
| CUST-ADDR-STATE-CD       | PIC X(02)    | 234    | 2      | 236        |
| CUST-ADDR-COUNTRY-CD     | PIC X(03)    | 236    | 3      | 239        |
| CUST-ADDR-ZIP            | PIC X(10)    | 239    | 10     | 249        |
| CUST-PHONE-NUM-1         | PIC X(15)    | 249    | 15     | 264        |
| CUST-PHONE-NUM-2         | PIC X(15)    | 264    | 15     | 279        |
| CUST-SSN                 | PIC 9(09)    | 279    | 9      | 288        |
| CUST-GOVT-ISSUED-ID      | PIC X(20)    | 288    | 20     | 308        |
| CUST-DOB-YYYYMMDD        | PIC X(10)    | 308    | 10     | 318        |
| CUST-EFT-ACCOUNT-ID      | PIC X(10)    | 318    | 10     | 328        |
| CUST-PRI-CARD-HOLDER-IND | PIC X(01)    | 328    | 1      | 329        |
| CUST-FICO-CREDIT-SCORE   | PIC 9(03)    | 329    | 3      | 332        |
| FILLER                   | PIC X(168)   | 332    | 168    | **500**    |

### CARD-RECORD (150 bytes)

| Field              | PIC Clause   | Offset | Length | Cumulative |
|--------------------|--------------|--------|--------|------------|
| CARD-NUM           | PIC X(16)    | 0      | 16     | 16         |
| CARD-ACCT-ID       | PIC 9(11)    | 16     | 11     | 27         |
| CARD-CVV-CD        | PIC 9(03)    | 27     | 3      | 30         |
| CARD-EMBOSSED-NAME | PIC X(50)    | 30     | 50     | 80         |
| CARD-EXPIRAION-DATE| PIC X(10)    | 80     | 10     | 90         |
| CARD-ACTIVE-STATUS | PIC X(01)    | 90     | 1      | 91         |
| FILLER             | PIC X(59)    | 91     | 59     | **150**    |

---

## Design Decisions & Notes

1. **Field names use underscores instead of hyphens:** COBOL uses hyphens in field names
   (e.g., `ACCT-CURR-BAL`), but PySpark column names with hyphens require backtick
   escaping. All field names are converted to use underscores (e.g., `ACCT_CURR_BAL`).

2. **Preserving original copybook typos:** The copybook contains `EXPIRAION` (missing 'T'
   in EXPIRATION). This is preserved in field names (`ACCT_EXPIRAION_DATE`,
   `CARD_EXPIRAION_DATE`) to maintain traceability to the original COBOL source.

3. **CARD-NUM kept as StringType:** Although `CARD-NUM` contains only digits (PIC X(16)),
   it is mapped to `StringType` rather than `LongType` to preserve leading zeros. Credit
   card numbers are identifiers, not quantities, and should not be treated as numeric.

4. **FILLER retained in schema, dropped from output:** FILLER fields are defined in the
   JSON schema for documentation completeness but are excluded from the analytical
   DataFrame and CSV output.

5. **No EBCDIC conversion needed:** The data files in `app/data/ASCII/` are already in
   ASCII encoding. The EBCDIC versions in `app/data/EBCDIC/` would require character set
   conversion (e.g., using `codecs` with `cp037` or `cp1140` encoding) before parsing.

6. **UDF vs. native Spark functions for overpunch:** A Python UDF is used for trailing
   overpunch decoding because Spark SQL does not have a built-in function for this
   mainframe-specific encoding. For production workloads at scale, this UDF could be
   reimplemented as a Scala/Java UDF for better performance, or the overpunch decoding
   could be done as a pre-processing step.

7. **Decimal precision for financial fields:** All `PIC S9(10)V99` fields are mapped to
   `DecimalType(12, 2)` — 12 total digits, 2 decimal places. This matches the COBOL
   precision exactly and avoids floating-point rounding errors inherent in DoubleType.
