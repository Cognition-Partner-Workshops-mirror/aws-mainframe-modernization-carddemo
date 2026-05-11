"""
PySpark script to parse app/data/ASCII/custdata.txt as a fixed-width file.

Derived from COBOL copybook: app/cpy/CUSTREC.cpy
Record layout: CUSTOMER-RECORD (500 bytes)

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
# Field layout derived from CUSTREC.cpy
# Each tuple: (field_name, start_pos (1-based), length)
# ---------------------------------------------------------------------------
FIELD_LAYOUT = [
    ("CUST_ID",                   1,   9),
    ("CUST_FIRST_NAME",          10,  25),
    ("CUST_MIDDLE_NAME",         35,  25),
    ("CUST_LAST_NAME",           60,  25),
    ("CUST_ADDR_LINE_1",         85,  50),
    ("CUST_ADDR_LINE_2",        135,  50),
    ("CUST_ADDR_LINE_3",        185,  50),
    ("CUST_ADDR_STATE_CD",      235,   2),
    ("CUST_ADDR_COUNTRY_CD",    237,   3),
    ("CUST_ADDR_ZIP",           240,  10),
    ("CUST_PHONE_NUM_1",        250,  15),
    ("CUST_PHONE_NUM_2",        265,  15),
    ("CUST_SSN",                280,   9),
    ("CUST_GOVT_ISSUED_ID",     289,  20),
    ("CUST_DOB_YYYYMMDD",       309,  10),
    ("CUST_EFT_ACCOUNT_ID",     319,  10),
    ("CUST_PRI_CARD_HOLDER_IND",329,   1),
    ("CUST_FICO_CREDIT_SCORE",  330,   3),
    ("FILLER",                  333, 168),
]

# Fields to cast from display-numeric strings to integer types
NUMERIC_FIELDS = {
    "CUST_ID": LongType(),               # PIC 9(09) — 9-digit unsigned integer
    "CUST_SSN": LongType(),              # PIC 9(09) — social security number
    "CUST_FICO_CREDIT_SCORE": IntegerType(),  # PIC 9(03) — 3-digit score
}


def main():
    """Read custdata.txt, apply copybook schema, print schema and first 5 rows."""

    spark = SparkSession.builder \
        .appName("CardDemo_CUSTREC_CustData_Parser") \
        .master("local[*]") \
        .getOrCreate()

    # Resolve the data file path relative to this script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    data_path = os.path.join(repo_root, "app", "data", "ASCII", "custdata.txt")

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
    print("CUSTOMER-RECORD DataFrame Schema (from CUSTREC.cpy)")
    print("=" * 80)
    df.printSchema()

    print("=" * 80)
    print("First 5 rows of custdata.txt")
    print("=" * 80)
    df.show(5, truncate=False)

    spark.stop()


if __name__ == "__main__":
    main()
