"""
PySpark parser for CVACT01Y.cpy (ACCOUNT-RECORD) -> acctdata.txt

Reads the fixed-width account data file using the COBOL copybook-derived schema.
Record length: 300 bytes per line.
"""

import os
import json
from decimal import Decimal

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, DecimalType
)
from pyspark.sql.functions import udf, col, trim

# Zoned decimal sign overpunch mapping (ASCII representation)
# Positive: { = 0, A = 1, B = 2, C = 3, D = 4, E = 5, F = 6, G = 7, H = 8, I = 9
# Negative: } = 0, J = 1, K = 2, L = 3, M = 4, N = 5, O = 6, P = 7, Q = 8, R = 9
POSITIVE_OVERPUNCH = {"{": "0", "A": "1", "B": "2", "C": "3", "D": "4",
                      "E": "5", "F": "6", "G": "7", "H": "8", "I": "9"}
NEGATIVE_OVERPUNCH = {"}": "0", "J": "1", "K": "2", "L": "3", "M": "4",
                      "N": "5", "O": "6", "P": "7", "Q": "8", "R": "9"}


def decode_signed_zoned_decimal(raw: str, scale: int) -> Decimal:
    """
    Decode a signed zoned decimal field from its ASCII overpunch representation.

    Args:
        raw: The raw string from the fixed-width file (e.g., '00000001940{')
        scale: Number of implied decimal places (V99 -> scale=2)

    Returns:
        Decimal value with proper sign and scale
    """
    if raw is None or raw.strip() == "":
        return Decimal("0")

    last_char = raw[-1]
    digits = raw[:-1]

    if last_char in POSITIVE_OVERPUNCH:
        sign = 1
        last_digit = POSITIVE_OVERPUNCH[last_char]
    elif last_char in NEGATIVE_OVERPUNCH:
        sign = -1
        last_digit = NEGATIVE_OVERPUNCH[last_char]
    elif last_char.isdigit():
        sign = 1
        last_digit = last_char
    else:
        return Decimal("0")

    full_digits = digits + last_digit
    integer_value = int(full_digits)
    result = Decimal(sign * integer_value) / Decimal(10 ** scale)
    return result


# Field layout derived from CVACT01Y.cpy
FIELD_LAYOUT = [
    ("ACCT_ID", 0, 11, "numeric"),
    ("ACCT_ACTIVE_STATUS", 11, 1, "string"),
    ("ACCT_CURR_BAL", 12, 12, "signed_decimal"),
    ("ACCT_CREDIT_LIMIT", 24, 12, "signed_decimal"),
    ("ACCT_CASH_CREDIT_LIMIT", 36, 12, "signed_decimal"),
    ("ACCT_OPEN_DATE", 48, 10, "string"),
    ("ACCT_EXPIRAION_DATE", 58, 10, "string"),
    ("ACCT_REISSUE_DATE", 68, 10, "string"),
    ("ACCT_CURR_CYC_CREDIT", 78, 12, "signed_decimal"),
    ("ACCT_CURR_CYC_DEBIT", 90, 12, "signed_decimal"),
    ("ACCT_ADDR_ZIP", 102, 10, "string"),
    ("ACCT_GROUP_ID", 112, 10, "string"),
    ("FILLER", 122, 178, "string"),
]


def parse_account_record(line: str) -> dict:
    """Parse a single 300-byte account record line."""
    record = {}
    for name, offset, length, field_type in FIELD_LAYOUT:
        raw_value = line[offset:offset + length]
        if field_type == "numeric":
            record[name] = int(raw_value) if raw_value.strip() else 0
        elif field_type == "signed_decimal":
            record[name] = decode_signed_zoned_decimal(raw_value, 2)
        else:
            record[name] = raw_value.strip()
    return record


def main():
    """Main entry point for parsing acctdata.txt."""
    spark = SparkSession.builder \
        .appName("CardDemo_Account_Parser") \
        .master("local[*]") \
        .getOrCreate()

    # Determine file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    data_file = os.path.join(project_root, "app", "data", "ASCII", "acctdata.txt")
    output_dir = os.path.join(project_root, "validation")

    # Read raw lines
    raw_rdd = spark.sparkContext.textFile(data_file)
    raw_count = raw_rdd.count()

    # Parse records
    parsed_rdd = raw_rdd.map(parse_account_record)

    # Define PySpark schema
    schema = StructType([
        StructField("ACCT_ID", LongType(), False),
        StructField("ACCT_ACTIVE_STATUS", StringType(), True),
        StructField("ACCT_CURR_BAL", DecimalType(12, 2), True),
        StructField("ACCT_CREDIT_LIMIT", DecimalType(12, 2), True),
        StructField("ACCT_CASH_CREDIT_LIMIT", DecimalType(12, 2), True),
        StructField("ACCT_OPEN_DATE", StringType(), True),
        StructField("ACCT_EXPIRAION_DATE", StringType(), True),
        StructField("ACCT_REISSUE_DATE", StringType(), True),
        StructField("ACCT_CURR_CYC_CREDIT", DecimalType(12, 2), True),
        StructField("ACCT_CURR_CYC_DEBIT", DecimalType(12, 2), True),
        StructField("ACCT_ADDR_ZIP", StringType(), True),
        StructField("ACCT_GROUP_ID", StringType(), True),
        StructField("FILLER", StringType(), True),
    ])

    # Create DataFrame from parsed data
    df = spark.createDataFrame(parsed_rdd, schema=schema)

    # Drop FILLER column for display
    df_display = df.drop("FILLER")

    parsed_count = df_display.count()

    # Validation output
    validation = {
        "source_file": "app/data/ASCII/acctdata.txt",
        "copybook": "app/cpy/CVACT01Y.cpy",
        "record_length_bytes": 300,
        "raw_line_count": raw_count,
        "parsed_row_count": parsed_count,
        "counts_match": raw_count == parsed_count,
        "sample_records": []
    }

    # Collect first 5 rows as sample
    sample_rows = df_display.limit(5).collect()
    for row in sample_rows:
        validation["sample_records"].append(row.asDict())

    # Write validation output
    output_file = os.path.join(output_dir, "acctdata_validation.json")
    with open(output_file, "w") as f:
        json.dump(validation, f, indent=2, default=str)

    print(f"Source file: {data_file}")
    print(f"Raw line count: {raw_count}")
    print(f"Parsed row count: {parsed_count}")
    print(f"Counts match: {raw_count == parsed_count}")
    print(f"\nSchema:")
    df_display.printSchema()
    print(f"\nFirst 5 records:")
    df_display.show(5, truncate=False)
    print(f"\nValidation output written to: {output_file}")

    spark.stop()


if __name__ == "__main__":
    main()
