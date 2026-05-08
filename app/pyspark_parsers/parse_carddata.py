"""
PySpark script to parse carddata.txt (fixed-width, 150 bytes/record)
using the schema derived from COBOL copybook CVACT02Y.cpy (CARD-RECORD).

All fields are either unsigned numeric (PIC 9) or alphanumeric (PIC X),
so no sign-overpunch decoding is required for this copybook.
"""

import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import LongType

# ---------------------------------------------------------------------------
# Constants derived from CVACT02Y.cpy  (CARD-RECORD, RECLN 150)
# ---------------------------------------------------------------------------
RECORD_LENGTH = 150

# Each tuple: (field_name, cobol_pic, start_pos_1based, length, pyspark_type)
FIELD_DEFS = [
    ("CARD_NUM",             "X(16)",   1,  16, "StringType"),
    ("CARD_ACCT_ID",         "9(11)",  17,  11, "LongType"),
    ("CARD_CVV_CD",          "9(03)",  28,   3, "LongType"),
    ("CARD_EMBOSSED_NAME",   "X(50)",  31,  50, "StringType"),
    ("CARD_EXPIRAION_DATE",  "X(10)",  81,  10, "StringType"),
    ("CARD_ACTIVE_STATUS",   "X(01)",  91,   1, "StringType"),
    ("FILLER",               "X(59)",  92,  59, "StringType"),
]


def build_spark_session(app_name: str = "ParseCardData") -> SparkSession:
    """Create or retrieve a local SparkSession."""
    return (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .getOrCreate()
    )


def parse_carddata(spark: SparkSession, input_path: str):
    """Read the fixed-width carddata.txt and return a typed DataFrame."""
    # Read every line as a single string column called 'raw'
    raw_df = spark.read.text(input_path).withColumnRenamed("value", "raw")

    # Slice each field out of the raw string using 1-based substr
    for name, _pic, start, length, _ in FIELD_DEFS:
        raw_df = raw_df.withColumn(name, F.substring("raw", start, length))

    # Trim whitespace from all string fields
    for name, _pic, _s, _l, spark_type in FIELD_DEFS:
        if spark_type == "StringType":
            raw_df = raw_df.withColumn(name, F.trim(F.col(name)))

    # Cast unsigned numeric fields to LongType
    for name, _pic, _s, _l, spark_type in FIELD_DEFS:
        if spark_type == "LongType":
            raw_df = raw_df.withColumn(name, F.col(name).cast(LongType()))

    # Drop the raw line and FILLER column
    result_df = raw_df.drop("raw", "FILLER")
    return result_df


def validate(spark: SparkSession, df, input_path: str, output_dir: str):
    """Compare parsed DataFrame against the raw file and write validation report."""
    raw_df = spark.read.text(input_path)
    raw_count = raw_df.count()
    parsed_count = df.count()

    report_lines = [
        "=" * 72,
        "VALIDATION REPORT – carddata.txt  (CVACT02Y.cpy / CARD-RECORD)",
        "=" * 72,
        f"Raw file line count   : {raw_count}",
        f"Parsed DataFrame rows : {parsed_count}",
        f"Row-count match       : {'PASS' if raw_count == parsed_count else 'FAIL'}",
        "",
        "--- Sample rows (first 5) ---",
    ]

    # Collect first 5 rows for display
    sample_rows = df.limit(5).collect()
    col_names = df.columns
    for i, row in enumerate(sample_rows):
        report_lines.append(f"\nRow {i + 1}:")
        for col_name in col_names:
            report_lines.append(f"  {col_name:30s} = {row[col_name]}")

    # Null / anomaly checks
    report_lines.append("\n--- Null-value counts per column ---")
    null_counts = {}
    for col_name in col_names:
        cnt = df.filter(F.col(col_name).isNull()).count()
        null_counts[col_name] = cnt
        report_lines.append(f"  {col_name:30s} : {cnt}")

    report_text = "\n".join(report_lines) + "\n"

    # Write validation report to file
    report_path = os.path.join(output_dir, "validation_carddata.txt")
    with open(report_path, "w") as f:
        f.write(report_text)
    print(report_text)
    return report_path


def main():
    # Resolve paths relative to this script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    input_path = os.path.join(repo_root, "app", "data", "ASCII", "carddata.txt")
    output_dir = os.path.join(repo_root, "app", "pyspark_parsers")

    if not os.path.isfile(input_path):
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    spark = build_spark_session()
    try:
        df = parse_carddata(spark, input_path)
        print(f"Schema for carddata.txt ({df.count()} rows):")
        df.printSchema()
        df.show(5, truncate=False)
        validate(spark, df, input_path, output_dir)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
