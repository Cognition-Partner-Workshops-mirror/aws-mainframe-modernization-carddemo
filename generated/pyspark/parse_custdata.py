"""
PySpark script to parse app/data/ASCII/custdata.txt as a fixed-width file
using the schema derived from COBOL copybook app/cpy/CUSTREC.cpy.

Copybook: CUSTREC.cpy
Record: CUSTOMER-RECORD (500 bytes per line)
"""

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, LongType
)
from pyspark.sql.functions import col, trim, substring
import os

# --- Field layout derived from CUSTREC.cpy ---
# Total record length: 500 bytes
# All fields are either PIC 9 (unsigned numeric) or PIC X (alphanumeric string).
# No signed/packed fields in this copybook.
# Fields: (name, start_pos (1-based for substring), length, type)
CUSTOMER_FIELDS = [
    ("CUST_ID",                   1,   9, "numeric"),   # PIC 9(09)
    ("CUST_FIRST_NAME",          10,  25, "string"),    # PIC X(25)
    ("CUST_MIDDLE_NAME",         35,  25, "string"),    # PIC X(25)
    ("CUST_LAST_NAME",           60,  25, "string"),    # PIC X(25)
    ("CUST_ADDR_LINE_1",         85,  50, "string"),    # PIC X(50)
    ("CUST_ADDR_LINE_2",        135,  50, "string"),    # PIC X(50)
    ("CUST_ADDR_LINE_3",        185,  50, "string"),    # PIC X(50)
    ("CUST_ADDR_STATE_CD",      235,   2, "string"),    # PIC X(02)
    ("CUST_ADDR_COUNTRY_CD",    237,   3, "string"),    # PIC X(03)
    ("CUST_ADDR_ZIP",           240,  10, "string"),    # PIC X(10)
    ("CUST_PHONE_NUM_1",        250,  15, "string"),    # PIC X(15)
    ("CUST_PHONE_NUM_2",        265,  15, "string"),    # PIC X(15)
    ("CUST_SSN",                280,   9, "numeric"),   # PIC 9(09)
    ("CUST_GOVT_ISSUED_ID",     289,  20, "string"),    # PIC X(20)
    ("CUST_DOB_YYYYMMDD",       309,  10, "string"),    # PIC X(10)
    ("CUST_EFT_ACCOUNT_ID",     319,  10, "string"),    # PIC X(10)
    ("CUST_PRI_CARD_HOLDER_IND",329,   1, "string"),    # PIC X(01)
    ("CUST_FICO_CREDIT_SCORE",  330,   3, "numeric"),   # PIC 9(03)
    ("FILLER",                  333, 168, "string"),    # PIC X(168)
]


def main():
    """Main entry point: read fixed-width customer data and parse using copybook schema."""
    spark = SparkSession.builder \
        .appName("CUSTREC_CustomerData_Parser") \
        .master("local[*]") \
        .getOrCreate()

    # Determine file path relative to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    data_file = os.path.join(project_root, "app", "data", "ASCII", "custdata.txt")

    # Read raw text file - each line is a 500-byte fixed-width record
    raw_df = spark.read.text(data_file)

    # Extract fields using substring (1-based positions)
    parsed_df = raw_df
    for field_name, start, length, field_type in CUSTOMER_FIELDS:
        parsed_df = parsed_df.withColumn(field_name, substring(col("value"), start, length))

    # Apply type conversions
    # Unsigned numeric fields: cast to long integer after trimming
    numeric_fields = [f[0] for f in CUSTOMER_FIELDS if f[3] == "numeric"]
    for field_name in numeric_fields:
        parsed_df = parsed_df.withColumn(field_name, trim(col(field_name)).cast("long"))

    # String fields: trim trailing/leading spaces
    string_fields = [f[0] for f in CUSTOMER_FIELDS if f[3] == "string"]
    for field_name in string_fields:
        parsed_df = parsed_df.withColumn(field_name, trim(col(field_name)))

    # Drop raw 'value' column and FILLER
    result_df = parsed_df.drop("value", "FILLER")

    # Show results
    print("=" * 80)
    print("CUSTOMER-RECORD Parsed Output (from CUSTREC.cpy / custdata.txt)")
    print("=" * 80)
    result_df.printSchema()
    print(f"\nTotal records: {result_df.count()}")
    print("\nSample records (first 10):")
    result_df.show(10, truncate=False)

    spark.stop()


if __name__ == "__main__":
    main()
