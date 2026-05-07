# COBOL Copybook → PySpark Type-Mapping Notes

This document describes how COBOL PIC clauses from the CardDemo copybooks are
mapped to PySpark data types, and the rationale behind each decision.

---

## 1. Copybooks Processed

| Copybook       | Record Name       | Record Length | Data File                         |
|----------------|-------------------|---------------|-----------------------------------|
| `CVACT01Y.cpy` | ACCOUNT-RECORD    | 300 bytes     | `app/data/ASCII/acctdata.txt`     |
| `CUSTREC.cpy`  | CUSTOMER-RECORD   | 500 bytes     | `app/data/ASCII/custdata.txt`     |
| `CVACT02Y.cpy` | CARD-RECORD       | 150 bytes     | `app/data/ASCII/carddata.txt`     |

---

## 2. Type-Mapping Rules

### 2.1 `PIC X(n)` → `StringType`

Alphanumeric fields (`PIC X`) are mapped directly to PySpark `StringType`.
Trailing spaces are trimmed during parsing via `pyspark.sql.functions.trim()`.

**Examples:**
- `ACCT-ACTIVE-STATUS  PIC X(01)` → `StringType` (values: `Y` / `N`)
- `CUST-FIRST-NAME     PIC X(25)` → `StringType`
- `CARD-EMBOSSED-NAME  PIC X(50)` → `StringType`

**Date fields** like `ACCT-OPEN-DATE PIC X(10)` are kept as `StringType` rather
than cast to `DateType` because:
1. The copybook declares them as alphanumeric (`PIC X`), not numeric.
2. Downstream consumers may need the raw format (e.g., `YYYY-MM-DD`).
3. Preserves fidelity to the original COBOL definition.

### 2.2 `PIC 9(n)` (unsigned) → `LongType` or `IntegerType`

Unsigned numeric fields in DISPLAY format occupy exactly `n` bytes (one ASCII
digit per byte). The choice between `LongType` and `IntegerType` is based on
the digit count:

| Digit Count | PySpark Type    | Rationale                                  |
|-------------|-----------------|---------------------------------------------|
| ≤ 9         | `IntegerType`   | Fits within 32-bit signed integer range     |
| 10–18       | `LongType`      | Requires 64-bit signed integer              |

**Examples:**
- `ACCT-ID           PIC 9(11)` → `LongType`  (11 digits exceeds int range)
- `CUST-ID           PIC 9(09)` → `LongType`  (9 digits, but can reach 999 999 999)
- `CUST-FICO-CREDIT-SCORE PIC 9(03)` → `IntegerType`
- `CARD-CVV-CD       PIC 9(03)` → `IntegerType`

> **Note on CARD-NUM (`PIC X(16)`):** Although this holds numeric digits, the
> copybook declares it as `PIC X` (alphanumeric). It is kept as `StringType`
> to preserve leading zeros, which are significant for card numbers.

### 2.3 `PIC S9(n)V99` (signed zoned-decimal) → `DecimalType(12, 2)`

Signed numeric fields in DISPLAY format use **sign-overpunch encoding** on the
last byte. The `V` indicates an *implied* decimal point (no physical decimal
character in the data).

**Storage format (DISPLAY, not COMP-3):**
- Physical length = total digit count (integer digits + decimal digits)
- `S9(10)V99` → 10 + 2 = 12 bytes
- Last byte encodes both the sign and the final digit

**Sign-overpunch decoding table:**

| Last Byte | Sign | Digit | | Last Byte | Sign | Digit |
|-----------|------|-------|-|-----------|------|-------|
| `{`       | +    | 0     | | `}`       | −    | 0     |
| `A`       | +    | 1     | | `J`       | −    | 1     |
| `B`       | +    | 2     | | `K`       | −    | 2     |
| `C`       | +    | 3     | | `L`       | −    | 3     |
| `D`       | +    | 4     | | `M`       | −    | 4     |
| `E`       | +    | 5     | | `N`       | −    | 5     |
| `F`       | +    | 6     | | `O`       | −    | 6     |
| `G`       | +    | 7     | | `P`       | −    | 7     |
| `H`       | +    | 8     | | `Q`       | −    | 8     |
| `I`       | +    | 9     | | `R`       | −    | 9     |

**Decoding example:**
```
Raw bytes:  00000001940{
Digits:     00000001940  (first 11 bytes)
Last byte:  {  →  sign = +, digit = 0
Full value: 000000019400  (positive)
With V99:   0000000194.00  →  $194.00
```

**PySpark mapping:** `DecimalType(12, 2)` — 12 total digits, 2 after the
decimal point. `DecimalType` (backed by Python `Decimal`) is chosen over
`DoubleType` to avoid floating-point precision errors in financial data.

A custom PySpark UDF (`decode_signed_zoned_decimal`) performs the overpunch
decoding and returns `decimal.Decimal` values.

### 2.4 `COMP-3` (packed decimal) — Not Present But Documented

Although no COMP-3 fields appear in these three copybooks, COMP-3 is common
in mainframe data. For reference, the mapping would be:

| COBOL Clause           | PySpark Type         | Notes                            |
|------------------------|----------------------|----------------------------------|
| `PIC S9(n)V99 COMP-3` | `DecimalType(n+2,2)` | Packed BCD, 2 nibbles per byte   |

**COMP-3 storage:** Each byte stores two BCD digits (4 bits each), with the
last nibble encoding the sign (`C`=positive, `D`=negative, `F`=unsigned).
Physical length = `ceil((n + 1) / 2)` bytes.

### 2.5 `FILLER` Fields

FILLER fields are extracted during parsing to maintain correct byte offsets
but are **dropped** from the final DataFrame. They contain only padding
spaces and carry no business meaning.

---

## 3. Encoding Considerations

The data files in `app/data/ASCII/` are already converted from EBCDIC to ASCII.
Key implications:

1. **Character encoding:** Standard ASCII — no EBCDIC-to-ASCII translation
   needed at the PySpark level.
2. **Sign overpunch:** Uses the ASCII overpunch convention (`{`/`}` and
   `A`–`I`/`J`–`R`), which differs from the EBCDIC overpunch byte values.
3. **Record delimiters:** Each record ends with a newline (`\n`), allowing
   `spark.read.text()` to read one record per line.

---

## 4. Fixed-Width Parsing Strategy

PySpark does not have a built-in fixed-width file reader. The approach used:

1. **Read as text:** `spark.read.text(path)` loads each line into a single
   `value` column.
2. **Substring extraction:** `pyspark.sql.functions.substring(col, pos, len)`
   extracts each field. PySpark uses **1-based** positions, so the 0-based
   byte offset from the copybook is incremented by 1.
3. **Type casting:** Numeric fields are cast via `.cast()` or UDF as
   appropriate.
4. **Trimming:** `trim()` removes padding spaces from string fields.

---

## 5. Validation Approach

Each PySpark script produces a validation report that includes:

- **Row count comparison:** Raw file line count vs. parsed DataFrame row count
  (must match exactly).
- **Schema dump:** PySpark schema tree showing column names and types.
- **Sample rows:** First 5 rows with all field values printed.
- **Cross-check:** The first raw line is manually sliced by offset/length and
  compared against parsed values to verify alignment.

---

## 6. Artifacts Generated

```
schemas/
  acct_schema.json      # JSON schema for ACCOUNT-RECORD fields
  cust_schema.json      # JSON schema for CUSTOMER-RECORD fields
  card_schema.json      # JSON schema for CARD-RECORD fields

scripts/
  parse_acctdata.py     # PySpark parser for acctdata.txt
  parse_custdata.py     # PySpark parser for custdata.txt
  parse_carddata.py     # PySpark parser for carddata.txt

validation/
  validate_acctdata.txt # Validation output for account data
  validate_custdata.txt # Validation output for customer data
  validate_carddata.txt # Validation output for card data
```

---

## 7. Known Quirks in Source Data

1. **Typo in field names:** The copybooks spell "expiration" as `EXPIRAION`
   (missing the 't'). This is preserved as-is in field names and schemas to
   match the original COBOL source.
2. **ACCT-ADDR-ZIP values:** Account records contain `A000000000` in the ZIP
   field — likely placeholder/test data rather than real ZIP codes.
3. **ACCT-GROUP-ID:** All 50 account records have empty (space-padded) group
   IDs.
4. **CARD-NUM as PIC X:** Card numbers are declared as alphanumeric to preserve
   leading zeros, even though the values are purely numeric.
