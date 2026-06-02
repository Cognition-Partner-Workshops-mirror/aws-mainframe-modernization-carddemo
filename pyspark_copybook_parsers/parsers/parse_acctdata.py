"""
PySpark parser for COBOL copybook CVACT01Y.cpy → acctdata.txt

Reads the fixed-width Account Record file (300 bytes per line) and applies
the field layout defined in app/cpy/CVACT01Y.cpy.  Signed zoned-decimal
fields (PIC S9(n)V99) are decoded using pure Spark SQL expressions that
translate ASCII sign-overpunch characters into explicit numeric values.

Usage:
    spark-submit parse_acctdata.py [--input <path>] [--output <path>]
"""

import argparse
import os

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType


# ---------------------------------------------------------------------------
# Sign-overpunch decoding via pure Spark SQL expressions
#
# ASCII / DISPLAY format encodes the sign in the last byte:
#   Positive: { = 0, A = 1, B = 2, … I = 9
#   Negative: } = 0, J = 1, K = 2, … R = 9
# ---------------------------------------------------------------------------
_POS_MAP = {"{": "0", "A": "1", "B": "2", "C": "3", "D": "4",
            "E": "5", "F": "6", "G": "7", "H": "8", "I": "9"}
_NEG_MAP = {"}": "0", "J": "1", "K": "2", "L": "3", "M": "4",
            "N": "5", "O": "6", "P": "7", "Q": "8", "R": "9"}


def _decode_signed_col(col, scale: int = 2):
    """Build a Spark Column expression that decodes a sign-overpunch
    zoned-decimal field into a DecimalType value.

    Uses chained F.when() — no Python UDF required, so there are no
    serialization issues and execution stays within the JVM.
    """
    last_char = F.substring(col, -1, 1)
    leading = F.substring(col, 1, F.length(col) - 1)

    # CASE expression mapping overpunch char → decoded digit
    case_expr = None
    for ch, digit in _POS_MAP.items():
        cond = last_char == F.lit(ch)
        if case_expr is None:
            case_expr = F.when(cond, F.lit(digit))
        else:
            case_expr = case_expr.when(cond, F.lit(digit))
    for ch, digit in _NEG_MAP.items():
        case_expr = case_expr.when(last_char == F.lit(ch), F.lit(digit))
    # Fallback: last char is already a digit (no overpunch)
    case_expr = case_expr.otherwise(last_char)

    # Sign multiplier: -1 for negative overpunch chars, +1 otherwise
    sign_case = None
    for ch in _NEG_MAP:
        cond = last_char == F.lit(ch)
        if sign_case is None:
            sign_case = F.when(cond, F.lit(-1))
        else:
            sign_case = sign_case.when(cond, F.lit(-1))
    sign_case = sign_case.otherwise(F.lit(1))

    # Concatenate leading digits + decoded last digit, apply scale and sign
    full_digits = F.concat(leading, case_expr)
    numeric_val = full_digits.cast(DecimalType(20, 0)) / F.lit(10 ** scale)
    return (numeric_val * sign_case).cast(DecimalType(12, 2))

# ---------------------------------------------------------------------------
# Field layout derived from CVACT01Y.cpy  (ACCOUNT-RECORD, 300 bytes)
#   offset is 1-based for PySpark substr()
# ---------------------------------------------------------------------------
ACCOUNT_FIELDS = [
    # (field_name,       offset, length, is_signed_decimal)
    ("ACCT_ID",                1,  11, False),
    ("ACCT_ACTIVE_STATUS",    12,   1, False),
    ("ACCT_CURR_BAL",         13,  12, True),
    ("ACCT_CREDIT_LIMIT",     25,  12, True),
    ("ACCT_CASH_CREDIT_LIMIT",37,  12, True),
    ("ACCT_OPEN_DATE",        49,  10, False),
    ("ACCT_EXPIRAION_DATE",   59,  10, False),
    ("ACCT_REISSUE_DATE",     69,  10, False),
    ("ACCT_CURR_CYC_CREDIT",  79,  12, True),
    ("ACCT_CURR_CYC_DEBIT",   91,  12, True),
    ("ACCT_ADDR_ZIP",        103,  10, False),
    ("ACCT_GROUP_ID",        113,  10, False),
    ("FILLER",               123, 178, False),
]

RECORD_LENGTH = 300  # total bytes per record


def parse_acctdata(spark: SparkSession, input_path: str):
    """Read acctdata.txt as a fixed-width file and return a parsed DataFrame.

    Each line is expected to be exactly 300 characters (matching RECLN 300
    declared in the copybook).
    """
    # Read raw lines
    raw_df = spark.read.text(input_path)

    # Slice each field using substr (1-based offsets)
    parsed = raw_df
    for name, offset, length, is_signed in ACCOUNT_FIELDS:
        col_expr = F.substring(F.col("value"), offset, length)
        if is_signed:
            # Decode sign-overpunch via pure SQL expressions → Decimal(12,2)
            col_expr = _decode_signed_col(col_expr)
        else:
            # Trim trailing spaces from alphanumeric fields
            col_expr = F.trim(col_expr)
        parsed = parsed.withColumn(name, col_expr)

    # Drop the raw line and FILLER columns
    parsed = parsed.drop("value", "FILLER")
    return parsed


def main():
    parser = argparse.ArgumentParser(
        description="Parse COBOL CVACT01Y account data into PySpark DataFrame")
    # Default paths are relative to the repo root
    default_input = os.path.join(
        os.path.dirname(__file__), "..", "..", "app", "data", "ASCII",
        "acctdata.txt")
    parser.add_argument("--input", default=default_input,
                        help="Path to acctdata.txt")
    parser.add_argument("--output", default=None,
                        help="Optional output path (parquet)")
    args = parser.parse_args()

    spark = SparkSession.builder \
        .appName("CVACT01Y_AccountParser") \
        .master("local[*]") \
        .getOrCreate()

    df = parse_acctdata(spark, args.input)

    # Show parsed results
    print(f"\n=== Parsed Account Records (CVACT01Y) ===")
    print(f"Total rows: {df.count()}")
    df.printSchema()
    df.show(10, truncate=False)

    if args.output:
        df.write.mode("overwrite").parquet(args.output)
        print(f"Written to {args.output}")

    spark.stop()


if __name__ == "__main__":
    main()
