"""Parse acctdata.txt using the CVACT01Y.cpy ACCOUNT-RECORD layout (300 bytes).

Reads the fixed-width ASCII file, applies the copybook-derived schema,
decodes signed zoned-decimal fields, and writes the result to Parquet.
"""

import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, concat, lit, regexp_replace, substring, trim, upper, when,
)
from pyspark.sql.types import DecimalType

# ---------- schema derived from CVACT01Y.cpy ----------
RECORD_LENGTH = 300
FIELDS = [
    # (name, offset, length, field_type)
    ("ACCT_ID",                0,   11, "string"),
    ("ACCT_ACTIVE_STATUS",    11,    1, "string"),
    ("ACCT_CURR_BAL",         12,   12, "signed_decimal"),
    ("ACCT_CREDIT_LIMIT",     24,   12, "signed_decimal"),
    ("ACCT_CASH_CREDIT_LIMIT",36,   12, "signed_decimal"),
    ("ACCT_OPEN_DATE",        48,   10, "string"),
    ("ACCT_EXPIRAION_DATE",   58,   10, "string"),
    ("ACCT_REISSUE_DATE",     68,   10, "string"),
    ("ACCT_CURR_CYC_CREDIT",  78,  12, "signed_decimal"),
    ("ACCT_CURR_CYC_DEBIT",   90,  12, "signed_decimal"),
    ("ACCT_ADDR_ZIP",        102,   10, "string"),
    ("ACCT_GROUP_ID",        112,   10, "string"),
    ("FILLER",               122,  178, "string"),
]

# EBCDIC overpunch sign maps
_POS = {"{": "0", "A": "1", "B": "2", "C": "3", "D": "4",
        "E": "5", "F": "6", "G": "7", "H": "8", "I": "9"}
_NEG = {"}": "0", "J": "1", "K": "2", "L": "3", "M": "4",
        "N": "5", "O": "6", "P": "7", "Q": "8", "R": "9"}


def decode_overpunch_column(df, col_name, total_digits=12, scale=2):
    """Decode a signed zoned-decimal column using native Spark SQL expressions."""
    raw = col(col_name)
    last_char = upper(substring(raw, total_digits, 1))
    leading = substring(raw, 1, total_digits - 1)

    expr = None
    for char, digit in _POS.items():
        branch = concat(leading, lit(digit))
        if expr is None:
            expr = when(last_char == lit(char), branch)
        else:
            expr = expr.when(last_char == lit(char), branch)
    for char, digit in _NEG.items():
        expr = expr.when(last_char == lit(char),
                         concat(lit("-"), leading, lit(digit)))
    expr = expr.otherwise(raw)

    if scale > 0:
        pattern = f"^(-?)(\\d+)(\\d{{{scale}}})$"
        expr = regexp_replace(expr, pattern, "$1$2.$3")

    return df.withColumn(col_name, expr.cast(DecimalType(total_digits, scale)))


def build_spark_session(app_name="ParseAcctData"):
    return (SparkSession.builder
            .appName(app_name)
            .master("local[*]")
            .getOrCreate())


def parse_fixed_width(spark, input_path):
    """Read fixed-width file and extract fields based on copybook layout."""
    raw_df = (spark.read
              .text(input_path)
              .filter(col("value").isNotNull())
              .filter(col("value") != ""))

    parsed_df = raw_df
    for name, offset, length, _ in FIELDS:
        parsed_df = parsed_df.withColumn(
            name, substring(col("value"), offset + 1, length)
        )

    parsed_df = parsed_df.drop("value")

    for name, _, _, ftype in FIELDS:
        if ftype == "string" and name != "FILLER":
            parsed_df = parsed_df.withColumn(name, trim(col(name)))
        elif ftype == "signed_decimal":
            parsed_df = decode_overpunch_column(parsed_df, name)

    return parsed_df


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    input_path = os.path.join(base_dir, "app", "data", "ASCII", "acctdata.txt")
    output_path = os.path.join(base_dir, "copybook_parsing", "output",
                               "acctdata_parsed.parquet")

    spark = build_spark_session()
    try:
        df = parse_fixed_width(spark, input_path)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.write.mode("overwrite").parquet(output_path)

        print(f"Schema for ACCOUNT-RECORD ({RECORD_LENGTH}-byte layout):")
        df.printSchema()
        print(f"\nRow count: {df.count()}")
        print("\nSample rows (first 5):")
        df.show(5, truncate=False)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
