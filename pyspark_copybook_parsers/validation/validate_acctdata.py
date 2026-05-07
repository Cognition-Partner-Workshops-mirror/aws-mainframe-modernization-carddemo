"""
Validation script for CVACT01Y account data parsing.

Compares the PySpark-parsed DataFrame against the raw acctdata.txt feed file
to verify row counts, field widths, and sample values.

Usage:
    spark-submit validate_acctdata.py [--input <path>]
"""

import argparse
import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Add parsers directory to path so we can import the parser module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "parsers"))
from parse_acctdata import parse_acctdata, RECORD_LENGTH, ACCOUNT_FIELDS


def validate(spark: SparkSession, input_path: str):
    """Run validation checks and print a report."""
    passed = 0
    failed = 0
    results = []

    # --- 1. Raw file row count ---
    raw_df = spark.read.text(input_path)
    raw_count = raw_df.count()
    results.append(f"  Raw file row count: {raw_count}")

    # --- 2. Verify every raw line matches expected record length ---
    bad_len = raw_df.filter(F.length("value") != RECORD_LENGTH).count()
    if bad_len == 0:
        results.append(f"  [PASS] All {raw_count} lines are exactly "
                       f"{RECORD_LENGTH} bytes")
        passed += 1
    else:
        results.append(f"  [FAIL] {bad_len} lines do NOT match expected "
                       f"{RECORD_LENGTH}-byte record length")
        failed += 1

    # --- 3. Parse and compare row counts ---
    parsed_df = parse_acctdata(spark, input_path)
    parsed_count = parsed_df.count()
    if parsed_count == raw_count:
        results.append(f"  [PASS] Parsed row count ({parsed_count}) matches "
                       f"raw row count ({raw_count})")
        passed += 1
    else:
        results.append(f"  [FAIL] Parsed row count ({parsed_count}) != "
                       f"raw row count ({raw_count})")
        failed += 1

    # --- 4. Check for NULL values in key non-FILLER fields ---
    key_fields = [f[0] for f in ACCOUNT_FIELDS if f[0] != "FILLER"]
    # FILLER is already dropped from parsed_df
    for col_name in parsed_df.columns:
        null_count = parsed_df.filter(F.col(col_name).isNull()).count()
        if null_count == 0:
            results.append(f"  [PASS] Column '{col_name}' has zero NULLs")
            passed += 1
        else:
            results.append(f"  [WARN] Column '{col_name}' has {null_count} "
                           f"NULL value(s)")
            # NULLs in numeric decode could indicate bad overpunch chars
            failed += 1

    # --- 5. Spot-check first record values against manual extraction ---
    first_raw = raw_df.first()["value"]
    first_parsed = parsed_df.first()

    # Manual extraction from first raw line
    expected_acct_id = first_raw[0:11].strip()
    expected_status = first_raw[11:12].strip()
    expected_open_date = first_raw[48:58].strip()

    checks = [
        ("ACCT_ID", first_parsed["ACCT_ID"], expected_acct_id),
        ("ACCT_ACTIVE_STATUS", first_parsed["ACCT_ACTIVE_STATUS"],
         expected_status),
        ("ACCT_OPEN_DATE", first_parsed["ACCT_OPEN_DATE"],
         expected_open_date),
    ]
    for col_name, actual, expected in checks:
        if str(actual) == expected:
            results.append(f"  [PASS] First-row '{col_name}': "
                           f"expected='{expected}', got='{actual}'")
            passed += 1
        else:
            results.append(f"  [FAIL] First-row '{col_name}': "
                           f"expected='{expected}', got='{actual}'")
            failed += 1

    # --- 6. Display sample parsed rows ---
    results.append("\n  --- Sample Parsed Rows (first 5) ---")

    # --- Print summary ---
    print("\n" + "=" * 60)
    print("  VALIDATION REPORT: CVACT01Y (acctdata.txt)")
    print("=" * 60)
    for line in results:
        print(line)

    print(f"\n  TOTAL:  {passed} passed,  {failed} failed")
    print("=" * 60)

    # Show sample data
    parsed_df.show(5, truncate=False)

    return failed == 0


def main():
    parser = argparse.ArgumentParser(
        description="Validate parsed CVACT01Y account data")
    default_input = os.path.join(
        os.path.dirname(__file__), "..", "..", "app", "data", "ASCII",
        "acctdata.txt")
    parser.add_argument("--input", default=default_input,
                        help="Path to acctdata.txt")
    args = parser.parse_args()

    spark = SparkSession.builder \
        .appName("CVACT01Y_Validation") \
        .master("local[*]") \
        .getOrCreate()

    success = validate(spark, args.input)
    spark.stop()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
