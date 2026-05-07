"""
PySpark script to parse app/data/ASCII/acctdata.txt using the CVACT01Y.cpy
(ACCOUNT-RECORD) copybook layout.

Record length: 300 bytes (fixed-width, one record per line).

Signed zoned-decimal fields (PIC S9(n)V99) use ASCII overpunch encoding in
the last byte to represent both the sign and the trailing digit.
"""

import json
import os
from decimal import Decimal

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    DecimalType,
    LongType,
    StringType,
    StructField,
    StructType,
)

# ---------------------------------------------------------------------------
# ASCII overpunch sign decoding
# ---------------------------------------------------------------------------
POSITIVE_OVERPUNCH = {
    "{": "0", "A": "1", "B": "2", "C": "3", "D": "4",
    "E": "5", "F": "6", "G": "7", "H": "8", "I": "9",
}
NEGATIVE_OVERPUNCH = {
    "}": "0", "J": "1", "K": "2", "L": "3", "M": "4",
    "N": "5", "O": "6", "P": "7", "Q": "8", "R": "9",
}


def decode_signed_zoned_decimal(raw: str, decimal_places: int) -> Decimal:
    """Decode a COBOL signed zoned-decimal (DISPLAY) field from ASCII text.

    The last character carries the sign via overpunch encoding.
    ``decimal_places`` is the number of implied decimal digits (from V99).
    """
    if not raw or raw.strip() == "":
        return Decimal("0")

    last_char = raw[-1]
    digits = raw[:-1]

    if last_char in POSITIVE_OVERPUNCH:
        digits += POSITIVE_OVERPUNCH[last_char]
        sign = ""
    elif last_char in NEGATIVE_OVERPUNCH:
        digits += NEGATIVE_OVERPUNCH[last_char]
        sign = "-"
    elif last_char.isdigit():
        digits += last_char
        sign = ""
    else:
        digits += "0"
        sign = ""

    if decimal_places > 0:
        int_part = digits[:-decimal_places] or "0"
        dec_part = digits[-decimal_places:]
        return Decimal(f"{sign}{int_part}.{dec_part}")
    return Decimal(f"{sign}{digits}")


# ---------------------------------------------------------------------------
# Field layout derived from CVACT01Y.cpy
# ---------------------------------------------------------------------------
FIELDS = [
    ("ACCT_ID",                11, "long"),
    ("ACCT_ACTIVE_STATUS",      1, "string"),
    ("ACCT_CURR_BAL",          12, "signed_decimal_2"),
    ("ACCT_CREDIT_LIMIT",      12, "signed_decimal_2"),
    ("ACCT_CASH_CREDIT_LIMIT", 12, "signed_decimal_2"),
    ("ACCT_OPEN_DATE",         10, "string"),
    ("ACCT_EXPIRAION_DATE",    10, "string"),
    ("ACCT_REISSUE_DATE",      10, "string"),
    ("ACCT_CURR_CYC_CREDIT",   12, "signed_decimal_2"),
    ("ACCT_CURR_CYC_DEBIT",    12, "signed_decimal_2"),
    ("ACCT_ADDR_ZIP",          10, "string"),
    ("ACCT_GROUP_ID",          10, "string"),
    ("FILLER",                178, "string"),
]

RECORD_LENGTH = 300


def build_spark_schema():
    """Return a StructType matching the parsed output."""
    spark_fields = []
    for name, _, ftype in FIELDS:
        if ftype == "long":
            spark_fields.append(StructField(name, LongType(), True))
        elif ftype.startswith("signed_decimal"):
            spark_fields.append(StructField(name, DecimalType(12, 2), True))
        else:
            spark_fields.append(StructField(name, StringType(), True))
    return StructType(spark_fields)


def parse_record(line: str):
    """Slice a fixed-width line into a tuple of typed values."""
    values = []
    offset = 0
    for _, length, ftype in FIELDS:
        raw = line[offset:offset + length]
        offset += length

        if ftype == "long":
            values.append(int(raw) if raw.strip() else None)
        elif ftype == "signed_decimal_2":
            values.append(decode_signed_zoned_decimal(raw, 2))
        else:
            values.append(raw.strip())
    return tuple(values)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    data_path = os.path.join(repo_root, "app", "data", "ASCII", "acctdata.txt")
    schema_path = os.path.join(
        repo_root, "generated", "schemas", "CVACT01Y_account_schema.json"
    )
    validation_path = os.path.join(
        repo_root, "generated", "validation", "acctdata_validation.json"
    )

    spark = SparkSession.builder \
        .master("local[*]") \
        .appName("CVACT01Y_AccountRecord_Parser") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    try:
        # Read raw lines
        raw_rdd = spark.sparkContext.textFile(data_path)
        raw_count = raw_rdd.count()

        # Validate record lengths
        bad_lengths = raw_rdd.filter(lambda line: len(line) != RECORD_LENGTH).count()

        # Parse records
        parsed_rdd = raw_rdd.map(parse_record)
        schema = build_spark_schema()
        df = spark.createDataFrame(parsed_rdd, schema)

        parsed_count = df.count()

        # Collect sample rows for validation
        sample_rows = []
        for row in df.head(5):
            sample_rows.append(row.asDict())

        # Serialise Decimal values for JSON
        for row_dict in sample_rows:
            for k, v in row_dict.items():
                if isinstance(v, Decimal):
                    row_dict[k] = str(v)

        # Print summary
        print(f"Source file       : {data_path}")
        print("Copybook          : CVACT01Y.cpy")
        print(f"Record length     : {RECORD_LENGTH}")
        print(f"Raw line count    : {raw_count}")
        print(f"Bad-length lines  : {bad_lengths}")
        print(f"Parsed row count  : {parsed_count}")
        print(f"Row count match   : {raw_count == parsed_count}")
        print()
        df.printSchema()
        df.show(5, truncate=False)

        # Load JSON schema for field metadata
        with open(schema_path, "r") as f:
            schema_meta = json.load(f)

        validation_output = {
            "copybook": "CVACT01Y.cpy",
            "data_file": "app/data/ASCII/acctdata.txt",
            "record_length": RECORD_LENGTH,
            "raw_line_count": raw_count,
            "bad_length_lines": bad_lengths,
            "parsed_row_count": parsed_count,
            "row_count_match": raw_count == parsed_count,
            "schema_field_count": len(schema_meta["fields"]),
            "sample_rows": sample_rows,
        }

        os.makedirs(os.path.dirname(validation_path), exist_ok=True)
        with open(validation_path, "w") as f:
            json.dump(validation_output, f, indent=2)

        print(f"\nValidation output written to: {validation_path}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
