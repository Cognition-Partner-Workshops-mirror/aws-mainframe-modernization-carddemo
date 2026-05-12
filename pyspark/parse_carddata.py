"""
PySpark script to parse COBOL fixed-width file: carddata.txt
Copybook: CVACT02Y.cpy — CARD-RECORD layout (150 bytes)

Reads the ASCII fixed-width card data file and parses each field
according to the COBOL copybook-derived schema. This copybook uses
PIC X (alphanumeric) and PIC 9 (unsigned zoned-decimal) fields only,
with no signed overpunch encoding required.

Usage:
    spark-submit parse_carddata.py [--data-path <path>] [--output-path <path>]
"""

import argparse
import os
import sys

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType
)

# -------------------------------------------------------------------
# CVACT02Y.cpy field layout: CARD-RECORD (150 bytes total)
# Each tuple: (field_name, byte_offset, length)
# FILLER at offset 91 (59 bytes) is excluded from the DataFrame.
# -------------------------------------------------------------------
CARD_FIELDS = [
    ("CARD_NUM",             0,  16),  # PIC X(16) — card number
    ("CARD_ACCT_ID",        16,  11),  # PIC 9(11) — associated account ID
    ("CARD_CVV_CD",         27,   3),  # PIC 9(03) — CVV code
    ("CARD_EMBOSSED_NAME",  30,  50),  # PIC X(50) — name on card
    ("CARD_EXPIRAION_DATE", 80,  10),  # PIC X(10) — expiration date (YYYY-MM-DD)
    ("CARD_ACTIVE_STATUS",  90,   1),  # PIC X(01) — active flag (Y/N)
]

RECORD_LENGTH = 150


def parse_carddata(spark, data_path):
    """
    Parse the COBOL fixed-width card data file into a PySpark DataFrame.

    Reads raw text lines, extracts fields via substring positions derived
    from the CVACT02Y.cpy copybook. All fields are kept as StringType;
    PIC 9 fields (CARD_ACCT_ID, CARD_CVV_CD) retain leading zeros.

    Args:
        spark: Active SparkSession
        data_path: Path to the carddata.txt file
    Returns:
        Parsed PySpark DataFrame with typed columns
    """
    # Read raw text — each line is one 150-byte fixed-width record
    raw_df = spark.read.text(data_path)

    # Extract each field using substring (PySpark substr is 1-indexed)
    parsed_df = raw_df
    for field_name, offset, length in CARD_FIELDS:
        parsed_df = parsed_df.withColumn(
            field_name,
            F.trim(F.col("value").substr(offset + 1, length))
        )

    # Drop the raw 'value' column
    parsed_df = parsed_df.drop("value")

    return parsed_df


def validate_carddata(spark, data_path, parsed_df):
    """
    Validate parsed DataFrame against the raw feed file.

    Compares row counts and prints sample values to verify parsing
    correctness.

    Args:
        spark: Active SparkSession
        data_path: Path to the original carddata.txt file
        parsed_df: The parsed DataFrame from parse_carddata()
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
    print("VALIDATION REPORT: carddata.txt (CVACT02Y.cpy — CARD-RECORD)")
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

    # Show distinct active status values
    print("Distinct CARD_ACTIVE_STATUS values:")
    parsed_df.groupBy("CARD_ACTIVE_STATUS").count().show()

    # Check card number lengths for consistency
    print("Card Number Length Distribution:")
    parsed_df.select(
        F.length("CARD_NUM").alias("card_num_length")
    ).groupBy("card_num_length").count().show()

    # Verify first record values
    first_row = parsed_df.first()
    print("First Record Field Values:")
    for field_name, _, _ in CARD_FIELDS:
        print(f"  {field_name:30s} = {first_row[field_name]}")
    print("=" * 70)

    return results


def main():
    """Entry point: parse carddata.txt and run validation."""
    parser = argparse.ArgumentParser(
        description="Parse COBOL fixed-width card data (CVACT02Y.cpy)"
    )
    default_data = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "app", "data", "ASCII", "carddata.txt"
    )
    parser.add_argument("--data-path", default=default_data,
                        help="Path to carddata.txt")
    parser.add_argument("--output-path", default=None,
                        help="Optional path to write parsed Parquet output")
    args = parser.parse_args()

    spark = SparkSession.builder \
        .appName("CardDemo_CVACT02Y_CardParser") \
        .master("local[*]") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    try:
        print(f"Parsing: {args.data_path}")
        parsed_df = parse_carddata(spark, args.data_path)

        # Run validation comparing parsed DataFrame vs raw file
        validate_carddata(spark, args.data_path, parsed_df)

        if args.output_path:
            parsed_df.write.mode("overwrite").parquet(args.output_path)
            print(f"Parquet output written to: {args.output_path}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
