"""Validation script that compares PySpark-parsed DataFrames against raw feed files.

For each copybook/data pair, verifies:
  - Row count matches the number of lines in the raw file
  - Record length matches the copybook-specified length
  - Sample field values match expected substrings from the raw file
  - Signed zoned-decimal fields decode correctly (overpunch sign)

Writes a validation report to validation/validation_report.txt.
"""

import json
import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, length as spark_length, substring, trim

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "scripts"))
from cobol_utils import decode_signed_zoned_decimal

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
SCHEMA_DIR = os.path.join(BASE_DIR, "copybook_parsing", "schemas")
DATA_DIR = os.path.join(BASE_DIR, "app", "data", "ASCII")
REPORT_PATH = os.path.join(BASE_DIR, "copybook_parsing", "validation",
                           "validation_report.txt")


def count_raw_lines(file_path):
    with open(file_path, "r") as f:
        return sum(1 for line in f if line.strip())


def read_raw_first_record(file_path):
    with open(file_path, "r") as f:
        return f.readline().rstrip("\n")


def load_schema(schema_name):
    path = os.path.join(SCHEMA_DIR, schema_name)
    with open(path, "r") as f:
        return json.load(f)


def build_spark_session():
    return (SparkSession.builder
            .appName("ValidateAll")
            .master("local[*]")
            .getOrCreate())


def validate_record_length(raw_line, expected_length, report):
    actual = len(raw_line)
    status = "PASS" if actual == expected_length else "FAIL"
    report.append(f"  Record length check: expected={expected_length}, "
                  f"actual={actual} [{status}]")
    return status == "PASS"


def validate_row_count(df, raw_count, report):
    parsed_count = df.count()
    status = "PASS" if parsed_count == raw_count else "FAIL"
    report.append(f"  Row count check: raw={raw_count}, "
                  f"parsed={parsed_count} [{status}]")
    return status == "PASS"


def validate_field_extraction(raw_line, schema, first_row, report):
    """Check that substring extraction matches raw bytes for the first record."""
    all_pass = True
    for field in schema["fields"]:
        if field["name"] == "FILLER":
            continue
        offset = field["offset"]
        length = field["length"]
        raw_value = raw_line[offset:offset + length]

        parsed_value = str(first_row[field["name"]]) if first_row[field["name"]] is not None else ""

        if field["cobol_pic"].startswith("PIC S"):
            decoded = decode_signed_zoned_decimal(raw_value, scale=2)
            expected_str = str(decoded) if decoded is not None else ""
            status = "PASS" if parsed_value == expected_str else "FAIL"
            report.append(
                f"    {field['name']:30s} raw='{raw_value}' "
                f"decoded='{expected_str}' parsed='{parsed_value}' [{status}]"
            )
        else:
            raw_trimmed = raw_value.strip()
            status = "PASS" if parsed_value == raw_trimmed else "FAIL"
            report.append(
                f"    {field['name']:30s} raw='{raw_trimmed}' "
                f"parsed='{parsed_value}' [{status}]"
            )

        if status == "FAIL":
            all_pass = False
    return all_pass


def validate_dataset(spark, schema_file, data_file, label, report):
    """Run all validations for one copybook/data pair."""
    report.append(f"\n{'='*70}")
    report.append(f"Validation: {label}")
    report.append(f"  Schema : {schema_file}")
    report.append(f"  Data   : {data_file}")
    report.append(f"{'='*70}")

    schema = load_schema(schema_file)
    data_path = os.path.join(DATA_DIR, data_file)
    raw_count = count_raw_lines(data_path)
    raw_first = read_raw_first_record(data_path)

    report.append(f"\n  --- Record Length ---")
    validate_record_length(raw_first, schema["record_length"], report)

    # Parse via the corresponding script's logic
    from parse_acctdata import parse_fixed_width as parse_acct
    from parse_custdata import parse_fixed_width as parse_cust
    from parse_carddata import parse_fixed_width as parse_card

    parsers = {
        "acctdata.txt": parse_acct,
        "custdata.txt": parse_cust,
        "carddata.txt": parse_card,
    }
    parse_fn = parsers[data_file]
    df = parse_fn(spark, data_path)

    report.append(f"\n  --- Row Count ---")
    validate_row_count(df, raw_count, report)

    report.append(f"\n  --- Field Extraction (first record) ---")
    first_row = df.first()
    validate_field_extraction(raw_first, schema, first_row, report)

    report.append(f"\n  --- Schema ---")
    schema_str = df._jdf.schema().treeString()
    for line in schema_str.split("\n"):
        report.append(f"    {line}")

    report.append(f"\n  --- Sample Data (first 3 rows) ---")
    sample_rows = df.limit(3).collect()
    non_filler = [f["name"] for f in schema["fields"] if f["name"] != "FILLER"]
    header = " | ".join(f"{n[:20]:20s}" for n in non_filler[:6])
    report.append(f"    {header}")
    report.append(f"    {'-'*len(header)}")
    for row in sample_rows:
        vals = " | ".join(
            f"{str(row[n] if row[n] is not None else '')[:20]:20s}"
            for n in non_filler[:6]
        )
        report.append(f"    {vals}")

    return df


def main():
    report = []
    report.append("COBOL Copybook Parsing — Validation Report")
    report.append(f"{'='*70}")

    spark = build_spark_session()

    datasets = [
        ("CVACT01Y_schema.json", "acctdata.txt",
         "CVACT01Y.cpy → ACCOUNT-RECORD (300 bytes)"),
        ("CUSTREC_schema.json", "custdata.txt",
         "CUSTREC.cpy → CUSTOMER-RECORD (500 bytes)"),
        ("CVACT02Y_schema.json", "carddata.txt",
         "CVACT02Y.cpy → CARD-RECORD (150 bytes)"),
    ]

    try:
        for schema_file, data_file, label in datasets:
            validate_dataset(spark, schema_file, data_file, label, report)
    finally:
        spark.stop()

    report_text = "\n".join(report) + "\n"
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.write(report_text)

    print(report_text)
    print(f"\nReport written to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
