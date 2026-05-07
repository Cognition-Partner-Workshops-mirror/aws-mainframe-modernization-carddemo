"""
PySpark script to parse app/data/ASCII/custdata.txt using the COBOL copybook
layout defined in app/cpy/CUSTREC.cpy (CUSTOMER-RECORD, 500 bytes).

All fields in CUSTREC are unsigned (no sign-overpunch decoding needed).
PIC 9(n) identifier fields (CUST_ID, CUST_SSN) are kept as StringType to
preserve leading zeros.  Only true numeric values (FICO score) are cast.

Usage:
    spark-submit scripts/parse_custdata.py
    # or
    python scripts/parse_custdata.py
"""

import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, substring, trim
from pyspark.sql.types import IntegerType

# ---------------------------------------------------------------------------
# Field layout derived from CUSTREC.cpy  (CUSTOMER-RECORD, 500 bytes)
# Each tuple: (field_name, cobol_pic, pyspark_type, offset, length)
# Offsets are 0-based byte positions within the 500-byte record.
# ---------------------------------------------------------------------------
CUSTOMER_FIELDS = [
    ("CUST_ID",                 "9(09)",  "StringType",  0,    9),
    ("CUST_FIRST_NAME",         "X(25)",  "StringType",  9,   25),
    ("CUST_MIDDLE_NAME",        "X(25)",  "StringType",  34,  25),
    ("CUST_LAST_NAME",          "X(25)",  "StringType",  59,  25),
    ("CUST_ADDR_LINE_1",        "X(50)",  "StringType",  84,  50),
    ("CUST_ADDR_LINE_2",        "X(50)",  "StringType",  134, 50),
    ("CUST_ADDR_LINE_3",        "X(50)",  "StringType",  184, 50),
    ("CUST_ADDR_STATE_CD",      "X(02)",  "StringType",  234,  2),
    ("CUST_ADDR_COUNTRY_CD",    "X(03)",  "StringType",  236,  3),
    ("CUST_ADDR_ZIP",           "X(10)",  "StringType",  239, 10),
    ("CUST_PHONE_NUM_1",        "X(15)",  "StringType",  249, 15),
    ("CUST_PHONE_NUM_2",        "X(15)",  "StringType",  264, 15),
    ("CUST_SSN",                "9(09)",  "StringType",  279,  9),
    ("CUST_GOVT_ISSUED_ID",     "X(20)",  "StringType",  288, 20),
    ("CUST_DOB_YYYYMMDD",       "X(10)",  "StringType",  308, 10),
    ("CUST_EFT_ACCOUNT_ID",     "X(10)",  "StringType",  318, 10),
    ("CUST_PRI_CARD_HOLDER_IND","X(01)",  "StringType",  328,  1),
    ("CUST_FICO_CREDIT_SCORE",  "9(03)",  "IntegerType", 329,  3),
    ("FILLER",                  "X(168)", "StringType",  332, 168),
]

RECORD_LENGTH = 500  # Total record length in bytes


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
    """Read custdata.txt, parse fields, validate, and write results."""
    # Verify field layout alignment before processing any data
    verify_byte_offsets(CUSTOMER_FIELDS, RECORD_LENGTH)
    # Resolve paths relative to the repo root
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(repo_root, "app", "data", "ASCII", "custdata.txt")
    validation_path = os.path.join(repo_root, "validation", "validate_custdata.txt")

    spark = SparkSession.builder \
        .appName("CardDemo_CustomerData_Parser") \
        .master("local[*]") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    # Read the fixed-width file as raw text lines
    raw_df = spark.read.text(data_path)

    # --- Extract fields using substring (1-based positions in PySpark) ---
    parsed_df = raw_df.select(
        *[
            substring(col("value"), offset + 1, length).alias(name)
            for name, _, _, offset, length in CUSTOMER_FIELDS
        ]
    )

    # --- Apply type conversions ---
    # CUST_ID and CUST_SSN kept as StringType to preserve leading zeros

    # Unsigned numeric PIC 9(03) → IntegerType (true numeric, no meaningful leading zeros)
    parsed_df = parsed_df.withColumn(
        "CUST_FICO_CREDIT_SCORE", col("CUST_FICO_CREDIT_SCORE").cast(IntegerType())
    )

    # Trim whitespace from string fields
    string_fields = [name for name, _, ptype, _, _ in CUSTOMER_FIELDS
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
    validation_lines.append("VALIDATION REPORT: custdata.txt  (CUSTREC.cpy / CUSTOMER-RECORD)")
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
    for name, pic, _, offset, length in CUSTOMER_FIELDS:
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
