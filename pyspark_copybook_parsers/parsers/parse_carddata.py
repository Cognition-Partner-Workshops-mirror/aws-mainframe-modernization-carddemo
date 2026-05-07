"""
PySpark parser for COBOL copybook CVACT02Y.cpy → carddata.txt

Reads the fixed-width Card Record file (150 bytes per line) and applies
the field layout defined in app/cpy/CVACT02Y.cpy.  All fields in this
copybook use DISPLAY format with no sign-overpunch.

Usage:
    spark-submit parse_carddata.py [--input <path>] [--output <path>]
"""

import argparse
import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType


# ---------------------------------------------------------------------------
# Field layout derived from CVACT02Y.cpy  (CARD-RECORD, 150 bytes)
#   offset is 1-based for PySpark substr()
# ---------------------------------------------------------------------------
CARD_FIELDS = [
    # (field_name,              offset, length)
    ("CARD_NUM",                     1,  16),
    ("CARD_ACCT_ID",                17,  11),
    ("CARD_CVV_CD",                 28,   3),
    ("CARD_EMBOSSED_NAME",          31,  50),
    ("CARD_EXPIRAION_DATE",         81,  10),
    ("CARD_ACTIVE_STATUS",          91,   1),
    ("FILLER",                      92,  59),
]

RECORD_LENGTH = 150  # total bytes per record


def parse_carddata(spark: SparkSession, input_path: str):
    """Read carddata.txt as a fixed-width file and return a parsed DataFrame.

    Each line is expected to be exactly 150 characters (matching RECLN 150
    declared in the copybook).
    """
    # Read raw lines
    raw_df = spark.read.text(input_path)

    # Slice each field using substr (1-based offsets)
    parsed = raw_df
    for name, offset, length in CARD_FIELDS:
        # Trim trailing spaces from every field
        col_expr = F.trim(F.substring(F.col("value"), offset, length))
        parsed = parsed.withColumn(name, col_expr)

    # Drop the raw line and FILLER columns
    parsed = parsed.drop("value", "FILLER")
    return parsed


def main():
    parser = argparse.ArgumentParser(
        description="Parse COBOL CVACT02Y card data into PySpark DataFrame")
    default_input = os.path.join(
        os.path.dirname(__file__), "..", "..", "app", "data", "ASCII",
        "carddata.txt")
    parser.add_argument("--input", default=default_input,
                        help="Path to carddata.txt")
    parser.add_argument("--output", default=None,
                        help="Optional output path (parquet)")
    args = parser.parse_args()

    spark = SparkSession.builder \
        .appName("CVACT02Y_CardParser") \
        .master("local[*]") \
        .getOrCreate()

    df = parse_carddata(spark, args.input)

    # Show parsed results
    print(f"\n=== Parsed Card Records (CVACT02Y) ===")
    print(f"Total rows: {df.count()}")
    df.printSchema()
    df.show(10, truncate=False)

    if args.output:
        df.write.mode("overwrite").parquet(args.output)
        print(f"Written to {args.output}")

    spark.stop()


if __name__ == "__main__":
    main()
