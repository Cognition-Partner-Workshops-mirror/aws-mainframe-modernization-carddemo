"""
Validation script that runs all three PySpark parsers and compares
parsed DataFrame row counts and sample values against the raw feed files.

Outputs a validation report to generated/validation/validation_report.txt
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, trim, substring, udf, length as spark_length
from pyspark.sql.types import DecimalType
from decimal import Decimal
import os
import json
import sys

# --- Reusable overpunch decoder (same as parse_acctdata.py) ---
POSITIVE_OVERPUNCH = {'{': '0', 'A': '1', 'B': '2', 'C': '3', 'D': '4',
                      'E': '5', 'F': '6', 'G': '7', 'H': '8', 'I': '9'}
NEGATIVE_OVERPUNCH = {'}': '0', 'J': '1', 'K': '2', 'L': '3', 'M': '4',
                      'N': '5', 'O': '6', 'P': '7', 'Q': '8', 'R': '9'}


def decode_signed_numeric(raw_str, scale=2):
    """Decode COBOL DISPLAY signed numeric with overpunch on last byte."""
    if raw_str is None or len(raw_str.strip()) == 0:
        return None
    raw_str = raw_str.strip()
    last_char = raw_str[-1]
    digits_prefix = raw_str[:-1]

    if last_char in POSITIVE_OVERPUNCH:
        sign = ''
        last_digit = POSITIVE_OVERPUNCH[last_char]
    elif last_char in NEGATIVE_OVERPUNCH:
        sign = '-'
        last_digit = NEGATIVE_OVERPUNCH[last_char]
    elif last_char.isdigit():
        sign = ''
        last_digit = last_char
    else:
        return None

    full_digits = digits_prefix + last_digit
    if scale > 0:
        integer_part = full_digits[:-scale]
        decimal_part = full_digits[-scale:]
        numeric_str = sign + integer_part + '.' + decimal_part
    else:
        numeric_str = sign + full_digits
    return Decimal(numeric_str)


def count_raw_lines(file_path):
    """Count number of non-empty lines in raw data file."""
    count = 0
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def get_raw_line(file_path, line_num=0):
    """Get a specific raw line from the file (0-indexed)."""
    with open(file_path, 'r') as f:
        for i, line in enumerate(f):
            if i == line_num:
                return line.rstrip('\n')
    return None


def validate_account_data(spark, project_root, report_lines):
    """Validate CVACT01Y.cpy / acctdata.txt parsing."""
    report_lines.append("=" * 80)
    report_lines.append("VALIDATION: ACCOUNT-RECORD (CVACT01Y.cpy -> acctdata.txt)")
    report_lines.append("=" * 80)

    data_file = os.path.join(project_root, "app", "data", "ASCII", "acctdata.txt")

    # Raw file metrics
    raw_count = count_raw_lines(data_file)
    raw_line_1 = get_raw_line(data_file, 0)
    raw_line_len = len(raw_line_1) if raw_line_1 else 0

    report_lines.append(f"\n[RAW FILE]")
    report_lines.append(f"  File: {data_file}")
    report_lines.append(f"  Raw line count: {raw_count}")
    report_lines.append(f"  First line length: {raw_line_len} bytes (expected: 300)")
    report_lines.append(f"  Length check: {'PASS' if raw_line_len == 300 else 'FAIL'}")

    # Parse with PySpark
    decode_s9_10_v99 = udf(lambda x: decode_signed_numeric(x, scale=2), DecimalType(12, 2))

    raw_df = spark.read.text(data_file)
    parsed_df = raw_df \
        .withColumn("ACCT_ID", trim(substring(col("value"), 1, 11)).cast("long")) \
        .withColumn("ACCT_ACTIVE_STATUS", trim(substring(col("value"), 12, 1))) \
        .withColumn("ACCT_CURR_BAL", decode_s9_10_v99(substring(col("value"), 13, 12))) \
        .withColumn("ACCT_CREDIT_LIMIT", decode_s9_10_v99(substring(col("value"), 25, 12))) \
        .withColumn("ACCT_CASH_CREDIT_LIMIT", decode_s9_10_v99(substring(col("value"), 37, 12))) \
        .withColumn("ACCT_OPEN_DATE", trim(substring(col("value"), 49, 10))) \
        .withColumn("ACCT_EXPIRAION_DATE", trim(substring(col("value"), 59, 10))) \
        .withColumn("ACCT_REISSUE_DATE", trim(substring(col("value"), 69, 10))) \
        .withColumn("ACCT_CURR_CYC_CREDIT", decode_s9_10_v99(substring(col("value"), 79, 12))) \
        .withColumn("ACCT_CURR_CYC_DEBIT", decode_s9_10_v99(substring(col("value"), 91, 12))) \
        .withColumn("ACCT_ADDR_ZIP", trim(substring(col("value"), 103, 10))) \
        .withColumn("ACCT_GROUP_ID", trim(substring(col("value"), 113, 10))) \
        .drop("value")

    pyspark_count = parsed_df.count()

    report_lines.append(f"\n[PYSPARK PARSED]")
    report_lines.append(f"  DataFrame row count: {pyspark_count}")
    report_lines.append(f"  Row count match: {'PASS' if pyspark_count == raw_count else 'FAIL'}")

    # Sample value validation - first row
    first_row = parsed_df.first()
    report_lines.append(f"\n[SAMPLE VALUES - First Record]")
    report_lines.append(f"  ACCT_ID: {first_row['ACCT_ID']} (expected: 1)")
    report_lines.append(f"  ACCT_ACTIVE_STATUS: '{first_row['ACCT_ACTIVE_STATUS']}' (expected: 'Y')")
    report_lines.append(f"  ACCT_CURR_BAL: {first_row['ACCT_CURR_BAL']} (expected: 194.00)")
    report_lines.append(f"  ACCT_CREDIT_LIMIT: {first_row['ACCT_CREDIT_LIMIT']} (expected: 2020.00)")
    report_lines.append(f"  ACCT_OPEN_DATE: '{first_row['ACCT_OPEN_DATE']}' (expected: '2014-11-20')")

    # Assertions
    checks = [
        ("Row count", pyspark_count == raw_count),
        ("ACCT_ID = 1", first_row['ACCT_ID'] == 1),
        ("ACCT_ACTIVE_STATUS = 'Y'", first_row['ACCT_ACTIVE_STATUS'] == 'Y'),
        ("ACCT_CURR_BAL = 194.00", first_row['ACCT_CURR_BAL'] == Decimal('194.00')),
        ("ACCT_CREDIT_LIMIT = 2020.00", first_row['ACCT_CREDIT_LIMIT'] == Decimal('2020.00')),
        ("ACCT_OPEN_DATE = '2014-11-20'", first_row['ACCT_OPEN_DATE'] == '2014-11-20'),
    ]

    report_lines.append(f"\n[ASSERTIONS]")
    all_pass = True
    for check_name, result in checks:
        status = "PASS" if result else "FAIL"
        if not result:
            all_pass = False
        report_lines.append(f"  {status}: {check_name}")

    report_lines.append(f"\n  OVERALL: {'ALL PASSED' if all_pass else 'SOME FAILED'}")
    report_lines.append("")
    return all_pass


def validate_customer_data(spark, project_root, report_lines):
    """Validate CUSTREC.cpy / custdata.txt parsing."""
    report_lines.append("=" * 80)
    report_lines.append("VALIDATION: CUSTOMER-RECORD (CUSTREC.cpy -> custdata.txt)")
    report_lines.append("=" * 80)

    data_file = os.path.join(project_root, "app", "data", "ASCII", "custdata.txt")

    # Raw file metrics
    raw_count = count_raw_lines(data_file)
    raw_line_1 = get_raw_line(data_file, 0)
    raw_line_len = len(raw_line_1) if raw_line_1 else 0

    report_lines.append(f"\n[RAW FILE]")
    report_lines.append(f"  File: {data_file}")
    report_lines.append(f"  Raw line count: {raw_count}")
    report_lines.append(f"  First line length: {raw_line_len} bytes (expected: 500)")
    report_lines.append(f"  Length check: {'PASS' if raw_line_len == 500 else 'FAIL'}")

    # Parse with PySpark
    raw_df = spark.read.text(data_file)
    parsed_df = raw_df \
        .withColumn("CUST_ID", trim(substring(col("value"), 1, 9)).cast("long")) \
        .withColumn("CUST_FIRST_NAME", trim(substring(col("value"), 10, 25))) \
        .withColumn("CUST_MIDDLE_NAME", trim(substring(col("value"), 35, 25))) \
        .withColumn("CUST_LAST_NAME", trim(substring(col("value"), 60, 25))) \
        .withColumn("CUST_ADDR_LINE_1", trim(substring(col("value"), 85, 50))) \
        .withColumn("CUST_ADDR_LINE_2", trim(substring(col("value"), 135, 50))) \
        .withColumn("CUST_ADDR_LINE_3", trim(substring(col("value"), 185, 50))) \
        .withColumn("CUST_ADDR_STATE_CD", trim(substring(col("value"), 235, 2))) \
        .withColumn("CUST_ADDR_COUNTRY_CD", trim(substring(col("value"), 237, 3))) \
        .withColumn("CUST_ADDR_ZIP", trim(substring(col("value"), 240, 10))) \
        .withColumn("CUST_PHONE_NUM_1", trim(substring(col("value"), 250, 15))) \
        .withColumn("CUST_PHONE_NUM_2", trim(substring(col("value"), 265, 15))) \
        .withColumn("CUST_SSN", trim(substring(col("value"), 280, 9)).cast("long")) \
        .withColumn("CUST_GOVT_ISSUED_ID", trim(substring(col("value"), 289, 20))) \
        .withColumn("CUST_DOB_YYYYMMDD", trim(substring(col("value"), 309, 10))) \
        .withColumn("CUST_EFT_ACCOUNT_ID", trim(substring(col("value"), 319, 10))) \
        .withColumn("CUST_PRI_CARD_HOLDER_IND", trim(substring(col("value"), 329, 1))) \
        .withColumn("CUST_FICO_CREDIT_SCORE", trim(substring(col("value"), 330, 3)).cast("int")) \
        .drop("value")

    pyspark_count = parsed_df.count()

    report_lines.append(f"\n[PYSPARK PARSED]")
    report_lines.append(f"  DataFrame row count: {pyspark_count}")
    report_lines.append(f"  Row count match: {'PASS' if pyspark_count == raw_count else 'FAIL'}")

    # Sample value validation - first row
    first_row = parsed_df.first()
    report_lines.append(f"\n[SAMPLE VALUES - First Record]")
    report_lines.append(f"  CUST_ID: {first_row['CUST_ID']} (expected: 1)")
    report_lines.append(f"  CUST_FIRST_NAME: '{first_row['CUST_FIRST_NAME']}' (expected: 'Immanuel')")
    report_lines.append(f"  CUST_LAST_NAME: '{first_row['CUST_LAST_NAME']}' (expected: 'Kessler')")
    report_lines.append(f"  CUST_ADDR_STATE_CD: '{first_row['CUST_ADDR_STATE_CD']}' (expected: 'NC')")
    report_lines.append(f"  CUST_FICO_CREDIT_SCORE: {first_row['CUST_FICO_CREDIT_SCORE']} (expected: 274)")

    # Assertions
    checks = [
        ("Row count", pyspark_count == raw_count),
        ("CUST_ID = 1", first_row['CUST_ID'] == 1),
        ("CUST_FIRST_NAME = 'Immanuel'", first_row['CUST_FIRST_NAME'] == 'Immanuel'),
        ("CUST_LAST_NAME = 'Kessler'", first_row['CUST_LAST_NAME'] == 'Kessler'),
        ("CUST_ADDR_STATE_CD = 'NC'", first_row['CUST_ADDR_STATE_CD'] == 'NC'),
        ("CUST_FICO_CREDIT_SCORE = 274", first_row['CUST_FICO_CREDIT_SCORE'] == 274),
    ]

    report_lines.append(f"\n[ASSERTIONS]")
    all_pass = True
    for check_name, result in checks:
        status = "PASS" if result else "FAIL"
        if not result:
            all_pass = False
        report_lines.append(f"  {status}: {check_name}")

    report_lines.append(f"\n  OVERALL: {'ALL PASSED' if all_pass else 'SOME FAILED'}")
    report_lines.append("")
    return all_pass


def validate_card_data(spark, project_root, report_lines):
    """Validate CVACT02Y.cpy / carddata.txt parsing."""
    report_lines.append("=" * 80)
    report_lines.append("VALIDATION: CARD-RECORD (CVACT02Y.cpy -> carddata.txt)")
    report_lines.append("=" * 80)

    data_file = os.path.join(project_root, "app", "data", "ASCII", "carddata.txt")

    # Raw file metrics
    raw_count = count_raw_lines(data_file)
    raw_line_1 = get_raw_line(data_file, 0)
    raw_line_len = len(raw_line_1) if raw_line_1 else 0

    report_lines.append(f"\n[RAW FILE]")
    report_lines.append(f"  File: {data_file}")
    report_lines.append(f"  Raw line count: {raw_count}")
    report_lines.append(f"  First line length: {raw_line_len} bytes (expected: 150)")
    report_lines.append(f"  Length check: {'PASS' if raw_line_len == 150 else 'FAIL'}")

    # Parse with PySpark
    raw_df = spark.read.text(data_file)
    parsed_df = raw_df \
        .withColumn("CARD_NUM", trim(substring(col("value"), 1, 16))) \
        .withColumn("CARD_ACCT_ID", trim(substring(col("value"), 17, 11)).cast("long")) \
        .withColumn("CARD_CVV_CD", trim(substring(col("value"), 28, 3)).cast("int")) \
        .withColumn("CARD_EMBOSSED_NAME", trim(substring(col("value"), 31, 50))) \
        .withColumn("CARD_EXPIRAION_DATE", trim(substring(col("value"), 81, 10))) \
        .withColumn("CARD_ACTIVE_STATUS", trim(substring(col("value"), 91, 1))) \
        .drop("value")

    pyspark_count = parsed_df.count()

    report_lines.append(f"\n[PYSPARK PARSED]")
    report_lines.append(f"  DataFrame row count: {pyspark_count}")
    report_lines.append(f"  Row count match: {'PASS' if pyspark_count == raw_count else 'FAIL'}")

    # Sample value validation - first row
    first_row = parsed_df.first()
    report_lines.append(f"\n[SAMPLE VALUES - First Record]")
    report_lines.append(f"  CARD_NUM: '{first_row['CARD_NUM']}' (expected: '0500024453765740')")
    report_lines.append(f"  CARD_ACCT_ID: {first_row['CARD_ACCT_ID']} (expected: 50)")
    report_lines.append(f"  CARD_CVV_CD: {first_row['CARD_CVV_CD']} (expected: 747)")
    report_lines.append(f"  CARD_EMBOSSED_NAME: '{first_row['CARD_EMBOSSED_NAME']}' (expected: 'Aniya Von')")
    report_lines.append(f"  CARD_EXPIRAION_DATE: '{first_row['CARD_EXPIRAION_DATE']}' (expected: '2023-03-09')")
    report_lines.append(f"  CARD_ACTIVE_STATUS: '{first_row['CARD_ACTIVE_STATUS']}' (expected: 'Y')")

    # Assertions
    checks = [
        ("Row count", pyspark_count == raw_count),
        ("CARD_NUM = '0500024453765740'", first_row['CARD_NUM'] == '0500024453765740'),
        ("CARD_ACCT_ID = 50", first_row['CARD_ACCT_ID'] == 50),
        ("CARD_CVV_CD = 747", first_row['CARD_CVV_CD'] == 747),
        ("CARD_EMBOSSED_NAME = 'Aniya Von'", first_row['CARD_EMBOSSED_NAME'] == 'Aniya Von'),
        ("CARD_EXPIRAION_DATE = '2023-03-09'", first_row['CARD_EXPIRAION_DATE'] == '2023-03-09'),
        ("CARD_ACTIVE_STATUS = 'Y'", first_row['CARD_ACTIVE_STATUS'] == 'Y'),
    ]

    report_lines.append(f"\n[ASSERTIONS]")
    all_pass = True
    for check_name, result in checks:
        status = "PASS" if result else "FAIL"
        if not result:
            all_pass = False
        report_lines.append(f"  {status}: {check_name}")

    report_lines.append(f"\n  OVERALL: {'ALL PASSED' if all_pass else 'SOME FAILED'}")
    report_lines.append("")
    return all_pass


def main():
    """Run validation for all three copybook/data file pairs."""
    spark = SparkSession.builder \
        .appName("CopybookValidation") \
        .master("local[*]") \
        .getOrCreate()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    output_dir = os.path.join(project_root, "generated", "validation")
    os.makedirs(output_dir, exist_ok=True)

    report_lines = []
    report_lines.append("COPYBOOK PARSING VALIDATION REPORT")
    report_lines.append("=" * 80)
    report_lines.append(f"Project root: {project_root}")
    report_lines.append("")

    # Run all three validations
    acct_pass = validate_account_data(spark, project_root, report_lines)
    cust_pass = validate_customer_data(spark, project_root, report_lines)
    card_pass = validate_card_data(spark, project_root, report_lines)

    # Summary
    report_lines.append("=" * 80)
    report_lines.append("SUMMARY")
    report_lines.append("=" * 80)
    report_lines.append(f"  ACCOUNT-RECORD (CVACT01Y.cpy): {'PASS' if acct_pass else 'FAIL'}")
    report_lines.append(f"  CUSTOMER-RECORD (CUSTREC.cpy):  {'PASS' if cust_pass else 'FAIL'}")
    report_lines.append(f"  CARD-RECORD (CVACT02Y.cpy):     {'PASS' if card_pass else 'FAIL'}")
    all_pass = acct_pass and cust_pass and card_pass
    report_lines.append(f"\n  OVERALL RESULT: {'ALL VALIDATIONS PASSED' if all_pass else 'SOME VALIDATIONS FAILED'}")

    # Write report
    report_text = "\n".join(report_lines)
    report_path = os.path.join(output_dir, "validation_report.txt")
    with open(report_path, 'w') as f:
        f.write(report_text)

    print(report_text)
    print(f"\nReport written to: {report_path}")

    spark.stop()
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
