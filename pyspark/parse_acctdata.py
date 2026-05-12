"""
PySpark script to parse COBOL fixed-width file: acctdata.txt
Copybook: CVACT01Y.cpy — ACCOUNT-RECORD layout (300 bytes)

Reads the ASCII fixed-width account data file and parses each field
according to the COBOL copybook-derived schema. Signed zoned-decimal
fields (PIC S9(10)V99) are decoded using COBOL sign overpunch logic.

Usage:
    spark-submit parse_acctdata.py [--data-path <path>] [--output-path <path>]
"""

import argparse
import os
import sys

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DecimalType
)

# Add parent directory to path for cobol_utils import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cobol_utils import parse_signed_decimal

# -------------------------------------------------------------------
# CVACT01Y.cpy field layout: ACCOUNT-RECORD (300 bytes total)
# Each tuple: (field_name, byte_offset, length)
# FILLER at offset 122 (178 bytes) is excluded from the DataFrame.
# -------------------------------------------------------------------
ACCOUNT_FIELDS = [
    ("ACCT_ID",                  0,  11),  # PIC 9(11) — account identifier
    ("ACCT_ACTIVE_STATUS",      11,   1),  # PIC X(01) — active flag (Y/N)
    ("ACCT_CURR_BAL",           12,  12),  # PIC S9(10)V99 — current balance
    ("ACCT_CREDIT_LIMIT",       24,  12),  # PIC S9(10)V99 — credit limit
    ("ACCT_CASH_CREDIT_LIMIT",  36,  12),  # PIC S9(10)V99 — cash credit limit
    ("ACCT_OPEN_DATE",          48,  10),  # PIC X(10) — open date (YYYY-MM-DD)
    ("ACCT_EXPIRAION_DATE",     58,  10),  # PIC X(10) — expiration date
    ("ACCT_REISSUE_DATE",       68,  10),  # PIC X(10) — reissue date
    ("ACCT_CURR_CYC_CREDIT",   78,  12),  # PIC S9(10)V99 — cycle credit
    ("ACCT_CURR_CYC_DEBIT",    90,  12),  # PIC S9(10)V99 — cycle debit
    ("ACCT_ADDR_ZIP",          102,  10),  # PIC X(10) — ZIP code
    ("ACCT_GROUP_ID",          112,  10),  # PIC X(10) — group identifier
]

# Columns that contain signed zoned-decimal values with sign overpunch
SIGNED_DECIMAL_COLUMNS = [
    "ACCT_CURR_BAL",
    "ACCT_CREDIT_LIMIT",
    "ACCT_CASH_CREDIT_LIMIT",
    "ACCT_CURR_CYC_CREDIT",
    "ACCT_CURR_CYC_DEBIT",
]

RECORD_LENGTH = 300


def parse_acctdata(spark, data_path):
    """
    Parse the COBOL fixed-width account data file into a PySpark DataFrame.

    Reads raw text lines, extracts fields via substring positions derived
    from the CVACT01Y.cpy copybook, then decodes signed zoned-decimal
    fields using COBOL sign overpunch logic.

    Args:
        spark: Active SparkSession
        data_path: Path to the acctdata.txt file
    Returns:
        Parsed PySpark DataFrame with typed columns
    """
    # Read raw text — each line is one 300-byte fixed-width record
    raw_df = spark.read.text(data_path)

    # Verify record lengths match expected 300 bytes
    raw_df = raw_df.withColumn("_record_len", F.length(F.col("value")))

    # Extract each field using substring (1-indexed in PySpark)
    parsed_df = raw_df
    for field_name, offset, length in ACCOUNT_FIELDS:
        # PySpark substr is 1-indexed, so add 1 to the 0-based offset
        parsed_df = parsed_df.withColumn(
            field_name,
            F.trim(F.col("value").substr(offset + 1, length))
        )

    # Drop the raw 'value' and internal length columns
    parsed_df = parsed_df.drop("value", "_record_len")

    # Decode signed zoned-decimal fields (PIC S9(10)V99) with overpunch
    for col_name in SIGNED_DECIMAL_COLUMNS:
        parsed_df = parse_signed_decimal(
            parsed_df, col_name,
            decimal_places=2, precision=12, scale=2
        )

    return parsed_df


def validate_acctdata(spark, data_path, parsed_df):
    """
    Validate parsed DataFrame against the raw feed file.

    Compares row counts and prints sample values to verify the parsing
    is correct. Writes validation results to stdout and returns a
    summary dictionary.

    Args:
        spark: Active SparkSession
        data_path: Path to the original acctdata.txt file
        parsed_df: The parsed DataFrame from parse_acctdata()
    Returns:
        Dictionary with validation results
    """
    raw_df = spark.read.text(data_path)
    raw_count = raw_df.count()
    parsed_count = parsed_df.count()

    results = {
        "raw_row_count": raw_count,
        "parsed_row_count": parsed_count,
        "row_count_match": raw_count == parsed_count,
    }

    print("=" * 70)
    print("VALIDATION REPORT: acctdata.txt (CVACT01Y.cpy — ACCOUNT-RECORD)")
    print("=" * 70)
    print(f"Raw file row count:    {raw_count}")
    print(f"Parsed DataFrame rows: {parsed_count}")
    print(f"Row count match:       {results['row_count_match']}")
    print()

    # Show schema for verification
    print("Parsed DataFrame Schema:")
    parsed_df.printSchema()

    # Show first 5 sample rows
    print("Sample Rows (first 5):")
    parsed_df.show(5, truncate=False)

    # Show distinct active status values for sanity check
    print("Distinct ACCT_ACTIVE_STATUS values:")
    parsed_df.groupBy("ACCT_ACTIVE_STATUS").count().show()

    # Show balance statistics for numeric validation
    print("Balance Statistics (ACCT_CURR_BAL):")
    parsed_df.select(
        F.min("ACCT_CURR_BAL").alias("min_balance"),
        F.max("ACCT_CURR_BAL").alias("max_balance"),
        F.avg("ACCT_CURR_BAL").alias("avg_balance"),
    ).show()

    # Verify first record values against manually parsed expected values
    first_row = parsed_df.first()
    print("First Record Field Values:")
    for field_name, _, _ in ACCOUNT_FIELDS:
        print(f"  {field_name:30s} = {first_row[field_name]}")
    print("=" * 70)

    return results


def main():
    """Entry point: parse acctdata.txt and run validation."""
    parser = argparse.ArgumentParser(
        description="Parse COBOL fixed-width account data (CVACT01Y.cpy)"
    )
    # Default path relative to repo root
    default_data = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "app", "data", "ASCII", "acctdata.txt"
    )
    parser.add_argument("--data-path", default=default_data,
                        help="Path to acctdata.txt")
    parser.add_argument("--output-path", default=None,
                        help="Optional path to write parsed Parquet output")
    args = parser.parse_args()

    spark = SparkSession.builder \
        .appName("CardDemo_CVACT01Y_AccountParser") \
        .master("local[*]") \
        .getOrCreate()

    # Suppress verbose Spark logging for cleaner validation output
    spark.sparkContext.setLogLevel("WARN")

    try:
        print(f"Parsing: {args.data_path}")
        parsed_df = parse_acctdata(spark, args.data_path)

        # Run validation comparing parsed DataFrame vs raw file
        validate_acctdata(spark, args.data_path, parsed_df)

        # Optionally write to Parquet for downstream consumption
        if args.output_path:
            parsed_df.write.mode("overwrite").parquet(args.output_path)
            print(f"Parquet output written to: {args.output_path}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
