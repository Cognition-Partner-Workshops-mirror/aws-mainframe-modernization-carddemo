# COBOL Copybook Parsing Notes

## Overview

This document describes the type-mapping decisions, encoding handling, and edge-case strategies used when converting COBOL copybook-defined fixed-width records into PySpark DataFrames. Three copybooks from the CardDemo application are covered:

| Copybook | Record Name | Record Length | Data File | Fields |
|----------|-------------|---------------|-----------|--------|
| `CVACT01Y.cpy` | ACCOUNT-RECORD | 300 bytes | `acctdata.txt` | 13 (incl. FILLER) |
| `CUSTREC.cpy` | CUSTOMER-RECORD | 500 bytes | `custdata.txt` | 19 (incl. FILLER) |
| `CVACT02Y.cpy` | CARD-RECORD | 150 bytes | `carddata.txt` | 7 (incl. FILLER) |

---

## Type-Mapping Decisions

### PIC X(n) → StringType

All alphanumeric COBOL fields (`PIC X(...)`) are mapped to PySpark `StringType`. Values are right-trimmed to remove the space padding that COBOL uses to fill fixed-width fields.

**Examples:**
- `ACCT-ACTIVE-STATUS PIC X(01)` → `StringType` (single character: `Y` or `N`)
- `CUST-FIRST-NAME PIC X(25)` → `StringType` (e.g., `"Immanuel"` after trim)
- `CARD-EMBOSSED-NAME PIC X(50)` → `StringType` (e.g., `"Aniya Von"` after trim)

**Rationale:** `StringType` is the natural PySpark equivalent for COBOL alphanumeric data. Space-trimming is applied because COBOL right-pads all `PIC X` fields to their declared length.

### PIC 9(n) (Unsigned Numeric) → LongType or IntegerType

Unsigned numeric fields are mapped based on their digit count:
- `PIC 9(09)` and `PIC 9(11)` → `LongType` (exceeds int32 range for 11-digit IDs)
- `PIC 9(03)` → `IntegerType` (small values like credit scores and CVV codes)

**Examples:**
- `ACCT-ID PIC 9(11)` → `LongType` (account IDs up to 99,999,999,999)
- `CUST-FICO-CREDIT-SCORE PIC 9(03)` → `IntegerType` (values 000-999)

**Rationale:** Using `LongType` for fields with more than 9 digits avoids integer overflow. `IntegerType` is used for shorter fields where the value range fits comfortably.

### PIC 9(n) for Identifiers → StringType (exceptions)

Two numeric-typed fields are intentionally mapped to `StringType` instead of a numeric type:

1. **`CUST-SSN PIC 9(09)` → `StringType`**: Social Security Numbers have meaningful leading zeros (e.g., `020973888`). Casting to `IntegerType` would lose the leading zero, producing `20973888` which is wrong.

2. **`CARD-CVV-CD PIC 9(03)` → `StringType`**: CVV codes can have leading zeros (e.g., `047`). A numeric cast would produce `47`, which is incorrect for card processing.

**Rationale:** When a `PIC 9(...)` field represents an identifier rather than a quantity, preserving the exact character representation is more important than numeric semantics. The JSON schema documents these decisions.

### PIC S9(n)V99 (Signed Numeric with Implied Decimal) → DecimalType(12,2)

Signed numeric fields with an implied decimal point (`V99`) are the most complex type mapping. These fields use **ASCII sign-overpunch encoding** in the last byte.

**Examples:**
- `ACCT-CURR-BAL PIC S9(10)V99` → `DecimalType(12,2)`
- `ACCT-CREDIT-LIMIT PIC S9(10)V99` → `DecimalType(12,2)`

**Rationale:** `DecimalType` (not `DoubleType`) is used because these are financial amounts that require exact decimal arithmetic. The precision `(12,2)` matches the COBOL layout: 10 integer digits + 2 decimal digits = 12 total.

### PIC X(10) Date Fields → DateType

Date fields stored as `PIC X(10)` strings in the copybook are mapped to PySpark `DateType`. In the ASCII export, these contain `YYYY-MM-DD` formatted strings.

**Examples:**
- `ACCT-OPEN-DATE PIC X(10)` → `DateType` (e.g., `"2014-11-20"`)
- `CUST-DOB-YYYYMMDD PIC X(10)` → `DateType` (e.g., `"1961-06-08"`)
- `CARD-EXPIRAION-DATE PIC X(10)` → `DateType` (e.g., `"2023-03-09"`)

**Rationale:** The ASCII export uses ISO 8601 date format, which PySpark's `to_date("yyyy-MM-dd")` handles natively. Note that the original COBOL programs may store these in `YYYYMMDD` (no separators) on the mainframe; the ASCII export process adds hyphens.

### FILLER → Dropped

All `FILLER` fields are extracted during parsing (to correctly advance the byte offset) but are dropped from the final DataFrame since they contain no business data — only padding bytes to reach the declared record length.

---

## Sign-Overpunch Encoding

### Background

COBOL `PIC S9(...)` (signed DISPLAY numeric) fields use **sign-overpunch encoding** where the sign is embedded in the last byte of the field rather than using a separate `+` or `-` character. This is a legacy of IBM punch card encoding.

In the ASCII representation used by the CardDemo data files, the overpunch characters are:

| Last Byte | Digit Value | Sign |
|-----------|-------------|------|
| `{` | 0 | Positive |
| `A` | 1 | Positive |
| `B` | 2 | Positive |
| `C` | 3 | Positive |
| `D` | 4 | Positive |
| `E` | 5 | Positive |
| `F` | 6 | Positive |
| `G` | 7 | Positive |
| `H` | 8 | Positive |
| `I` | 9 | Positive |
| `}` | 0 | Negative |
| `J` | 1 | Negative |
| `K` | 2 | Negative |
| `L` | 3 | Negative |
| `M` | 4 | Negative |
| `N` | 5 | Negative |
| `O` | 6 | Negative |
| `P` | 7 | Negative |
| `Q` | 8 | Negative |
| `R` | 9 | Negative |

### Decoding Example

Given `ACCT-CURR-BAL PIC S9(10)V99` with raw value `00000001940{`:

1. **Last byte:** `{` → digit `0`, sign = positive
2. **Replace last byte:** `00000001940{` → `000000019400`
3. **Apply V99 (2 implied decimal places):** `0000000194.00`
4. **Apply sign:** `+194.00`

Result: The account's current balance is `$194.00`.

### Implementation

The decoding is implemented as:
- **Pure Python function** (`decode_sign_overpunch`) for validation and testing without Spark
- **PySpark UDF** (`register_overpunch_udf`) for DataFrame transformations at scale

The UDF is parameterized by `decimal_places` since different fields may have different `V` clause precision (though all fields in these copybooks use `V99`).

### Edge Cases

| Case | Handling |
|------|----------|
| Null/blank input | Returns `Decimal("0")` |
| Plain digit as last byte (no overpunch) | Treated as positive (some ASCII exports omit overpunch) |
| Unrecognized last character | Logged as warning, returns `Decimal("0")` |
| All zeros with `{` | Correctly returns `0.00` (not treated as error) |

---

## COMP-3 (Packed Decimal) — Not Present

The CardDemo copybooks do **not** use `COMP-3` (packed decimal) encoding. All numeric fields are `DISPLAY` format (one character per digit, with sign-overpunch for signed fields).

If `COMP-3` fields were present, the mapping would be:
- `PIC S9(n)V99 COMP-3` → `DecimalType(n+2, 2)`
- Each byte stores two BCD digits (4 bits each)
- The last nibble encodes the sign (`C` = positive, `D` = negative, `F` = unsigned)
- Storage length = `ceil((n + 1) / 2)` bytes

The `cobol_common.py` module could be extended with a `decode_comp3()` function if needed for other copybooks.

---

## Fixed-Width Parsing Strategy

### Approach: Substring Extraction

Rather than using a full COBOL copybook parser library, we use PySpark's built-in `substring()` function with byte offsets derived from the copybook analysis:

```python
# Spark substring is 1-indexed (not 0-indexed)
raw_df.withColumn("ACCT-ID", F.substring(F.col("value"), 1, 11))
```

**Rationale:**
1. **No external dependencies** — uses only PySpark built-ins + one UDF for sign-overpunch
2. **Transparent** — all offsets are documented in JSON schema files
3. **Debuggable** — raw text is available alongside parsed columns during development
4. **Performant** — `substring()` is a native Spark expression (not a Python UDF) for non-signed fields

### Offset Calculation Method

Byte offsets are calculated by walking through the copybook fields sequentially:
- Start at offset 0
- Each field's offset = previous field's offset + previous field's length
- `PIC 9(n)` contributes `n` bytes
- `PIC X(n)` contributes `n` bytes
- `PIC S9(n)V99` contributes `n + 2` bytes (sign is embedded, V is implied — no extra storage)
- `FILLER PIC X(n)` contributes `n` bytes

The total of all field lengths must equal the declared record length (verified by validation).

---

## Artifacts Summary

| Artifact | Path | Description |
|----------|------|-------------|
| Account schema | `pyspark/schemas/account_record_schema.json` | JSON schema for CVACT01Y.cpy |
| Customer schema | `pyspark/schemas/customer_record_schema.json` | JSON schema for CUSTREC.cpy |
| Card schema | `pyspark/schemas/card_record_schema.json` | JSON schema for CVACT02Y.cpy |
| Common utilities | `pyspark/scripts/cobol_common.py` | Shared parsing: overpunch decode, fixed-width extract, Spark UDF |
| Account parser | `pyspark/scripts/parse_accounts.py` | PySpark script for acctdata.txt |
| Customer parser | `pyspark/scripts/parse_customers.py` | PySpark script for custdata.txt |
| Card parser | `pyspark/scripts/parse_cards.py` | PySpark script for carddata.txt |
| Validation script | `pyspark/validation/validate_parsing.py` | Pure-Python validation (no Spark required) |
| Validation results | `pyspark/validation/VALIDATION_RESULTS.md` | 18/18 checks passed across all 3 datasets |

---

## Known Observations from Validation

1. **ACCT-ADDR-ZIP** in `acctdata.txt` contains values like `A000000000` — this is the ZIP field from the account record, but the `A` prefix suggests it may contain alpha-encoded data rather than a standard US ZIP code. The field is mapped as `StringType` which preserves the raw value.

2. **ACCT-GROUP-ID** is blank (all spaces) for the first record. This is a nullable field in the copybook (no `NOT NULL` constraint in COBOL); the PySpark parser trims it to an empty string.

3. **CUST-FICO-CREDIT-SCORE** has a value of `274` for the first customer, which is below the standard FICO range of 300-850. This may indicate test/synthetic data or a legacy scoring model. The parser preserves the raw value.

4. **Misspelling in copybook**: Both `ACCT-EXPIRAION-DATE` and `CARD-EXPIRAION-DATE` are misspelled (should be "EXPIRATION"). The field names are preserved as-is from the original copybook to maintain traceability.
