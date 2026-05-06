"""
PySpark script to parse app/data/ASCII/acctdata.txt using the layout defined
in app/cpy/CVACT01Y.cpy (ACCOUNT-RECORD, 300 bytes fixed-width).
"""

import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, substring, trim, udf
from pyspark.sql.types import (
    DecimalType,
    LongType,
    StringType,
    StructField,
    StructType,
)

sys.path.insert(0, os.path.dirname(__file__))
from cobol_utils import decode_zoned_decimal  # noqa: E402

# ---------------------------------------------------------------------------
# Schema derived from CVACT01Y.cpy  (ACCOUNT-RECORD, RECLN 300)
# ---------------------------------------------------------------------------
FIELDS = [
    # (name, offset_1based, length, type_tag)
    ("ACCT_ID",                1,  11, "numeric"),
    ("ACCT_ACTIVE_STATUS",    12,   1, "string"),
    ("ACCT_CURR_BAL",         13,  12, "signed_decimal"),
    ("ACCT_CREDIT_LIMIT",     25,  12, "signed_decimal"),
    ("ACCT_CASH_CREDIT_LIMIT",37,  12, "signed_decimal"),
    ("ACCT_OPEN_DATE",        49,  10, "string"),
    ("ACCT_EXPIRAION_DATE",   59,  10, "string"),
    ("ACCT_REISSUE_DATE",     69,  10, "string"),
    ("ACCT_CURR_CYC_CREDIT",  79, 12, "signed_decimal"),
    ("ACCT_CURR_CYC_DEBIT",   91, 12, "signed_decimal"),
    ("ACCT_ADDR_ZIP",        103,  10, "string"),
    ("ACCT_GROUP_ID",        113,  10, "string"),
    ("FILLER",               123, 178, "string"),
]

RECORD_LENGTH = 300
DATA_FILE = "app/data/ASCII/acctdata.txt"


def main(repo_root: str = ".") -> None:
    spark = SparkSession.builder \
        .appName("Parse CVACT01Y Account Data") \
        .master("local[*]") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    spark.sparkContext.addPyFile(
        os.path.join(os.path.dirname(__file__), "cobol_utils.py")
    )

    data_path = os.path.join(repo_root, DATA_FILE)

    raw_df = spark.read.text(data_path)

    for name, offset, length, _ in FIELDS:
        raw_df = raw_df.withColumn(name, substring(col("value"), offset, length))

    raw_df = raw_df.drop("value")

    decode_udf = udf(lambda v: str(decode_zoned_decimal(v, 2)), StringType())

    for name, _, _, type_tag in FIELDS:
        if type_tag == "numeric":
            raw_df = raw_df.withColumn(name, trim(col(name)).cast(LongType()))
        elif type_tag == "signed_decimal":
            raw_df = raw_df.withColumn(name, decode_udf(col(name)).cast(DecimalType(12, 2)))
        elif type_tag == "string":
            raw_df = raw_df.withColumn(name, trim(col(name)))

    print("=" * 70)
    print("ACCOUNT-RECORD  (CVACT01Y.cpy → acctdata.txt)")
    print("=" * 70)
    print(f"\nSchema:")
    raw_df.printSchema()
    print(f"Row count: {raw_df.count()}")
    print("\nFirst 5 rows:")
    raw_df.drop("FILLER").show(5, truncate=False)

    output_path = os.path.join(repo_root, "pyspark_parsers", "validation",
                               "acctdata_parsed.csv")
    raw_df.drop("FILLER").toPandas().to_csv(output_path, index=False)
    print(f"\nParsed output written to: {output_path}")

    spark.stop()


if __name__ == "__main__":
    repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
    main(repo_root)
