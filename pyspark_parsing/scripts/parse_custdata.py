"""
PySpark script to parse the CUSTOMER-RECORD fixed-width file (custdata.txt)
using the schema derived from COBOL copybook CUSTREC.cpy.

Record layout: 500 bytes per line.
No sign-encoded fields — all numerics are unsigned zoned decimal (PIC 9)
or alphanumeric (PIC X).

Usage:
    spark-submit parse_custdata.py [--data-path <path>] [--output-dir <path>]
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
# Constants derived from CUSTREC.cpy
# ---------------------------------------------------------------------------
RECORD_LENGTH = 500
COPYBOOK_NAME = "CUSTREC.cpy"

# Field definitions: (name, offset, length)
FIELD_DEFS = [
    ("CUST_ID",                   0,   9),
    ("CUST_FIRST_NAME",           9,  25),
    ("CUST_MIDDLE_NAME",         34,  25),
    ("CUST_LAST_NAME",           59,  25),
    ("CUST_ADDR_LINE_1",         84,  50),
    ("CUST_ADDR_LINE_2",        134,  50),
    ("CUST_ADDR_LINE_3",        184,  50),
    ("CUST_ADDR_STATE_CD",      234,   2),
    ("CUST_ADDR_COUNTRY_CD",    236,   3),
    ("CUST_ADDR_ZIP",           239,  10),
    ("CUST_PHONE_NUM_1",        249,  15),
    ("CUST_PHONE_NUM_2",        264,  15),
    ("CUST_SSN",                279,   9),
    ("CUST_GOVT_ISSUED_ID",     288,  20),
    ("CUST_DOB_YYYYMMDD",       308,  10),
    ("CUST_EFT_ACCOUNT_ID",     318,  10),
    ("CUST_PRI_CARD_HOLDER_IND",328,   1),
    ("CUST_FICO_CREDIT_SCORE",  329,   3),
    ("FILLER",                  332, 168),
]

# Alphanumeric fields to trim trailing spaces
ALPHA_FIELDS = [
    "CUST_FIRST_NAME", "CUST_MIDDLE_NAME", "CUST_LAST_NAME",
    "CUST_ADDR_LINE_1", "CUST_ADDR_LINE_2", "CUST_ADDR_LINE_3",
    "CUST_ADDR_STATE_CD", "CUST_ADDR_COUNTRY_CD", "CUST_ADDR_ZIP",
    "CUST_PHONE_NUM_1", "CUST_PHONE_NUM_2",
    "CUST_GOVT_ISSUED_ID", "CUST_DOB_YYYYMMDD", "CUST_EFT_ACCOUNT_ID",
    "CUST_PRI_CARD_HOLDER_IND", "FILLER",
]


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Parse COBOL CUSTOMER-RECORD fixed-width file with PySpark"
    )
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    parser.add_argument(
        "--data-path",
        default=os.path.join(repo_root, "app", "data", "ASCII", "custdata.txt"),
        help="Path to the custdata.txt fixed-width file",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(repo_root, "pyspark_parsing", "validation"),
        help="Directory to write validation output",
    )
    return parser.parse_args()


def build_dataframe(spark, data_path):
    """Read the fixed-width file and parse fields per the CUSTREC.cpy layout.

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
    # CUST_ID: PIC 9(09) → LongType
    parsed_df = parsed_df.withColumn(
        "CUST_ID", col("CUST_ID").cast(LongType())
    )

    # CUST_SSN: PIC 9(09) → keep as StringType to preserve leading zeros
    # (already a string from substring extraction)

    # CUST_FICO_CREDIT_SCORE: PIC 9(03) → IntegerType
    parsed_df = parsed_df.withColumn(
        "CUST_FICO_CREDIT_SCORE",
        col("CUST_FICO_CREDIT_SCORE").cast(IntegerType())
    )

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
    numeric_fields = ["CUST_ID", "CUST_FICO_CREDIT_SCORE"]
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
    report_path = os.path.join(output_dir, "custdata_validation.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Print summary to stdout
    print("=" * 70)
    print(f"VALIDATION REPORT — {COPYBOOK_NAME} → custdata.txt")
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
        .appName("COBOL_Custdata_Parser") \
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
