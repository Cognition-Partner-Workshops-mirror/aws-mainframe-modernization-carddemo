"""
PySpark script to parse app/data/ASCII/carddata.txt using the COBOL copybook
layout defined in app/cpy/CVACT02Y.cpy (CARD-RECORD, 150 bytes).

All fields are unsigned — no sign-overpunch decoding required.
PIC 9(n) fields are cast to numeric types; PIC X(n) fields become strings.

Usage:
    spark-submit scripts/parse_carddata.py
    # or
    python scripts/parse_carddata.py
"""

import json
import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, substring, trim
from pyspark.sql.types import (
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
)

# ---------------------------------------------------------------------------
# Field layout derived from CVACT02Y.cpy  (CARD-RECORD, 150 bytes)
# Each tuple: (field_name, cobol_pic, pyspark_type, offset, length)
# Offsets are 0-based byte positions within the 150-byte record.
# ---------------------------------------------------------------------------
CARD_FIELDS = [
    ("CARD_NUM",             "X(16)",  "StringType",  0,   16),
    ("CARD_ACCT_ID",         "9(11)",  "LongType",    16,  11),
    ("CARD_CVV_CD",          "9(03)",  "IntegerType", 27,   3),
    ("CARD_EMBOSSED_NAME",   "X(50)",  "StringType",  30,  50),
    ("CARD_EXPIRAION_DATE",  "X(10)",  "StringType",  80,  10),
    ("CARD_ACTIVE_STATUS",   "X(01)",  "StringType",  90,   1),
    ("FILLER",               "X(59)",  "StringType",  91,  59),
]

RECORD_LENGTH = 150  # Total record length in bytes


def main():
    """Read carddata.txt, parse fields, validate, and write results."""
    # Resolve paths relative to the repo root
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(repo_root, "app", "data", "ASCII", "carddata.txt")
    validation_path = os.path.join(repo_root, "validation", "validate_carddata.txt")

    spark = SparkSession.builder \
        .appName("CardDemo_CardData_Parser") \
        .master("local[*]") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    # Read the fixed-width file as raw text lines
    raw_df = spark.read.text(data_path)

    # --- Extract fields using substring (1-based positions in PySpark) ---
    parsed_df = raw_df.select(
        *[
            substring(col("value"), offset + 1, length).alias(name)
            for name, _, _, offset, length in CARD_FIELDS
        ]
    )

    # --- Apply type conversions ---
    # Unsigned numeric PIC 9(11) → LongType
    parsed_df = parsed_df.withColumn("CARD_ACCT_ID", col("CARD_ACCT_ID").cast(LongType()))

    # Unsigned numeric PIC 9(03) → IntegerType
    parsed_df = parsed_df.withColumn("CARD_CVV_CD", col("CARD_CVV_CD").cast(IntegerType()))

    # Trim whitespace from string fields
    string_fields = [name for name, _, ptype, _, _ in CARD_FIELDS
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
    validation_lines.append("VALIDATION REPORT: carddata.txt  (CVACT02Y.cpy / CARD-RECORD)")
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
    for name, pic, _, offset, length in CARD_FIELDS:
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
