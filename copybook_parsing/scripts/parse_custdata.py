"""
PySpark script to parse custdata.txt using the CUSTREC.cpy copybook layout.

CUSTOMER-RECORD: 500-byte fixed-width records.
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
# Schema derived from CUSTREC.cpy (see schemas/CUSTREC_schema.json)
# ---------------------------------------------------------------------------
FIELD_LAYOUT = [
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


def main(data_path: str, schema_path: str, output_path: str):
    spark = SparkSession.builder \
        .master("local[*]") \
        .appName("CUSTREC_CustomerParser") \
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
        "copybook": "CUSTREC.cpy",
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
    data_path = os.path.join(repo_dir, "app", "data", "ASCII", "custdata.txt")
    schema_path = os.path.join(base_dir, "schemas", "CUSTREC_schema.json")
    output_path = os.path.join(base_dir, "validation", "custdata_validation.json")
    main(data_path, schema_path, output_path)
