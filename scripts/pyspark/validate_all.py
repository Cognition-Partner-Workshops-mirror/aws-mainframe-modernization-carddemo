"""
Validation script that compares parsed PySpark DataFrame row counts and
sample values against the raw fixed-width feed files for all three
copybook/data pairs:

  1. CVACT01Y.cpy  -> acctdata.txt  (ACCOUNT-RECORD, 300 bytes)
  2. CUSTREC.cpy   -> custdata.txt  (CUSTOMER-RECORD, 500 bytes)
  3. CVACT02Y.cpy  -> carddata.txt  (CARD-RECORD, 150 bytes)

Validation checks performed:
  - Row count matches between raw file and parsed DataFrame
  - Record length consistency (all lines equal expected length)
  - Sample field value spot-checks against manually extracted values
  - Null/blank detection in key fields
  - Data type integrity (numeric fields parse without errors)

Usage:
    python validate_all.py
"""

import json
import os
import sys
from decimal import Decimal

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Ensure the scripts directory is on the path for shared utility imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cobol_parser_utils import extract_fixed_width_fields

# Import field definitions from each parser module
from parse_acctdata import ACCOUNT_FIELDS
from parse_custdata import CUSTOMER_FIELDS
from parse_carddata import CARD_FIELDS

# Repository root for resolving data file paths
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


def count_raw_lines(file_path):
    """Count lines in a raw text file (without Spark overhead)."""
    with open(file_path, "r") as f:
        return sum(1 for _ in f)


def check_record_lengths(file_path, expected_length):
    """Verify every line in the file has the expected fixed-width length."""
    mismatched = []
    with open(file_path, "r") as f:
        for i, line in enumerate(f, start=1):
            # Strip only the trailing newline, not spaces (they are part of the record)
            stripped = line.rstrip("\n").rstrip("\r")
            if len(stripped) != expected_length:
                mismatched.append((i, len(stripped)))
    return mismatched


def validate_dataset(spark, name, data_file, field_defs, expected_length, spot_checks):
    """
    Run validation checks for a single copybook/data pair.

    Args:
        spark:           Active SparkSession.
        name:            Human-readable name for the dataset.
        data_file:       Relative path to the data file (from repo root).
        field_defs:      List of field definition dicts.
        expected_length: Expected record length in bytes.
        spot_checks:     List of dicts with {row_index, field, expected_value}
                         for sample value verification.

    Returns:
        A dict summarizing all validation results.
    """
    file_path = os.path.join(REPO_ROOT, data_file)
    results = {"dataset": name, "file": data_file, "checks": []}

    # --- Check 1: Raw line count ---
    raw_count = count_raw_lines(file_path)
    results["raw_line_count"] = raw_count
    results["checks"].append({
        "check": "raw_line_count",
        "value": raw_count,
        "status": "PASS" if raw_count > 0 else "FAIL"
    })

    # --- Check 2: Record length consistency ---
    length_mismatches = check_record_lengths(file_path, expected_length)
    results["checks"].append({
        "check": "record_length_consistency",
        "expected_length": expected_length,
        "mismatched_lines": len(length_mismatches),
        "details": length_mismatches[:5] if length_mismatches else [],
        "status": "PASS" if not length_mismatches else "FAIL"
    })

    # --- Check 3: PySpark parsed row count matches raw count ---
    raw_df = spark.read.text(file_path)
    parsed_df = extract_fixed_width_fields(raw_df, field_defs)

    # Drop FILLER for analysis
    if "FILLER" in parsed_df.columns:
        analysis_df = parsed_df.drop("FILLER")
    else:
        analysis_df = parsed_df

    parsed_count = analysis_df.count()
    count_match = (parsed_count == raw_count)
    results["parsed_row_count"] = parsed_count
    results["checks"].append({
        "check": "row_count_match",
        "raw_count": raw_count,
        "parsed_count": parsed_count,
        "status": "PASS" if count_match else "FAIL"
    })

    # --- Check 4: Null detection in key fields (non-FILLER) ---
    non_filler_fields = [f["name"] for f in field_defs if f["name"] != "FILLER"]
    null_counts = {}
    for col_name in non_filler_fields:
        if col_name in analysis_df.columns:
            nc = analysis_df.filter(F.col(col_name).isNull()).count()
            if nc > 0:
                null_counts[col_name] = nc

    results["checks"].append({
        "check": "null_detection",
        "fields_with_nulls": null_counts if null_counts else "none",
        "status": "PASS" if not null_counts else "WARN"
    })

    # --- Check 5: Spot-check sample values ---
    # Collect rows as a list for indexed access
    rows = analysis_df.collect()
    spot_results = []
    for sc in spot_checks:
        row_idx = sc["row_index"]
        field = sc["field"]
        expected = sc["expected_value"]

        if row_idx < len(rows):
            actual = rows[row_idx][field]
            # Convert Decimal to string for comparison if needed
            if isinstance(actual, Decimal):
                actual_str = str(actual)
                expected_str = str(expected)
                match = actual_str == expected_str
            else:
                actual_str = str(actual) if actual is not None else "None"
                expected_str = str(expected)
                match = actual_str == expected_str

            spot_results.append({
                "row": row_idx,
                "field": field,
                "expected": expected_str,
                "actual": actual_str,
                "status": "PASS" if match else "FAIL"
            })
        else:
            spot_results.append({
                "row": row_idx,
                "field": field,
                "expected": str(expected),
                "actual": "ROW_NOT_FOUND",
                "status": "FAIL"
            })

    results["checks"].append({
        "check": "spot_check_values",
        "details": spot_results,
        "status": "PASS" if all(s["status"] == "PASS" for s in spot_results) else "FAIL"
    })

    # --- Check 6: Sample rows for human review ---
    sample_rows = []
    for row in rows[:3]:
        sample_rows.append(row.asDict())
    # Convert Decimal objects to strings for JSON serialization
    for sr in sample_rows:
        for k, v in sr.items():
            if isinstance(v, Decimal):
                sr[k] = str(v)
    results["sample_rows"] = sample_rows

    return results


def main():
    """Run validation for all three copybook/data pairs."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    spark = SparkSession.builder \
        .appName("CardDemo_CopybookValidation") \
        .master("local[*]") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    all_results = []

    # -----------------------------------------------------------------------
    # 1. CVACT01Y.cpy -> acctdata.txt (ACCOUNT-RECORD)
    # Spot checks derived from manual inspection of first few raw lines
    # -----------------------------------------------------------------------
    acct_spot_checks = [
        {"row_index": 0, "field": "ACCT_ID",            "expected_value": 1},
        {"row_index": 0, "field": "ACCT_ACTIVE_STATUS",  "expected_value": "Y"},
        {"row_index": 0, "field": "ACCT_CURR_BAL",       "expected_value": "194.00"},
        {"row_index": 0, "field": "ACCT_CREDIT_LIMIT",   "expected_value": "2020.00"},
        {"row_index": 0, "field": "ACCT_OPEN_DATE",      "expected_value": "2014-11-20"},
        {"row_index": 1, "field": "ACCT_ID",             "expected_value": 2},
        {"row_index": 1, "field": "ACCT_CURR_BAL",       "expected_value": "158.00"},
    ]
    acct_results = validate_dataset(
        spark, "ACCOUNT-RECORD (CVACT01Y.cpy)",
        "app/data/ASCII/acctdata.txt", ACCOUNT_FIELDS,
        300, acct_spot_checks
    )
    all_results.append(acct_results)

    # -----------------------------------------------------------------------
    # 2. CUSTREC.cpy -> custdata.txt (CUSTOMER-RECORD)
    # -----------------------------------------------------------------------
    cust_spot_checks = [
        {"row_index": 0, "field": "CUST_ID",               "expected_value": 1},
        {"row_index": 0, "field": "CUST_FIRST_NAME",       "expected_value": "Immanuel"},
        {"row_index": 0, "field": "CUST_LAST_NAME",        "expected_value": "Kessler"},
        {"row_index": 0, "field": "CUST_ADDR_STATE_CD",    "expected_value": "NC"},
        {"row_index": 0, "field": "CUST_ADDR_COUNTRY_CD",  "expected_value": "USA"},
        {"row_index": 2, "field": "CUST_ID",               "expected_value": 3},
        {"row_index": 2, "field": "CUST_FIRST_NAME",       "expected_value": "Larry"},
    ]
    cust_results = validate_dataset(
        spark, "CUSTOMER-RECORD (CUSTREC.cpy)",
        "app/data/ASCII/custdata.txt", CUSTOMER_FIELDS,
        500, cust_spot_checks
    )
    all_results.append(cust_results)

    # -----------------------------------------------------------------------
    # 3. CVACT02Y.cpy -> carddata.txt (CARD-RECORD)
    # -----------------------------------------------------------------------
    card_spot_checks = [
        {"row_index": 0, "field": "CARD_NUM",            "expected_value": "0500024453765740"},
        {"row_index": 0, "field": "CARD_ACCT_ID",        "expected_value": 50},
        {"row_index": 0, "field": "CARD_CVV_CD",         "expected_value": 747},
        {"row_index": 0, "field": "CARD_EMBOSSED_NAME",  "expected_value": "Aniya Von"},
        {"row_index": 0, "field": "CARD_EXPIRAION_DATE", "expected_value": "2023-03-09"},
        {"row_index": 0, "field": "CARD_ACTIVE_STATUS",  "expected_value": "Y"},
    ]
    card_results = validate_dataset(
        spark, "CARD-RECORD (CVACT02Y.cpy)",
        "app/data/ASCII/carddata.txt", CARD_FIELDS,
        150, card_spot_checks
    )
    all_results.append(card_results)

    # -----------------------------------------------------------------------
    # Print and save consolidated results
    # -----------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("VALIDATION RESULTS SUMMARY")
    print("=" * 80)

    overall_pass = True
    for r in all_results:
        print(f"\n--- {r['dataset']} ---")
        print(f"  Raw lines:   {r['raw_line_count']}")
        print(f"  Parsed rows: {r['parsed_row_count']}")
        for check in r["checks"]:
            status = check["status"]
            if status == "FAIL":
                overall_pass = False
            print(f"  [{status}] {check['check']}", end="")
            if check["check"] == "spot_check_values":
                details = check.get("details", [])
                fails = [d for d in details if d["status"] == "FAIL"]
                if fails:
                    print(f" - {len(fails)} FAILED:")
                    for f in fails:
                        print(f"      Row {f['row']}, {f['field']}: "
                              f"expected={f['expected']}, actual={f['actual']}")
                else:
                    print(f" - all {len(details)} checks passed")
            elif check["check"] == "null_detection":
                nulls = check.get("fields_with_nulls", "none")
                if nulls != "none":
                    print(f" - fields: {nulls}")
                else:
                    print()
            else:
                print()

    # Write JSON validation report
    output_path = os.path.join(OUTPUT_DIR, "validation_report.json")
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nFull validation report written to: {output_path}")

    print("\n" + "=" * 80)
    if overall_pass:
        print("OVERALL: ALL VALIDATION CHECKS PASSED")
    else:
        print("OVERALL: SOME VALIDATION CHECKS FAILED - review details above")
    print("=" * 80)

    spark.stop()
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
