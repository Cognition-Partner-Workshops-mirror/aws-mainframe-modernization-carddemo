"""
PySpark script to parse the COBOL fixed-width customer data file (custdata.txt)
using the field layout defined in copybook CUSTREC.cpy.

Record layout: CUSTOMER-RECORD, 500 bytes per line.
All fields are either alphanumeric (PIC X) or unsigned numeric display (PIC 9).
No signed zoned-decimal fields in this copybook.

Usage:
    spark-submit parse_custdata.py
    # or
    python parse_custdata.py
"""

import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql.types import IntegerType, LongType, StringType

# Ensure the scripts directory is on the path for shared utility imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cobol_parser_utils import build_pyspark_schema, extract_fixed_width_fields

# ---------------------------------------------------------------------------
# Field definitions derived from CUSTREC.cpy (CUSTOMER-RECORD, 500 bytes)
# Each entry maps a COBOL field to its PySpark type, byte offset, and length.
# ---------------------------------------------------------------------------
CUSTOMER_FIELDS = [
    {"name": "CUST_ID",                "pic": "PIC 9(09)",  "spark_type": LongType(),      "offset": 0,   "length": 9},
    {"name": "CUST_FIRST_NAME",        "pic": "PIC X(25)",  "spark_type": StringType(),    "offset": 9,   "length": 25},
    {"name": "CUST_MIDDLE_NAME",       "pic": "PIC X(25)",  "spark_type": StringType(),    "offset": 34,  "length": 25},
    {"name": "CUST_LAST_NAME",         "pic": "PIC X(25)",  "spark_type": StringType(),    "offset": 59,  "length": 25},
    {"name": "CUST_ADDR_LINE_1",       "pic": "PIC X(50)",  "spark_type": StringType(),    "offset": 84,  "length": 50},
    {"name": "CUST_ADDR_LINE_2",       "pic": "PIC X(50)",  "spark_type": StringType(),    "offset": 134, "length": 50},
    {"name": "CUST_ADDR_LINE_3",       "pic": "PIC X(50)",  "spark_type": StringType(),    "offset": 184, "length": 50},
    {"name": "CUST_ADDR_STATE_CD",     "pic": "PIC X(02)",  "spark_type": StringType(),    "offset": 234, "length": 2},
    {"name": "CUST_ADDR_COUNTRY_CD",   "pic": "PIC X(03)",  "spark_type": StringType(),    "offset": 236, "length": 3},
    {"name": "CUST_ADDR_ZIP",          "pic": "PIC X(10)",  "spark_type": StringType(),    "offset": 239, "length": 10},
    {"name": "CUST_PHONE_NUM_1",       "pic": "PIC X(15)",  "spark_type": StringType(),    "offset": 249, "length": 15},
    {"name": "CUST_PHONE_NUM_2",       "pic": "PIC X(15)",  "spark_type": StringType(),    "offset": 264, "length": 15},
    {"name": "CUST_SSN",               "pic": "PIC 9(09)",  "spark_type": LongType(),      "offset": 279, "length": 9},
    {"name": "CUST_GOVT_ISSUED_ID",    "pic": "PIC X(20)",  "spark_type": StringType(),    "offset": 288, "length": 20},
    {"name": "CUST_DOB_YYYYMMDD",      "pic": "PIC X(10)",  "spark_type": StringType(),    "offset": 308, "length": 10},
    {"name": "CUST_EFT_ACCOUNT_ID",    "pic": "PIC X(10)",  "spark_type": StringType(),    "offset": 318, "length": 10},
    {"name": "CUST_PRI_CARD_HOLDER_IND","pic": "PIC X(01)", "spark_type": StringType(),    "offset": 328, "length": 1},
    {"name": "CUST_FICO_CREDIT_SCORE", "pic": "PIC 9(03)",  "spark_type": IntegerType(),   "offset": 329, "length": 3},
    # FILLER is included for completeness but typically excluded from analytics
    {"name": "FILLER",                 "pic": "PIC X(168)", "spark_type": StringType(),    "offset": 332, "length": 168},
]


def main():
    """Parse custdata.txt and display the resulting DataFrame."""
    # Resolve paths relative to the repository root
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    data_path = os.path.join(repo_root, "app", "data", "ASCII", "custdata.txt")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Initialize Spark session
    spark = SparkSession.builder \
        .appName("CardDemo_CUSTREC_CustomerParser") \
        .master("local[*]") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    print("=" * 80)
    print("Parsing CUSTOMER-RECORD from CUSTREC.cpy -> custdata.txt")
    print(f"Data file: {data_path}")
    print(f"Expected record length: 500 bytes")
    print("=" * 80)

    # Read the fixed-width file as raw text lines
    raw_df = spark.read.text(data_path)
    raw_count = raw_df.count()
    print(f"\nRaw line count: {raw_count}")

    # Extract and type fields using the copybook-derived layout
    parsed_df = extract_fixed_width_fields(raw_df, CUSTOMER_FIELDS)

    # Drop the FILLER column for display
    display_df = parsed_df.drop("FILLER")

    print(f"Parsed row count: {display_df.count()}")
    print("\nSchema:")
    display_df.printSchema()
    print("\nFirst 10 rows:")
    display_df.show(10, truncate=False)

    # Write parsed output as CSV for downstream validation
    output_path = os.path.join(output_dir, "custdata_parsed.csv")
    display_df.toPandas().to_csv(output_path, index=False)
    print(f"\nParsed output written to: {output_path}")

    spark.stop()


if __name__ == "__main__":
    main()
