"""
PySpark script to parse app/data/ASCII/carddata.txt as a fixed-width file.

Derived from COBOL copybook: app/cpy/CVACT02Y.cpy
Record layout: CARD-RECORD (150 bytes)

This script reads each line as a raw string, extracts fields using byte-offset
slicing, and exposes the result as a typed PySpark DataFrame.

All fields in this record are either unsigned numeric (PIC 9) or alphanumeric
(PIC X), so no sign-overpunch decoding is required.

Type-mapping decisions are documented in COPYBOOK_PARSING_NOTES.md.
"""

import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, substring, trim
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, IntegerType
)

# ---------------------------------------------------------------------------
# Field layout derived from CVACT02Y.cpy
# Each tuple: (field_name, start_pos (1-based), length)
# ---------------------------------------------------------------------------
FIELD_LAYOUT = [
    ("CARD_NUM",              1,  16),
    ("CARD_ACCT_ID",         17,  11),
    ("CARD_CVV_CD",          28,   3),
    ("CARD_EMBOSSED_NAME",   31,  50),
    ("CARD_EXPIRAION_DATE",  81,  10),
    ("CARD_ACTIVE_STATUS",   91,   1),
    ("FILLER",               92,  59),
]

# Fields to cast from display-numeric strings to integer types
NUMERIC_FIELDS = {
    "CARD_ACCT_ID": LongType(),    # PIC 9(11) — 11-digit unsigned integer
    "CARD_CVV_CD": IntegerType(),  # PIC 9(03) — 3-digit CVV code
}


def main():
    """Read carddata.txt, apply copybook schema, print schema and first 5 rows."""

    spark = SparkSession.builder \
        .appName("CardDemo_CVACT02Y_CardData_Parser") \
        .master("local[*]") \
        .getOrCreate()

    # Resolve the data file path relative to this script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    data_path = os.path.join(repo_root, "app", "data", "ASCII", "carddata.txt")

    # Read the file as raw text — one line per record
    raw_df = spark.read.text(data_path)

    # Extract each field using substring (1-based positions)
    df = raw_df
    for field_name, start, length in FIELD_LAYOUT:
        df = df.withColumn(field_name, substring(col("value"), start, length))

    # Drop the raw line and the FILLER column
    df = df.drop("value", "FILLER")

    # Cast unsigned numeric fields to their target types
    for field_name, target_type in NUMERIC_FIELDS.items():
        df = df.withColumn(field_name, col(field_name).cast(target_type))

    # Trim trailing spaces from all remaining string fields
    string_fields = [
        name for name, _, _ in FIELD_LAYOUT
        if name not in NUMERIC_FIELDS and name != "FILLER"
    ]
    for field_name in string_fields:
        df = df.withColumn(field_name, trim(col(field_name)))

    # Print the DataFrame schema and the first 5 rows for validation
    print("=" * 80)
    print("CARD-RECORD DataFrame Schema (from CVACT02Y.cpy)")
    print("=" * 80)
    df.printSchema()

    print("=" * 80)
    print("First 5 rows of carddata.txt")
    print("=" * 80)
    df.show(5, truncate=False)

    spark.stop()


if __name__ == "__main__":
    main()
