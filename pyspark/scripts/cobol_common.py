"""
Common utilities for parsing COBOL fixed-width files exported as ASCII text.

Handles the COBOL sign-overpunch encoding used in PIC S9(...) fields,
where the last byte of a signed numeric field encodes both a digit and
a sign using special characters:

Positive:  { = 0, A = 1, B = 2, C = 3, D = 4, E = 5, F = 6, G = 7, H = 8, I = 9
Negative:  } = 0, J = 1, K = 2, L = 3, M = 4, N = 5, O = 6, P = 7, Q = 8, R = 9

For example, with PIC S9(10)V99:
  '00000001940{' -> +19400 -> with V99 implied decimal -> +194.00
  '00000001940}' -> -19400 -> with V99 implied decimal -> -194.00
"""

from decimal import Decimal
import json
import logging

# PySpark imports are deferred to function scope so pure-Python utilities
# (decode_sign_overpunch, parse_fixed_width_line, load_schema) can be used
# in environments without PySpark installed (e.g., validation scripts).

logger = logging.getLogger("cobol_parser")

# ---------------------------------------------------------------------------
# Sign-overpunch decode maps
# ---------------------------------------------------------------------------

# Maps the overpunch character to (digit, sign_multiplier)
OVERPUNCH_MAP = {
    "{": ("0", 1), "A": ("1", 1), "B": ("2", 1), "C": ("3", 1), "D": ("4", 1),
    "E": ("5", 1), "F": ("6", 1), "G": ("7", 1), "H": ("8", 1), "I": ("9", 1),
    "}": ("0", -1), "J": ("1", -1), "K": ("2", -1), "L": ("3", -1), "M": ("4", -1),
    "N": ("5", -1), "O": ("6", -1), "P": ("7", -1), "Q": ("8", -1), "R": ("9", -1),
}


def decode_sign_overpunch(raw_value: str, decimal_places: int) -> Decimal:
    """
    Decode a COBOL sign-overpunch encoded numeric string to a Python Decimal.

    Args:
        raw_value: The raw fixed-width string (e.g., '00000001940{')
        decimal_places: Number of implied decimal places from the V clause (e.g., 2 for V99)

    Returns:
        Decimal value with the correct sign and decimal position.
        Returns Decimal('0') for null/blank input.
    """
    if not raw_value or raw_value.strip() == "":
        return Decimal("0")

    last_char = raw_value[-1]

    if last_char in OVERPUNCH_MAP:
        digit, sign = OVERPUNCH_MAP[last_char]
        # Replace the overpunch character with its digit value
        numeric_str = raw_value[:-1] + digit
    elif last_char.isdigit():
        # No overpunch — treat as positive (sometimes seen in ASCII exports)
        numeric_str = raw_value
        sign = 1
    else:
        # Unrecognized trailing character — log and treat as zero
        logger.warning(f"Unrecognized overpunch character '{last_char}' in value '{raw_value}'")
        return Decimal("0")

    # Insert decimal point at the correct position based on V clause
    if decimal_places > 0:
        integer_part = numeric_str[:-decimal_places]
        decimal_part = numeric_str[-decimal_places:]
        numeric_str = f"{integer_part}.{decimal_part}"

    return Decimal(numeric_str) * sign


# Register as a Spark UDF for use in DataFrame transformations
def register_overpunch_udf(spark):
    """
    Register the sign-overpunch decoder as a Spark UDF.

    Returns a UDF that takes (raw_string, decimal_places) and returns DecimalType.
    Since UDFs can't take two columns easily, we create a closure per decimal_places value.
    """
    from pyspark.sql import functions as F
    from pyspark.sql.types import DecimalType

    def make_udf(decimal_places):
        """Create a UDF closure for a specific number of decimal places."""
        @F.udf(DecimalType(12, decimal_places))
        def decode_overpunch_udf(raw_value):
            if raw_value is None:
                return None
            return decode_sign_overpunch(raw_value, decimal_places)
        return decode_overpunch_udf

    return make_udf


def parse_fixed_width_line(line: str, field_specs: list) -> dict:
    """
    Parse a single fixed-width line into a dict of field values.

    Args:
        line: The raw text line from the fixed-width file
        field_specs: List of dicts with 'name', 'byte_offset', 'length', 'signed',
                     'decimal_places' keys (from the JSON schema)

    Returns:
        Dict mapping field names to raw string values (pre-type-conversion)
    """
    result = {}
    for field in field_specs:
        start = field["byte_offset"]
        end = start + field["length"]
        raw = line[start:end] if len(line) >= end else ""
        result[field["name"]] = raw
    return result


def load_schema(schema_path: str) -> dict:
    """Load a JSON schema file describing the copybook layout."""
    with open(schema_path, "r") as f:
        return json.load(f)


def create_fixed_width_df(spark, data_path: str, schema: dict):
    """
    Read a fixed-width file and parse it into a Spark DataFrame using the copybook schema.

    Steps:
    1. Read the entire file as single-column text (one row per record)
    2. Extract each field using substring based on byte_offset and length
    3. Apply type conversions (sign-overpunch for signed numerics, cast for others)

    All parse errors produce null values with warning log messages rather than
    failing the pipeline (consistent with the "flag, don't drop" philosophy).
    """
    from pyspark.sql import functions as F

    # Step 1: Read as raw text lines
    raw_df = spark.read.text(data_path)

    fields = schema["fields"]
    make_overpunch_udf = register_overpunch_udf(spark)

    # Step 2: Extract each field via substring
    for field in fields:
        col_name = field["name"]
        # Spark substring is 1-indexed
        start_pos = field["byte_offset"] + 1
        length = field["length"]

        # Extract raw substring
        raw_df = raw_df.withColumn(
            col_name,
            F.substring(F.col("value"), start_pos, length)
        )

    # Step 3: Apply type conversions per field
    for field in fields:
        col_name = field["name"]
        pyspark_type = field["pyspark_type"]

        if col_name == "FILLER":
            # Skip filler fields — will be dropped later
            continue

        if field.get("signed", False):
            # Signed numeric with overpunch encoding -> DecimalType
            decimal_places = field.get("decimal_places", 0)
            overpunch_udf = make_overpunch_udf(decimal_places)
            raw_df = raw_df.withColumn(col_name, overpunch_udf(F.col(col_name)))

        elif pyspark_type == "LongType":
            # Unsigned numeric PIC 9(...) -> LongType
            raw_df = raw_df.withColumn(col_name, F.trim(F.col(col_name)).cast("long"))

        elif pyspark_type == "IntegerType":
            # Short unsigned numeric PIC 9(03) -> IntegerType
            raw_df = raw_df.withColumn(col_name, F.trim(F.col(col_name)).cast("int"))

        elif pyspark_type == "DateType":
            # Date string (YYYY-MM-DD format in ASCII export) -> DateType
            raw_df = raw_df.withColumn(
                col_name,
                F.to_date(F.trim(F.col(col_name)), "yyyy-MM-dd")
            )

        elif pyspark_type == "StringType":
            # Alphanumeric PIC X(...) -> trimmed string
            raw_df = raw_df.withColumn(col_name, F.trim(F.col(col_name)))

    # Drop the raw text column and FILLER
    columns_to_keep = [f["name"] for f in fields if f["name"] != "FILLER"]
    result_df = raw_df.select(columns_to_keep)

    return result_df
