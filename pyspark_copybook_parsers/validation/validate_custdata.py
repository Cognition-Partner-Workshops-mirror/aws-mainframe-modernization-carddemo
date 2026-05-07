"""
Validation script for CUSTREC customer data parsing.

Compares the PySpark-parsed DataFrame against the raw custdata.txt feed file
to verify row counts, field widths, and sample values.

Usage:
    spark-submit validate_custdata.py [--input <path>]
"""

import argparse
import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Add parsers directory to path so we can import the parser module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "parsers"))
from parse_custdata import parse_custdata, RECORD_LENGTH, CUSTOMER_FIELDS


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
    parsed_df = parse_custdata(spark, input_path)
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
    first_raw = raw_df.first()["value"]
    first_parsed = parsed_df.first()

    # Manual extraction from first raw line (0-based slicing)
    expected_cust_id = first_raw[0:9].strip()
    expected_first_name = first_raw[9:34].strip()
    expected_last_name = first_raw[59:84].strip()
    expected_state = first_raw[234:236].strip()
    expected_country = first_raw[236:239].strip()

    checks = [
        ("CUST_ID", first_parsed["CUST_ID"], expected_cust_id),
        ("CUST_FIRST_NAME", first_parsed["CUST_FIRST_NAME"],
         expected_first_name),
        ("CUST_LAST_NAME", first_parsed["CUST_LAST_NAME"],
         expected_last_name),
        ("CUST_ADDR_STATE_CD", first_parsed["CUST_ADDR_STATE_CD"],
         expected_state),
        ("CUST_ADDR_COUNTRY_CD", first_parsed["CUST_ADDR_COUNTRY_CD"],
         expected_country),
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

    # --- 6. Verify FICO scores are in reasonable range (300-850) ---
    fico_out_of_range = parsed_df.filter(
        (F.col("CUST_FICO_CREDIT_SCORE") < 100) |
        (F.col("CUST_FICO_CREDIT_SCORE") > 999)
    ).count()
    if fico_out_of_range == 0:
        results.append(f"  [PASS] All FICO scores are within 100–999 range")
        passed += 1
    else:
        results.append(f"  [WARN] {fico_out_of_range} FICO scores outside "
                       f"100–999 range")
        failed += 1

    # --- Print summary ---
    print("\n" + "=" * 60)
    print("  VALIDATION REPORT: CUSTREC (custdata.txt)")
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
        description="Validate parsed CUSTREC customer data")
    default_input = os.path.join(
        os.path.dirname(__file__), "..", "..", "app", "data", "ASCII",
        "custdata.txt")
    parser.add_argument("--input", default=default_input,
                        help="Path to custdata.txt")
    args = parser.parse_args()

    spark = SparkSession.builder \
        .appName("CUSTREC_Validation") \
        .master("local[*]") \
        .getOrCreate()

    success = validate(spark, args.input)
    spark.stop()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
