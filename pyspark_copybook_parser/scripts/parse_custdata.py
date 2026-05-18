"""
PySpark script to parse the COBOL fixed-width customer data file
(``app/data/ASCII/custdata.txt``) using the copybook-derived schema
from ``CUSTREC.cpy``.

Record layout: CUSTOMER-RECORD  (500 bytes per record)
Key type-mapping decisions:
  - PIC 9(09)  → LongType      (unsigned numeric display, 9-digit IDs/SSN)
  - PIC 9(03)  → IntegerType   (unsigned numeric display, 3-digit score)
  - PIC X(n)   → StringType    (alphanumeric, trailing spaces trimmed)

No signed-decimal (PIC S9…V99) fields exist in CUSTREC — all numeric
fields are unsigned display (PIC 9).

Usage:
    spark-submit parse_custdata.py
    # or
    python parse_custdata.py
"""

import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Allow running from any working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cobol_utils import get_project_root, load_schema, parse_fixed_width_file

# ---------------------------------------------------------------------------
# Spark session
# ---------------------------------------------------------------------------
spark = SparkSession.builder \
    .appName("CardDemo_CUSTREC_CustData_Parser") \
    .master("local[*]") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = get_project_root()
DATA_FILE = os.path.join(PROJECT_ROOT, "app", "data", "ASCII", "custdata.txt")
SCHEMA_FILE = os.path.join(
    PROJECT_ROOT, "pyspark_copybook_parser", "schemas", "CUSTREC_schema.json"
)
VALIDATION_OUTPUT = os.path.join(
    PROJECT_ROOT, "pyspark_copybook_parser", "validation", "custdata_validation.txt"
)

# ---------------------------------------------------------------------------
# Load schema and parse fixed-width file
# ---------------------------------------------------------------------------
schema_json = load_schema(SCHEMA_FILE)
df = parse_fixed_width_file(spark, DATA_FILE, schema_json)

# No signed-decimal columns in CUSTREC — all fields are either PIC X or PIC 9

# ---------------------------------------------------------------------------
# Validation: row count and sample data
# ---------------------------------------------------------------------------
raw_line_count = spark.read.text(DATA_FILE).count()
parsed_row_count = df.count()

sample_rows = df.limit(5).collect()

# Build validation report
validation_lines = []
validation_lines.append("=" * 80)
validation_lines.append("VALIDATION REPORT: custdata.txt (CUSTREC.cpy / CUSTOMER-RECORD)")
validation_lines.append("=" * 80)
validation_lines.append(f"Copybook:           CUSTREC.cpy")
validation_lines.append(f"Record layout:      CUSTOMER-RECORD (500 bytes)")
validation_lines.append(f"Data file:          app/data/ASCII/custdata.txt")
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

print(validation_text)

print("\n\nDataFrame Schema:")
df.printSchema()
print("\nFirst 10 rows:")
df.show(10, truncate=False)

spark.stop()
