"""Parse carddata.txt using the CVACT02Y.cpy CARD-RECORD layout (150 bytes).

Reads the fixed-width ASCII file, applies the copybook-derived schema,
and writes the result to Parquet.
"""

import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, substring, trim
from pyspark.sql.types import (
    StringType,
    StructField,
    StructType,
)

# ---------- schema derived from CVACT02Y.cpy ----------
RECORD_LENGTH = 150
FIELDS = [
    # (name, offset, length, field_type)
    ("CARD_NUM",             0,   16, "string"),
    ("CARD_ACCT_ID",        16,   11, "string"),
    ("CARD_CVV_CD",         27,    3, "string"),
    ("CARD_EMBOSSED_NAME",  30,   50, "string"),
    ("CARD_EXPIRAION_DATE", 80,   10, "string"),
    ("CARD_ACTIVE_STATUS",  90,    1, "string"),
    ("FILLER",              91,   59, "string"),
]


def build_spark_session(app_name="ParseCardData"):
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

    return parsed_df


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    input_path = os.path.join(base_dir, "app", "data", "ASCII", "carddata.txt")
    output_path = os.path.join(base_dir, "copybook_parsing", "output",
                               "carddata_parsed.parquet")

    spark = build_spark_session()
    try:
        df = parse_fixed_width(spark, input_path)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.write.mode("overwrite").parquet(output_path)

        print(f"Schema for CARD-RECORD ({RECORD_LENGTH}-byte layout):")
        df.printSchema()
        print(f"\nRow count: {df.count()}")
        print("\nSample rows (first 5):")
        df.show(5, truncate=False)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
