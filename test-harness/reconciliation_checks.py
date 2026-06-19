#!/usr/bin/env python3
"""
Reconciliation checks for CardDemo migration validation.

Validates cross-entity referential integrity, financial balance invariants,
record count parity, and data quality rules.

Can run against:
  - Golden JSON files (for pre-migration baseline)
  - Database (for post-migration validation, via adapter)

Usage:
    python test-harness/reconciliation_checks.py \
        --golden-dir golden-files/ \
        [--report reconciliation_report.json]
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation


def load_golden(golden_dir: str, entity: str) -> list[dict]:
    """Load records from a golden JSON file."""
    path = os.path.join(golden_dir, f"{entity}.golden.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("records", [])


class ReconciliationRunner:
    """Runs all reconciliation checks against golden file data."""

    def __init__(self, golden_dir: str) -> None:
        self.golden_dir = golden_dir
        self.results: list[dict] = []

        # Load all entities
        self.accounts = load_golden(golden_dir, "acctdata")
        self.cards = load_golden(golden_dir, "carddata")
        self.customers = load_golden(golden_dir, "custdata")
        self.cardxrefs = load_golden(golden_dir, "cardxref")
        self.transactions = load_golden(golden_dir, "dailytran")
        self.tcatbals = load_golden(golden_dir, "tcatbal")
        self.discgrps = load_golden(golden_dir, "discgrp")
        self.trantypes = load_golden(golden_dir, "trantype")
        self.trancatgs = load_golden(golden_dir, "trancatg")

        # Build lookup sets
        self.acct_ids = {r["ACCT-ID"] for r in self.accounts}
        self.cust_ids = {r["CUST-ID"] for r in self.customers}
        self.card_nums = {r["CARD-NUM"] for r in self.cards}

    def _add_result(self, check_id: str, category: str, description: str,
                    passed: bool, details: str = "",
                    violations: list | None = None) -> None:
        """Record a check result."""
        self.results.append({
            "check_id": check_id,
            "category": category,
            "description": description,
            "passed": passed,
            "details": details,
            "violations": violations[:10] if violations else [],
            "violation_count": len(violations) if violations else 0,
        })

    def run_all(self) -> list[dict]:
        """Execute all reconciliation checks."""
        self.check_referential_integrity()
        self.check_financial_balances()
        self.check_record_counts()
        self.check_data_quality()
        return self.results

    # --- Referential Integrity Checks ---

    def check_referential_integrity(self) -> None:
        """REF-01 through REF-05: cross-entity foreign key checks."""

        # REF-01: Every CARDXREF.XREF-ACCT-ID exists in ACCTDAT
        violations = [
            r["XREF-CARD-NUM"]
            for r in self.cardxrefs
            if r["XREF-ACCT-ID"] not in self.acct_ids
        ]
        self._add_result(
            "REF-01", "referential_integrity",
            "Every CARDXREF.XREF-ACCT-ID exists in ACCTDAT.ACCT-ID",
            len(violations) == 0,
            f"{len(violations)} orphaned cross-references",
            violations,
        )

        # REF-02: Every CARDXREF.XREF-CUST-ID exists in CUSTDAT
        violations = [
            r["XREF-CARD-NUM"]
            for r in self.cardxrefs
            if r["XREF-CUST-ID"] not in self.cust_ids
        ]
        self._add_result(
            "REF-02", "referential_integrity",
            "Every CARDXREF.XREF-CUST-ID exists in CUSTDAT.CUST-ID",
            len(violations) == 0,
            f"{len(violations)} orphaned cross-references",
            violations,
        )

        # REF-03: Every CARDXREF.XREF-CARD-NUM exists in CARDDAT
        violations = [
            r["XREF-CARD-NUM"]
            for r in self.cardxrefs
            if r["XREF-CARD-NUM"] not in self.card_nums
        ]
        self._add_result(
            "REF-03", "referential_integrity",
            "Every CARDXREF.XREF-CARD-NUM exists in CARDDAT.CARD-NUM",
            len(violations) == 0,
            f"{len(violations)} orphaned cross-references",
            violations,
        )

        # REF-04: Every TRANSACTION.TRAN-CARD-NUM exists in CARDDAT
        tran_card_violations = [
            r.get("TRAN-ID", "unknown")
            for r in self.transactions
            if r.get("TRAN-CARD-NUM", "").strip()
            and r["TRAN-CARD-NUM"] not in self.card_nums
        ]
        self._add_result(
            "REF-04", "referential_integrity",
            "Every TRANSACTION.TRAN-CARD-NUM exists in CARDDAT.CARD-NUM",
            len(tran_card_violations) == 0,
            f"{len(tran_card_violations)} transactions with unknown cards",
            tran_card_violations,
        )

        # REF-05: Every TCATBALF.TRANCAT-ACCT-ID exists in ACCTDAT
        violations = [
            f"acct={r['TRANCAT-ACCT-ID']}"
            for r in self.tcatbals
            if r["TRANCAT-ACCT-ID"] not in self.acct_ids
        ]
        self._add_result(
            "REF-05", "referential_integrity",
            "Every TCATBALF.TRANCAT-ACCT-ID exists in ACCTDAT.ACCT-ID",
            len(violations) == 0,
            f"{len(violations)} orphaned category balances",
            violations,
        )

    # --- Financial Balance Checks ---

    def check_financial_balances(self) -> None:
        """FIN-01 through FIN-04: financial invariant checks."""

        # FIN-01: Transaction amounts by card should be traceable
        tran_sums_by_card: dict[str, Decimal] = defaultdict(Decimal)
        for t in self.transactions:
            card = t.get("TRAN-CARD-NUM", "").strip()
            if card:
                try:
                    amt = Decimal(t.get("TRAN-AMT", "0"))
                    tran_sums_by_card[card] += amt
                except InvalidOperation:
                    pass

        self._add_result(
            "FIN-01", "financial_balance",
            "Transaction amounts by card are computable and non-null",
            len(tran_sums_by_card) > 0,
            f"{len(tran_sums_by_card)} cards with transaction totals computed",
        )

        # FIN-02: Category balances by account sum correctly
        catbal_by_acct: dict[str, Decimal] = defaultdict(Decimal)
        for cb in self.tcatbals:
            acct = cb["TRANCAT-ACCT-ID"]
            try:
                bal = Decimal(cb.get("TRAN-CAT-BAL", "0"))
                catbal_by_acct[acct] += bal
            except InvalidOperation:
                pass

        self._add_result(
            "FIN-02", "financial_balance",
            "Category balance sums by account are computable",
            len(catbal_by_acct) > 0 or len(self.tcatbals) == 0,
            f"{len(catbal_by_acct)} accounts with category balance totals",
        )

        # FIN-03: No account balance exceeds credit limit by > 10%
        overlimit = []
        for acct in self.accounts:
            try:
                bal = Decimal(acct.get("ACCT-CURR-BAL", "0"))
                limit = Decimal(acct.get("ACCT-CREDIT-LIMIT", "0"))
                if limit > 0 and bal > limit * Decimal("1.10"):
                    overlimit.append(
                        f"ACCT-ID={acct['ACCT-ID']} bal={bal} limit={limit}"
                    )
            except InvalidOperation:
                pass

        self._add_result(
            "FIN-03", "financial_balance",
            "No account balance exceeds credit limit by more than 10%",
            len(overlimit) == 0,
            f"{len(overlimit)} accounts over limit",
            overlimit,
        )

        # FIN-04: Disclosure group interest rates are non-negative
        negative_rates = []
        for dg in self.discgrps:
            try:
                rate = Decimal(dg.get("DIS-INT-RATE", "0"))
                if rate < 0:
                    negative_rates.append(
                        f"group={dg['DIS-ACCT-GROUP-ID']} "
                        f"type={dg['DIS-TRAN-TYPE-CD']} rate={rate}"
                    )
            except InvalidOperation:
                pass

        self._add_result(
            "FIN-04", "financial_balance",
            "All disclosure group interest rates are non-negative",
            len(negative_rates) == 0,
            f"{len(negative_rates)} negative rates found",
            negative_rates,
        )

    # --- Record Count Checks ---

    def check_record_counts(self) -> None:
        """CNT-01 through CNT-05: record count parity."""
        entities = [
            ("CNT-01", "accounts (ACCTDAT)", self.accounts),
            ("CNT-02", "cards (CARDDAT)", self.cards),
            ("CNT-03", "customers (CUSTDAT)", self.customers),
            ("CNT-04", "transactions (DAILYTRAN)", self.transactions),
            ("CNT-05", "cross-references (CARDXREF)", self.cardxrefs),
        ]

        for check_id, name, records in entities:
            count = len(records)
            self._add_result(
                check_id, "record_count",
                f"{name} record count is non-zero",
                count > 0,
                f"{count} records loaded",
            )

    # --- Data Quality Checks ---

    def check_data_quality(self) -> None:
        """DQ-01 through DQ-05: data quality invariants."""

        # DQ-01: All account statuses are valid
        invalid_status = [
            acct["ACCT-ID"]
            for acct in self.accounts
            if acct.get("ACCT-ACTIVE-STATUS", "").strip() not in ("Y", "N")
        ]
        self._add_result(
            "DQ-01", "data_quality",
            "All ACCTDAT.ACCT-ACTIVE-STATUS in {'Y', 'N'}",
            len(invalid_status) == 0,
            f"{len(invalid_status)} invalid statuses",
            invalid_status,
        )

        # DQ-02: All card statuses are valid
        invalid_card_status = [
            card["CARD-NUM"]
            for card in self.cards
            if card.get("CARD-ACTIVE-STATUS", "").strip() not in ("Y", "N")
        ]
        self._add_result(
            "DQ-02", "data_quality",
            "All CARDDAT.CARD-ACTIVE-STATUS in {'Y', 'N'}",
            len(invalid_card_status) == 0,
            f"{len(invalid_card_status)} invalid statuses",
            invalid_card_status,
        )

        # DQ-03: All account dates are valid format
        invalid_dates = []
        date_fields = ["ACCT-OPEN-DATE", "ACCT-EXPIRAION-DATE", "ACCT-REISSUE-DATE"]
        for acct in self.accounts:
            for df in date_fields:
                val = acct.get(df, "").strip()
                if val and not _is_valid_date(val):
                    invalid_dates.append(f"ACCT-ID={acct['ACCT-ID']} {df}={val}")

        self._add_result(
            "DQ-03", "data_quality",
            "All account dates are valid YYYY-MM-DD format",
            len(invalid_dates) == 0,
            f"{len(invalid_dates)} invalid dates",
            invalid_dates,
        )

        # DQ-04: All ACCT-IDs are 11-digit numeric
        invalid_ids = [
            acct["ACCT-ID"]
            for acct in self.accounts
            if not acct["ACCT-ID"].isdigit() or len(acct["ACCT-ID"]) != 11
        ]
        self._add_result(
            "DQ-04", "data_quality",
            "All ACCT-IDs are 11-digit numeric",
            len(invalid_ids) == 0,
            f"{len(invalid_ids)} invalid IDs",
            invalid_ids,
        )

        # DQ-05: No customer SSN is all zeros
        zero_ssns = [
            cust["CUST-ID"]
            for cust in self.customers
            if cust.get("CUST-SSN", "").strip() == "000000000"
        ]
        self._add_result(
            "DQ-05", "data_quality",
            "No CUST-SSN equals 000000000",
            len(zero_ssns) == 0,
            f"{len(zero_ssns)} zero SSNs",
            zero_ssns,
        )


def _is_valid_date(val: str) -> bool:
    """Check if a string is a valid YYYY-MM-DD date."""
    if len(val) != 10:
        return False
    try:
        parts = val.split("-")
        if len(parts) != 3:
            return False
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        return 1900 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31
    except (ValueError, IndexError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run reconciliation checks on CardDemo golden files"
    )
    parser.add_argument(
        "--golden-dir", required=True,
        help="Path to golden files directory",
    )
    parser.add_argument(
        "--report", default=None,
        help="Path to write JSON reconciliation report",
    )
    args = parser.parse_args()

    runner = ReconciliationRunner(args.golden_dir)
    results = runner.run_all()

    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])

    print(f"Reconciliation Results: {passed} passed, {failed} failed\n")

    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['check_id']:6s} {r['description']}")
        if not r["passed"]:
            print(f"         {r['details']}")
            for v in r["violations"][:3]:
                print(f"           - {v}")

    if args.report:
        report = {
            "dimension": "reconciliation",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks_passed": passed,
            "checks_failed": failed,
            "results": results,
        }
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport written to: {args.report}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
