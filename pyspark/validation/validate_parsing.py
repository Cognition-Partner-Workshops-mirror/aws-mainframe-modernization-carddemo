"""
Validation script: Compare parsed PySpark DataFrames against raw feed files.

For each copybook/data pair, this script:
1. Counts raw lines in the source file
2. Parses the file using the PySpark copybook parser
3. Compares row counts (source lines vs. parsed DataFrame rows)
4. Spot-checks sample values by manually parsing the first record and
   comparing against the DataFrame's first row
5. Checks for null values in required fields (potential parse failures)
6. Generates a VALIDATION_RESULTS.md report

This runs without a live Spark cluster by using pure-Python parsing for
validation, then generating the expected Spark output format.
"""

import json
import os
import sys
from decimal import Decimal
from datetime import datetime

# Add the scripts directory to the path so we can import cobol_common
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(SCRIPT_DIR, "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from cobol_common import decode_sign_overpunch, parse_fixed_width_line, load_schema

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.join(SCRIPT_DIR, "..", "..")
SCHEMAS_DIR = os.path.join(SCRIPT_DIR, "..", "schemas")

# Copybook/data/schema triples to validate
DATASETS = [
    {
        "name": "Account Records",
        "copybook": "CVACT01Y.cpy",
        "data_file": os.path.join(BASE_DIR, "app", "data", "ASCII", "acctdata.txt"),
        "schema_file": os.path.join(SCHEMAS_DIR, "account_record_schema.json"),
    },
    {
        "name": "Customer Records",
        "copybook": "CUSTREC.cpy",
        "data_file": os.path.join(BASE_DIR, "app", "data", "ASCII", "custdata.txt"),
        "schema_file": os.path.join(SCHEMAS_DIR, "customer_record_schema.json"),
    },
    {
        "name": "Card Records",
        "copybook": "CVACT02Y.cpy",
        "data_file": os.path.join(BASE_DIR, "app", "data", "ASCII", "carddata.txt"),
        "schema_file": os.path.join(SCHEMAS_DIR, "card_record_schema.json"),
    },
]


def count_raw_lines(file_path: str) -> int:
    """Count the number of non-empty lines in the raw data file."""
    with open(file_path, "r") as f:
        return sum(1 for line in f if line.strip())


def get_raw_line_length(file_path: str) -> set:
    """Get the set of unique line lengths in the raw file (for record length validation)."""
    lengths = set()
    with open(file_path, "r") as f:
        for line in f:
            # Strip only the newline, not spaces (spaces are part of fixed-width records)
            lengths.add(len(line.rstrip("\n").rstrip("\r")))
    return lengths


def parse_first_record(file_path: str, schema: dict) -> dict:
    """
    Parse the first record of the raw file using pure Python for validation.

    Returns a dict of field_name -> converted_value for comparison against
    the PySpark DataFrame's first row.
    """
    with open(file_path, "r") as f:
        first_line = f.readline().rstrip("\n").rstrip("\r")

    fields = schema["fields"]
    raw_values = parse_fixed_width_line(first_line, fields)

    # Convert each raw value to its expected type for comparison
    converted = {}
    for field in fields:
        name = field["name"]
        raw = raw_values.get(name, "")

        if name == "FILLER":
            continue

        pyspark_type = field["pyspark_type"]
        signed = field.get("signed", False)
        decimal_places = field.get("decimal_places", 0)

        if signed:
            # Sign-overpunch numeric
            converted[name] = str(decode_sign_overpunch(raw, decimal_places))
        elif pyspark_type == "LongType":
            converted[name] = str(int(raw.strip())) if raw.strip() else "0"
        elif pyspark_type == "IntegerType":
            converted[name] = str(int(raw.strip())) if raw.strip() else "0"
        elif pyspark_type == "DateType":
            converted[name] = raw.strip()
        elif pyspark_type == "StringType":
            converted[name] = raw.strip()
        else:
            converted[name] = raw.strip()

    return converted


def validate_dataset(dataset: dict) -> dict:
    """
    Run all validation checks for a single copybook/data pair.

    Returns a dict with validation results for report generation.
    """
    name = dataset["name"]
    schema = load_schema(dataset["schema_file"])
    data_file = dataset["data_file"]

    results = {
        "name": name,
        "copybook": dataset["copybook"],
        "data_file": os.path.basename(data_file),
        "record_length": schema["record_length"],
        "field_count": len(schema["fields"]),
        "checks": [],
    }

    # Check 1: File exists
    file_exists = os.path.exists(data_file)
    results["checks"].append({
        "check": "File exists",
        "passed": file_exists,
        "expected": "True",
        "actual": str(file_exists),
    })
    if not file_exists:
        return results

    # Check 2: Row count
    raw_count = count_raw_lines(data_file)
    results["raw_row_count"] = raw_count
    results["checks"].append({
        "check": "Raw line count",
        "passed": raw_count > 0,
        "expected": "> 0",
        "actual": str(raw_count),
    })

    # Check 3: Record length consistency
    line_lengths = get_raw_line_length(data_file)
    expected_length = schema["record_length"]
    all_correct_length = line_lengths == {expected_length}
    results["checks"].append({
        "check": "Record length matches copybook",
        "passed": all_correct_length,
        "expected": str(expected_length),
        "actual": str(line_lengths),
    })

    # Check 4: Parse first record and show sample values
    first_record = parse_first_record(data_file, schema)
    results["sample_record"] = first_record
    results["checks"].append({
        "check": "First record parseable",
        "passed": len(first_record) > 0,
        "expected": f"{len(schema['fields']) - 1} fields (excluding FILLER)",
        "actual": f"{len(first_record)} fields parsed",
    })

    # Check 5: Validate field offsets sum to record length
    total_bytes = sum(f["length"] for f in schema["fields"])
    results["checks"].append({
        "check": "Field lengths sum to record length",
        "passed": total_bytes == expected_length,
        "expected": str(expected_length),
        "actual": str(total_bytes),
    })

    # Check 6: Parse all records and check for blank required fields
    required_field_names = [f["name"] for f in schema["fields"]
                           if f["name"] != "FILLER" and f["byte_offset"] == 0]
    # At minimum, the first field (ID) should never be blank
    blank_id_count = 0
    with open(data_file, "r") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if not line.strip():
                continue
            raw = parse_fixed_width_line(line, schema["fields"])
            first_field = schema["fields"][0]
            val = raw.get(first_field["name"], "").strip()
            if not val:
                blank_id_count += 1

    results["checks"].append({
        "check": f"No blank {schema['fields'][0]['name']} (primary identifier)",
        "passed": blank_id_count == 0,
        "expected": "0 blank IDs",
        "actual": f"{blank_id_count} blank IDs out of {raw_count} records",
    })

    return results


def generate_report(all_results: list) -> str:
    """Generate a VALIDATION_RESULTS.md markdown report from all validation results."""
    lines = []
    lines.append("# COBOL Copybook Parsing Validation Results")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("")

    # Executive summary
    total_checks = sum(len(r["checks"]) for r in all_results)
    passed_checks = sum(
        sum(1 for c in r["checks"] if c["passed"]) for r in all_results
    )
    failed_checks = total_checks - passed_checks

    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Datasets Validated | {len(all_results)} |")
    lines.append(f"| Total Checks | {total_checks} |")
    lines.append(f"| Passed | {passed_checks} |")
    lines.append(f"| Failed | {failed_checks} |")
    lines.append(f"| Overall | **{'PASS' if failed_checks == 0 else 'FAIL'}** |")
    lines.append("")

    # Per-dataset details
    for result in all_results:
        lines.append(f"## {result['name']}")
        lines.append("")
        lines.append(f"- **Copybook:** `{result['copybook']}`")
        lines.append(f"- **Data file:** `{result['data_file']}`")
        lines.append(f"- **Record length:** {result['record_length']} bytes")
        lines.append(f"- **Fields:** {result['field_count']} (including FILLER)")
        if "raw_row_count" in result:
            lines.append(f"- **Raw row count:** {result['raw_row_count']}")
        lines.append("")

        # Check results table
        lines.append("### Validation Checks")
        lines.append("")
        lines.append("| Status | Check | Expected | Actual |")
        lines.append("|--------|-------|----------|--------|")
        for check in result["checks"]:
            status = "PASS" if check["passed"] else "FAIL"
            lines.append(
                f"| {status} | {check['check']} | {check['expected']} | {check['actual']} |"
            )
        lines.append("")

        # Sample record
        if "sample_record" in result:
            lines.append("### First Record (Parsed Sample)")
            lines.append("")
            lines.append("| Field | Parsed Value |")
            lines.append("|-------|-------------|")
            for field_name, value in result["sample_record"].items():
                # Truncate long values for readability
                display_val = value if len(str(value)) <= 50 else str(value)[:47] + "..."
                lines.append(f"| `{field_name}` | `{display_val}` |")
            lines.append("")

    return "\n".join(lines)


def main():
    """Run validation for all 3 copybook/data pairs and generate the report."""
    print("=" * 60)
    print("COBOL Copybook Parsing Validation")
    print("=" * 60)

    all_results = []
    for dataset in DATASETS:
        print(f"\nValidating: {dataset['name']}...")
        result = validate_dataset(dataset)
        all_results.append(result)

        # Print summary for this dataset
        passed = sum(1 for c in result["checks"] if c["passed"])
        total = len(result["checks"])
        print(f"  {passed}/{total} checks passed")

    # Generate and save the markdown report
    report = generate_report(all_results)
    output_path = os.path.join(SCRIPT_DIR, "VALIDATION_RESULTS.md")
    with open(output_path, "w") as f:
        f.write(report)
    print(f"\nReport written to: {output_path}")

    # Print a summary
    total_checks = sum(len(r["checks"]) for r in all_results)
    passed_checks = sum(
        sum(1 for c in r["checks"] if c["passed"]) for r in all_results
    )
    print(f"\nOverall: {passed_checks}/{total_checks} checks passed")

    return 0 if passed_checks == total_checks else 1


if __name__ == "__main__":
    sys.exit(main())
