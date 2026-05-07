"""Utility functions for parsing COBOL fixed-width data in PySpark.

Handles zoned-decimal sign overpunch decoding for PIC S9(n)V99 fields
that have been converted from EBCDIC to ASCII.
"""

from decimal import Decimal

# EBCDIC overpunch sign mapping (last byte of a signed zoned-decimal field).
# Positive: {=0, A=1, B=2, C=3, D=4, E=5, F=6, G=7, H=8, I=9
# Negative: }=0, J=1, K=2, L=3, M=4, N=5, O=6, P=7, Q=8, R=9
OVERPUNCH_POSITIVE = {"{": "0", "A": "1", "B": "2", "C": "3", "D": "4",
                      "E": "5", "F": "6", "G": "7", "H": "8", "I": "9"}
OVERPUNCH_NEGATIVE = {"}": "0", "J": "1", "K": "2", "L": "3", "M": "4",
                      "N": "5", "O": "6", "P": "7", "Q": "8", "R": "9"}


def decode_signed_zoned_decimal(raw_value, scale=2):
    """Decode a signed zoned-decimal field with EBCDIC overpunch sign.

    Args:
        raw_value: Raw string from fixed-width file (e.g. '00000001940{').
        scale: Number of implied decimal places (V99 = 2).

    Returns:
        Decimal value with correct sign and implied decimal point,
        or None if the input is None or blank.
    """
    if raw_value is None or raw_value.strip() == "":
        return None

    last_char = raw_value[-1]
    digits = raw_value[:-1]

    if last_char in OVERPUNCH_POSITIVE:
        sign = 1
        digits += OVERPUNCH_POSITIVE[last_char]
    elif last_char in OVERPUNCH_NEGATIVE:
        sign = -1
        digits += OVERPUNCH_NEGATIVE[last_char]
    elif last_char.isdigit():
        sign = 1
        digits += last_char
    else:
        return None

    if not digits.isdigit():
        return None

    integer_part = digits[:-scale] if scale > 0 else digits
    decimal_part = digits[-scale:] if scale > 0 else ""

    numeric_str = f"{integer_part}.{decimal_part}" if scale > 0 else integer_part
    return Decimal(numeric_str) * sign
