"""
Copybook-based parser for CardDemo ASCII data files.

Parses fixed-width ASCII records using COBOL copybook layout definitions.
Handles EBCDIC zoned-decimal overpunch encoding for signed numeric fields.
"""

import json
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


# Zoned-decimal overpunch mapping: last byte of a signed field encodes
# both the digit value (0-9) and the sign (+/-).
OVERPUNCH_POSITIVE = {
    "{": 0, "A": 1, "B": 2, "C": 3, "D": 4,
    "E": 5, "F": 6, "G": 7, "H": 8, "I": 9,
}
OVERPUNCH_NEGATIVE = {
    "}": 0, "J": 1, "K": 2, "L": 3, "M": 4,
    "N": 5, "O": 6, "P": 7, "Q": 8, "R": 9,
}


@dataclass
class CopybookField:
    """A single field from a COBOL copybook layout."""
    name: str
    pic: str
    offset: int
    length: int
    field_type: str  # "alphanumeric", "unsigned_numeric", "signed_decimal"
    decimal_places: int = 0


# Copybook layout definitions derived from app/cpy/*.cpy
# Each layout is a list of CopybookField entries (excluding FILLER).

ACCOUNT_LAYOUT = [
    CopybookField("ACCT-ID", "9(11)", 0, 11, "unsigned_numeric"),
    CopybookField("ACCT-ACTIVE-STATUS", "X(01)", 11, 1, "alphanumeric"),
    CopybookField("ACCT-CURR-BAL", "S9(10)V99", 12, 12, "signed_decimal", 2),
    CopybookField("ACCT-CREDIT-LIMIT", "S9(10)V99", 24, 12, "signed_decimal", 2),
    CopybookField("ACCT-CASH-CREDIT-LIMIT", "S9(10)V99", 36, 12, "signed_decimal", 2),
    CopybookField("ACCT-OPEN-DATE", "X(10)", 48, 10, "alphanumeric"),
    CopybookField("ACCT-EXPIRAION-DATE", "X(10)", 58, 10, "alphanumeric"),
    CopybookField("ACCT-REISSUE-DATE", "X(10)", 68, 10, "alphanumeric"),
    CopybookField("ACCT-CURR-CYC-CREDIT", "S9(10)V99", 78, 12, "signed_decimal", 2),
    CopybookField("ACCT-CURR-CYC-DEBIT", "S9(10)V99", 90, 12, "signed_decimal", 2),
    CopybookField("ACCT-ADDR-ZIP", "X(10)", 102, 10, "alphanumeric"),
    CopybookField("ACCT-GROUP-ID", "X(10)", 112, 10, "alphanumeric"),
    # FILLER PIC X(178) at offset 122, length 178 — skipped
]

CARD_LAYOUT = [
    CopybookField("CARD-NUM", "X(16)", 0, 16, "alphanumeric"),
    CopybookField("CARD-ACCT-ID", "9(11)", 16, 11, "unsigned_numeric"),
    CopybookField("CARD-CVV-CD", "9(03)", 27, 3, "unsigned_numeric"),
    CopybookField("CARD-EMBOSSED-NAME", "X(50)", 30, 50, "alphanumeric"),
    CopybookField("CARD-EXPIRAION-DATE", "X(10)", 80, 10, "alphanumeric"),
    CopybookField("CARD-ACTIVE-STATUS", "X(01)", 90, 1, "alphanumeric"),
    # FILLER PIC X(59) at offset 91, length 59 — skipped
]

CUSTOMER_LAYOUT = [
    CopybookField("CUST-ID", "9(09)", 0, 9, "unsigned_numeric"),
    CopybookField("CUST-FIRST-NAME", "X(25)", 9, 25, "alphanumeric"),
    CopybookField("CUST-MIDDLE-NAME", "X(25)", 34, 25, "alphanumeric"),
    CopybookField("CUST-LAST-NAME", "X(25)", 59, 25, "alphanumeric"),
    CopybookField("CUST-ADDR-LINE-1", "X(50)", 84, 50, "alphanumeric"),
    CopybookField("CUST-ADDR-LINE-2", "X(50)", 134, 50, "alphanumeric"),
    CopybookField("CUST-ADDR-LINE-3", "X(50)", 184, 50, "alphanumeric"),
    CopybookField("CUST-ADDR-STATE-CD", "X(02)", 234, 2, "alphanumeric"),
    CopybookField("CUST-ADDR-COUNTRY-CD", "X(03)", 236, 3, "alphanumeric"),
    CopybookField("CUST-ADDR-ZIP", "X(10)", 239, 10, "alphanumeric"),
    CopybookField("CUST-PHONE-NUM-1", "X(15)", 249, 15, "alphanumeric"),
    CopybookField("CUST-PHONE-NUM-2", "X(15)", 264, 15, "alphanumeric"),
    CopybookField("CUST-SSN", "9(09)", 279, 9, "unsigned_numeric"),
    CopybookField("CUST-GOVT-ISSUED-ID", "X(20)", 288, 20, "alphanumeric"),
    CopybookField("CUST-DOB-YYYY-MM-DD", "X(10)", 308, 10, "alphanumeric"),
    CopybookField("CUST-EFT-ACCOUNT-ID", "X(10)", 318, 10, "alphanumeric"),
    CopybookField("CUST-PRI-CARD-HOLDER-IND", "X(01)", 328, 1, "alphanumeric"),
    CopybookField("CUST-FICO-CREDIT-SCORE", "9(03)", 329, 3, "unsigned_numeric"),
    # FILLER PIC X(168) at offset 332, length 168 — skipped
]

CARDXREF_LAYOUT = [
    CopybookField("XREF-CARD-NUM", "X(16)", 0, 16, "alphanumeric"),
    CopybookField("XREF-CUST-ID", "9(09)", 16, 9, "unsigned_numeric"),
    CopybookField("XREF-ACCT-ID", "9(11)", 25, 11, "unsigned_numeric"),
    # FILLER PIC X(14) at offset 36, length 14 — skipped
]

TRANSACTION_LAYOUT = [
    CopybookField("TRAN-ID", "X(16)", 0, 16, "alphanumeric"),
    CopybookField("TRAN-TYPE-CD", "X(02)", 16, 2, "alphanumeric"),
    CopybookField("TRAN-CAT-CD", "9(04)", 18, 4, "unsigned_numeric"),
    CopybookField("TRAN-SOURCE", "X(10)", 22, 10, "alphanumeric"),
    CopybookField("TRAN-DESC", "X(100)", 32, 100, "alphanumeric"),
    CopybookField("TRAN-AMT", "S9(09)V99", 132, 11, "signed_decimal", 2),
    CopybookField("TRAN-MERCHANT-ID", "9(09)", 143, 9, "unsigned_numeric"),
    CopybookField("TRAN-MERCHANT-NAME", "X(50)", 152, 50, "alphanumeric"),
    CopybookField("TRAN-MERCHANT-CITY", "X(50)", 202, 50, "alphanumeric"),
    CopybookField("TRAN-MERCHANT-ZIP", "X(10)", 252, 10, "alphanumeric"),
    CopybookField("TRAN-CARD-NUM", "X(16)", 262, 16, "alphanumeric"),
    CopybookField("TRAN-ORIG-TS", "X(26)", 278, 26, "alphanumeric"),
    CopybookField("TRAN-PROC-TS", "X(26)", 304, 26, "alphanumeric"),
    # FILLER PIC X(20) at offset 330, length 20 — skipped
]

TCATBAL_LAYOUT = [
    CopybookField("TRANCAT-ACCT-ID", "9(11)", 0, 11, "unsigned_numeric"),
    CopybookField("TRANCAT-TYPE-CD", "X(02)", 11, 2, "alphanumeric"),
    CopybookField("TRANCAT-CD", "9(04)", 13, 4, "unsigned_numeric"),
    CopybookField("TRAN-CAT-BAL", "S9(09)V99", 17, 11, "signed_decimal", 2),
    # FILLER PIC X(22) at offset 28, length 22 — skipped
]

DISCGRP_LAYOUT = [
    CopybookField("DIS-ACCT-GROUP-ID", "X(10)", 0, 10, "alphanumeric"),
    CopybookField("DIS-TRAN-TYPE-CD", "X(02)", 10, 2, "alphanumeric"),
    CopybookField("DIS-TRAN-CAT-CD", "9(04)", 12, 4, "unsigned_numeric"),
    CopybookField("DIS-INT-RATE", "S9(04)V99", 16, 6, "signed_decimal", 2),
    # FILLER PIC X(28) at offset 22, length 28 — skipped
]

TRANTYPE_LAYOUT = [
    CopybookField("TRAN-TYPE", "X(02)", 0, 2, "alphanumeric"),
    CopybookField("TRAN-TYPE-DESC", "X(50)", 2, 50, "alphanumeric"),
    # FILLER PIC X(08) at offset 52, length 8 — skipped
]

TRANCATG_LAYOUT = [
    CopybookField("TRAN-TYPE-CD", "X(02)", 0, 2, "alphanumeric"),
    CopybookField("TRAN-CAT-CD", "9(04)", 2, 4, "unsigned_numeric"),
    CopybookField("TRAN-CAT-TYPE-DESC", "X(50)", 6, 50, "alphanumeric"),
    # FILLER PIC X(04) at offset 56, length 4 — skipped
]

# Registry mapping file basenames to their layouts
LAYOUT_REGISTRY = {
    "acctdata": ACCOUNT_LAYOUT,
    "carddata": CARD_LAYOUT,
    "custdata": CUSTOMER_LAYOUT,
    "cardxref": CARDXREF_LAYOUT,
    "dailytran": TRANSACTION_LAYOUT,
    "tcatbal": TCATBAL_LAYOUT,
    "discgrp": DISCGRP_LAYOUT,
    "trantype": TRANTYPE_LAYOUT,
    "trancatg": TRANCATG_LAYOUT,
}

# Expected record lengths (from copybook comments)
RECORD_LENGTHS = {
    "acctdata": 300,
    "carddata": 150,
    "custdata": 500,
    "cardxref": 50,
    "dailytran": 350,
    "tcatbal": 50,
    "discgrp": 50,
    "trantype": 60,
    "trancatg": 60,
}


def decode_signed_decimal(raw: str, decimal_places: int) -> str:
    """
    Decode an EBCDIC zoned-decimal overpunch string to a decimal string.

    The last character encodes both the final digit and the sign.
    Example: "00000001940{" with decimal_places=2 → "1940.00"
    Example: "0000009190}" with decimal_places=2 → "-919.00"
    """
    if not raw:
        return "0"

    last_char = raw[-1]
    digits_before_last = raw[:-1]

    if last_char in OVERPUNCH_POSITIVE:
        sign = ""
        last_digit = str(OVERPUNCH_POSITIVE[last_char])
    elif last_char in OVERPUNCH_NEGATIVE:
        sign = "-"
        last_digit = str(OVERPUNCH_NEGATIVE[last_char])
    elif last_char.isdigit():
        sign = ""
        last_digit = last_char
    else:
        sign = ""
        last_digit = "0"

    full_digits = digits_before_last + last_digit

    if decimal_places > 0:
        integer_part = full_digits[:-decimal_places] or "0"
        decimal_part = full_digits[-decimal_places:]
        result = f"{sign}{int(integer_part)}.{decimal_part}"
    else:
        result = f"{sign}{int(full_digits)}"

    return result


def parse_record(line: str, layout: list[CopybookField]) -> dict[str, Any]:
    """Parse a single fixed-width record using the given copybook layout."""
    record = {}
    for field in layout:
        raw = line[field.offset:field.offset + field.length]

        if field.field_type == "alphanumeric":
            record[field.name] = raw.rstrip()
        elif field.field_type == "unsigned_numeric":
            cleaned = raw.strip()
            record[field.name] = cleaned if cleaned else "0"
        elif field.field_type == "signed_decimal":
            record[field.name] = decode_signed_decimal(raw, field.decimal_places)

    return record


def parse_file(filepath: str, layout: list[CopybookField],
               record_length: int) -> list[dict[str, Any]]:
    """
    Parse an ASCII data file into a list of structured records.

    Reads fixed-width lines and applies the copybook layout to extract
    typed fields. Lines shorter than record_length are padded; lines
    that are empty or contain only whitespace are skipped.
    """
    records = []
    with open(filepath, "r", encoding="ascii", errors="replace") as f:
        for line in f:
            # Strip trailing newline/CR but preserve internal spaces
            line = line.rstrip("\n").rstrip("\r")

            # Skip empty lines
            if not line or line.isspace():
                continue

            # Pad short lines to expected record length
            if len(line) < record_length:
                line = line.ljust(record_length)

            record = parse_record(line, layout)
            records.append(record)

    return records


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal objects."""
    def default(self, obj: object) -> Any:
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)


def generate_golden_file(data_dir: str, output_dir: str,
                         file_key: str) -> dict[str, Any]:
    """
    Parse an ASCII data file and write the golden JSON reference.

    Returns a summary dict with record count and status.
    """
    input_path = os.path.join(data_dir, f"{file_key}.txt")
    output_path = os.path.join(output_dir, f"{file_key}.golden.json")

    if not os.path.exists(input_path):
        return {"file": file_key, "status": "skipped", "reason": "file not found"}

    layout = LAYOUT_REGISTRY[file_key]
    record_length = RECORD_LENGTHS[file_key]

    records = parse_file(input_path, layout, record_length)

    golden = {
        "metadata": {
            "source_file": f"app/data/ASCII/{file_key}.txt",
            "copybook": _get_copybook_name(file_key),
            "record_length": record_length,
            "record_count": len(records),
            "fields": [
                {
                    "name": f.name,
                    "pic": f.pic,
                    "offset": f.offset,
                    "length": f.length,
                    "type": f.field_type,
                }
                for f in layout
            ],
        },
        "records": records,
    }

    os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(golden, f, indent=2, cls=DecimalEncoder)

    return {
        "file": file_key,
        "status": "generated",
        "records": len(records),
        "output": output_path,
    }


def _get_copybook_name(file_key: str) -> str:
    """Map data file key to its copybook name."""
    mapping = {
        "acctdata": "CVACT01Y",
        "carddata": "CVACT02Y",
        "custdata": "CVCUS01Y",
        "cardxref": "CVACT03Y",
        "dailytran": "CVTRA05Y",
        "tcatbal": "CVTRA01Y",
        "discgrp": "CVTRA02Y",
        "trantype": "CVTRA03Y",
        "trancatg": "CVTRA04Y",
    }
    return mapping.get(file_key, "UNKNOWN")
