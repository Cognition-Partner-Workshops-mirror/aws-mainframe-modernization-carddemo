"""
PySpark script to parse the COBOL fixed-width account data file (acctdata.txt)
using the field layout defined in copybook CVACT01Y.cpy.

Record layout: ACCOUNT-RECORD, 300 bytes per line.
Signed zoned-decimal fields use trailing overpunch encoding (ASCII convention).

Usage:
    spark-submit parse_acctdata.py
    # or
    python parse_acctdata.py
"""

import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql.types import DecimalType, LongType, StringType

# Ensure the scripts directory is on the path for shared utility imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cobol_parser_utils import build_pyspark_schema, extract_fixed_width_fields

# ---------------------------------------------------------------------------
# Field definitions derived from CVACT01Y.cpy (ACCOUNT-RECORD, 300 bytes)
# Each entry maps a COBOL field to its PySpark type, byte offset, and length.
# Offsets are cumulative: each field starts where the previous one ends.
# ---------------------------------------------------------------------------
ACCOUNT_FIELDS = [
    {"name": "ACCT_ID",               "pic": "PIC 9(11)",      "spark_type": LongType(),          "offset": 0,   "length": 11},
    {"name": "ACCT_ACTIVE_STATUS",    "pic": "PIC X(01)",      "spark_type": StringType(),        "offset": 11,  "length": 1},
    {"name": "ACCT_CURR_BAL",         "pic": "PIC S9(10)V99",  "spark_type": DecimalType(12, 2),  "offset": 12,  "length": 12},
    {"name": "ACCT_CREDIT_LIMIT",     "pic": "PIC S9(10)V99",  "spark_type": DecimalType(12, 2),  "offset": 24,  "length": 12},
    {"name": "ACCT_CASH_CREDIT_LIMIT","pic": "PIC S9(10)V99",  "spark_type": DecimalType(12, 2),  "offset": 36,  "length": 12},
    {"name": "ACCT_OPEN_DATE",        "pic": "PIC X(10)",      "spark_type": StringType(),        "offset": 48,  "length": 10},
    {"name": "ACCT_EXPIRAION_DATE",   "pic": "PIC X(10)",      "spark_type": StringType(),        "offset": 58,  "length": 10},
    {"name": "ACCT_REISSUE_DATE",     "pic": "PIC X(10)",      "spark_type": StringType(),        "offset": 68,  "length": 10},
    {"name": "ACCT_CURR_CYC_CREDIT",  "pic": "PIC S9(10)V99",  "spark_type": DecimalType(12, 2),  "offset": 78,  "length": 12},
    {"name": "ACCT_CURR_CYC_DEBIT",   "pic": "PIC S9(10)V99",  "spark_type": DecimalType(12, 2),  "offset": 90,  "length": 12},
    {"name": "ACCT_ADDR_ZIP",         "pic": "PIC X(10)",      "spark_type": StringType(),        "offset": 102, "length": 10},
    {"name": "ACCT_GROUP_ID",         "pic": "PIC X(10)",      "spark_type": StringType(),        "offset": 112, "length": 10},
    # FILLER is included for completeness but typically excluded from analytics
    {"name": "FILLER",                "pic": "PIC X(178)",     "spark_type": StringType(),        "offset": 122, "length": 178},
]


def main():
    """Parse acctdata.txt and display the resulting DataFrame."""
    # Resolve paths relative to the repository root
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    data_path = os.path.join(repo_root, "app", "data", "ASCII", "acctdata.txt")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Initialize Spark session
    spark = SparkSession.builder \
        .appName("CardDemo_CVACT01Y_AccountParser") \
        .master("local[*]") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    print("=" * 80)
    print("Parsing ACCOUNT-RECORD from CVACT01Y.cpy -> acctdata.txt")
    print(f"Data file: {data_path}")
    print(f"Expected record length: 300 bytes")
    print("=" * 80)

    # Read the fixed-width file as raw text lines
    raw_df = spark.read.text(data_path)
    raw_count = raw_df.count()
    print(f"\nRaw line count: {raw_count}")

    # Extract and type fields using the copybook-derived layout
    parsed_df = extract_fixed_width_fields(raw_df, ACCOUNT_FIELDS)

    # Drop the FILLER column for display (it's just padding)
    display_df = parsed_df.drop("FILLER")

    print(f"Parsed row count: {display_df.count()}")
    print("\nSchema:")
    display_df.printSchema()
    print("\nFirst 10 rows:")
    display_df.show(10, truncate=False)

    # Write parsed output as CSV for downstream validation
    output_path = os.path.join(output_dir, "acctdata_parsed.csv")
    display_df.toPandas().to_csv(output_path, index=False)
    print(f"\nParsed output written to: {output_path}")

    spark.stop()


if __name__ == "__main__":
    main()
