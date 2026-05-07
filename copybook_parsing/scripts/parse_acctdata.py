"""
PySpark script to parse acctdata.txt using the CVACT01Y.cpy copybook layout.

ACCOUNT-RECORD: 300-byte fixed-width records.
Signed numeric fields (PIC S9(10)V99) use EBCDIC zoned-decimal sign overpunch
on the last byte. In the ASCII export the trailing character encodes both the
digit and the sign:
    '{' = +0, 'A'-'I' = +1..+9
    '}' = -0, 'J'-'R' = -1..-9
The implied decimal (V99) means the last two digits are fractional.
"""

import json
import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, substring, trim, udf
from pyspark.sql.types import (
    DecimalType,
    LongType,
    StringType,
    StructField,
    StructType,
)
from decimal import Decimal

# ---------------------------------------------------------------------------
# EBCDIC zoned-decimal sign-overpunch helpers
# ---------------------------------------------------------------------------
POSITIVE_OVERPUNCH = {
    "{": "0", "A": "1", "B": "2", "C": "3", "D": "4",
    "E": "5", "F": "6", "G": "7", "H": "8", "I": "9",
}
NEGATIVE_OVERPUNCH = {
    "}": "0", "J": "1", "K": "2", "L": "3", "M": "4",
    "N": "5", "O": "6", "P": "7", "Q": "8", "R": "9",
}


def decode_signed_numeric(raw: str, decimal_places: int = 2) -> Decimal:
    """Decode a COBOL zoned-decimal string with trailing sign overpunch."""
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    last_char = raw[-1]
    if last_char in POSITIVE_OVERPUNCH:
        digits = raw[:-1] + POSITIVE_OVERPUNCH[last_char]
        sign = 1
    elif last_char in NEGATIVE_OVERPUNCH:
        digits = raw[:-1] + NEGATIVE_OVERPUNCH[last_char]
        sign = -1
    elif last_char.isdigit():
        digits = raw
        sign = 1
    else:
        return None
    if decimal_places > 0:
        int_part = digits[:-decimal_places]
        dec_part = digits[-decimal_places:]
        return Decimal(f"{'-' if sign < 0 else ''}{int(int_part)}.{dec_part}")
    return Decimal(f"{'-' if sign < 0 else ''}{int(digits)}")


decode_signed_udf = udf(
    lambda raw: decode_signed_numeric(raw, 2), DecimalType(12, 2)
)

# ---------------------------------------------------------------------------
# Schema derived from CVACT01Y.cpy (see schemas/CVACT01Y_schema.json)
# ---------------------------------------------------------------------------
FIELD_LAYOUT = [
    ("ACCT_ID",               1,  11, "numeric"),
    ("ACCT_ACTIVE_STATUS",   12,   1, "string"),
    ("ACCT_CURR_BAL",        13,  12, "signed_decimal"),
    ("ACCT_CREDIT_LIMIT",    25,  12, "signed_decimal"),
    ("ACCT_CASH_CREDIT_LIMIT", 37, 12, "signed_decimal"),
    ("ACCT_OPEN_DATE",       49,  10, "string"),
    ("ACCT_EXPIRAION_DATE",  59,  10, "string"),
    ("ACCT_REISSUE_DATE",    69,  10, "string"),
    ("ACCT_CURR_CYC_CREDIT", 79, 12, "signed_decimal"),
    ("ACCT_CURR_CYC_DEBIT",  91, 12, "signed_decimal"),
    ("ACCT_ADDR_ZIP",       103,  10, "string"),
    ("ACCT_GROUP_ID",       113,  10, "string"),
    ("FILLER",              123, 178, "string"),
]


def main(data_path: str, schema_path: str, output_path: str):
    spark = SparkSession.builder \
        .master("local[*]") \
        .appName("CVACT01Y_AccountParser") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    # Read the raw fixed-width file as single-column text
    raw_df = spark.read.text(data_path)

    # Slice each field using 1-based substring positions
    parsed_df = raw_df
    for name, start, length, _ in FIELD_LAYOUT:
        parsed_df = parsed_df.withColumn(name, substring(col("value"), start, length))

    # Drop the raw column
    parsed_df = parsed_df.drop("value")

    # Convert numeric / signed-decimal columns
    for name, _, _, ftype in FIELD_LAYOUT:
        if ftype == "numeric":
            parsed_df = parsed_df.withColumn(name, col(name).cast(LongType()))
        elif ftype == "signed_decimal":
            parsed_df = parsed_df.withColumn(name, decode_signed_udf(col(name)))
        else:
            parsed_df = parsed_df.withColumn(name, trim(col(name)))

    # Drop FILLER
    parsed_df = parsed_df.drop("FILLER")

    # ---- Validation ----
    raw_line_count = raw_df.count()
    parsed_row_count = parsed_df.count()

    validation = {
        "source_file": os.path.basename(data_path),
        "copybook": "CVACT01Y.cpy",
        "raw_line_count": raw_line_count,
        "parsed_row_count": parsed_row_count,
        "counts_match": raw_line_count == parsed_row_count,
        "schema_fields": [f[0] for f in FIELD_LAYOUT if f[0] != "FILLER"],
        "sample_rows": [],
    }

    sample_rows = parsed_df.limit(5).collect()
    for row in sample_rows:
        validation["sample_rows"].append(row.asDict())

    # Write validation JSON (convert Decimals to strings for JSON)
    class DecimalEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, Decimal):
                return str(o)
            return super().default(o)

    with open(output_path, "w") as f:
        json.dump(validation, f, indent=2, cls=DecimalEncoder)

    print(f"Raw lines : {raw_line_count}")
    print(f"Parsed rows: {parsed_row_count}")
    print(f"Match      : {raw_line_count == parsed_row_count}")
    parsed_df.show(5, truncate=False)

    spark.stop()


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo_dir = os.path.dirname(base_dir)
    data_path = os.path.join(repo_dir, "app", "data", "ASCII", "acctdata.txt")
    schema_path = os.path.join(base_dir, "schemas", "CVACT01Y_schema.json")
    output_path = os.path.join(base_dir, "validation", "acctdata_validation.json")
    main(data_path, schema_path, output_path)
