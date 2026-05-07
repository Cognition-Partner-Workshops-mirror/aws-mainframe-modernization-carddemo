"""Parse custdata.txt using the CUSTREC.cpy CUSTOMER-RECORD layout (500 bytes).

Reads the fixed-width ASCII file, applies the copybook-derived schema,
and writes the result to Parquet.
"""

import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, substring, trim
from pyspark.sql.types import (
    IntegerType,
    StringType,
    StructField,
    StructType,
)

# ---------- schema derived from CUSTREC.cpy ----------
RECORD_LENGTH = 500
FIELDS = [
    # (name, offset, length, field_type)
    ("CUST_ID",                  0,    9, "string"),
    ("CUST_FIRST_NAME",          9,   25, "string"),
    ("CUST_MIDDLE_NAME",        34,   25, "string"),
    ("CUST_LAST_NAME",          59,   25, "string"),
    ("CUST_ADDR_LINE_1",        84,   50, "string"),
    ("CUST_ADDR_LINE_2",       134,   50, "string"),
    ("CUST_ADDR_LINE_3",       184,   50, "string"),
    ("CUST_ADDR_STATE_CD",     234,    2, "string"),
    ("CUST_ADDR_COUNTRY_CD",   236,    3, "string"),
    ("CUST_ADDR_ZIP",          239,   10, "string"),
    ("CUST_PHONE_NUM_1",       249,   15, "string"),
    ("CUST_PHONE_NUM_2",       264,   15, "string"),
    ("CUST_SSN",               279,    9, "string"),
    ("CUST_GOVT_ISSUED_ID",    288,   20, "string"),
    ("CUST_DOB_YYYYMMDD",      308,   10, "string"),
    ("CUST_EFT_ACCOUNT_ID",    318,   10, "string"),
    ("CUST_PRI_CARD_HOLDER_IND", 328,  1, "string"),
    ("CUST_FICO_CREDIT_SCORE", 329,    3, "integer"),
    ("FILLER",                 332,  168, "string"),
]


def build_spark_session(app_name="ParseCustData"):
    return (SparkSession.builder
            .appName(app_name)
            .master("local[*]")
            .getOrCreate())


def parse_fixed_width(spark, input_path):
    """Read fixed-width file and extract fields based on copybook layout."""
    raw_df = (spark.read
              .text(input_path)
              .filter(col("value").isNotNull())
              .filter(col("value") != ""))

    parsed_df = raw_df
    for name, offset, length, _ in FIELDS:
        parsed_df = parsed_df.withColumn(
            name, substring(col("value"), offset + 1, length)
        )

    parsed_df = parsed_df.drop("value")

    for name, _, _, ftype in FIELDS:
        if ftype == "string" and name != "FILLER":
            parsed_df = parsed_df.withColumn(name, trim(col(name)))
        elif ftype == "integer":
            parsed_df = (parsed_df
                         .withColumn(name, trim(col(name)))
                         .withColumn(name, col(name).cast(IntegerType())))

    return parsed_df


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    input_path = os.path.join(base_dir, "app", "data", "ASCII", "custdata.txt")
    output_path = os.path.join(base_dir, "copybook_parsing", "output",
                               "custdata_parsed.parquet")

    spark = build_spark_session()
    try:
        df = parse_fixed_width(spark, input_path)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.write.mode("overwrite").parquet(output_path)

        print(f"Schema for CUSTOMER-RECORD ({RECORD_LENGTH}-byte layout):")
        df.printSchema()
        print(f"\nRow count: {df.count()}")
        print("\nSample rows (first 5):")
        df.show(5, truncate=False)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
