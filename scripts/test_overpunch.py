"""
Unit tests for the sign-overpunch decoder used by parse_acctdata.py.

Validates positive, negative, unsigned, and edge-case inputs against the
COBOL DISPLAY-format overpunch encoding table.

Usage:
    python scripts/test_overpunch.py
"""

from decimal import Decimal

# ---------------------------------------------------------------------------
# Import the decoder and lookup tables from parse_acctdata
# ---------------------------------------------------------------------------
import os
import sys

# Ensure the scripts directory is on the path so we can import parse_acctdata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parse_acctdata import (
    POSITIVE_OVERPUNCH,
    NEGATIVE_OVERPUNCH,
    decode_signed_zoned_decimal,
)


def test_positive_overpunch():
    """Verify all 10 positive overpunch characters decode correctly."""
    # { = +0, A = +1, B = +2, ..., I = +9
    cases = [
        # (raw_input, expected_decimal_value)
        ("00000001940{", Decimal("194.00")),   # { → +0 → 000000019400 → 194.00
        ("00000001940A", Decimal("194.01")),   # A → +1 → 000000019401 → 194.01
        ("00000001940B", Decimal("194.02")),   # B → +2
        ("00000001940C", Decimal("194.03")),   # C → +3
        ("00000001940D", Decimal("194.04")),   # D → +4
        ("00000001940E", Decimal("194.05")),   # E → +5
        ("00000001940F", Decimal("194.06")),   # F → +6
        ("00000001940G", Decimal("194.07")),   # G → +7
        ("00000001940H", Decimal("194.08")),   # H → +8
        ("00000001940I", Decimal("194.09")),   # I → +9
    ]
    for raw, expected in cases:
        result = decode_signed_zoned_decimal(raw, scale=2)
        assert result == expected, (
            f"POSITIVE FAIL: decode('{raw}') = {result}, expected {expected}"
        )
    print("  PASS: All 10 positive overpunch characters decoded correctly")


def test_negative_overpunch():
    """Verify all 10 negative overpunch characters decode correctly."""
    # } = -0, J = -1, K = -2, ..., R = -9
    # } maps digit 0 with negative sign: 00000001940 + 0 = 000000019400, negated = -194.00
    cases = [
        ("00000001940}", Decimal("-194.00")),   # } → -0 → -000000019400 → -194.00
        ("00000001940J", Decimal("-194.01")),   # J → -1
        ("00000001940K", Decimal("-194.02")),   # K → -2
        ("00000001940L", Decimal("-194.03")),   # L → -3
        ("00000001940M", Decimal("-194.04")),   # M → -4
        ("00000001940N", Decimal("-194.05")),   # N → -5
        ("00000001940O", Decimal("-194.06")),   # O → -6
        ("00000001940P", Decimal("-194.07")),   # P → -7
        ("00000001940Q", Decimal("-194.08")),   # Q → -8
        ("00000001940R", Decimal("-194.09")),   # R → -9
    ]
    for raw, expected in cases:
        result = decode_signed_zoned_decimal(raw, scale=2)
        assert result == expected, (
            f"NEGATIVE FAIL: decode('{raw}') = {result}, expected {expected}"
        )
    print("  PASS: All 10 negative overpunch characters decoded correctly")


def test_unsigned_digits():
    """Verify plain digit characters (no overpunch) are treated as positive."""
    cases = [
        ("000000019400", Decimal("194.00")),
        ("000000019401", Decimal("194.01")),
        ("000000019409", Decimal("194.09")),
    ]
    for raw, expected in cases:
        result = decode_signed_zoned_decimal(raw, scale=2)
        assert result == expected, (
            f"UNSIGNED FAIL: decode('{raw}') = {result}, expected {expected}"
        )
    print("  PASS: Unsigned digit inputs decoded correctly")


def test_zero_value():
    """Verify zero values decode to 0.00."""
    result = decode_signed_zoned_decimal("00000000000{", scale=2)
    assert result == Decimal("0"), f"ZERO FAIL: got {result}, expected 0"
    print("  PASS: Zero value decoded correctly")


def test_edge_cases():
    """Verify None, empty, and whitespace inputs return None."""
    assert decode_signed_zoned_decimal(None) is None, "None input should return None"
    assert decode_signed_zoned_decimal("") is None, "Empty string should return None"
    assert decode_signed_zoned_decimal("   ") is None, "Whitespace should return None"
    print("  PASS: Edge cases (None, empty, whitespace) return None")


def test_large_negative_balance():
    """Verify a large negative balance decodes correctly (e.g., -$99,999,999.99)."""
    # S9(10)V99 max negative: 9999999999.99
    # Raw: 99999999R9 — wait, the overpunch is on the LAST byte
    # 9999999999 + 99 decimal = 999999999999 digits, last byte R = -9
    raw = "9999999999R"  # 11 chars, but S9(10)V99 = 12 chars
    # Correct 12-char example: "99999999999R" → R = -9 → -999999999999 / 100 = -9999999999.99
    raw = "99999999999R"
    result = decode_signed_zoned_decimal(raw, scale=2)
    expected = Decimal("-9999999999.99")
    assert result == expected, (
        f"LARGE NEG FAIL: decode('{raw}') = {result}, expected {expected}"
    )
    print("  PASS: Large negative balance decoded correctly (-9999999999.99)")


def test_lookup_table_completeness():
    """Verify overpunch lookup tables cover all 10 digits (0-9) for both signs."""
    assert len(POSITIVE_OVERPUNCH) == 10, (
        f"Positive table has {len(POSITIVE_OVERPUNCH)} entries, expected 10"
    )
    assert len(NEGATIVE_OVERPUNCH) == 10, (
        f"Negative table has {len(NEGATIVE_OVERPUNCH)} entries, expected 10"
    )
    pos_digits = set(POSITIVE_OVERPUNCH.values())
    neg_digits = set(NEGATIVE_OVERPUNCH.values())
    expected_digits = {str(d) for d in range(10)}
    assert pos_digits == expected_digits, f"Positive table digits: {pos_digits}"
    assert neg_digits == expected_digits, f"Negative table digits: {neg_digits}"
    print("  PASS: Overpunch lookup tables are complete (10 entries each)")


def main():
    """Run all overpunch decoder tests."""
    print("=" * 60)
    print("SIGN-OVERPUNCH DECODER TEST SUITE")
    print("=" * 60)

    tests = [
        test_positive_overpunch,
        test_negative_overpunch,
        test_unsigned_digits,
        test_zero_value,
        test_edge_cases,
        test_large_negative_balance,
        test_lookup_table_completeness,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {e}")
            failed += 1

    print("")
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
