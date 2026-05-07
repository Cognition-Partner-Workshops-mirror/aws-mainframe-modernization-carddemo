"""
PySpark parser for CUSTREC.cpy (CUSTOMER-RECORD) -> custdata.txt

Reads the fixed-width customer data file using the COBOL copybook-derived schema.
Record length: 500 bytes per line.
"""

import os
import json

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, IntegerType
)

# Field layout derived from CUSTREC.cpy
FIELD_LAYOUT = [
    ("CUST_ID", 0, 9, "numeric_long"),
    ("CUST_FIRST_NAME", 9, 25, "string"),
    ("CUST_MIDDLE_NAME", 34, 25, "string"),
    ("CUST_LAST_NAME", 59, 25, "string"),
    ("CUST_ADDR_LINE_1", 84, 50, "string"),
    ("CUST_ADDR_LINE_2", 134, 50, "string"),
    ("CUST_ADDR_LINE_3", 184, 50, "string"),
    ("CUST_ADDR_STATE_CD", 234, 2, "string"),
    ("CUST_ADDR_COUNTRY_CD", 236, 3, "string"),
    ("CUST_ADDR_ZIP", 239, 10, "string"),
    ("CUST_PHONE_NUM_1", 249, 15, "string"),
    ("CUST_PHONE_NUM_2", 264, 15, "string"),
    ("CUST_SSN", 279, 9, "numeric_long"),
    ("CUST_GOVT_ISSUED_ID", 288, 20, "string"),
    ("CUST_DOB_YYYYMMDD", 308, 10, "string"),
    ("CUST_EFT_ACCOUNT_ID", 318, 10, "string"),
    ("CUST_PRI_CARD_HOLDER_IND", 328, 1, "string"),
    ("CUST_FICO_CREDIT_SCORE", 329, 3, "numeric_int"),
    ("FILLER", 332, 168, "string"),
]


def parse_customer_record(line: str) -> dict:
    """Parse a single 500-byte customer record line."""
    record = {}
    for name, offset, length, field_type in FIELD_LAYOUT:
        raw_value = line[offset:offset + length]
        if field_type == "numeric_long":
            record[name] = int(raw_value) if raw_value.strip().isdigit() else 0
        elif field_type == "numeric_int":
            record[name] = int(raw_value) if raw_value.strip().isdigit() else 0
        else:
            record[name] = raw_value.strip()
    return record


def main():
    """Main entry point for parsing custdata.txt."""
    spark = SparkSession.builder \
        .appName("CardDemo_Customer_Parser") \
        .master("local[*]") \
        .getOrCreate()

    # Determine file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    data_file = os.path.join(project_root, "app", "data", "ASCII", "custdata.txt")
    output_dir = os.path.join(project_root, "validation")

    # Read raw lines
    raw_rdd = spark.sparkContext.textFile(data_file)
    raw_count = raw_rdd.count()

    # Parse records
    parsed_rdd = raw_rdd.map(parse_customer_record)

    # Define PySpark schema
    schema = StructType([
        StructField("CUST_ID", LongType(), False),
        StructField("CUST_FIRST_NAME", StringType(), True),
        StructField("CUST_MIDDLE_NAME", StringType(), True),
        StructField("CUST_LAST_NAME", StringType(), True),
        StructField("CUST_ADDR_LINE_1", StringType(), True),
        StructField("CUST_ADDR_LINE_2", StringType(), True),
        StructField("CUST_ADDR_LINE_3", StringType(), True),
        StructField("CUST_ADDR_STATE_CD", StringType(), True),
        StructField("CUST_ADDR_COUNTRY_CD", StringType(), True),
        StructField("CUST_ADDR_ZIP", StringType(), True),
        StructField("CUST_PHONE_NUM_1", StringType(), True),
        StructField("CUST_PHONE_NUM_2", StringType(), True),
        StructField("CUST_SSN", LongType(), True),
        StructField("CUST_GOVT_ISSUED_ID", StringType(), True),
        StructField("CUST_DOB_YYYYMMDD", StringType(), True),
        StructField("CUST_EFT_ACCOUNT_ID", StringType(), True),
        StructField("CUST_PRI_CARD_HOLDER_IND", StringType(), True),
        StructField("CUST_FICO_CREDIT_SCORE", IntegerType(), True),
        StructField("FILLER", StringType(), True),
    ])

    # Create DataFrame from parsed data
    df = spark.createDataFrame(parsed_rdd, schema=schema)

    # Drop FILLER column for display
    df_display = df.drop("FILLER")

    parsed_count = df_display.count()

    # Validation output
    validation = {
        "source_file": "app/data/ASCII/custdata.txt",
        "copybook": "app/cpy/CUSTREC.cpy",
        "record_length_bytes": 500,
        "raw_line_count": raw_count,
        "parsed_row_count": parsed_count,
        "counts_match": raw_count == parsed_count,
        "sample_records": []
    }

    # Collect first 5 rows as sample
    sample_rows = df_display.limit(5).collect()
    for row in sample_rows:
        validation["sample_records"].append(row.asDict())

    # Write validation output
    output_file = os.path.join(output_dir, "custdata_validation.json")
    with open(output_file, "w") as f:
        json.dump(validation, f, indent=2, default=str)

    print(f"Source file: {data_file}")
    print(f"Raw line count: {raw_count}")
    print(f"Parsed row count: {parsed_count}")
    print(f"Counts match: {raw_count == parsed_count}")
    print(f"\nSchema:")
    df_display.printSchema()
    print(f"\nFirst 5 records:")
    df_display.show(5, truncate=False)
    print(f"\nValidation output written to: {output_file}")

    spark.stop()


if __name__ == "__main__":
    main()
