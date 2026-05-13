"""
PySpark script to parse app/data/ASCII/acctdata.txt as a fixed-width file
using the schema derived from COBOL copybook app/cpy/CVACT01Y.cpy.

Copybook: CVACT01Y.cpy
Record: ACCOUNT-RECORD (300 bytes per line)
"""

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, DecimalType, IntegerType
)
from pyspark.sql.functions import col, trim, substring, udf
from decimal import Decimal
import os

# --- Overpunch sign decoding for COBOL DISPLAY signed numeric fields ---
# In ASCII-format COBOL data, the sign is encoded in the last byte (overpunch).
# Positive: '{' = 0, 'A' = 1, 'B' = 2, ..., 'I' = 9
# Negative: '}' = 0, 'J' = 1, 'K' = 2, ..., 'R' = 9
POSITIVE_OVERPUNCH = {'{': '0', 'A': '1', 'B': '2', 'C': '3', 'D': '4',
                      'E': '5', 'F': '6', 'G': '7', 'H': '8', 'I': '9'}
NEGATIVE_OVERPUNCH = {'}': '0', 'J': '1', 'K': '2', 'L': '3', 'M': '4',
                      'N': '5', 'O': '6', 'P': '7', 'Q': '8', 'R': '9'}


def decode_signed_numeric(raw_str, scale=2):
    """
    Decode a COBOL DISPLAY signed numeric field with overpunch.
    The last character encodes both the sign and the last digit.
    'scale' indicates the number of implied decimal places (V99 => scale=2).
    Returns a Decimal value.
    """
    if raw_str is None or len(raw_str) == 0:
        return None
    raw_str = raw_str.strip()
    if len(raw_str) == 0:
        return None

    last_char = raw_str[-1]
    digits_prefix = raw_str[:-1]

    # Determine sign and last digit from overpunch character
    if last_char in POSITIVE_OVERPUNCH:
        sign = ''
        last_digit = POSITIVE_OVERPUNCH[last_char]
    elif last_char in NEGATIVE_OVERPUNCH:
        sign = '-'
        last_digit = NEGATIVE_OVERPUNCH[last_char]
    elif last_char.isdigit():
        # No overpunch, treat as unsigned positive
        sign = ''
        last_digit = last_char
    else:
        return None

    full_digits = digits_prefix + last_digit
    # Insert implied decimal point based on scale
    if scale > 0:
        integer_part = full_digits[:-scale]
        decimal_part = full_digits[-scale:]
        numeric_str = sign + integer_part + '.' + decimal_part
    else:
        numeric_str = sign + full_digits

    return Decimal(numeric_str)


# Register UDF for signed numeric with 2 decimal places (PIC S9(10)V99)
decode_s9_10_v99 = udf(lambda x: decode_signed_numeric(x, scale=2), DecimalType(12, 2))

# --- Field layout derived from CVACT01Y.cpy ---
# Total record length: 300 bytes
# Fields: (name, start_pos (1-based for substring), length, type)
ACCOUNT_FIELDS = [
    ("ACCT_ID",                  1,  11, "numeric"),        # PIC 9(11)
    ("ACCT_ACTIVE_STATUS",      12,   1, "string"),         # PIC X(01)
    ("ACCT_CURR_BAL",           13,  12, "signed_decimal"), # PIC S9(10)V99
    ("ACCT_CREDIT_LIMIT",       25,  12, "signed_decimal"), # PIC S9(10)V99
    ("ACCT_CASH_CREDIT_LIMIT",  37,  12, "signed_decimal"), # PIC S9(10)V99
    ("ACCT_OPEN_DATE",          49,  10, "string"),         # PIC X(10)
    ("ACCT_EXPIRAION_DATE",     59,  10, "string"),         # PIC X(10)
    ("ACCT_REISSUE_DATE",       69,  10, "string"),         # PIC X(10)
    ("ACCT_CURR_CYC_CREDIT",   79,  12, "signed_decimal"), # PIC S9(10)V99
    ("ACCT_CURR_CYC_DEBIT",    91,  12, "signed_decimal"), # PIC S9(10)V99
    ("ACCT_ADDR_ZIP",          103,  10, "string"),         # PIC X(10)
    ("ACCT_GROUP_ID",          113,  10, "string"),         # PIC X(10)
    ("FILLER",                 123, 178, "string"),         # PIC X(178)
]


def main():
    """Main entry point: read fixed-width account data and parse using copybook schema."""
    spark = SparkSession.builder \
        .appName("CVACT01Y_AccountData_Parser") \
        .master("local[*]") \
        .getOrCreate()

    # Determine file path relative to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    data_file = os.path.join(project_root, "app", "data", "ASCII", "acctdata.txt")

    # Read raw text file - each line is a 300-byte fixed-width record
    raw_df = spark.read.text(data_file)

    # Extract fields using substring (1-based positions)
    parsed_df = raw_df
    for field_name, start, length, field_type in ACCOUNT_FIELDS:
        parsed_df = parsed_df.withColumn(field_name, substring(col("value"), start, length))

    # Apply type conversions
    # Signed decimal fields: decode overpunch sign encoding
    signed_fields = [f[0] for f in ACCOUNT_FIELDS if f[3] == "signed_decimal"]
    for field_name in signed_fields:
        parsed_df = parsed_df.withColumn(field_name, decode_s9_10_v99(col(field_name)))

    # Numeric fields: cast to long integer after trimming
    numeric_fields = [f[0] for f in ACCOUNT_FIELDS if f[3] == "numeric"]
    for field_name in numeric_fields:
        parsed_df = parsed_df.withColumn(field_name, trim(col(field_name)).cast("long"))

    # String fields: trim trailing/leading spaces
    string_fields = [f[0] for f in ACCOUNT_FIELDS if f[3] == "string"]
    for field_name in string_fields:
        parsed_df = parsed_df.withColumn(field_name, trim(col(field_name)))

    # Drop raw 'value' column and FILLER
    result_df = parsed_df.drop("value", "FILLER")

    # Show results
    print("=" * 80)
    print("ACCOUNT-RECORD Parsed Output (from CVACT01Y.cpy / acctdata.txt)")
    print("=" * 80)
    result_df.printSchema()
    print(f"\nTotal records: {result_df.count()}")
    print("\nSample records (first 10):")
    result_df.show(10, truncate=False)

    spark.stop()


if __name__ == "__main__":
    main()
