"""
Validation script for CVACT02Y card data parsing.

Compares the PySpark-parsed DataFrame against the raw carddata.txt feed file
to verify row counts, field widths, and sample values.

Usage:
    spark-submit validate_carddata.py [--input <path>]
"""

import argparse
import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Add parsers directory to path so we can import the parser module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "parsers"))
from parse_carddata import parse_carddata, RECORD_LENGTH, CARD_FIELDS


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
    parsed_df = parse_carddata(spark, input_path)
    parsed_count = parsed_df.count()
    if parsed_count == raw_count:
        results.append(f"  [PASS] Parsed row count ({parsed_count}) matches "
                       f"raw row count ({raw_count})")
        passed += 1
    else:
        results.append(f"  [FAIL] Parsed row count ({parsed_count}) != "
                       f"raw row count ({raw_count})")
        failed += 1

    # --- 4. Check for NULL values in parsed columns ---
    for col_name in parsed_df.columns:
        null_count = parsed_df.filter(F.col(col_name).isNull()).count()
        if null_count == 0:
            results.append(f"  [PASS] Column '{col_name}' has zero NULLs")
            passed += 1
        else:
            results.append(f"  [WARN] Column '{col_name}' has {null_count} "
                           f"NULL value(s)")
            failed += 1

    # --- 5. Spot-check first record values against manual extraction ---
    # Sort by CARD_NUM to get deterministic ordering
    parsed_sorted = parsed_df.orderBy("CARD_NUM")
    raw_sorted = raw_df.orderBy("value")

    first_raw = raw_sorted.first()["value"]
    first_parsed = parsed_sorted.first()

    # Manual extraction from first raw line (0-based slicing)
    expected_card_num = first_raw[0:16].strip()
    expected_acct_id = first_raw[16:27].strip()
    expected_name = first_raw[30:80].strip()
    expected_status = first_raw[90:91].strip()

    checks = [
        ("CARD_NUM", first_parsed["CARD_NUM"], expected_card_num),
        ("CARD_ACCT_ID", first_parsed["CARD_ACCT_ID"], expected_acct_id),
        ("CARD_EMBOSSED_NAME", first_parsed["CARD_EMBOSSED_NAME"],
         expected_name),
        ("CARD_ACTIVE_STATUS", first_parsed["CARD_ACTIVE_STATUS"],
         expected_status),
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

    # --- 6. Verify CARD_ACTIVE_STATUS contains only expected values ---
    unexpected_status = parsed_df.filter(
        ~F.col("CARD_ACTIVE_STATUS").isin("Y", "N")
    ).count()
    if unexpected_status == 0:
        results.append(f"  [PASS] All CARD_ACTIVE_STATUS values are Y or N")
        passed += 1
    else:
        results.append(f"  [WARN] {unexpected_status} rows have unexpected "
                       f"CARD_ACTIVE_STATUS values")
        failed += 1

    # --- Print summary ---
    print("\n" + "=" * 60)
    print("  VALIDATION REPORT: CVACT02Y (carddata.txt)")
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
        description="Validate parsed CVACT02Y card data")
    default_input = os.path.join(
        os.path.dirname(__file__), "..", "..", "app", "data", "ASCII",
        "carddata.txt")
    parser.add_argument("--input", default=default_input,
                        help="Path to carddata.txt")
    args = parser.parse_args()

    spark = SparkSession.builder \
        .appName("CVACT02Y_Validation") \
        .master("local[*]") \
        .getOrCreate()

    success = validate(spark, args.input)
    spark.stop()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
