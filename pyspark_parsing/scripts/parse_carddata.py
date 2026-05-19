"""
PySpark script to parse the CARD-RECORD fixed-width file (carddata.txt)
using the schema derived from COBOL copybook CVACT02Y.cpy.

Record layout: 150 bytes per line.
No sign-encoded fields — all numerics are unsigned zoned decimal (PIC 9)
or alphanumeric (PIC X).

Usage:
    spark-submit parse_carddata.py [--data-path <path>] [--output-dir <path>]
"""

import argparse
import json
import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, trim, length as spark_length
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, IntegerType
)

# ---------------------------------------------------------------------------
# Constants derived from CVACT02Y.cpy
# ---------------------------------------------------------------------------
RECORD_LENGTH = 150
COPYBOOK_NAME = "CVACT02Y.cpy"

# Field definitions: (name, offset, length)
FIELD_DEFS = [
    ("CARD_NUM",              0,  16),
    ("CARD_ACCT_ID",         16,  11),
    ("CARD_CVV_CD",          27,   3),
    ("CARD_EMBOSSED_NAME",   30,  50),
    ("CARD_EXPIRAION_DATE",  80,  10),
    ("CARD_ACTIVE_STATUS",   90,   1),
    ("FILLER",               91,  59),
]

# Alphanumeric fields to trim trailing spaces
ALPHA_FIELDS = [
    "CARD_NUM", "CARD_EMBOSSED_NAME", "CARD_EXPIRAION_DATE",
    "CARD_ACTIVE_STATUS", "FILLER",
]


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Parse COBOL CARD-RECORD fixed-width file with PySpark"
    )
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    parser.add_argument(
        "--data-path",
        default=os.path.join(repo_root, "app", "data", "ASCII", "carddata.txt"),
        help="Path to the carddata.txt fixed-width file",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(repo_root, "pyspark_parsing", "validation"),
        help="Directory to write validation output",
    )
    return parser.parse_args()


def build_dataframe(spark, data_path):
    """Read the fixed-width file and parse fields per the CVACT02Y.cpy layout.

    Reads each line as a single string column, then slices substrings
    according to the byte offsets defined in the copybook.
    """
    # Read entire lines as single-column raw text
    raw_df = spark.read.text(data_path)

    # Slice each field using substring (PySpark substring is 1-based)
    parsed_df = raw_df
    for field_name, offset, field_length in FIELD_DEFS:
        parsed_df = parsed_df.withColumn(
            field_name,
            col("value").substr(offset + 1, field_length)
        )

    # Drop the original raw line column
    parsed_df = parsed_df.drop("value")

    # --- Type conversions ---
    # CARD_ACCT_ID: PIC 9(11) → LongType
    parsed_df = parsed_df.withColumn(
        "CARD_ACCT_ID", col("CARD_ACCT_ID").cast(LongType())
    )

    # CARD_CVV_CD: PIC 9(03) → keep as StringType to preserve leading zeros
    # (already a string from substring extraction)

    # Trim whitespace from alphanumeric fields
    for field_name in ALPHA_FIELDS:
        parsed_df = parsed_df.withColumn(field_name, trim(col(field_name)))

    return parsed_df


def validate_and_report(spark, parsed_df, data_path, output_dir):
    """Generate validation output comparing parsed DataFrame to raw file.

    Writes a JSON report with row counts, schema, sample rows, and
    basic integrity checks.
    """
    # Raw file line count
    raw_lines = spark.read.text(data_path)
    raw_count = raw_lines.count()

    # Check that every raw line is the expected record length
    bad_length_count = raw_lines.filter(
        spark_length(col("value")) != RECORD_LENGTH
    ).count()

    parsed_count = parsed_df.count()

    # Collect first 5 rows as sample data
    sample_rows = [row.asDict() for row in parsed_df.limit(5).collect()]

    # Summary statistics for numeric columns
    numeric_fields = ["CARD_ACCT_ID"]
    numeric_summary = {}
    for field_name in numeric_fields:
        stats = parsed_df.select(field_name).summary("min", "max", "count").collect()
        numeric_summary[field_name] = {s["summary"]: s[field_name] for s in stats}

    # Null counts per column
    null_counts = {}
    for field_name, _, _ in FIELD_DEFS:
        nc = parsed_df.filter(col(field_name).isNull()).count()
        if nc > 0:
            null_counts[field_name] = nc

    report = {
        "copybook": COPYBOOK_NAME,
        "data_file": data_path,
        "record_length": RECORD_LENGTH,
        "raw_line_count": raw_count,
        "parsed_row_count": parsed_count,
        "row_count_match": raw_count == parsed_count,
        "lines_with_wrong_length": bad_length_count,
        "null_counts": null_counts,
        "numeric_summary": numeric_summary,
        "sample_rows": sample_rows,
        "schema": parsed_df.dtypes,
    }

    # Write validation report to JSON
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, "carddata_validation.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Print summary to stdout
    print("=" * 70)
    print(f"VALIDATION REPORT — {COPYBOOK_NAME} → carddata.txt")
    print("=" * 70)
    print(f"  Raw file lines:        {raw_count}")
    print(f"  Parsed DataFrame rows: {parsed_count}")
    print(f"  Row count match:       {raw_count == parsed_count}")
    print(f"  Lines wrong length:    {bad_length_count}")
    print(f"  Columns with nulls:    {null_counts if null_counts else 'None'}")
    print(f"  Report written to:     {report_path}")
    print()
    print("SCHEMA:")
    for col_name, dtype in parsed_df.dtypes:
        print(f"  {col_name:30s}  {dtype}")
    print()
    print("SAMPLE ROWS (first 5):")
    parsed_df.show(5, truncate=40)

    return report


def main():
    args = parse_args()

    spark = SparkSession.builder \
        .appName("COBOL_Carddata_Parser") \
        .master("local[*]") \
        .getOrCreate()

    # Suppress verbose Spark logs for cleaner validation output
    spark.sparkContext.setLogLevel("WARN")

    try:
        parsed_df = build_dataframe(spark, args.data_path)
        validate_and_report(spark, parsed_df, args.data_path, args.output_dir)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
