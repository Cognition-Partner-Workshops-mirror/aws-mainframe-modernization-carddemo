"""
Utility functions for parsing COBOL zoned-decimal fields in ASCII fixed-width files.

In COBOL, PIC S9(n)V99 fields store the sign as an overpunch character on the
last byte. When mainframe data is converted from EBCDIC to ASCII, the sign
overpunch is mapped to specific ASCII characters:

  Positive: 0='{', 1='A', 2='B', 3='C', 4='D', 5='E', 6='F', 7='G', 8='H', 9='I'
  Negative: 0='}', 1='J', 2='K', 3='L', 4='M', 5='N', 6='O', 7='P', 8='Q', 9='R'

The 'V' in PIC S9(10)V99 denotes an *implied* decimal point — no literal '.'
appears in the data. For example, PIC S9(10)V99 occupies 12 bytes and represents
a value with 10 integer digits and 2 fractional digits.
"""

from decimal import Decimal

POSITIVE_OVERPUNCH = {
    "{": "0", "A": "1", "B": "2", "C": "3", "D": "4",
    "E": "5", "F": "6", "G": "7", "H": "8", "I": "9",
}

NEGATIVE_OVERPUNCH = {
    "}": "0", "J": "1", "K": "2", "L": "3", "M": "4",
    "N": "5", "O": "6", "P": "7", "Q": "8", "R": "9",
}


def decode_zoned_decimal(raw: str, scale: int) -> Decimal:
    """Decode a COBOL signed zoned-decimal string to a Python Decimal.

    Args:
        raw: The raw fixed-width string for the field.
        scale: Number of implied decimal places (e.g. 2 for V99).

    Returns:
        A Decimal value with proper sign and decimal placement.
    """
    if not raw or raw.isspace():
        return Decimal("0")

    last_char = raw[-1]
    leading = raw[:-1]

    if last_char in POSITIVE_OVERPUNCH:
        sign = 1
        last_digit = POSITIVE_OVERPUNCH[last_char]
    elif last_char in NEGATIVE_OVERPUNCH:
        sign = -1
        last_digit = NEGATIVE_OVERPUNCH[last_char]
    elif last_char.isdigit():
        sign = 1
        last_digit = last_char
    else:
        return Decimal("0")

    digits = leading + last_digit
    digits = digits.lstrip("0") or "0"

    if scale > 0:
        digits = digits.zfill(scale + 1)
        integer_part = digits[:-scale]
        fractional_part = digits[-scale:]
        value = Decimal(f"{integer_part}.{fractional_part}")
    else:
        value = Decimal(digits)

    return value * sign
