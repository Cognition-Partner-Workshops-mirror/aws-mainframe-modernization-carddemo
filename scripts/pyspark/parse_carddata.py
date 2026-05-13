"""
PySpark script to parse the COBOL fixed-width card data file (carddata.txt)
using the field layout defined in copybook CVACT02Y.cpy.

Record layout: CARD-RECORD, 150 bytes per line.
All fields are either alphanumeric (PIC X) or unsigned numeric display (PIC 9).
No signed zoned-decimal fields in this copybook.

Usage:
    spark-submit parse_carddata.py
    # or
    python parse_carddata.py
"""

import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql.types import IntegerType, LongType, StringType

# Ensure the scripts directory is on the path for shared utility imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cobol_parser_utils import build_pyspark_schema, extract_fixed_width_fields

# ---------------------------------------------------------------------------
# Field definitions derived from CVACT02Y.cpy (CARD-RECORD, 150 bytes)
# Each entry maps a COBOL field to its PySpark type, byte offset, and length.
# ---------------------------------------------------------------------------
CARD_FIELDS = [
    {"name": "CARD_NUM",            "pic": "PIC X(16)",  "spark_type": StringType(),    "offset": 0,   "length": 16},
    {"name": "CARD_ACCT_ID",        "pic": "PIC 9(11)",  "spark_type": LongType(),      "offset": 16,  "length": 11},
    {"name": "CARD_CVV_CD",         "pic": "PIC 9(03)",  "spark_type": IntegerType(),   "offset": 27,  "length": 3},
    {"name": "CARD_EMBOSSED_NAME",  "pic": "PIC X(50)",  "spark_type": StringType(),    "offset": 30,  "length": 50},
    {"name": "CARD_EXPIRAION_DATE", "pic": "PIC X(10)",  "spark_type": StringType(),    "offset": 80,  "length": 10},
    {"name": "CARD_ACTIVE_STATUS",  "pic": "PIC X(01)",  "spark_type": StringType(),    "offset": 90,  "length": 1},
    # FILLER is included for completeness but typically excluded from analytics
    {"name": "FILLER",              "pic": "PIC X(59)",  "spark_type": StringType(),    "offset": 91,  "length": 59},
]


def main():
    """Parse carddata.txt and display the resulting DataFrame."""
    # Resolve paths relative to the repository root
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    data_path = os.path.join(repo_root, "app", "data", "ASCII", "carddata.txt")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Initialize Spark session
    spark = SparkSession.builder \
        .appName("CardDemo_CVACT02Y_CardParser") \
        .master("local[*]") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    print("=" * 80)
    print("Parsing CARD-RECORD from CVACT02Y.cpy -> carddata.txt")
    print(f"Data file: {data_path}")
    print(f"Expected record length: 150 bytes")
    print("=" * 80)

    # Read the fixed-width file as raw text lines
    raw_df = spark.read.text(data_path)
    raw_count = raw_df.count()
    print(f"\nRaw line count: {raw_count}")

    # Extract and type fields using the copybook-derived layout
    parsed_df = extract_fixed_width_fields(raw_df, CARD_FIELDS)

    # Drop the FILLER column for display
    display_df = parsed_df.drop("FILLER")

    print(f"Parsed row count: {display_df.count()}")
    print("\nSchema:")
    display_df.printSchema()
    print("\nFirst 10 rows:")
    display_df.show(10, truncate=False)

    # Write parsed output as CSV for downstream validation
    output_path = os.path.join(output_dir, "carddata_parsed.csv")
    display_df.toPandas().to_csv(output_path, index=False)
    print(f"\nParsed output written to: {output_path}")

    spark.stop()


if __name__ == "__main__":
    main()
