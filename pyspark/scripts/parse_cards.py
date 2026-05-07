"""
PySpark script: Parse COBOL CARD-RECORD fixed-width file (carddata.txt).

Reads app/data/ASCII/carddata.txt using the schema derived from CVACT02Y.cpy.
Record length: 150 bytes, 7 fields (including FILLER).

Key parsing notes:
- No signed numeric fields in this copybook (no sign-overpunch decoding needed)
- CARD-NUM (PIC X(16)) is kept as StringType to preserve leading zeros and
  avoid numeric overflow (16-digit card numbers exceed Long.MAX_VALUE)
- CARD-CVV-CD (PIC 9(03)) is mapped to StringType to preserve leading zeros
- CARD-EXPIRAION-DATE (PIC X(10)) contains YYYY-MM-DD date strings
"""

from pyspark.sql import SparkSession
import os

from cobol_common import create_fixed_width_df, load_schema


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(SCRIPT_DIR, "..", "schemas", "card_record_schema.json")
DATA_PATH = os.path.join(SCRIPT_DIR, "..", "..", "app", "data", "ASCII", "carddata.txt")


def run(spark: SparkSession):
    """
    Main entry point: read carddata.txt, parse using CVACT02Y.cpy schema, show results.

    Returns the parsed DataFrame for downstream use or validation.
    """
    schema = load_schema(SCHEMA_PATH)
    print(f"[cards] Loaded schema: {schema['copybook']} ({schema['record_length']} bytes)")
    print(f"[cards] Fields: {len(schema['fields'])} (including FILLER)")

    df = create_fixed_width_df(spark, DATA_PATH, schema)

    print("\n[cards] Parsed DataFrame schema:")
    df.printSchema()
    print(f"\n[cards] Row count: {df.count()}")
    print("\n[cards] First 5 rows:")
    df.show(5, truncate=False)

    return df


if __name__ == "__main__":
    spark = SparkSession.builder.appName("COBOL_Card_Parser").getOrCreate()
    run(spark)
    spark.stop()
