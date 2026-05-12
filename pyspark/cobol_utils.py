"""
Shared utility functions for parsing COBOL fixed-width data files.

Handles COBOL sign overpunch decoding for signed zoned-decimal fields
(PIC S9(n)Vxx) stored in ASCII display format.

COBOL Sign Overpunch Convention (ASCII):
  Positive: { = +0, A = +1, B = +2, ..., I = +9
  Negative: } = -0, J = -1, K = -2, ..., R = -9

The sign is encoded in the last byte of the field. The overpunch character
replaces the final digit and simultaneously encodes the sign and digit value.
"""

from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType

# Mapping of COBOL sign overpunch characters to (sign_multiplier, digit_value).
# Positive overpunches: { = +0, A-I = +1 through +9
# Negative overpunches: } = -0, J-R = -1 through -9
POSITIVE_OVERPUNCH = {"{": "0", "A": "1", "B": "2", "C": "3", "D": "4",
                      "E": "5", "F": "6", "G": "7", "H": "8", "I": "9"}
NEGATIVE_OVERPUNCH = {"}": "0", "J": "1", "K": "2", "L": "3", "M": "4",
                      "N": "5", "O": "6", "P": "7", "Q": "8", "R": "9"}


def decode_sign_overpunch_udf():
    """
    Returns a PySpark UDF that decodes a COBOL signed zoned-decimal field
    (PIC S9(n)V99) from its ASCII display representation.

    The last character in the field is a sign overpunch that encodes both
    the sign (+/-) and the final digit. This UDF:
      1. Extracts the overpunch character (last byte)
      2. Determines sign and final digit
      3. Reconstructs the full numeric string
      4. Inserts the implied decimal point (V99 = 2 decimal places)
      5. Returns the signed decimal string (e.g., "-194.00")
    """
    def _decode(raw_value, decimal_places=2):
        """Decode a single COBOL signed overpunch field value."""
        if raw_value is None or len(raw_value) == 0:
            return None

        raw_value = raw_value.strip()
        if len(raw_value) == 0:
            return None

        # Extract the overpunch character (last byte of the field)
        overpunch_char = raw_value[-1]
        digits_before_overpunch = raw_value[:-1]

        # Determine the sign and the digit encoded in the overpunch
        if overpunch_char in POSITIVE_OVERPUNCH:
            sign = ""
            last_digit = POSITIVE_OVERPUNCH[overpunch_char]
        elif overpunch_char in NEGATIVE_OVERPUNCH:
            sign = "-"
            last_digit = NEGATIVE_OVERPUNCH[overpunch_char]
        elif overpunch_char.isdigit():
            # No overpunch — treat as unsigned positive
            sign = ""
            last_digit = overpunch_char
        else:
            return None

        # Reconstruct full digit string (without sign, without decimal)
        full_digits = digits_before_overpunch + last_digit

        # Insert the implied decimal point (V99 → 2 decimal places)
        if decimal_places > 0 and len(full_digits) > decimal_places:
            integer_part = full_digits[:-decimal_places]
            fractional_part = full_digits[-decimal_places:]
            result = f"{sign}{integer_part}.{fractional_part}"
        else:
            result = f"{sign}{full_digits}"

        return result

    return F.udf(_decode)


def parse_signed_decimal(df, col_name, decimal_places=2, precision=12, scale=2):
    """
    Parse a COBOL signed zoned-decimal column with sign overpunch encoding.

    Applies the sign overpunch UDF and casts to DecimalType for proper
    numeric handling in downstream PySpark operations.

    Args:
        df: PySpark DataFrame containing the raw string column
        col_name: Name of the column to parse
        decimal_places: Number of implied decimal places (V99 = 2)
        precision: Total number of digits in the DecimalType
        scale: Number of digits after the decimal point
    Returns:
        DataFrame with the column converted to DecimalType
    """
    udf_func = decode_sign_overpunch_udf()
    return df.withColumn(
        col_name,
        udf_func(F.col(col_name), F.lit(decimal_places)).cast(DecimalType(precision, scale))
    )
