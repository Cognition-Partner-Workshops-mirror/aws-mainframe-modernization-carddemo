# COBOL Copybook Parsing Notes

## Overview

This directory contains PySpark scripts, JSON schemas, and validation tools for parsing
three COBOL copybook-defined fixed-width data files from the CardDemo application.

| Copybook       | Record Layout     | Length | Data File        |
|----------------|-------------------|--------|------------------|
| `CVACT01Y.cpy` | ACCOUNT-RECORD    | 300    | `acctdata.txt`   |
| `CUSTREC.cpy`  | CUSTOMER-RECORD   | 500    | `custdata.txt`   |
| `CVACT02Y.cpy` | CARD-RECORD       | 150    | `carddata.txt`   |

## Type-Mapping Decisions

### PIC X(n) → StringType

All alphanumeric COBOL fields (`PIC X(n)`) map to PySpark `StringType`. Values are
right-padded with spaces in the fixed-width file; the parsing scripts apply `trim()` to
remove trailing whitespace.

**Fields affected:** All date fields (e.g. `ACCT-OPEN-DATE`), name fields, address fields,
status flags, ZIP codes, phone numbers, government IDs.

**Rationale:** `PIC X` is a general-purpose alphanumeric type with no numeric semantics.
`StringType` preserves the original content without data loss.

### PIC 9(n) — Unsigned Display Numeric

Unsigned numeric fields are mapped based on their semantic purpose:

| Mapping Target   | Fields                                                         | Rationale                                                  |
|------------------|----------------------------------------------------------------|------------------------------------------------------------|
| **StringType**   | `ACCT-ID`, `CUST-ID`, `CUST-SSN`, `CARD-ACCT-ID`, `CARD-CVV-CD`, `CARD-NUM` (PIC X but numeric content) | Identifiers and codes where leading zeros are meaningful    |
| **IntegerType**  | `CUST-FICO-CREDIT-SCORE`                                      | True numeric value used in calculations/comparisons         |

**Rationale:** COBOL `PIC 9(n)` in DISPLAY format stores digits as ASCII characters
(one byte per digit). For identifiers like account IDs and SSNs, leading zeros carry
meaning (e.g., `000000001` ≠ `1`), so `StringType` preserves fidelity. For numeric
values like credit scores, `IntegerType` enables arithmetic operations.

### PIC S9(10)V99 → DecimalType(12, 2)

Signed numeric fields with implied decimal points map to PySpark `DecimalType(12, 2)`.

**Fields affected:** `ACCT-CURR-BAL`, `ACCT-CREDIT-LIMIT`, `ACCT-CASH-CREDIT-LIMIT`,
`ACCT-CURR-CYC-CREDIT`, `ACCT-CURR-CYC-DEBIT`.

**Breakdown of the PIC clause:**
- `S` — signed (positive or negative)
- `9(10)` — 10 integer digits
- `V` — implied decimal point (not stored in the data)
- `99` — 2 decimal digits

**Total storage:** 12 bytes in DISPLAY (zoned decimal) format.

**DecimalType(12, 2)** provides 12 total digits of precision with 2 decimal places,
exactly matching the COBOL definition. `DecimalType` is preferred over `DoubleType`
for financial data to avoid floating-point rounding errors.

### COMP-3 (Packed Decimal) — Not Present but Documented

The three copybooks analyzed here use only DISPLAY format (zoned decimal). No `COMP-3`
(packed decimal) fields are present. However, for reference:

| COBOL Usage | Storage            | PySpark Mapping     | Notes                              |
|-------------|--------------------|---------------------|------------------------------------|
| COMP-3      | Packed BCD         | `DecimalType(p, s)` | Each byte stores 2 digits; last nibble is sign |
| DISPLAY     | Zoned decimal      | `DecimalType(p, s)` | One byte per digit; sign in last byte overpunch |

If future copybooks contain `COMP-3` fields, the data must be read as binary and
decoded using packed-decimal logic (nibble extraction), **not** as text.

### FILLER → StringType (excluded from output)

COBOL `FILLER` fields are reserved padding. They are extracted as `StringType` for
completeness in the schema but carry no business meaning. Downstream consumers should
ignore these fields.

## Zoned Decimal Sign Overpunch Convention

The data files are ASCII conversions of EBCDIC mainframe records. Signed numeric fields
use the **EBCDIC overpunch** convention where the sign is encoded in the last byte:

| Last Byte | Digit | Sign     |
|-----------|-------|----------|
| `{`       | 0     | Positive |
| `A`–`I`   | 1–9   | Positive |
| `}`       | 0     | Negative |
| `J`–`R`   | 1–9   | Negative |

**Example:** `00000001940{` → digits `000000019400`, sign `+`, with `V99` → **+194.00**

The `cobol_utils.py` module implements this decoding via the `decode_signed_zoned_decimal()`
function, which is registered as a PySpark UDF for DataFrame column transformations.

## Byte Offset Verification

All byte offsets were manually verified against the copybook definitions and confirmed
by comparing substring extractions against raw file content.

### CVACT01Y.cpy — ACCOUNT-RECORD (300 bytes)

| Field                  | PIC           | Offset | Length | Running Total |
|------------------------|---------------|--------|--------|---------------|
| ACCT-ID                | 9(11)         | 0      | 11     | 11            |
| ACCT-ACTIVE-STATUS     | X(01)         | 11     | 1      | 12            |
| ACCT-CURR-BAL          | S9(10)V99     | 12     | 12     | 24            |
| ACCT-CREDIT-LIMIT      | S9(10)V99     | 24     | 12     | 36            |
| ACCT-CASH-CREDIT-LIMIT | S9(10)V99     | 36     | 12     | 48            |
| ACCT-OPEN-DATE         | X(10)         | 48     | 10     | 58            |
| ACCT-EXPIRAION-DATE    | X(10)         | 58     | 10     | 68            |
| ACCT-REISSUE-DATE      | X(10)         | 68     | 10     | 78            |
| ACCT-CURR-CYC-CREDIT   | S9(10)V99     | 78     | 12     | 90            |
| ACCT-CURR-CYC-DEBIT    | S9(10)V99     | 90     | 12     | 102           |
| ACCT-ADDR-ZIP          | X(10)         | 102    | 10     | 112           |
| ACCT-GROUP-ID          | X(10)         | 112    | 10     | 122           |
| FILLER                 | X(178)        | 122    | 178    | **300**       |

### CUSTREC.cpy — CUSTOMER-RECORD (500 bytes)

| Field                    | PIC       | Offset | Length | Running Total |
|--------------------------|-----------|--------|--------|---------------|
| CUST-ID                  | 9(09)     | 0      | 9      | 9             |
| CUST-FIRST-NAME          | X(25)     | 9      | 25     | 34            |
| CUST-MIDDLE-NAME         | X(25)     | 34     | 25     | 59            |
| CUST-LAST-NAME           | X(25)     | 59     | 25     | 84            |
| CUST-ADDR-LINE-1         | X(50)     | 84     | 50     | 134           |
| CUST-ADDR-LINE-2         | X(50)     | 134    | 50     | 184           |
| CUST-ADDR-LINE-3         | X(50)     | 184    | 50     | 234           |
| CUST-ADDR-STATE-CD       | X(02)     | 234    | 2      | 236           |
| CUST-ADDR-COUNTRY-CD     | X(03)     | 236    | 3      | 239           |
| CUST-ADDR-ZIP            | X(10)     | 239    | 10     | 249           |
| CUST-PHONE-NUM-1         | X(15)     | 249    | 15     | 264           |
| CUST-PHONE-NUM-2         | X(15)     | 264    | 15     | 279           |
| CUST-SSN                 | 9(09)     | 279    | 9      | 288           |
| CUST-GOVT-ISSUED-ID      | X(20)     | 288    | 20     | 308           |
| CUST-DOB-YYYYMMDD        | X(10)     | 308    | 10     | 318           |
| CUST-EFT-ACCOUNT-ID      | X(10)     | 318    | 10     | 328           |
| CUST-PRI-CARD-HOLDER-IND | X(01)     | 328    | 1      | 329           |
| CUST-FICO-CREDIT-SCORE   | 9(03)     | 329    | 3      | 332           |
| FILLER                   | X(168)    | 332    | 168    | **500**       |

### CVACT02Y.cpy — CARD-RECORD (150 bytes)

| Field               | PIC       | Offset | Length | Running Total |
|---------------------|-----------|--------|--------|---------------|
| CARD-NUM            | X(16)     | 0      | 16     | 16            |
| CARD-ACCT-ID        | 9(11)     | 16     | 11     | 27            |
| CARD-CVV-CD         | 9(03)     | 27     | 3      | 30            |
| CARD-EMBOSSED-NAME  | X(50)     | 30     | 50     | 80            |
| CARD-EXPIRAION-DATE | X(10)     | 80     | 10     | 90            |
| CARD-ACTIVE-STATUS  | X(01)     | 90     | 1      | 91            |
| FILLER              | X(59)     | 91     | 59     | **150**       |

## Directory Structure

```
copybook_parsing/
├── COPYBOOK_PARSING_NOTES.md        # This document
├── schemas/
│   ├── CVACT01Y_schema.json          # Account record JSON schema
│   ├── CUSTREC_schema.json           # Customer record JSON schema
│   └── CVACT02Y_schema.json          # Card record JSON schema
├── scripts/
│   ├── cobol_utils.py                # Shared overpunch decoding utilities
│   ├── parse_acctdata.py             # PySpark parser for acctdata.txt
│   ├── parse_custdata.py             # PySpark parser for custdata.txt
│   └── parse_carddata.py             # PySpark parser for carddata.txt
└── validation/
    ├── validate_all.py               # Cross-file validation script
    └── validation_report.txt         # Generated validation output
```

## Running the Scripts

**Prerequisites:** Python 3.8+, PySpark 3.x or 4.x, Java 8+/11+/17+.

```bash
# Install PySpark
pip install pyspark

# Parse individual data files
python copybook_parsing/scripts/parse_acctdata.py
python copybook_parsing/scripts/parse_custdata.py
python copybook_parsing/scripts/parse_carddata.py

# Run full validation suite
python copybook_parsing/validation/validate_all.py
```

Each parser writes a Parquet file to `copybook_parsing/output/` and prints the schema,
row count, and sample rows to stdout. The validation script produces a detailed report
comparing parsed values against raw file content.
