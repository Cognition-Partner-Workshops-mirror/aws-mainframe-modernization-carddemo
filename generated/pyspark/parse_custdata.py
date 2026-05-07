"""
PySpark script to parse app/data/ASCII/custdata.txt using the CUSTREC.cpy
(CUSTOMER-RECORD) copybook layout.

Record length: 500 bytes (fixed-width, one record per line).

All numeric fields in this copybook are unsigned zoned decimal (PIC 9(n))
and all alphanumeric fields are PIC X(n).  No signed or packed-decimal
fields are present.
"""

import json
import os

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
)

# ---------------------------------------------------------------------------
# Field layout derived from CUSTREC.cpy
# ---------------------------------------------------------------------------
FIELDS = [
    ("CUST_ID",                  9, "long"),
    ("CUST_FIRST_NAME",         25, "string"),
    ("CUST_MIDDLE_NAME",        25, "string"),
    ("CUST_LAST_NAME",          25, "string"),
    ("CUST_ADDR_LINE_1",        50, "string"),
    ("CUST_ADDR_LINE_2",        50, "string"),
    ("CUST_ADDR_LINE_3",        50, "string"),
    ("CUST_ADDR_STATE_CD",       2, "string"),
    ("CUST_ADDR_COUNTRY_CD",     3, "string"),
    ("CUST_ADDR_ZIP",           10, "string"),
    ("CUST_PHONE_NUM_1",        15, "string"),
    ("CUST_PHONE_NUM_2",        15, "string"),
    ("CUST_SSN",                 9, "long"),
    ("CUST_GOVT_ISSUED_ID",     20, "string"),
    ("CUST_DOB_YYYYMMDD",       10, "string"),
    ("CUST_EFT_ACCOUNT_ID",     10, "string"),
    ("CUST_PRI_CARD_HOLDER_IND", 1, "string"),
    ("CUST_FICO_CREDIT_SCORE",   3, "int"),
    ("FILLER",                 168, "string"),
]

RECORD_LENGTH = 500


def build_spark_schema():
    """Return a StructType matching the parsed output."""
    spark_fields = []
    for name, _, ftype in FIELDS:
        if ftype == "long":
            spark_fields.append(StructField(name, LongType(), True))
        elif ftype == "int":
            spark_fields.append(StructField(name, IntegerType(), True))
        else:
            spark_fields.append(StructField(name, StringType(), True))
    return StructType(spark_fields)


def parse_record(line: str):
    """Slice a fixed-width line into a tuple of typed values."""
    values = []
    offset = 0
    for _, length, ftype in FIELDS:
        raw = line[offset:offset + length]
        offset += length

        if ftype == "long":
            values.append(int(raw) if raw.strip() else None)
        elif ftype == "int":
            values.append(int(raw) if raw.strip() else None)
        else:
            values.append(raw.strip())
    return tuple(values)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    data_path = os.path.join(repo_root, "app", "data", "ASCII", "custdata.txt")
    schema_path = os.path.join(
        repo_root, "generated", "schemas", "CUSTREC_customer_schema.json"
    )
    validation_path = os.path.join(
        repo_root, "generated", "validation", "custdata_validation.json"
    )

    spark = SparkSession.builder \
        .master("local[*]") \
        .appName("CUSTREC_CustomerRecord_Parser") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    try:
        # Read raw lines
        raw_rdd = spark.sparkContext.textFile(data_path)
        raw_count = raw_rdd.count()

        # Validate record lengths
        bad_lengths = raw_rdd.filter(lambda line: len(line) != RECORD_LENGTH).count()

        # Parse records
        parsed_rdd = raw_rdd.map(parse_record)
        schema = build_spark_schema()
        df = spark.createDataFrame(parsed_rdd, schema)

        parsed_count = df.count()

        # Collect sample rows for validation
        sample_rows = []
        for row in df.head(5):
            sample_rows.append(row.asDict())

        # Print summary
        print(f"Source file       : {data_path}")
        print("Copybook          : CUSTREC.cpy")
        print(f"Record length     : {RECORD_LENGTH}")
        print(f"Raw line count    : {raw_count}")
        print(f"Bad-length lines  : {bad_lengths}")
        print(f"Parsed row count  : {parsed_count}")
        print(f"Row count match   : {raw_count == parsed_count}")
        print()
        df.printSchema()
        df.show(5, truncate=False)

        # Load JSON schema for field metadata
        with open(schema_path, "r") as f:
            schema_meta = json.load(f)

        validation_output = {
            "copybook": "CUSTREC.cpy",
            "data_file": "app/data/ASCII/custdata.txt",
            "record_length": RECORD_LENGTH,
            "raw_line_count": raw_count,
            "bad_length_lines": bad_lengths,
            "parsed_row_count": parsed_count,
            "row_count_match": raw_count == parsed_count,
            "schema_field_count": len(schema_meta["fields"]),
            "sample_rows": sample_rows,
        }

        os.makedirs(os.path.dirname(validation_path), exist_ok=True)
        with open(validation_path, "w") as f:
            json.dump(validation_output, f, indent=2)

        print(f"\nValidation output written to: {validation_path}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
