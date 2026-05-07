# COBOL Copybook to PySpark Type-Mapping Notes

This document describes the decisions made when translating COBOL copybook
field definitions into PySpark types for the CardDemo fixed-width data files.

---

## Copybooks Covered

| Copybook | Record Name | Length | Data File |
|---|---|---|---|
| `CVACT01Y.cpy` | ACCOUNT-RECORD | 300 | `app/data/ASCII/acctdata.txt` |
| `CUSTREC.cpy` | CUSTOMER-RECORD | 500 | `app/data/ASCII/custdata.txt` |
| `CVACT02Y.cpy` | CARD-RECORD | 150 | `app/data/ASCII/carddata.txt` |

---

## Type-Mapping Rules

### 1. `PIC 9(n)` — Unsigned Zoned Decimal

**COBOL behaviour:** Each byte represents one decimal digit in DISPLAY
(zoned-decimal) format.  In ASCII files the bytes are literal `'0'`–`'9'`
characters.

| Digits (n) | PySpark Type | Rationale |
|---|---|---|
| n <= 9 | `IntegerType` (32-bit) | Fits within signed 32-bit range (max ~2.1 × 10⁹) |
| 10 <= n <= 18 | `LongType` (64-bit) | Exceeds 32-bit range; fits 64-bit signed long |

**Examples:**
- `ACCT-ID PIC 9(11)` → `LongType` (11 digits exceeds `IntegerType` max)
- `CUST-ID PIC 9(09)` → `LongType` (9 digits; 999 999 999 fits `IntegerType` but `LongType` is used for consistency with other ID fields)
- `CARD-CVV-CD PIC 9(03)` → `IntegerType` (3-digit code)
- `CUST-FICO-CREDIT-SCORE PIC 9(03)` → `IntegerType` (3-digit score)

> **Note on CUST-ID / CUST-SSN:** Although `PIC 9(09)` fits in 32 bits, we
> use `LongType` for all identifier and SSN fields.  This avoids silent
> overflow if the source system ever uses values close to 999 999 999 and
> maintains type consistency across ID columns.

### 2. `PIC S9(n)V99` — Signed Zoned Decimal with Implied Decimal

**COBOL behaviour:** `S` indicates a signed field.  `V99` places an implied
decimal point two digits from the right (no literal `.` in the data).  In
DISPLAY format without a separate `SIGN` clause, the sign is encoded in the
**last byte** using overpunch notation.

**ASCII overpunch mapping (last byte):**

| Character | Digit | Sign |
|---|---|---|
| `{` | 0 | + |
| `A`–`I` | 1–9 | + |
| `}` | 0 | − |
| `J`–`R` | 1–9 | − |

**PySpark type:** `DecimalType(12, 2)`

- 12 total digits of precision (10 integer + 2 fractional) matches
  `S9(10)V99`.
- `DecimalType` preserves exact decimal arithmetic — critical for financial
  amounts (balance, credit limit, transaction amounts).

**Decoding steps (implemented in `decode_signed_zoned_decimal()`):**

1. Extract the last character of the raw field.
2. Look up the character in the positive or negative overpunch table to
   recover the trailing digit and sign.
3. Insert the implied decimal point two positions from the right.
4. Return a Python `Decimal` value.

**Example:** Raw bytes `00000001940{`
- Last char `{` → digit `0`, sign `+`
- All digits become: `000000019400`
- V99 splits last 2 digits as fractional: `0000000194.00` → **$194.00**

### 3. `PIC X(n)` — Alphanumeric

**COBOL behaviour:** Each byte is one character.  The field is space-padded
on the right.

**PySpark type:** `StringType`

All `PIC X(n)` fields — including dates stored as `PIC X(10)` in
`YYYY-MM-DD` format — are mapped to `StringType`.  Dates are **not**
converted to `DateType` to preserve the original representation and avoid
parse failures on malformed values.

**Post-processing note:** Trailing spaces are stripped (`.strip()`) during
parsing so downstream consumers receive clean strings.

### 4. `FILLER` Fields

Every copybook contains a trailing `FILLER` field that pads the record to
its declared length.  These are parsed as `StringType` for completeness
(allowing round-trip validation) but carry no business meaning and can be
dropped in downstream pipelines.

### 5. COMP-3 (Packed Decimal) — Not Present but Documented

None of the three copybooks analysed here use `COMP-3` (packed BCD) or
`COMP` (binary) fields.  All numeric fields are in DISPLAY (zoned-decimal)
format.  For reference, the recommended mapping if COMP-3 fields are
encountered in other CardDemo copybooks is:

| COBOL Usage | PySpark Type | Notes |
|---|---|---|
| `COMP-3` / `PACKED-DECIMAL` | `DecimalType(p, s)` | Each byte stores two BCD digits (plus a trailing sign nibble). Byte length = `floor((n+1)/2) + 1`. |
| `COMP` / `BINARY` | `IntegerType` or `LongType` | Native binary integer; byte length depends on PIC size. |

---

## Data File Characteristics

| Property | acctdata.txt | custdata.txt | carddata.txt |
|---|---|---|---|
| Encoding | ASCII | ASCII | ASCII |
| Record length | 300 bytes | 500 bytes | 150 bytes |
| Line terminator | LF (Unix) | LF (Unix) | LF (Unix) |
| Record count | 50 | 50 | 50 |
| Contains overpunch signs | Yes (5 fields) | No | No |
| Contains COMP-3 fields | No | No | No |

---

## Offset Calculations

Offsets are zero-based byte positions within each fixed-width record.  Full
offset tables are in the JSON schema files under `generated/schemas/`.

**Verification:** The sum of all field lengths in each copybook equals the
declared record length:

- **CVACT01Y:** 11+1+12+12+12+10+10+10+12+12+10+10+178 = **300**
- **CUSTREC:** 9+25+25+25+50+50+50+2+3+10+15+15+9+20+10+10+1+3+168 = **500**
- **CVACT02Y:** 16+11+3+50+10+1+59 = **150**

---

## Generated Artifacts

```
generated/
├── schemas/
│   ├── CVACT01Y_account_schema.json
│   ├── CUSTREC_customer_schema.json
│   └── CVACT02Y_card_schema.json
├── pyspark/
│   ├── parse_acctdata.py
│   ├── parse_custdata.py
│   └── parse_carddata.py
└── validation/
    ├── acctdata_validation.json
    ├── custdata_validation.json
    └── carddata_validation.json
```

---

## Running the Parsers

Each script is self-contained and uses PySpark in local mode:

```bash
pip install pyspark

python generated/pyspark/parse_acctdata.py
python generated/pyspark/parse_custdata.py
python generated/pyspark/parse_carddata.py
```

Each script:
1. Reads the corresponding fixed-width data file via `SparkContext.textFile()`.
2. Validates that every line matches the expected record length.
3. Parses fields by slicing at the correct byte offsets.
4. Decodes overpunch-signed fields where applicable.
5. Creates a typed PySpark DataFrame and prints schema + sample rows.
6. Writes a JSON validation report to `generated/validation/`.
