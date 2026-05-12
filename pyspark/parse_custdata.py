"""
PySpark script to parse COBOL fixed-width file: custdata.txt
Copybook: CUSTREC.cpy — CUSTOMER-RECORD layout (500 bytes)

Reads the ASCII fixed-width customer data file and parses each field
according to the COBOL copybook-derived schema. This copybook uses
only PIC X (alphanumeric) and PIC 9 (unsigned zoned-decimal) fields,
with no signed overpunch encoding required.

Usage:
    spark-submit parse_custdata.py [--data-path <path>] [--output-path <path>]
"""

import argparse
import os
import sys

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType
)

# -------------------------------------------------------------------
# CUSTREC.cpy field layout: CUSTOMER-RECORD (500 bytes total)
# Each tuple: (field_name, byte_offset, length, cast_type)
# FILLER at offset 332 (168 bytes) is excluded from the DataFrame.
# cast_type: None = keep as trimmed StringType, "int" = cast to Integer
# -------------------------------------------------------------------
CUSTOMER_FIELDS = [
    ("CUST_ID",                  0,   9, None),   # PIC 9(09) — customer ID (StringType for leading zeros)
    ("CUST_FIRST_NAME",          9,  25, None),   # PIC X(25) — first name
    ("CUST_MIDDLE_NAME",        34,  25, None),   # PIC X(25) — middle name
    ("CUST_LAST_NAME",          59,  25, None),   # PIC X(25) — last name
    ("CUST_ADDR_LINE_1",        84,  50, None),   # PIC X(50) — address line 1
    ("CUST_ADDR_LINE_2",       134,  50, None),   # PIC X(50) — address line 2
    ("CUST_ADDR_LINE_3",       184,  50, None),   # PIC X(50) — address line 3 (city)
    ("CUST_ADDR_STATE_CD",     234,   2, None),   # PIC X(02) — state code
    ("CUST_ADDR_COUNTRY_CD",   236,   3, None),   # PIC X(03) — country code
    ("CUST_ADDR_ZIP",          239,  10, None),   # PIC X(10) — ZIP code
    ("CUST_PHONE_NUM_1",       249,  15, None),   # PIC X(15) — primary phone
    ("CUST_PHONE_NUM_2",       264,  15, None),   # PIC X(15) — secondary phone
    ("CUST_SSN",               279,   9, None),   # PIC 9(09) — SSN (StringType for leading zeros)
    ("CUST_GOVT_ISSUED_ID",    288,  20, None),   # PIC X(20) — government ID
    ("CUST_DOB_YYYYMMDD",      308,  10, None),   # PIC X(10) — date of birth (YYYY-MM-DD)
    ("CUST_EFT_ACCOUNT_ID",    318,  10, None),   # PIC X(10) — EFT account ID
    ("CUST_PRI_CARD_HOLDER_IND", 328, 1, None),   # PIC X(01) — primary cardholder flag
    ("CUST_FICO_CREDIT_SCORE", 329,   3, "int"),  # PIC 9(03) — FICO score (IntegerType)
]

RECORD_LENGTH = 500


def parse_custdata(spark, data_path):
    """
    Parse the COBOL fixed-width customer data file into a PySpark DataFrame.

    Reads raw text lines, extracts fields via substring positions derived
    from the CUSTREC.cpy copybook. PIC X fields are trimmed strings; the
    FICO credit score (PIC 9(03)) is cast to IntegerType.

    Args:
        spark: Active SparkSession
        data_path: Path to the custdata.txt file
    Returns:
        Parsed PySpark DataFrame with typed columns
    """
    # Read raw text — each line is one 500-byte fixed-width record
    raw_df = spark.read.text(data_path)

    # Extract each field using substring (PySpark substr is 1-indexed)
    parsed_df = raw_df
    for field_name, offset, length, cast_type in CUSTOMER_FIELDS:
        parsed_df = parsed_df.withColumn(
            field_name,
            F.trim(F.col("value").substr(offset + 1, length))
        )

    # Drop the raw 'value' column
    parsed_df = parsed_df.drop("value")

    # Cast FICO credit score from string to integer
    parsed_df = parsed_df.withColumn(
        "CUST_FICO_CREDIT_SCORE",
        F.col("CUST_FICO_CREDIT_SCORE").cast(IntegerType())
    )

    return parsed_df


def validate_custdata(spark, data_path, parsed_df):
    """
    Validate parsed DataFrame against the raw feed file.

    Compares row counts and prints sample values to verify parsing
    correctness.

    Args:
        spark: Active SparkSession
        data_path: Path to the original custdata.txt file
        parsed_df: The parsed DataFrame from parse_custdata()
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
    print("VALIDATION REPORT: custdata.txt (CUSTREC.cpy — CUSTOMER-RECORD)")
    print("=" * 70)
    print(f"Raw file row count:    {raw_count}")
    print(f"Parsed DataFrame rows: {parsed_count}")
    print(f"Row count match:       {results['row_count_match']}")
    print()

    # Show schema for verification
    print("Parsed DataFrame Schema:")
    parsed_df.printSchema()

    # Show first 5 sample rows (selected key columns to fit display)
    print("Sample Rows — Key Columns (first 5):")
    parsed_df.select(
        "CUST_ID", "CUST_FIRST_NAME", "CUST_LAST_NAME",
        "CUST_ADDR_STATE_CD", "CUST_ADDR_ZIP", "CUST_SSN",
        "CUST_DOB_YYYYMMDD", "CUST_FICO_CREDIT_SCORE"
    ).show(5, truncate=False)

    # Show distinct state codes for sanity check
    print("Distinct CUST_ADDR_STATE_CD values:")
    parsed_df.groupBy("CUST_ADDR_STATE_CD").count().orderBy("count", ascending=False).show(10)

    # Show FICO score statistics
    print("FICO Credit Score Statistics:")
    parsed_df.select(
        F.min("CUST_FICO_CREDIT_SCORE").alias("min_fico"),
        F.max("CUST_FICO_CREDIT_SCORE").alias("max_fico"),
        F.avg("CUST_FICO_CREDIT_SCORE").alias("avg_fico"),
    ).show()

    # Verify first record values
    first_row = parsed_df.first()
    print("First Record Field Values:")
    for field_name, _, _, _ in CUSTOMER_FIELDS:
        print(f"  {field_name:30s} = {first_row[field_name]}")
    print("=" * 70)

    return results


def main():
    """Entry point: parse custdata.txt and run validation."""
    parser = argparse.ArgumentParser(
        description="Parse COBOL fixed-width customer data (CUSTREC.cpy)"
    )
    default_data = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "app", "data", "ASCII", "custdata.txt"
    )
    parser.add_argument("--data-path", default=default_data,
                        help="Path to custdata.txt")
    parser.add_argument("--output-path", default=None,
                        help="Optional path to write parsed Parquet output")
    args = parser.parse_args()

    spark = SparkSession.builder \
        .appName("CardDemo_CUSTREC_CustomerParser") \
        .master("local[*]") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    try:
        print(f"Parsing: {args.data_path}")
        parsed_df = parse_custdata(spark, args.data_path)

        # Run validation comparing parsed DataFrame vs raw file
        validate_custdata(spark, args.data_path, parsed_df)

        if args.output_path:
            parsed_df.write.mode("overwrite").parquet(args.output_path)
            print(f"Parquet output written to: {args.output_path}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
