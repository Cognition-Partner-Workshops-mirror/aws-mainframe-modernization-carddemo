"""
PySpark parser for CVACT02Y.cpy (CARD-RECORD) -> carddata.txt

Reads the fixed-width card data file using the COBOL copybook-derived schema.
Record length: 150 bytes per line.
"""

import os
import json

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, IntegerType
)

# Field layout derived from CVACT02Y.cpy
FIELD_LAYOUT = [
    ("CARD_NUM", 0, 16, "string"),
    ("CARD_ACCT_ID", 16, 11, "numeric_long"),
    ("CARD_CVV_CD", 27, 3, "numeric_int"),
    ("CARD_EMBOSSED_NAME", 30, 50, "string"),
    ("CARD_EXPIRAION_DATE", 80, 10, "string"),
    ("CARD_ACTIVE_STATUS", 90, 1, "string"),
    ("FILLER", 91, 59, "string"),
]


def parse_card_record(line: str) -> dict:
    """Parse a single 150-byte card record line."""
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
    """Main entry point for parsing carddata.txt."""
    spark = SparkSession.builder \
        .appName("CardDemo_Card_Parser") \
        .master("local[*]") \
        .getOrCreate()

    # Determine file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    data_file = os.path.join(project_root, "app", "data", "ASCII", "carddata.txt")
    output_dir = os.path.join(project_root, "validation")

    # Read raw lines
    raw_rdd = spark.sparkContext.textFile(data_file)
    raw_count = raw_rdd.count()

    # Parse records
    parsed_rdd = raw_rdd.map(parse_card_record)

    # Define PySpark schema
    schema = StructType([
        StructField("CARD_NUM", StringType(), False),
        StructField("CARD_ACCT_ID", LongType(), False),
        StructField("CARD_CVV_CD", IntegerType(), True),
        StructField("CARD_EMBOSSED_NAME", StringType(), True),
        StructField("CARD_EXPIRAION_DATE", StringType(), True),
        StructField("CARD_ACTIVE_STATUS", StringType(), True),
        StructField("FILLER", StringType(), True),
    ])

    # Create DataFrame from parsed data
    df = spark.createDataFrame(parsed_rdd, schema=schema)

    # Drop FILLER column for display
    df_display = df.drop("FILLER")

    parsed_count = df_display.count()

    # Validation output
    validation = {
        "source_file": "app/data/ASCII/carddata.txt",
        "copybook": "app/cpy/CVACT02Y.cpy",
        "record_length_bytes": 150,
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
    output_file = os.path.join(output_dir, "carddata_validation.json")
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
