"""
PySpark script to parse acctdata.txt (fixed-width, 300 bytes/record)
using the schema derived from COBOL copybook CVACT01Y.cpy (ACCOUNT-RECORD).

Sign-overpunch decoding is applied to PIC S9(10)V99 fields, where the
last byte encodes both the trailing digit and the sign:
  Positive: {=0, A=1, B=2, C=3, D=4, E=5, F=6, G=7, H=8, I=9
  Negative: } =0, J=1, K=2, L=3, M=4, N=5, O=6, P=7, Q=8, R=9
"""

import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DecimalType,
    LongType,
    StringType,
)

# ---------------------------------------------------------------------------
# Constants derived from CVACT01Y.cpy  (ACCOUNT-RECORD, RECLN 300)
# ---------------------------------------------------------------------------
RECORD_LENGTH = 300

# Each tuple: (field_name, cobol_pic, start_pos_1based, length, pyspark_type)
FIELD_DEFS = [
    ("ACCT_ID",                "9(11)",       1,  11, "LongType"),
    ("ACCT_ACTIVE_STATUS",     "X(01)",      12,   1, "StringType"),
    ("ACCT_CURR_BAL",          "S9(10)V99",  13,  12, "DecimalType(12,2)"),
    ("ACCT_CREDIT_LIMIT",      "S9(10)V99",  25,  12, "DecimalType(12,2)"),
    ("ACCT_CASH_CREDIT_LIMIT", "S9(10)V99",  37,  12, "DecimalType(12,2)"),
    ("ACCT_OPEN_DATE",         "X(10)",      49,  10, "StringType"),
    ("ACCT_EXPIRAION_DATE",    "X(10)",      59,  10, "StringType"),
    ("ACCT_REISSUE_DATE",      "X(10)",      69,  10, "StringType"),
    ("ACCT_CURR_CYC_CREDIT",   "S9(10)V99",  79,  12, "DecimalType(12,2)"),
    ("ACCT_CURR_CYC_DEBIT",    "S9(10)V99",  91,  12, "DecimalType(12,2)"),
    ("ACCT_ADDR_ZIP",          "X(10)",     103,  10, "StringType"),
    ("ACCT_GROUP_ID",          "X(10)",     113,  10, "StringType"),
    ("FILLER",                 "X(178)",    123, 178, "StringType"),
]

# ---------------------------------------------------------------------------
# Sign-overpunch maps  (EBCDIC-compatible, used in ASCII export files)
# ---------------------------------------------------------------------------
POSITIVE_MAP = {
    "{": "0", "A": "1", "B": "2", "C": "3", "D": "4",
    "E": "5", "F": "6", "G": "7", "H": "8", "I": "9",
}
NEGATIVE_MAP = {
    "}": "0", "J": "1", "K": "2", "L": "3", "M": "4",
    "N": "5", "O": "6", "P": "7", "Q": "8", "R": "9",
}


def decode_sign_overpunch(raw_value: str, scale: int = 2) -> str:
    """Decode a zoned-decimal string with sign overpunch on the last byte.

    Returns a string representation of the signed decimal number with
    *scale* implied decimal places.
    """
    if raw_value is None or len(raw_value) == 0:
        return None
    last_char = raw_value[-1]
    leading = raw_value[:-1]
    if last_char in POSITIVE_MAP:
        digits = leading + POSITIVE_MAP[last_char]
        sign = ""
    elif last_char in NEGATIVE_MAP:
        digits = leading + NEGATIVE_MAP[last_char]
        sign = "-"
    elif last_char.isdigit():
        # No overpunch – treat as positive unsigned value
        digits = raw_value
        sign = ""
    else:
        return None  # Unrecognised overpunch character

    # Insert implied decimal point
    if scale > 0:
        integer_part = digits[:-scale].lstrip("0") or "0"
        decimal_part = digits[-scale:]
        return f"{sign}{integer_part}.{decimal_part}"
    else:
        return f"{sign}{digits.lstrip('0') or '0'}"


# Register as a Spark UDF
decode_sign_overpunch_udf = F.udf(
    lambda v: decode_sign_overpunch(v, 2), StringType()
)


def build_spark_session(app_name: str = "ParseAcctData") -> SparkSession:
    """Create or retrieve a local SparkSession."""
    return (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .getOrCreate()
    )


def parse_acctdata(spark: SparkSession, input_path: str):
    """Read the fixed-width acctdata.txt and return a typed DataFrame."""
    # Read every line as a single string column called 'raw'
    raw_df = spark.read.text(input_path).withColumnRenamed("value", "raw")

    # Slice each field out of the raw string using 1-based substr
    for name, _pic, start, length, _ in FIELD_DEFS:
        raw_df = raw_df.withColumn(name, F.substring("raw", start, length))

    # Trim whitespace from all string fields
    for name, _pic, _s, _l, spark_type in FIELD_DEFS:
        if spark_type == "StringType":
            raw_df = raw_df.withColumn(name, F.trim(F.col(name)))

    # Decode sign-overpunch fields and cast to DecimalType(12,2)
    signed_fields = [
        name for name, _pic, _s, _l, st in FIELD_DEFS
        if st.startswith("DecimalType")
    ]
    for name in signed_fields:
        raw_df = raw_df.withColumn(name, decode_sign_overpunch_udf(F.col(name)))
        raw_df = raw_df.withColumn(name, F.col(name).cast(DecimalType(12, 2)))

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
        "VALIDATION REPORT – acctdata.txt  (CVACT01Y.cpy / ACCOUNT-RECORD)",
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
    report_path = os.path.join(output_dir, "validation_acctdata.txt")
    with open(report_path, "w") as f:
        f.write(report_text)
    print(report_text)
    return report_path


def main():
    # Resolve paths relative to this script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    input_path = os.path.join(repo_root, "app", "data", "ASCII", "acctdata.txt")
    output_dir = os.path.join(repo_root, "app", "pyspark_parsers")

    if not os.path.isfile(input_path):
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    spark = build_spark_session()
    try:
        df = parse_acctdata(spark, input_path)
        print(f"Schema for acctdata.txt ({df.count()} rows):")
        df.printSchema()
        df.show(5, truncate=False)
        validate(spark, df, input_path, output_dir)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
