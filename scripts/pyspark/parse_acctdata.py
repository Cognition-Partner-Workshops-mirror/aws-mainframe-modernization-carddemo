"""
PySpark script to parse app/data/ASCII/acctdata.txt as a fixed-width file.

Derived from COBOL copybook: app/cpy/CVACT01Y.cpy
Record layout: ACCOUNT-RECORD (300 bytes)

This script reads each line as a raw string, extracts fields using byte-offset
slicing, decodes EBCDIC-style zoned-decimal sign overpunch characters for
signed numeric fields (PIC S9(n)V99), and exposes the result as a typed
PySpark DataFrame.

Type-mapping decisions are documented in COPYBOOK_PARSING_NOTES.md.
"""

import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, substring, trim, udf, lit, when, regexp_replace
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, DecimalType, IntegerType
)
from decimal import Decimal

# ---------------------------------------------------------------------------
# Zoned-decimal sign-overpunch lookup tables
# In ASCII representations of COBOL DISPLAY numeric fields with SIGN TRAILING,
# the last byte encodes both the digit value and the sign.
# Positive: { = 0, A = 1, B = 2, C = 3, D = 4, E = 5, F = 6, G = 7, H = 8, I = 9
# Negative: } = 0, J = 1, K = 2, L = 3, M = 4, N = 5, O = 6, P = 7, Q = 8, R = 9
# ---------------------------------------------------------------------------

# Mapping from overpunch character to (digit, sign_multiplier)
OVERPUNCH_MAP = {
    "{": ("0", 1), "A": ("1", 1), "B": ("2", 1), "C": ("3", 1), "D": ("4", 1),
    "E": ("5", 1), "F": ("6", 1), "G": ("7", 1), "H": ("8", 1), "I": ("9", 1),
    "}": ("0", -1), "J": ("1", -1), "K": ("2", -1), "L": ("3", -1), "M": ("4", -1),
    "N": ("5", -1), "O": ("6", -1), "P": ("7", -1), "Q": ("8", -1), "R": ("9", -1),
}


def decode_signed_numeric(raw_str, decimal_places=2):
    """
    Decode a COBOL zoned-decimal DISPLAY field with trailing sign overpunch.

    Parameters
    ----------
    raw_str : str
        The raw fixed-width field value (e.g. '00000001940{').
    decimal_places : int
        Number of implied decimal places from PIC V99 (default 2).

    Returns
    -------
    Decimal or None
        The decoded numeric value with the correct sign and decimal position.
    """
    if raw_str is None or len(raw_str) == 0:
        return None

    last_char = raw_str[-1]
    leading_digits = raw_str[:-1]

    if last_char in OVERPUNCH_MAP:
        digit, sign = OVERPUNCH_MAP[last_char]
    elif last_char.isdigit():
        # No overpunch — treat as unsigned positive
        digit = last_char
        sign = 1
    else:
        return None

    full_digits = leading_digits + digit
    # Insert the implied decimal point
    if decimal_places > 0:
        integer_part = full_digits[:-decimal_places] or "0"
        fractional_part = full_digits[-decimal_places:]
        numeric_str = f"{integer_part}.{fractional_part}"
    else:
        numeric_str = full_digits

    return Decimal(numeric_str) * sign


# Register as a PySpark UDF — returns DecimalType(12, 2) for PIC S9(10)V99
decode_signed_udf = udf(
    lambda raw: decode_signed_numeric(raw, decimal_places=2),
    DecimalType(12, 2),
)

# ---------------------------------------------------------------------------
# Field layout derived from CVACT01Y.cpy
# Each tuple: (field_name, start_pos (1-based), length)
# ---------------------------------------------------------------------------
FIELD_LAYOUT = [
    ("ACCT_ID",                 1,  11),
    ("ACCT_ACTIVE_STATUS",     12,   1),
    ("ACCT_CURR_BAL",          13,  12),
    ("ACCT_CREDIT_LIMIT",      25,  12),
    ("ACCT_CASH_CREDIT_LIMIT", 37,  12),
    ("ACCT_OPEN_DATE",         49,  10),
    ("ACCT_EXPIRAION_DATE",    59,  10),
    ("ACCT_REISSUE_DATE",      69,  10),
    ("ACCT_CURR_CYC_CREDIT",   79,  12),
    ("ACCT_CURR_CYC_DEBIT",    91,  12),
    ("ACCT_ADDR_ZIP",         103,  10),
    ("ACCT_GROUP_ID",         113,  10),
    ("FILLER",                123, 178),
]

# Signed numeric fields that need overpunch decoding (PIC S9(10)V99)
SIGNED_FIELDS = {
    "ACCT_CURR_BAL",
    "ACCT_CREDIT_LIMIT",
    "ACCT_CASH_CREDIT_LIMIT",
    "ACCT_CURR_CYC_CREDIT",
    "ACCT_CURR_CYC_DEBIT",
}


def main():
    """Read acctdata.txt, apply copybook schema, print schema and first 5 rows."""

    spark = SparkSession.builder \
        .appName("CardDemo_CVACT01Y_AcctData_Parser") \
        .master("local[*]") \
        .getOrCreate()

    # Resolve the data file path relative to this script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    data_path = os.path.join(repo_root, "app", "data", "ASCII", "acctdata.txt")

    # Read the file as raw text — one line per record
    raw_df = spark.read.text(data_path)

    # Extract each field using substring (1-based positions)
    df = raw_df
    for field_name, start, length in FIELD_LAYOUT:
        df = df.withColumn(field_name, substring(col("value"), start, length))

    # Drop the raw line and the FILLER column
    df = df.drop("value", "FILLER")

    # Decode signed numeric fields using the overpunch UDF
    for field_name in SIGNED_FIELDS:
        df = df.withColumn(field_name, decode_signed_udf(col(field_name)))

    # Cast unsigned numeric fields to appropriate types
    # ACCT_ID: PIC 9(11) → LongType (11-digit integer)
    df = df.withColumn("ACCT_ID", col("ACCT_ID").cast(LongType()))

    # Trim trailing spaces from string fields
    string_fields = [
        "ACCT_ACTIVE_STATUS", "ACCT_OPEN_DATE", "ACCT_EXPIRAION_DATE",
        "ACCT_REISSUE_DATE", "ACCT_ADDR_ZIP", "ACCT_GROUP_ID",
    ]
    for field_name in string_fields:
        df = df.withColumn(field_name, trim(col(field_name)))

    # Print the DataFrame schema and the first 5 rows for validation
    print("=" * 80)
    print("ACCOUNT-RECORD DataFrame Schema (from CVACT01Y.cpy)")
    print("=" * 80)
    df.printSchema()

    print("=" * 80)
    print("First 5 rows of acctdata.txt")
    print("=" * 80)
    df.show(5, truncate=False)

    spark.stop()


if __name__ == "__main__":
    main()
