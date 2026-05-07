"""
PySpark script: Parse COBOL CUSTOMER-RECORD fixed-width file (custdata.txt).

Reads app/data/ASCII/custdata.txt using the schema derived from CUSTREC.cpy.
Record length: 500 bytes, 19 fields (including FILLER).

Key parsing notes:
- No signed numeric fields in this copybook (no sign-overpunch decoding needed)
- CUST-SSN (PIC 9(09)) is mapped to StringType to preserve leading zeros
- CUST-DOB-YYYYMMDD (PIC X(10)) contains YYYY-MM-DD date strings
- Most fields are PIC X(...) alphanumeric, space-padded on the right
"""

from pyspark.sql import SparkSession
import os

from cobol_common import create_fixed_width_df, load_schema


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(SCRIPT_DIR, "..", "schemas", "customer_record_schema.json")
DATA_PATH = os.path.join(SCRIPT_DIR, "..", "..", "app", "data", "ASCII", "custdata.txt")


def run(spark: SparkSession):
    """
    Main entry point: read custdata.txt, parse using CUSTREC.cpy schema, show results.

    Returns the parsed DataFrame for downstream use or validation.
    """
    schema = load_schema(SCHEMA_PATH)
    print(f"[customers] Loaded schema: {schema['copybook']} ({schema['record_length']} bytes)")
    print(f"[customers] Fields: {len(schema['fields'])} (including FILLER)")

    df = create_fixed_width_df(spark, DATA_PATH, schema)

    print("\n[customers] Parsed DataFrame schema:")
    df.printSchema()
    print(f"\n[customers] Row count: {df.count()}")
    print("\n[customers] First 5 rows:")
    df.show(5, truncate=False)

    return df


if __name__ == "__main__":
    spark = SparkSession.builder.appName("COBOL_Customer_Parser").getOrCreate()
    run(spark)
    spark.stop()
