"""
PySpark script to parse app/data/ASCII/custdata.txt using the layout defined
in app/cpy/CUSTREC.cpy (CUSTOMER-RECORD, 500 bytes fixed-width).
"""

import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, substring, trim
from pyspark.sql.types import (
    IntegerType,
    LongType,
    StructField,
    StructType,
)

# ---------------------------------------------------------------------------
# Schema derived from CUSTREC.cpy  (CUSTOMER-RECORD, RECLN 500)
# ---------------------------------------------------------------------------
FIELDS = [
    # (name, offset_1based, length, type_tag)
    ("CUST_ID",                  1,   9, "numeric_long"),
    ("CUST_FIRST_NAME",         10,  25, "string"),
    ("CUST_MIDDLE_NAME",        35,  25, "string"),
    ("CUST_LAST_NAME",          60,  25, "string"),
    ("CUST_ADDR_LINE_1",        85,  50, "string"),
    ("CUST_ADDR_LINE_2",       135,  50, "string"),
    ("CUST_ADDR_LINE_3",       185,  50, "string"),
    ("CUST_ADDR_STATE_CD",     235,   2, "string"),
    ("CUST_ADDR_COUNTRY_CD",   237,   3, "string"),
    ("CUST_ADDR_ZIP",          240,  10, "string"),
    ("CUST_PHONE_NUM_1",       250,  15, "string"),
    ("CUST_PHONE_NUM_2",       265,  15, "string"),
    ("CUST_SSN",               280,   9, "numeric_long"),
    ("CUST_GOVT_ISSUED_ID",    289,  20, "string"),
    ("CUST_DOB_YYYYMMDD",      309,  10, "string"),
    ("CUST_EFT_ACCOUNT_ID",    319,  10, "string"),
    ("CUST_PRI_CARD_HOLDER_IND", 329, 1, "string"),
    ("CUST_FICO_CREDIT_SCORE", 330,   3, "numeric_int"),
    ("FILLER",                 333, 168, "string"),
]

RECORD_LENGTH = 500
DATA_FILE = "app/data/ASCII/custdata.txt"


def main(repo_root: str = ".") -> None:
    spark = SparkSession.builder \
        .appName("Parse CUSTREC Customer Data") \
        .master("local[*]") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    data_path = os.path.join(repo_root, DATA_FILE)

    raw_df = spark.read.text(data_path)

    for name, offset, length, _ in FIELDS:
        raw_df = raw_df.withColumn(name, substring(col("value"), offset, length))

    raw_df = raw_df.drop("value")

    for name, _, _, type_tag in FIELDS:
        if type_tag == "numeric_long":
            raw_df = raw_df.withColumn(name, trim(col(name)).cast(LongType()))
        elif type_tag == "numeric_int":
            raw_df = raw_df.withColumn(name, trim(col(name)).cast(IntegerType()))
        elif type_tag == "string":
            raw_df = raw_df.withColumn(name, trim(col(name)))

    print("=" * 70)
    print("CUSTOMER-RECORD  (CUSTREC.cpy → custdata.txt)")
    print("=" * 70)
    print(f"\nSchema:")
    raw_df.printSchema()
    print(f"Row count: {raw_df.count()}")
    print("\nFirst 5 rows (selected columns):")
    raw_df.select(
        "CUST_ID", "CUST_FIRST_NAME", "CUST_LAST_NAME",
        "CUST_ADDR_STATE_CD", "CUST_SSN", "CUST_DOB_YYYYMMDD",
        "CUST_FICO_CREDIT_SCORE"
    ).show(5, truncate=False)

    output_path = os.path.join(repo_root, "pyspark_parsers", "validation",
                               "custdata_parsed.csv")
    raw_df.drop("FILLER").toPandas().to_csv(output_path, index=False)
    print(f"\nParsed output written to: {output_path}")

    spark.stop()


if __name__ == "__main__":
    repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
    main(repo_root)
