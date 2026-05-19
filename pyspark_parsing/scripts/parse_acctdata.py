"""
PySpark script to parse the ACCOUNT-RECORD fixed-width file (acctdata.txt)
using the schema derived from COBOL copybook CVACT01Y.cpy.

Record layout: 300 bytes per line.
Sign-encoded fields use COBOL trailing-overpunch convention for
PIC S9(10)V99 (signed zoned decimal with 2 implied decimal places).

Usage:
    spark-submit parse_acctdata.py [--data-path <path>] [--output-dir <path>]
"""

import argparse
import json
import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, trim, length as spark_length
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, DecimalType, IntegerType
)

# Add parent scripts dir to path so cobol_utils is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cobol_utils import make_signed_decimal_udf  # noqa: E402

# ---------------------------------------------------------------------------
# Constants derived from CVACT01Y.cpy
# ---------------------------------------------------------------------------
RECORD_LENGTH = 300
COPYBOOK_NAME = "CVACT01Y.cpy"

# Field definitions: (name, offset, length)
FIELD_DEFS = [
    ("ACCT_ID",                  0,  11),
    ("ACCT_ACTIVE_STATUS",      11,   1),
    ("ACCT_CURR_BAL",           12,  12),
    ("ACCT_CREDIT_LIMIT",       24,  12),
    ("ACCT_CASH_CREDIT_LIMIT",  36,  12),
    ("ACCT_OPEN_DATE",          48,  10),
    ("ACCT_EXPIRAION_DATE",     58,  10),
    ("ACCT_REISSUE_DATE",       68,  10),
    ("ACCT_CURR_CYC_CREDIT",   78,  12),
    ("ACCT_CURR_CYC_DEBIT",    90,  12),
    ("ACCT_ADDR_ZIP",          102,  10),
    ("ACCT_GROUP_ID",          112,  10),
    ("FILLER",                 122, 178),
]

# Signed decimal fields requiring overpunch decoding (2 implied decimals)
SIGNED_DECIMAL_FIELDS = [
    "ACCT_CURR_BAL",
    "ACCT_CREDIT_LIMIT",
    "ACCT_CASH_CREDIT_LIMIT",
    "ACCT_CURR_CYC_CREDIT",
    "ACCT_CURR_CYC_DEBIT",
]


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Parse COBOL ACCOUNT-RECORD fixed-width file with PySpark"
    )
    # Default paths are relative to repo root
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    parser.add_argument(
        "--data-path",
        default=os.path.join(repo_root, "app", "data", "ASCII", "acctdata.txt"),
        help="Path to the acctdata.txt fixed-width file",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(repo_root, "pyspark_parsing", "validation"),
        help="Directory to write validation output",
    )
    return parser.parse_args()


def build_dataframe(spark, data_path):
    """Read the fixed-width file and parse fields per the copybook layout.

    Reads each line as a single string column, then slices substrings
    according to the byte offsets defined in CVACT01Y.cpy.
    """
    # Read entire lines as single-column raw text
    raw_df = spark.read.text(data_path)

    # Slice each field from the raw line using substring (1-based index)
    parsed_df = raw_df
    for field_name, offset, field_length in FIELD_DEFS:
        # PySpark substring is 1-based
        parsed_df = parsed_df.withColumn(
            field_name,
            col("value").substr(offset + 1, field_length)
        )

    # Drop the original raw line column
    parsed_df = parsed_df.drop("value")

    # --- Type conversions ---
    # Decode signed zoned-decimal fields (PIC S9(10)V99)
    overpunch_udf = make_signed_decimal_udf(decimal_places=2)
    for field_name in SIGNED_DECIMAL_FIELDS:
        parsed_df = (
            parsed_df
            .withColumn(field_name, overpunch_udf(col(field_name)))
            .withColumn(field_name, col(field_name).cast(DecimalType(12, 2)))
        )

    # Cast unsigned numeric field ACCT_ID to LongType
    parsed_df = parsed_df.withColumn(
        "ACCT_ID", col("ACCT_ID").cast(LongType())
    )

    # Trim whitespace from alphanumeric fields
    alpha_fields = [
        "ACCT_ACTIVE_STATUS", "ACCT_OPEN_DATE", "ACCT_EXPIRAION_DATE",
        "ACCT_REISSUE_DATE", "ACCT_ADDR_ZIP", "ACCT_GROUP_ID", "FILLER",
    ]
    for field_name in alpha_fields:
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
    # Convert Decimal objects to strings for JSON serialization
    for row in sample_rows:
        for k, v in row.items():
            if hasattr(v, "as_tuple"):  # Decimal
                row[k] = str(v)

    # Summary statistics for numeric columns
    numeric_summary = {}
    for field_name in SIGNED_DECIMAL_FIELDS + ["ACCT_ID"]:
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
    report_path = os.path.join(output_dir, "acctdata_validation.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Print summary to stdout
    print("=" * 70)
    print(f"VALIDATION REPORT — {COPYBOOK_NAME} → acctdata.txt")
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
        .appName("COBOL_Acctdata_Parser") \
        .master("local[*]") \
        .getOrCreate()

    # Suppress verbose Spark logs for cleaner validation output
    spark.sparkContext.setLogLevel("WARN")

    # Ship cobol_utils module to Spark workers so the UDF can be deserialized
    cobol_utils_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "cobol_utils.py"
    )
    spark.sparkContext.addPyFile(cobol_utils_path)

    try:
        parsed_df = build_dataframe(spark, args.data_path)
        validate_and_report(spark, parsed_df, args.data_path, args.output_dir)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
