"""
PySpark parser for COBOL copybook CUSTREC.cpy → custdata.txt

Reads the fixed-width Customer Record file (500 bytes per line) and applies
the field layout defined in app/cpy/CUSTREC.cpy.  All fields in this
copybook use DISPLAY format — no sign-overpunch decoding is needed.

Usage:
    spark-submit parse_custdata.py [--input <path>] [--output <path>]
"""

import argparse
import os

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType


# ---------------------------------------------------------------------------
# Field layout derived from CUSTREC.cpy  (CUSTOMER-RECORD, 500 bytes)
#   offset is 1-based for PySpark substr()
#   type_hint: 'str' → StringType, 'int' → IntegerType
# ---------------------------------------------------------------------------
CUSTOMER_FIELDS = [
    # (field_name,                  offset, length, type_hint)
    ("CUST_ID",                          1,   9, "str"),
    ("CUST_FIRST_NAME",                 10,  25, "str"),
    ("CUST_MIDDLE_NAME",                35,  25, "str"),
    ("CUST_LAST_NAME",                  60,  25, "str"),
    ("CUST_ADDR_LINE_1",               85,  50, "str"),
    ("CUST_ADDR_LINE_2",              135,  50, "str"),
    ("CUST_ADDR_LINE_3",              185,  50, "str"),
    ("CUST_ADDR_STATE_CD",            235,   2, "str"),
    ("CUST_ADDR_COUNTRY_CD",          237,   3, "str"),
    ("CUST_ADDR_ZIP",                 240,  10, "str"),
    ("CUST_PHONE_NUM_1",              250,  15, "str"),
    ("CUST_PHONE_NUM_2",              265,  15, "str"),
    ("CUST_SSN",                      280,   9, "str"),
    ("CUST_GOVT_ISSUED_ID",           289,  20, "str"),
    ("CUST_DOB_YYYYMMDD",            309,  10, "str"),
    ("CUST_EFT_ACCOUNT_ID",          319,  10, "str"),
    ("CUST_PRI_CARD_HOLDER_IND",     329,   1, "str"),
    ("CUST_FICO_CREDIT_SCORE",       330,   3, "int"),
    ("FILLER",                        333, 168, "str"),
]

RECORD_LENGTH = 500  # total bytes per record


def parse_custdata(spark: SparkSession, input_path: str):
    """Read custdata.txt as a fixed-width file and return a parsed DataFrame.

    Each line is expected to be exactly 500 characters (matching RECLN 500
    declared in the copybook).
    """
    # Read raw lines
    raw_df = spark.read.text(input_path)

    # Slice each field using substr (1-based offsets)
    parsed = raw_df
    for name, offset, length, type_hint in CUSTOMER_FIELDS:
        col_expr = F.trim(F.substring(F.col("value"), offset, length))
        if type_hint == "int":
            col_expr = col_expr.cast(IntegerType())
        parsed = parsed.withColumn(name, col_expr)

    # Drop the raw line and FILLER columns
    parsed = parsed.drop("value", "FILLER")
    return parsed


def main():
    parser = argparse.ArgumentParser(
        description="Parse COBOL CUSTREC customer data into PySpark DataFrame")
    default_input = os.path.join(
        os.path.dirname(__file__), "..", "..", "app", "data", "ASCII",
        "custdata.txt")
    parser.add_argument("--input", default=default_input,
                        help="Path to custdata.txt")
    parser.add_argument("--output", default=None,
                        help="Optional output path (parquet)")
    args = parser.parse_args()

    spark = SparkSession.builder \
        .appName("CUSTREC_CustomerParser") \
        .master("local[*]") \
        .getOrCreate()

    df = parse_custdata(spark, args.input)

    # Show parsed results
    print(f"\n=== Parsed Customer Records (CUSTREC) ===")
    print(f"Total rows: {df.count()}")
    df.printSchema()
    df.show(10, truncate=False)

    if args.output:
        df.write.mode("overwrite").parquet(args.output)
        print(f"Written to {args.output}")

    spark.stop()


if __name__ == "__main__":
    main()
