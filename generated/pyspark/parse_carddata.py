"""
PySpark script to parse app/data/ASCII/carddata.txt as a fixed-width file
using the schema derived from COBOL copybook app/cpy/CVACT02Y.cpy.

Copybook: CVACT02Y.cpy
Record: CARD-RECORD (150 bytes per line)
"""

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, LongType
)
from pyspark.sql.functions import col, trim, substring
import os

# --- Field layout derived from CVACT02Y.cpy ---
# Total record length: 150 bytes
# All fields are either PIC 9 (unsigned numeric) or PIC X (alphanumeric string).
# No signed/packed fields in this copybook.
# Fields: (name, start_pos (1-based for substring), length, type)
CARD_FIELDS = [
    ("CARD_NUM",              1,  16, "string"),    # PIC X(16)
    ("CARD_ACCT_ID",         17,  11, "numeric"),   # PIC 9(11)
    ("CARD_CVV_CD",          28,   3, "numeric"),   # PIC 9(03)
    ("CARD_EMBOSSED_NAME",   31,  50, "string"),    # PIC X(50)
    ("CARD_EXPIRAION_DATE",  81,  10, "string"),    # PIC X(10)
    ("CARD_ACTIVE_STATUS",   91,   1, "string"),    # PIC X(01)
    ("FILLER",               92,  59, "string"),    # PIC X(59)
]


def main():
    """Main entry point: read fixed-width card data and parse using copybook schema."""
    spark = SparkSession.builder \
        .appName("CVACT02Y_CardData_Parser") \
        .master("local[*]") \
        .getOrCreate()

    # Determine file path relative to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    data_file = os.path.join(project_root, "app", "data", "ASCII", "carddata.txt")

    # Read raw text file - each line is a 150-byte fixed-width record
    raw_df = spark.read.text(data_file)

    # Extract fields using substring (1-based positions)
    parsed_df = raw_df
    for field_name, start, length, field_type in CARD_FIELDS:
        parsed_df = parsed_df.withColumn(field_name, substring(col("value"), start, length))

    # Apply type conversions
    # Unsigned numeric fields: cast to long integer after trimming
    numeric_fields = [f[0] for f in CARD_FIELDS if f[3] == "numeric"]
    for field_name in numeric_fields:
        parsed_df = parsed_df.withColumn(field_name, trim(col(field_name)).cast("long"))

    # String fields: trim trailing/leading spaces
    string_fields = [f[0] for f in CARD_FIELDS if f[3] == "string"]
    for field_name in string_fields:
        parsed_df = parsed_df.withColumn(field_name, trim(col(field_name)))

    # Drop raw 'value' column and FILLER
    result_df = parsed_df.drop("value", "FILLER")

    # Show results
    print("=" * 80)
    print("CARD-RECORD Parsed Output (from CVACT02Y.cpy / carddata.txt)")
    print("=" * 80)
    result_df.printSchema()
    print(f"\nTotal records: {result_df.count()}")
    print("\nSample records (first 10):")
    result_df.show(10, truncate=False)

    spark.stop()


if __name__ == "__main__":
    main()
