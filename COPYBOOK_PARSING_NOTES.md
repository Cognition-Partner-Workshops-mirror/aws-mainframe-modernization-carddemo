# COBOL Copybook → PySpark Type-Mapping Notes

This document describes the decisions made when converting COBOL copybook
record layouts to PySpark DataFrame schemas for the CardDemo application.

## Copybooks Processed

| Copybook | Record Name | Length | Data File |
|---|---|---|---|
| `CVACT01Y.cpy` | ACCOUNT-RECORD | 300 bytes | `acctdata.txt` |
| `CUSTREC.cpy`  | CUSTOMER-RECORD | 500 bytes | `custdata.txt` |
| `CVACT02Y.cpy` | CARD-RECORD | 150 bytes | `carddata.txt` |

---

## 1. General Approach

Each data file uses **fixed-width records** where every line is exactly the
record length specified in the copybook (300, 500, or 150 bytes respectively).
PySpark reads each line via `spark.read.text()` and fields are extracted with
`substring()` at the byte offsets derived from the cumulative PIC clause widths.

---

## 2. PIC Clause → PySpark Type Mapping

### 2.1 `PIC X(n)` — Alphanumeric Fields → `StringType`

COBOL `PIC X(n)` fields store `n` bytes of arbitrary character data.
They map directly to PySpark `StringType`. After extraction, trailing spaces
are stripped with `trim()` since COBOL right-pads alphanumeric fields with
spaces.

**Date fields** (`ACCT-OPEN-DATE`, `CUST-DOB-YYYYMMDD`, etc.) are declared as
`PIC X(10)` in the copybooks. We keep them as `StringType` rather than casting
to `DateType` because:
- The copybook defines them as character data, not numeric dates.
- Different environments may use varying date formats; keeping them as strings
  avoids silent parse failures.
- Downstream consumers can cast to `DateType` with an explicit format when the
  format is validated.

### 2.2 `PIC 9(n)` — Unsigned Numeric (DISPLAY) → `LongType` or `IntegerType`

COBOL `PIC 9(n)` stores `n` digits in character (DISPLAY) format — one ASCII
byte per digit. Fields are cast to:
- **`LongType`** when `n > 9` (e.g. `PIC 9(11)` for account/card IDs) to
  avoid integer overflow.
- **`IntegerType`** when `n ≤ 9` and values fit within 32-bit range
  (e.g. `PIC 9(03)` for CVV codes and FICO scores).

**Special consideration — `CARD-NUM` (`PIC X(16)`):** Although card numbers
are all-digit data in practice, the copybook declares them as `PIC X(16)`
(alphanumeric), so they are kept as `StringType`. This also preserves leading
zeros that would be lost in a numeric cast.

**Special consideration — `CUST-SSN` (`PIC 9(09)`):** SSNs are stored as
9-digit unsigned integers. We map to `LongType` to preserve leading zeros in
the numeric representation. Downstream consumers should zero-pad if displaying
as a formatted string (e.g. `lpad(col, 9, '0')`).

### 2.3 `PIC S9(n)V99` — Signed Numeric with Implied Decimal → `DecimalType(n+2, 2)`

This is the most complex mapping. COBOL `PIC S9(10)V99` means:
- **S** — the field carries a sign (positive or negative).
- **9(10)** — 10 integer digits.
- **V** — an *implied* decimal point (occupies no storage).
- **99** — 2 fractional digits.

Total storage: **12 bytes** (10 + 2 digits in DISPLAY format).

#### 2.3.1 Sign Encoding — Trailing Overpunch

In IBM mainframe COBOL (and this CardDemo dataset), the sign is embedded in the
**last byte** of the field using the EBCDIC zoned-decimal convention, even when
the data has been converted to ASCII. The last character encodes both a digit
value and a sign:

| Digit | Positive | Negative |
|-------|----------|----------|
| 0     | `{`      | `}`      |
| 1     | `A`      | `J`      |
| 2     | `B`      | `K`      |
| 3     | `C`      | `L`      |
| 4     | `D`      | `M`      |
| 5     | `E`      | `N`      |
| 6     | `F`      | `O`      |
| 7     | `G`      | `P`      |
| 8     | `H`      | `Q`      |
| 9     | `I`      | `R`      |

**Example:** The raw bytes `00000001940{` decode as follows:
1. Leading digits: `00000001940`
2. Last character `{` → digit `0`, sign positive
3. Full digit string: `000000019400`
4. Insert implied decimal (V99): `0000000194.00`
5. Apply sign: **+194.00**

#### 2.3.2 PySpark Implementation

A Python UDF (`decode_signed_numeric`) handles this decoding:
1. Looks up the trailing character in the overpunch table.
2. Reconstructs the full digit string.
3. Inserts the implied decimal point.
4. Returns a `Decimal` value with the correct sign.

The UDF returns `DecimalType(12, 2)` — 12 total digits with 2 after the
decimal point — matching the COBOL precision exactly. We chose `DecimalType`
over `DoubleType` to avoid floating-point rounding errors on financial data.

### 2.4 `FILLER` — Padding → Dropped

Every copybook ends with a `FILLER` field that pads the record to its declared
length. These bytes carry no business data and are excluded from the final
PySpark DataFrames.

---

## 3. Per-Copybook Field Mapping Summary

### 3.1 CVACT01Y.cpy — ACCOUNT-RECORD (300 bytes)

| # | COBOL Field | PIC | Offset | Len | PySpark Type | Notes |
|---|---|---|---|---|---|---|
| 1 | ACCT-ID | 9(11) | 0 | 11 | LongType | Unsigned display numeric |
| 2 | ACCT-ACTIVE-STATUS | X(01) | 11 | 1 | StringType | Flag field |
| 3 | ACCT-CURR-BAL | S9(10)V99 | 12 | 12 | DecimalType(12,2) | Signed w/ overpunch |
| 4 | ACCT-CREDIT-LIMIT | S9(10)V99 | 24 | 12 | DecimalType(12,2) | Signed w/ overpunch |
| 5 | ACCT-CASH-CREDIT-LIMIT | S9(10)V99 | 36 | 12 | DecimalType(12,2) | Signed w/ overpunch |
| 6 | ACCT-OPEN-DATE | X(10) | 48 | 10 | StringType | YYYY-MM-DD in data |
| 7 | ACCT-EXPIRAION-DATE | X(10) | 58 | 10 | StringType | Typo preserved |
| 8 | ACCT-REISSUE-DATE | X(10) | 68 | 10 | StringType | YYYY-MM-DD in data |
| 9 | ACCT-CURR-CYC-CREDIT | S9(10)V99 | 78 | 12 | DecimalType(12,2) | Signed w/ overpunch |
| 10 | ACCT-CURR-CYC-DEBIT | S9(10)V99 | 90 | 12 | DecimalType(12,2) | Signed w/ overpunch |
| 11 | ACCT-ADDR-ZIP | X(10) | 102 | 10 | StringType | |
| 12 | ACCT-GROUP-ID | X(10) | 112 | 10 | StringType | |
| 13 | FILLER | X(178) | 122 | 178 | Dropped | Padding |

### 3.2 CUSTREC.cpy — CUSTOMER-RECORD (500 bytes)

| # | COBOL Field | PIC | Offset | Len | PySpark Type | Notes |
|---|---|---|---|---|---|---|
| 1 | CUST-ID | 9(09) | 0 | 9 | LongType | |
| 2 | CUST-FIRST-NAME | X(25) | 9 | 25 | StringType | |
| 3 | CUST-MIDDLE-NAME | X(25) | 34 | 25 | StringType | |
| 4 | CUST-LAST-NAME | X(25) | 59 | 25 | StringType | |
| 5 | CUST-ADDR-LINE-1 | X(50) | 84 | 50 | StringType | |
| 6 | CUST-ADDR-LINE-2 | X(50) | 134 | 50 | StringType | |
| 7 | CUST-ADDR-LINE-3 | X(50) | 184 | 50 | StringType | |
| 8 | CUST-ADDR-STATE-CD | X(02) | 234 | 2 | StringType | US state code |
| 9 | CUST-ADDR-COUNTRY-CD | X(03) | 236 | 3 | StringType | e.g. 'USA' |
| 10 | CUST-ADDR-ZIP | X(10) | 239 | 10 | StringType | May include ZIP+4 |
| 11 | CUST-PHONE-NUM-1 | X(15) | 249 | 15 | StringType | |
| 12 | CUST-PHONE-NUM-2 | X(15) | 264 | 15 | StringType | |
| 13 | CUST-SSN | 9(09) | 279 | 9 | LongType | |
| 14 | CUST-GOVT-ISSUED-ID | X(20) | 288 | 20 | StringType | |
| 15 | CUST-DOB-YYYYMMDD | X(10) | 308 | 10 | StringType | YYYY-MM-DD in data |
| 16 | CUST-EFT-ACCOUNT-ID | X(10) | 318 | 10 | StringType | |
| 17 | CUST-PRI-CARD-HOLDER-IND | X(01) | 328 | 1 | StringType | |
| 18 | CUST-FICO-CREDIT-SCORE | 9(03) | 329 | 3 | IntegerType | |
| 19 | FILLER | X(168) | 332 | 168 | Dropped | Padding |

### 3.3 CVACT02Y.cpy — CARD-RECORD (150 bytes)

| # | COBOL Field | PIC | Offset | Len | PySpark Type | Notes |
|---|---|---|---|---|---|---|
| 1 | CARD-NUM | X(16) | 0 | 16 | StringType | Preserves leading zeros |
| 2 | CARD-ACCT-ID | 9(11) | 16 | 11 | LongType | FK to ACCOUNT-RECORD |
| 3 | CARD-CVV-CD | 9(03) | 27 | 3 | IntegerType | |
| 4 | CARD-EMBOSSED-NAME | X(50) | 30 | 50 | StringType | |
| 5 | CARD-EXPIRAION-DATE | X(10) | 80 | 10 | StringType | Typo preserved |
| 6 | CARD-ACTIVE-STATUS | X(01) | 90 | 1 | StringType | |
| 7 | FILLER | X(59) | 91 | 59 | Dropped | Padding |

---

## 4. Assumptions and Limitations

1. **ASCII encoding only.** These scripts process the files in `app/data/ASCII/`.
   The EBCDIC-encoded files in `app/data/EBCDIC/` use different byte
   representations and would require additional decoding (e.g. EBCDIC-to-ASCII
   translation of the entire record before field extraction).

2. **No COMP or COMP-3 fields.** None of the three copybooks processed here
   use packed decimal (`COMP-3`) or binary (`COMP`) storage. If future
   copybooks include these, additional decode logic will be required.

3. **Sign convention.** The trailing overpunch sign encoding follows the
   standard IBM EBCDIC-to-ASCII mapping (`{/}` for ±0, `A-I`/`J-R` for ±1–9).
   This is the most common convention when COBOL data is converted from EBCDIC
   to ASCII with sign preservation.

4. **FILLER is excluded.** FILLER fields are not loaded into DataFrames. If
   future records store data in what is currently declared as FILLER, the
   scripts would need updating.

5. **Typos preserved.** Field names like `ACCT-EXPIRAION-DATE` and
   `CARD-EXPIRAION-DATE` contain a typo in the original copybooks. We preserve
   this spelling in both the JSON schemas and the PySpark column names
   (normalized to underscores: `ACCT_EXPIRAION_DATE`) to maintain traceability
   back to the source COBOL definitions.

6. **Date fields kept as strings.** All date fields are `PIC X(10)` in the
   copybooks, so they are mapped to `StringType`. The observed format in the
   ASCII data is `YYYY-MM-DD`, but we do not enforce this at the schema level.

---

## 5. Generated Artifacts

| Artifact | Path |
|---|---|
| Account PySpark parser | `scripts/pyspark/parse_acctdata.py` |
| Account JSON schema | `scripts/pyspark/schemas/CVACT01Y_schema.json` |
| Customer PySpark parser | `scripts/pyspark/parse_custdata.py` |
| Customer JSON schema | `scripts/pyspark/schemas/CUSTREC_schema.json` |
| Card PySpark parser | `scripts/pyspark/parse_carddata.py` |
| Card JSON schema | `scripts/pyspark/schemas/CVACT02Y_schema.json` |
| This document | `COPYBOOK_PARSING_NOTES.md` |
