"""
PySpark script to parse the COBOL fixed-width account data file
(``app/data/ASCII/acctdata.txt``) using the copybook-derived schema
from ``CVACT01Y.cpy``.

Record layout: ACCOUNT-RECORD  (300 bytes per record)
Key type-mapping decisions:
  - PIC 9(11)      → LongType    (unsigned numeric display)
  - PIC X(n)       → StringType  (alphanumeric, trailing spaces trimmed)
  - PIC S9(10)V99  → DecimalType(12,2)  (signed zoned-decimal with
                     ASCII overpunch on last byte; implied 2-decimal point)

Usage:
    spark-submit parse_acctdata.py
    # or
    python parse_acctdata.py
"""

import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType

# Allow running from any working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cobol_utils import (
    decode_signed_zoned_decimal,
    get_project_root,
    load_schema,
    parse_fixed_width_file,
)

# ---------------------------------------------------------------------------
# Spark session
# ---------------------------------------------------------------------------
spark = SparkSession.builder \
    .appName("CardDemo_CVACT01Y_AcctData_Parser") \
    .master("local[*]") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Distribute the cobol_utils module to Spark workers so UDFs can find it
COBOL_UTILS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cobol_utils.py")
spark.sparkContext.addPyFile(COBOL_UTILS_PATH)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = get_project_root()
DATA_FILE = os.path.join(PROJECT_ROOT, "app", "data", "ASCII", "acctdata.txt")
SCHEMA_FILE = os.path.join(
    PROJECT_ROOT, "pyspark_copybook_parser", "schemas", "CVACT01Y_schema.json"
)
VALIDATION_OUTPUT = os.path.join(
    PROJECT_ROOT, "pyspark_copybook_parser", "validation", "acctdata_validation.txt"
)

# ---------------------------------------------------------------------------
# Load schema and parse fixed-width file
# ---------------------------------------------------------------------------
schema_json = load_schema(SCHEMA_FILE)
df = parse_fixed_width_file(spark, DATA_FILE, schema_json)

# ---------------------------------------------------------------------------
# Apply signed zoned-decimal UDF to PIC S9(10)V99 columns
# The UDF decodes ASCII overpunch signs and inserts the implied decimal.
# ---------------------------------------------------------------------------
signed_decimal_udf = F.udf(
    lambda raw: decode_signed_zoned_decimal(raw, decimal_places=2)
    if raw is not None else None,
    DecimalType(12, 2),
)

# Columns that use PIC S9(10)V99 encoding
SIGNED_DECIMAL_COLS = [
    "ACCT_CURR_BAL",
    "ACCT_CREDIT_LIMIT",
    "ACCT_CASH_CREDIT_LIMIT",
    "ACCT_CURR_CYC_CREDIT",
    "ACCT_CURR_CYC_DEBIT",
]

for col_name in SIGNED_DECIMAL_COLS:
    df = df.withColumn(col_name, signed_decimal_udf(F.col(col_name)))

# ---------------------------------------------------------------------------
# Validation: row count and sample data
# ---------------------------------------------------------------------------
# Count raw lines in the file for comparison
raw_line_count = spark.read.text(DATA_FILE).count()
parsed_row_count = df.count()

# Collect first 5 rows for sample validation
sample_rows = df.limit(5).collect()

# Build validation report
validation_lines = []
validation_lines.append("=" * 80)
validation_lines.append("VALIDATION REPORT: acctdata.txt (CVACT01Y.cpy / ACCOUNT-RECORD)")
validation_lines.append("=" * 80)
validation_lines.append(f"Copybook:           CVACT01Y.cpy")
validation_lines.append(f"Record layout:      ACCOUNT-RECORD (300 bytes)")
validation_lines.append(f"Data file:          app/data/ASCII/acctdata.txt")
validation_lines.append(f"Raw line count:     {raw_line_count}")
validation_lines.append(f"Parsed row count:   {parsed_row_count}")
validation_lines.append(
    f"Row count match:    {'PASS' if raw_line_count == parsed_row_count else 'FAIL'}"
)
validation_lines.append("")
validation_lines.append("-" * 80)
validation_lines.append("SCHEMA (non-FILLER fields):")
validation_lines.append("-" * 80)
validation_lines.append(
    f"{'Field':<30} {'PIC':<18} {'PySpark Type':<20} {'Offset':<8} {'Len':<5}"
)
for field in schema_json["fields"]:
    if field["name"] == "FILLER":
        continue
    validation_lines.append(
        f"{field['name']:<30} {field['cobol_pic']:<18} "
        f"{field['pyspark_type']:<20} {field['byte_offset']:<8} {field['length']:<5}"
    )

validation_lines.append("")
validation_lines.append("-" * 80)
validation_lines.append("SAMPLE ROWS (first 5):")
validation_lines.append("-" * 80)
for i, row in enumerate(sample_rows):
    validation_lines.append(f"\n--- Record {i + 1} ---")
    for field in schema_json["fields"]:
        if field["name"] == "FILLER":
            continue
        val = row[field["name"]]
        validation_lines.append(f"  {field['name']:<30} = {val}")

validation_lines.append("")
validation_lines.append("-" * 80)
validation_lines.append("COLUMN-LEVEL STATISTICS:")
validation_lines.append("-" * 80)

# Null counts and distinct counts for each non-FILLER column
non_filler_cols = [f["name"] for f in schema_json["fields"] if f["name"] != "FILLER"]
null_exprs = [
    F.sum(F.when(F.col(c).isNull(), 1).otherwise(0)).alias(f"{c}_nulls")
    for c in non_filler_cols
]
distinct_exprs = [
    F.countDistinct(F.col(c)).alias(f"{c}_distinct")
    for c in non_filler_cols
]
null_stats = df.agg(*null_exprs).collect()[0]
distinct_stats = df.agg(*distinct_exprs).collect()[0]

validation_lines.append(
    f"{'Field':<30} {'Nulls':<10} {'Distinct':<10}"
)
for col_name in non_filler_cols:
    null_count = null_stats[f"{col_name}_nulls"]
    distinct_count = distinct_stats[f"{col_name}_distinct"]
    validation_lines.append(
        f"{col_name:<30} {null_count:<10} {distinct_count:<10}"
    )

validation_lines.append("")
validation_lines.append("=" * 80)
validation_lines.append("END OF VALIDATION REPORT")
validation_lines.append("=" * 80)

# Write validation output
validation_text = "\n".join(validation_lines)
os.makedirs(os.path.dirname(VALIDATION_OUTPUT), exist_ok=True)
with open(VALIDATION_OUTPUT, "w") as fh:
    fh.write(validation_text + "\n")

# Also print to console
print(validation_text)

# Show the full DataFrame schema and first 10 rows
print("\n\nDataFrame Schema:")
df.printSchema()
print("\nFirst 10 rows:")
df.show(10, truncate=False)

spark.stop()
