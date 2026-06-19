#!/usr/bin/env python3
"""
Compare modernized parser output against golden reference files.

Usage:
    python test-harness/compare_golden_files.py \
        --golden golden-files/ \
        --actual <modernized-output-dir>/

Performs field-by-field comparison and produces a detailed diff report.
Exit code 0 = all match, 1 = differences found.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from decimal import Decimal


def load_json(path: str) -> dict:
    """Load a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compare_field(field_name: str, expected: str, actual: str,
                  field_type: str) -> dict | None:
    """
    Compare a single field value. Returns None if equal, or a diff dict.

    For signed_decimal fields, compares numeric values (not string format).
    For alphanumeric fields, compares trimmed strings.
    """
    if field_type == "signed_decimal":
        try:
            exp_val = Decimal(str(expected))
            act_val = Decimal(str(actual))
            if exp_val == act_val:
                return None
            return {
                "field": field_name,
                "expected": str(expected),
                "actual": str(actual),
                "type": "numeric_mismatch",
                "delta": str(act_val - exp_val),
            }
        except Exception:
            pass

    # String comparison with whitespace normalization
    exp_str = str(expected).rstrip()
    act_str = str(actual).rstrip()
    if exp_str == act_str:
        return None

    return {
        "field": field_name,
        "expected": expected,
        "actual": actual,
        "type": "value_mismatch",
    }


def compare_records(expected: dict, actual: dict,
                    field_types: dict[str, str]) -> list[dict]:
    """Compare two record dicts field-by-field. Returns list of diffs."""
    diffs = []

    all_fields = set(expected.keys()) | set(actual.keys())
    for field in sorted(all_fields):
        if field not in expected:
            diffs.append({
                "field": field,
                "expected": "<missing>",
                "actual": actual[field],
                "type": "extra_field",
            })
        elif field not in actual:
            diffs.append({
                "field": field,
                "expected": expected[field],
                "actual": "<missing>",
                "type": "missing_field",
            })
        else:
            ft = field_types.get(field, "alphanumeric")
            diff = compare_field(field, expected[field], actual[field], ft)
            if diff:
                diffs.append(diff)

    return diffs


def compare_golden_file(golden_path: str, actual_path: str) -> dict:
    """
    Compare a golden file against an actual output file.

    Returns a comparison report dict.
    """
    golden = load_json(golden_path)
    actual = load_json(actual_path)

    entity = os.path.basename(golden_path).replace(".golden.json", "")

    # Build field type lookup from golden metadata
    field_types = {}
    if "metadata" in golden and "fields" in golden["metadata"]:
        for f in golden["metadata"]["fields"]:
            field_types[f["name"]] = f["type"]

    golden_records = golden.get("records", [])
    actual_records = actual.get("records", [])

    report = {
        "dimension": "golden-file",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "entity": entity,
        "records_expected": len(golden_records),
        "records_actual": len(actual_records),
        "records_compared": min(len(golden_records), len(actual_records)),
        "records_matched": 0,
        "records_failed": 0,
        "failures": [],
    }

    if len(golden_records) != len(actual_records):
        report["count_mismatch"] = True

    for i in range(min(len(golden_records), len(actual_records))):
        diffs = compare_records(golden_records[i], actual_records[i], field_types)
        if diffs:
            report["records_failed"] += 1
            report["failures"].append({
                "record_index": i,
                "diffs": diffs,
            })
        else:
            report["records_matched"] += 1

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare modernized output against golden reference files"
    )
    parser.add_argument(
        "--golden", required=True,
        help="Path to golden files directory",
    )
    parser.add_argument(
        "--actual", required=True,
        help="Path to actual (modernized) output directory",
    )
    parser.add_argument(
        "--report", default=None,
        help="Path to write JSON comparison report",
    )
    args = parser.parse_args()

    golden_dir = os.path.abspath(args.golden)
    actual_dir = os.path.abspath(args.actual)

    all_pass = True
    reports = []

    for filename in sorted(os.listdir(golden_dir)):
        if not filename.endswith(".golden.json"):
            continue

        golden_path = os.path.join(golden_dir, filename)
        actual_filename = filename  # Expect same name in actual dir
        actual_path = os.path.join(actual_dir, actual_filename)

        if not os.path.exists(actual_path):
            entity = filename.replace(".golden.json", "")
            reports.append({
                "entity": entity,
                "status": "MISSING",
                "message": f"Actual file not found: {actual_path}",
            })
            all_pass = False
            print(f"  FAIL  {entity:12s}  actual file missing")
            continue

        report = compare_golden_file(golden_path, actual_path)
        reports.append(report)

        entity = report["entity"]
        matched = report["records_matched"]
        failed = report["records_failed"]
        total = report["records_compared"]

        if failed == 0 and report.get("count_mismatch") is None:
            print(f"  PASS  {entity:12s}  {matched}/{total} records match")
        else:
            all_pass = False
            print(f"  FAIL  {entity:12s}  {failed}/{total} records differ")
            for failure in report["failures"][:3]:
                idx = failure["record_index"]
                for diff in failure["diffs"][:2]:
                    print(f"        record[{idx}].{diff['field']}: "
                          f"expected={diff['expected']!r} "
                          f"actual={diff['actual']!r}")

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(reports, f, indent=2)
        print(f"\nReport written to: {args.report}")

    if all_pass:
        print("\nAll golden file comparisons PASSED.")
        sys.exit(0)
    else:
        print("\nSome golden file comparisons FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
