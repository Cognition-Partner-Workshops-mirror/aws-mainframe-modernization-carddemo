"""
PySpark script: Parse COBOL ACCOUNT-RECORD fixed-width file (acctdata.txt).

Reads app/data/ASCII/acctdata.txt using the schema derived from CVACT01Y.cpy.
Record length: 300 bytes, 13 fields (including FILLER).

Key parsing challenges:
- PIC S9(10)V99 fields use ASCII sign-overpunch encoding in the last byte
  (e.g., '{' = positive zero, 'A'-'I' = positive 1-9)
- V99 means 2 implied decimal places (no literal decimal point in the data)
- Date fields are PIC X(10) stored as YYYY-MM-DD strings in the ASCII export
"""

from pyspark.sql import SparkSession
import json
import os

# Import shared parsing utilities
from cobol_common import create_fixed_width_df, load_schema


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(SCRIPT_DIR, "..", "schemas", "account_record_schema.json")
DATA_PATH = os.path.join(SCRIPT_DIR, "..", "..", "app", "data", "ASCII", "acctdata.txt")


def run(spark: SparkSession):
    """
    Main entry point: read acctdata.txt, parse using CVACT01Y.cpy schema, show results.

    Returns the parsed DataFrame for downstream use or validation.
    """
    # Load the JSON schema derived from the COBOL copybook
    schema = load_schema(SCHEMA_PATH)
    print(f"[accounts] Loaded schema: {schema['copybook']} ({schema['record_length']} bytes)")
    print(f"[accounts] Fields: {len(schema['fields'])} (including FILLER)")

    # Parse the fixed-width file into a typed DataFrame
    df = create_fixed_width_df(spark, DATA_PATH, schema)

    # Show schema and sample data for verification
    print("\n[accounts] Parsed DataFrame schema:")
    df.printSchema()
    print(f"\n[accounts] Row count: {df.count()}")
    print("\n[accounts] First 5 rows:")
    df.show(5, truncate=False)

    return df


if __name__ == "__main__":
    spark = SparkSession.builder.appName("COBOL_Account_Parser").getOrCreate()
    run(spark)
    spark.stop()
