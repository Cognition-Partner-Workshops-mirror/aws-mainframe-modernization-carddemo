"""
Master validation script — runs all three parsers and produces a consolidated
validation report comparing PySpark DataFrame outputs against the raw feed files.
"""

import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, length as spark_length, substring, trim, udf
from pyspark.sql.types import (
    DecimalType,
    IntegerType,
    LongType,
    StringType,
)

sys.path.insert(0, os.path.dirname(__file__))
from cobol_utils import decode_zoned_decimal  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# ── field specs ──────────────────────────────────────────────────────────────
ACCT_FIELDS = [
    ("ACCT_ID",                1,  11, "numeric"),
    ("ACCT_ACTIVE_STATUS",    12,   1, "string"),
    ("ACCT_CURR_BAL",         13,  12, "signed_decimal"),
    ("ACCT_CREDIT_LIMIT",     25,  12, "signed_decimal"),
    ("ACCT_CASH_CREDIT_LIMIT",37,  12, "signed_decimal"),
    ("ACCT_OPEN_DATE",        49,  10, "string"),
    ("ACCT_EXPIRAION_DATE",   59,  10, "string"),
    ("ACCT_REISSUE_DATE",     69,  10, "string"),
    ("ACCT_CURR_CYC_CREDIT",  79, 12, "signed_decimal"),
    ("ACCT_CURR_CYC_DEBIT",   91, 12, "signed_decimal"),
    ("ACCT_ADDR_ZIP",        103,  10, "string"),
    ("ACCT_GROUP_ID",        113,  10, "string"),
    ("FILLER",               123, 178, "string"),
]

CUST_FIELDS = [
    ("CUST_ID",                  1,   9, "numeric_long"),
    ("CUST_FIRST_NAME",         10,  25, "string"),
    ("CUST_MIDDLE_NAME",        35,  25, "string"),
    ("CUST_LAST_NAME",          60,  25, "string"),
    ("CUST_ADDR_LINE_1",        85,  50, "string"),
    ("CUST_ADDR_LINE_2",       135,  50, "string"),
    ("CUST_ADDR_LINE_3",       185,  50, "string"),
    ("CUST_ADDR_STATE_CD",     235,   2, "string"),
    ("CUST_ADDR_COUNTRY_CD",   237,   3, "string"),
    ("CUST_ADDR_ZIP",          240,  10, "string"),
    ("CUST_PHONE_NUM_1",       250,  15, "string"),
    ("CUST_PHONE_NUM_2",       265,  15, "string"),
    ("CUST_SSN",               280,   9, "numeric_long"),
    ("CUST_GOVT_ISSUED_ID",    289,  20, "string"),
    ("CUST_DOB_YYYYMMDD",      309,  10, "string"),
    ("CUST_EFT_ACCOUNT_ID",    319,  10, "string"),
    ("CUST_PRI_CARD_HOLDER_IND", 329, 1, "string"),
    ("CUST_FICO_CREDIT_SCORE", 330,   3, "numeric_int"),
    ("FILLER",                 333, 168, "string"),
]

CARD_FIELDS = [
    ("CARD_NUM",              1,  16, "string"),
    ("CARD_ACCT_ID",         17,  11, "numeric_long"),
    ("CARD_CVV_CD",          28,   3, "numeric_int"),
    ("CARD_EMBOSSED_NAME",   31,  50, "string"),
    ("CARD_EXPIRAION_DATE",  81,  10, "string"),
    ("CARD_ACTIVE_STATUS",   91,   1, "string"),
    ("FILLER",               92,  59, "string"),
]


def parse_fixed_width(spark, data_path, fields):
    """Read a fixed-width file and split into columns according to field spec."""
    raw_df = spark.read.text(data_path)

    decode_udf = udf(lambda v: str(decode_zoned_decimal(v, 2)), StringType())

    for name, offset, length, _ in fields:
        raw_df = raw_df.withColumn(name, substring(col("value"), offset, length))
    raw_df = raw_df.drop("value")

    for name, _, _, type_tag in fields:
        if type_tag == "numeric" or type_tag == "numeric_long":
            raw_df = raw_df.withColumn(name, trim(col(name)).cast(LongType()))
        elif type_tag == "numeric_int":
            raw_df = raw_df.withColumn(name, trim(col(name)).cast(IntegerType()))
        elif type_tag == "signed_decimal":
            raw_df = raw_df.withColumn(
                name, decode_udf(col(name)).cast(DecimalType(12, 2))
            )
        elif type_tag == "string":
            raw_df = raw_df.withColumn(name, trim(col(name)))

    return raw_df


def count_raw_lines(filepath):
    """Count non-empty lines in the raw text file."""
    with open(filepath) as fh:
        return sum(1 for line in fh if line.strip())


def validate_dataset(spark, label, data_path, fields, record_length, report_lines):
    """Parse one dataset, validate counts, and append results to report_lines."""
    report_lines.append(f"\n{'=' * 70}")
    report_lines.append(f"  {label}")
    report_lines.append(f"{'=' * 70}")

    raw_count = count_raw_lines(data_path)
    report_lines.append(f"Raw file line count : {raw_count}")

    df = parse_fixed_width(spark, data_path, fields)
    df_count = df.count()
    report_lines.append(f"PySpark row count   : {df_count}")
    match = "PASS" if raw_count == df_count else "FAIL"
    report_lines.append(f"Row count match     : {match}")

    # Record-length check
    raw_df = spark.read.text(data_path)
    bad_len = raw_df.filter(spark_length(col("value")) != record_length).count()
    len_check = "PASS" if bad_len == 0 else f"FAIL ({bad_len} bad rows)"
    report_lines.append(f"Record length check : {len_check}  (expected {record_length})")

    # Null check on key columns (exclude FILLER)
    key_cols = [name for name, _, _, _ in fields if name != "FILLER"]
    null_counts = {}
    for c in key_cols:
        nc = df.filter(col(c).isNull()).count()
        if nc > 0:
            null_counts[c] = nc
    if null_counts:
        report_lines.append(f"Null values found   : {null_counts}")
    else:
        report_lines.append(f"Null values found   : NONE (all key fields populated)")

    # Sample rows
    report_lines.append(f"\nSample rows (first 3):")
    sample_df = df.drop("FILLER")
    rows = sample_df.head(3)
    col_names = sample_df.columns
    for i, row in enumerate(rows):
        report_lines.append(f"  Row {i + 1}:")
        for cn in col_names:
            report_lines.append(f"    {cn:30s} = {row[cn]}")

    return df


def main():
    spark = SparkSession.builder \
        .appName("CardDemo Copybook Validation") \
        .master("local[*]") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    spark.sparkContext.addPyFile(
        os.path.join(os.path.dirname(__file__), "cobol_utils.py")
    )

    report = ["COPYBOOK PARSING VALIDATION REPORT", "=" * 70]

    # ── Account ──────────────────────────────────────────────────────────
    acct_path = os.path.join(REPO_ROOT, "app/data/ASCII/acctdata.txt")
    acct_df = validate_dataset(
        spark, "ACCOUNT-RECORD  (CVACT01Y.cpy → acctdata.txt)",
        acct_path, ACCT_FIELDS, 300, report,
    )

    # ── Customer ─────────────────────────────────────────────────────────
    cust_path = os.path.join(REPO_ROOT, "app/data/ASCII/custdata.txt")
    cust_df = validate_dataset(
        spark, "CUSTOMER-RECORD  (CUSTREC.cpy → custdata.txt)",
        cust_path, CUST_FIELDS, 500, report,
    )

    # ── Card ─────────────────────────────────────────────────────────────
    card_path = os.path.join(REPO_ROOT, "app/data/ASCII/carddata.txt")
    card_df = validate_dataset(
        spark, "CARD-RECORD  (CVACT02Y.cpy → carddata.txt)",
        card_path, CARD_FIELDS, 150, report,
    )

    # ── Write report ─────────────────────────────────────────────────────
    report_text = "\n".join(report) + "\n"
    print(report_text)

    output_path = os.path.join(
        REPO_ROOT, "pyspark_parsers", "validation", "validation_report.txt"
    )
    with open(output_path, "w") as fh:
        fh.write(report_text)
    print(f"\nReport written to: {output_path}")

    # ── Write CSVs ───────────────────────────────────────────────────────
    for label, df, fname in [
        ("account", acct_df, "acctdata_parsed.csv"),
        ("customer", cust_df, "custdata_parsed.csv"),
        ("card", card_df, "carddata_parsed.csv"),
    ]:
        csv_path = os.path.join(
            REPO_ROOT, "pyspark_parsers", "validation", fname
        )
        df.drop("FILLER").toPandas().to_csv(csv_path, index=False)
        print(f"  {label} CSV → {csv_path}")

    spark.stop()


if __name__ == "__main__":
    main()
