"""
PySpark script to parse app/data/ASCII/carddata.txt using the layout defined
in app/cpy/CVACT02Y.cpy (CARD-RECORD, 150 bytes fixed-width).
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
# Schema derived from CVACT02Y.cpy  (CARD-RECORD, RECLN 150)
# ---------------------------------------------------------------------------
FIELDS = [
    # (name, offset_1based, length, type_tag)
    ("CARD_NUM",              1,  16, "string"),
    ("CARD_ACCT_ID",         17,  11, "numeric_long"),
    ("CARD_CVV_CD",          28,   3, "numeric_int"),
    ("CARD_EMBOSSED_NAME",   31,  50, "string"),
    ("CARD_EXPIRAION_DATE",  81,  10, "string"),
    ("CARD_ACTIVE_STATUS",   91,   1, "string"),
    ("FILLER",               92,  59, "string"),
]

RECORD_LENGTH = 150
DATA_FILE = "app/data/ASCII/carddata.txt"


def main(repo_root: str = ".") -> None:
    spark = SparkSession.builder \
        .appName("Parse CVACT02Y Card Data") \
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
    print("CARD-RECORD  (CVACT02Y.cpy → carddata.txt)")
    print("=" * 70)
    print(f"\nSchema:")
    raw_df.printSchema()
    print(f"Row count: {raw_df.count()}")
    print("\nFirst 5 rows:")
    raw_df.drop("FILLER").show(5, truncate=False)

    output_path = os.path.join(repo_root, "pyspark_parsers", "validation",
                               "carddata_parsed.csv")
    raw_df.drop("FILLER").toPandas().to_csv(output_path, index=False)
    print(f"\nParsed output written to: {output_path}")

    spark.stop()


if __name__ == "__main__":
    repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
    main(repo_root)
