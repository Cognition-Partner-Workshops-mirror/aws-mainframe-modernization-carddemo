"""
Shared utility functions for parsing COBOL fixed-width data files.

Handles COBOL PIC clause type conversions to PySpark types, including:
- PIC 9(n)        -> Unsigned numeric display (LongType / IntegerType)
- PIC S9(m)V9(n)  -> Signed zoned decimal with implied decimal (DecimalType)
- PIC X(n)        -> Alphanumeric string (StringType)
- FILLER          -> Padding bytes (StringType, typically ignored)

Signed zoned-decimal fields use trailing overpunch encoding where the last
byte carries both the digit value and the sign. This module decodes those
overpunch characters for ASCII-encoded flat files.
"""

from pyspark.sql import functions as F
from pyspark.sql.types import (
    DecimalType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
)

# ---------------------------------------------------------------------------
# Trailing overpunch lookup tables (ASCII / EBCDIC-to-ASCII convention)
# Positive: { = 0, A = 1, B = 2, ... I = 9
# Negative: } = 0, J = 1, K = 2, ... R = 9
# ---------------------------------------------------------------------------
POSITIVE_OVERPUNCH = {"{": "0", "A": "1", "B": "2", "C": "3", "D": "4",
                      "E": "5", "F": "6", "G": "7", "H": "8", "I": "9"}
NEGATIVE_OVERPUNCH = {"}": "0", "J": "1", "K": "2", "L": "3", "M": "4",
                      "N": "5", "O": "6", "P": "7", "Q": "8", "R": "9"}


def decode_signed_zoned_decimal(raw_value: str, scale: int) -> str:
    """
    Decode a COBOL signed zoned-decimal (DISPLAY) string with trailing
    overpunch into a numeric string with explicit sign and decimal point.

    Args:
        raw_value: The raw fixed-width string (e.g. '00000001940{').
        scale:     Number of implied decimal digits (V9(scale)).

    Returns:
        A string like '+194.00' or '-50.25' suitable for Decimal casting.
        Returns None for null / empty input.
    """
    if raw_value is None or raw_value.strip() == "":
        return None

    # Extract the trailing overpunch character
    last_char = raw_value[-1]
    digits_before_last = raw_value[:-1]

    # Determine sign and decode last digit
    if last_char in POSITIVE_OVERPUNCH:
        sign = ""
        last_digit = POSITIVE_OVERPUNCH[last_char]
    elif last_char in NEGATIVE_OVERPUNCH:
        sign = "-"
        last_digit = NEGATIVE_OVERPUNCH[last_char]
    elif last_char.isdigit():
        # No overpunch; treat as unsigned positive
        sign = ""
        last_digit = last_char
    else:
        return None

    # Build the full digit string
    full_digits = digits_before_last + last_digit

    # Insert the decimal point based on scale
    if scale > 0:
        integer_part = full_digits[:-scale]
        decimal_part = full_digits[-scale:]
        return f"{sign}{integer_part}.{decimal_part}"
    else:
        return f"{sign}{full_digits}"


def build_pyspark_schema(field_definitions):
    """
    Build a PySpark StructType from a list of field definitions.

    Each field definition is a dict with keys:
        - name:       Field name (string)
        - pic:        COBOL PIC clause (string, for documentation)
        - spark_type: PySpark DataType instance
        - offset:     Byte offset (0-based) in the record
        - length:     Field length in bytes

    Returns:
        A PySpark StructType schema.
    """
    fields = []
    for f in field_definitions:
        # All fields are nullable since fixed-width data may contain blanks
        fields.append(StructField(f["name"], f["spark_type"], nullable=True))
    return StructType(fields)


def _decode_overpunch_expr(raw_col_expr, field_length, scale):
    """
    Build a pure Spark SQL expression to decode a trailing-overpunch
    signed zoned-decimal field into a numeric string.

    Uses F.when/F.otherwise chains instead of a Python UDF so the logic
    runs inside the JVM and avoids serialization issues with the Python
    worker.

    Args:
        raw_col_expr: A Spark Column expression for the raw field substring.
        field_length: Total byte length of the field.
        scale:        Number of implied decimal digits.

    Returns:
        A Spark Column expression producing a string like '194.00' or '-50.25'.
    """
    # Split into leading digits and the trailing overpunch character
    leading = F.substring(raw_col_expr, 1, field_length - 1)
    last_char = F.substring(raw_col_expr, field_length, 1)

    # Build the decoded last digit using when/otherwise for each overpunch char
    # Positive overpunch: { -> 0, A -> 1, B -> 2, ... I -> 9
    decoded_digit = (
        F.when(last_char == "{", F.lit("0"))
         .when(last_char == "A", F.lit("1"))
         .when(last_char == "B", F.lit("2"))
         .when(last_char == "C", F.lit("3"))
         .when(last_char == "D", F.lit("4"))
         .when(last_char == "E", F.lit("5"))
         .when(last_char == "F", F.lit("6"))
         .when(last_char == "G", F.lit("7"))
         .when(last_char == "H", F.lit("8"))
         .when(last_char == "I", F.lit("9"))
         # Negative overpunch: } -> 0, J -> 1, K -> 2, ... R -> 9
         .when(last_char == "}", F.lit("0"))
         .when(last_char == "J", F.lit("1"))
         .when(last_char == "K", F.lit("2"))
         .when(last_char == "L", F.lit("3"))
         .when(last_char == "M", F.lit("4"))
         .when(last_char == "N", F.lit("5"))
         .when(last_char == "O", F.lit("6"))
         .when(last_char == "P", F.lit("7"))
         .when(last_char == "Q", F.lit("8"))
         .when(last_char == "R", F.lit("9"))
         # Plain digit (no overpunch)
         .otherwise(last_char)
    )

    # Determine sign: negative if last_char is }, J-R
    sign_expr = (
        F.when(last_char == "}", F.lit("-"))
         .when(last_char == "J", F.lit("-"))
         .when(last_char == "K", F.lit("-"))
         .when(last_char == "L", F.lit("-"))
         .when(last_char == "M", F.lit("-"))
         .when(last_char == "N", F.lit("-"))
         .when(last_char == "O", F.lit("-"))
         .when(last_char == "P", F.lit("-"))
         .when(last_char == "Q", F.lit("-"))
         .when(last_char == "R", F.lit("-"))
         .otherwise(F.lit(""))
    )

    # Concatenate leading digits + decoded last digit to form full digit string
    full_digits = F.concat(leading, decoded_digit)

    # Insert the decimal point: integer_part.decimal_part
    if scale > 0:
        total_digits = field_length  # number of digit positions
        int_len = total_digits - scale
        integer_part = F.substring(full_digits, 1, int_len)
        decimal_part = F.substring(full_digits, int_len + 1, scale)
        numeric_str = F.concat(sign_expr, integer_part, F.lit("."), decimal_part)
    else:
        numeric_str = F.concat(sign_expr, full_digits)

    return numeric_str


def extract_fixed_width_fields(df, field_definitions, raw_col="value"):
    """
    Extract fixed-width fields from a single-column DataFrame.

    Uses PySpark's substring() function (1-based offset) to slice each
    field from the raw line.  Applies type-specific transformations:
      - StringType fields are right-trimmed.
      - Numeric PIC 9(n) fields are cast to LongType or IntegerType.
      - Signed decimal fields are decoded via UDF then cast to DecimalType.

    Args:
        df:                The DataFrame with a single 'value' column.
        field_definitions: List of field definition dicts (see build_pyspark_schema).
        raw_col:           Name of the raw text column.

    Returns:
        A DataFrame with one column per field, properly typed.
    """
    result_df = df
    select_cols = []

    for fdef in field_definitions:
        name = fdef["name"]
        # PySpark substring is 1-based
        start_pos = fdef["offset"] + 1
        length = fdef["length"]
        spark_type = fdef["spark_type"]

        # Extract the raw substring
        raw_field = F.substring(F.col(raw_col), start_pos, length)

        if isinstance(spark_type, StringType):
            # Trim trailing spaces from alphanumeric fields
            select_cols.append(F.rtrim(raw_field).alias(name))

        elif isinstance(spark_type, (LongType, IntegerType)):
            # Unsigned numeric display: cast directly after trimming
            select_cols.append(raw_field.cast(spark_type).alias(name))

        elif isinstance(spark_type, DecimalType):
            # Signed zoned decimal with trailing overpunch — decoded using
            # native Spark SQL expressions (no UDF) for serialization safety
            # and better performance.
            scale = spark_type.scale
            decoded = _decode_overpunch_expr(raw_field, length, scale)
            select_cols.append(decoded.cast(spark_type).alias(name))
        else:
            # Fallback: keep as string
            select_cols.append(raw_field.alias(name))

    return df.select(*select_cols)
