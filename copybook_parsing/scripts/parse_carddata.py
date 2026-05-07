"""
PySpark script to parse carddata.txt using the CVACT02Y.cpy copybook layout.

CARD-RECORD: 150-byte fixed-width records.
All fields are either PIC 9 (unsigned numeric) or PIC X (alphanumeric).
No signed-decimal fields in this copybook.
"""

import json
import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, substring, trim
from pyspark.sql.types import (
    IntegerType,
    LongType,
    StringType,
)

# ---------------------------------------------------------------------------
# Schema derived from CVACT02Y.cpy (see schemas/CVACT02Y_schema.json)
# ---------------------------------------------------------------------------
FIELD_LAYOUT = [
    ("CARD_NUM",              1, 16, "string"),
    ("CARD_ACCT_ID",         17, 11, "numeric_long"),
    ("CARD_CVV_CD",          28,  3, "numeric_int"),
    ("CARD_EMBOSSED_NAME",   31, 50, "string"),
    ("CARD_EXPIRAION_DATE",  81, 10, "string"),
    ("CARD_ACTIVE_STATUS",   91,  1, "string"),
    ("FILLER",               92, 59, "string"),
]


def main(data_path: str, schema_path: str, output_path: str):
    spark = SparkSession.builder \
        .master("local[*]") \
        .appName("CVACT02Y_CardParser") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    raw_df = spark.read.text(data_path)

    parsed_df = raw_df
    for name, start, length, _ in FIELD_LAYOUT:
        parsed_df = parsed_df.withColumn(name, substring(col("value"), start, length))

    parsed_df = parsed_df.drop("value")

    for name, _, _, ftype in FIELD_LAYOUT:
        if ftype == "numeric_long":
            parsed_df = parsed_df.withColumn(name, col(name).cast(LongType()))
        elif ftype == "numeric_int":
            parsed_df = parsed_df.withColumn(name, col(name).cast(IntegerType()))
        else:
            parsed_df = parsed_df.withColumn(name, trim(col(name)))

    parsed_df = parsed_df.drop("FILLER")

    # ---- Validation ----
    raw_line_count = raw_df.count()
    parsed_row_count = parsed_df.count()

    validation = {
        "source_file": os.path.basename(data_path),
        "copybook": "CVACT02Y.cpy",
        "raw_line_count": raw_line_count,
        "parsed_row_count": parsed_row_count,
        "counts_match": raw_line_count == parsed_row_count,
        "schema_fields": [f[0] for f in FIELD_LAYOUT if f[0] != "FILLER"],
        "sample_rows": [],
    }

    sample_rows = parsed_df.limit(5).collect()
    for row in sample_rows:
        validation["sample_rows"].append(row.asDict())

    with open(output_path, "w") as f:
        json.dump(validation, f, indent=2)

    print(f"Raw lines : {raw_line_count}")
    print(f"Parsed rows: {parsed_row_count}")
    print(f"Match      : {raw_line_count == parsed_row_count}")
    parsed_df.show(5, truncate=False)

    spark.stop()


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo_dir = os.path.dirname(base_dir)
    data_path = os.path.join(repo_dir, "app", "data", "ASCII", "carddata.txt")
    schema_path = os.path.join(base_dir, "schemas", "CVACT02Y_schema.json")
    output_path = os.path.join(base_dir, "validation", "carddata_validation.json")
    main(data_path, schema_path, output_path)
