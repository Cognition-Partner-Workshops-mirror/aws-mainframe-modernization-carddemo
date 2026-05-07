"""
PySpark script to parse app/data/ASCII/acctdata.txt using the COBOL copybook
layout defined in app/cpy/CVACT01Y.cpy (ACCOUNT-RECORD, 300 bytes).

Sign-overpunch decoding is applied to S9(10)V99 (signed zoned-decimal) fields.
The implied decimal point (V99) is resolved by dividing by 100 after decoding.

Usage:
    spark-submit scripts/parse_acctdata.py
    # or
    python scripts/parse_acctdata.py
"""

import os
from decimal import Decimal

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, substring, trim, udf
from pyspark.sql.types import DecimalType

# ---------------------------------------------------------------------------
# Sign-overpunch lookup tables (EBCDIC-to-ASCII DISPLAY format)
# Last byte of a signed zoned-decimal field encodes both the sign and the
# digit value.  Positive: {=0 A=1 B=2 … I=9   Negative: }=0 J=1 K=2 … R=9
# ---------------------------------------------------------------------------
POSITIVE_OVERPUNCH = {"{": "0", "A": "1", "B": "2", "C": "3", "D": "4",
                      "E": "5", "F": "6", "G": "7", "H": "8", "I": "9"}
NEGATIVE_OVERPUNCH = {"}": "0", "J": "1", "K": "2", "L": "3", "M": "4",
                      "N": "5", "O": "6", "P": "7", "Q": "8", "R": "9"}


def decode_signed_zoned_decimal(raw: str, scale: int = 2) -> Decimal:
    """Decode a COBOL signed zoned-decimal string with overpunch sign.

    The last byte of a signed DISPLAY-format field uses an overpunch
    character that encodes both the sign and the final digit.  The
    implied decimal point (Vnn) is resolved by dividing by 10**scale.

    Args:
        raw:   The raw fixed-width string extracted from the data file.
        scale: Number of implied decimal places (V99 → scale=2).

    Returns:
        A Decimal value, or None if the input is None/empty.
    """
    if raw is None or raw.strip() == "":
        return None
    raw = raw.strip()
    last_char = raw[-1]
    digits = raw[:-1]
    if last_char in POSITIVE_OVERPUNCH:
        # Positive value
        digits += POSITIVE_OVERPUNCH[last_char]
        sign = 1
    elif last_char in NEGATIVE_OVERPUNCH:
        # Negative value
        digits += NEGATIVE_OVERPUNCH[last_char]
        sign = -1
    elif last_char.isdigit():
        # No overpunch — treat as unsigned positive
        digits += last_char
        sign = 1
    else:
        return None
    # Return Decimal so PySpark DecimalType columns are populated correctly
    return Decimal(sign * int(digits)) / Decimal(10 ** scale)


# Register the decoder as a PySpark UDF returning DecimalType(12, 2)
decode_signed_udf = udf(
    lambda raw: decode_signed_zoned_decimal(raw, scale=2),
    DecimalType(12, 2),
)

# ---------------------------------------------------------------------------
# Field layout derived from CVACT01Y.cpy  (ACCOUNT-RECORD, 300 bytes)
# Each tuple: (field_name, cobol_pic, pyspark_type, offset, length)
# Offsets are 0-based byte positions within the 300-byte record.
# ---------------------------------------------------------------------------
ACCOUNT_FIELDS = [
    ("ACCT_ID",                "9(11)",      "StringType",  0,   11),
    ("ACCT_ACTIVE_STATUS",     "X(01)",      "StringType",  11,   1),
    ("ACCT_CURR_BAL",          "S9(10)V99",  "DecimalType", 12,  12),
    ("ACCT_CREDIT_LIMIT",      "S9(10)V99",  "DecimalType", 24,  12),
    ("ACCT_CASH_CREDIT_LIMIT", "S9(10)V99",  "DecimalType", 36,  12),
    ("ACCT_OPEN_DATE",         "X(10)",      "StringType",  48,  10),
    ("ACCT_EXPIRAION_DATE",    "X(10)",      "StringType",  58,  10),
    ("ACCT_REISSUE_DATE",      "X(10)",      "StringType",  68,  10),
    ("ACCT_CURR_CYC_CREDIT",   "S9(10)V99",  "DecimalType", 78,  12),
    ("ACCT_CURR_CYC_DEBIT",    "S9(10)V99",  "DecimalType", 90,  12),
    ("ACCT_ADDR_ZIP",          "X(10)",      "StringType",  102, 10),
    ("ACCT_GROUP_ID",          "X(10)",      "StringType",  112, 10),
    ("FILLER",                 "X(178)",     "StringType",  122, 178),
]

RECORD_LENGTH = 300  # Total record length in bytes


def verify_byte_offsets(fields, record_length):
    """Validate that field offsets and lengths are contiguous and sum to record_length.

    Checks that each field's offset + length equals the next field's offset, and
    that the last field ends exactly at the declared record length.  Raises
    ValueError on any misalignment.
    """
    for i in range(len(fields) - 1):
        name, _, _, offset, length = fields[i]
        next_name, _, _, next_offset, _ = fields[i + 1]
        if offset + length != next_offset:
            raise ValueError(
                f"Byte-offset gap/overlap between {name} and {next_name}: "
                f"{offset}+{length}={offset + length} but next offset is {next_offset}"
            )
    # Check last field reaches record_length
    last_name, _, _, last_offset, last_length = fields[-1]
    if last_offset + last_length != record_length:
        raise ValueError(
            f"Last field {last_name} ends at byte {last_offset + last_length}, "
            f"but record length is {record_length}"
        )


def main():
    """Read acctdata.txt, parse fields, validate, and write results."""
    # Verify field layout alignment before processing any data
    verify_byte_offsets(ACCOUNT_FIELDS, RECORD_LENGTH)
    # Resolve paths relative to the repo root
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(repo_root, "app", "data", "ASCII", "acctdata.txt")
    validation_path = os.path.join(repo_root, "validation", "validate_acctdata.txt")

    spark = SparkSession.builder \
        .appName("CardDemo_AccountData_Parser") \
        .master("local[*]") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    # Read the fixed-width file as raw text lines
    raw_df = spark.read.text(data_path)

    # --- Extract fields using substring (1-based positions in PySpark) ---
    parsed_df = raw_df.select(
        *[
            substring(col("value"), offset + 1, length).alias(name)
            for name, _, _, offset, length in ACCOUNT_FIELDS
        ]
    )

    # --- Apply type conversions ---
    # Signed zoned-decimal fields → DecimalType via UDF
    signed_fields = [name for name, pic, _, _, _ in ACCOUNT_FIELDS if pic.startswith("S")]
    for field in signed_fields:
        parsed_df = parsed_df.withColumn(field, decode_signed_udf(col(field)))

    # ACCT_ID kept as StringType to preserve leading zeros (mainframe identifiers)

    # Trim whitespace from all string fields (including PIC 9 identifiers)
    string_fields = [name for name, _, ptype, _, _ in ACCOUNT_FIELDS
                     if ptype == "StringType" and name != "FILLER"]
    for field in string_fields:
        parsed_df = parsed_df.withColumn(field, trim(col(field)))

    # Drop FILLER column (not useful for downstream processing)
    final_df = parsed_df.drop("FILLER")

    # --- Validation: compare row counts and sample values ---
    raw_line_count = raw_df.count()
    parsed_row_count = final_df.count()

    validation_lines = []
    validation_lines.append("=" * 70)
    validation_lines.append("VALIDATION REPORT: acctdata.txt  (CVACT01Y.cpy / ACCOUNT-RECORD)")
    validation_lines.append("=" * 70)
    validation_lines.append(f"Raw file line count        : {raw_line_count}")
    validation_lines.append(f"Parsed DataFrame row count : {parsed_row_count}")
    validation_lines.append(f"Counts match               : {raw_line_count == parsed_row_count}")
    validation_lines.append(f"Expected record length     : {RECORD_LENGTH}")
    validation_lines.append("")
    validation_lines.append("-" * 70)
    validation_lines.append("Schema:")
    validation_lines.append("-" * 70)
    for line in final_df._jdf.schema().treeString().split("\n"):
        validation_lines.append(f"  {line}")
    validation_lines.append("")
    validation_lines.append("-" * 70)
    validation_lines.append("Sample rows (first 5):")
    validation_lines.append("-" * 70)

    sample_rows = final_df.limit(5).collect()
    col_names = final_df.columns
    for i, row in enumerate(sample_rows):
        validation_lines.append(f"\n  Row {i + 1}:")
        for col_name in col_names:
            validation_lines.append(f"    {col_name:30s} = {row[col_name]}")

    # --- Cross-check: re-read first raw line and compare parsed values ---
    validation_lines.append("")
    validation_lines.append("-" * 70)
    validation_lines.append("Cross-check: First raw line manual extraction vs parsed values")
    validation_lines.append("-" * 70)
    first_raw = raw_df.first()["value"]
    validation_lines.append(f"  Raw line length: {len(first_raw)}")
    for name, pic, _, offset, length in ACCOUNT_FIELDS:
        if name == "FILLER":
            continue
        raw_val = first_raw[offset:offset + length]
        validation_lines.append(f"  {name:30s} raw='{raw_val}'")

    validation_lines.append("")
    validation_lines.append("=" * 70)
    validation_lines.append("END OF VALIDATION REPORT")
    validation_lines.append("=" * 70)

    report = "\n".join(validation_lines)
    print(report)

    # Write the validation report to file
    os.makedirs(os.path.dirname(validation_path), exist_ok=True)
    with open(validation_path, "w") as f:
        f.write(report + "\n")

    print(f"\nValidation report written to: {validation_path}")

    spark.stop()


if __name__ == "__main__":
    main()
