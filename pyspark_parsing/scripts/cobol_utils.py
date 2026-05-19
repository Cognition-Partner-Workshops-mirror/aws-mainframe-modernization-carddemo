"""
Shared utilities for parsing COBOL fixed-width files in PySpark.

Handles COBOL-specific data representations such as zoned-decimal
trailing sign overpunch characters used in PIC S9(n)Vnn fields.
"""

from pyspark.sql.functions import udf
from pyspark.sql.types import StringType
from decimal import Decimal, InvalidOperation

# -----------------------------------------------------------------------
# COBOL trailing-overpunch sign mapping (EBCDIC-to-ASCII convention).
#
# In zoned-decimal DISPLAY format the sign is encoded in the last byte:
#   Positive: { = 0, A = 1, B = 2, C = 3, D = 4,
#              E = 5, F = 6, G = 7, H = 8, I = 9
#   Negative: } = 0, J = 1, K = 2, L = 3, M = 4,
#              N = 5, O = 6, P = 7, Q = 8, R = 9
# -----------------------------------------------------------------------
POSITIVE_OVERPUNCH = {
    "{": "0", "A": "1", "B": "2", "C": "3", "D": "4",
    "E": "5", "F": "6", "G": "7", "H": "8", "I": "9",
}

NEGATIVE_OVERPUNCH = {
    "}": "0", "J": "1", "K": "2", "L": "3", "M": "4",
    "N": "5", "O": "6", "P": "7", "Q": "8", "R": "9",
}


def decode_signed_zoned_decimal(raw_value: str, decimal_places: int) -> str:
    """Decode a COBOL signed zoned-decimal field with trailing overpunch.

    Args:
        raw_value: The raw fixed-width string extracted from the data file
                   (e.g. '00000001940{').
        decimal_places: Number of implied decimal places (from the PIC V clause).

    Returns:
        A string representation of the decimal value suitable for casting
        (e.g. '19400.00' → with V99 applied → '194.00' is returned as
        the sign-adjusted string with the decimal point inserted).
    """
    if raw_value is None or raw_value.strip() == "":
        return None

    raw_value = raw_value.strip()

    # Last character carries the sign
    last_char = raw_value[-1]
    leading_digits = raw_value[:-1]

    # Determine sign and replace last char with its digit equivalent
    if last_char in POSITIVE_OVERPUNCH:
        sign = ""
        last_digit = POSITIVE_OVERPUNCH[last_char]
    elif last_char in NEGATIVE_OVERPUNCH:
        sign = "-"
        last_digit = NEGATIVE_OVERPUNCH[last_char]
    elif last_char.isdigit():
        # No overpunch — treat as unsigned positive
        sign = ""
        last_digit = last_char
    else:
        return None  # unrecognised character

    digit_str = leading_digits + last_digit

    # Insert implied decimal point (V clause)
    if decimal_places > 0:
        integer_part = digit_str[:-decimal_places]
        decimal_part = digit_str[-decimal_places:]
        result = f"{sign}{integer_part}.{decimal_part}"
    else:
        result = f"{sign}{digit_str}"

    return result


def make_signed_decimal_udf(decimal_places: int):
    """Create a PySpark UDF for a specific number of implied decimal places.

    Args:
        decimal_places: Number of implied decimal places from the COBOL PIC.

    Returns:
        A PySpark UDF that converts raw zoned-decimal strings to decimal strings.
    """
    def _udf_func(raw_value):
        return decode_signed_zoned_decimal(raw_value, decimal_places)

    return udf(_udf_func, StringType())
