# CardDemo Reconciliation Checks

> Per-job validation specifications for verifying data integrity during
> and after migration from COBOL/VSAM to the modernized platform.

---

## Check Categories

| Category                | Check IDs  | Purpose                                              | Run Frequency |
|:------------------------|:-----------|:-----------------------------------------------------|:--------------|
| Referential Integrity   | REF-01–05  | Foreign key relationships preserved across entities  | After every data load |
| Financial Balances      | FIN-01–05  | Monetary invariants hold ($0.00 tolerance)           | Nightly during parallel run |
| Record Counts           | CNT-01–06  | Source and target record counts match exactly         | After every data load |
| Data Quality            | DQ-01–05   | Business rule constraints satisfied                  | After every data load |
| Batch Job Validation    | JOB-01–08  | Per-job pre/post-condition checks                    | Per batch execution |

---

## 1. Referential Integrity Checks

### REF-01: Card Cross-Reference → Account

| Attribute    | Value                                                        |
|:-------------|:-------------------------------------------------------------|
| **Check**    | Every `CARDXREF.XREF-ACCT-ID` exists in `ACCTDAT.ACCT-ID`  |
| **Source**   | VSAM: CARDXREF, ACCTDAT — Target: `card_cross_references`, `accounts` |
| **SQL**      | `SELECT x.xref_card_num FROM card_cross_references x LEFT JOIN accounts a ON x.xref_acct_id = a.account_id WHERE a.account_id IS NULL` |
| **Tolerance**| 0 violations                                                 |
| **Severity** | Critical — orphaned cross-references break card-to-account lookups |

### REF-02: Card Cross-Reference → Customer

| Attribute    | Value                                                        |
|:-------------|:-------------------------------------------------------------|
| **Check**    | Every `CARDXREF.XREF-CUST-ID` exists in `CUSTDAT.CUST-ID`  |
| **SQL**      | `SELECT x.xref_card_num FROM card_cross_references x LEFT JOIN customers c ON x.xref_cust_id = c.customer_id WHERE c.customer_id IS NULL` |
| **Tolerance**| 0 violations                                                 |
| **Severity** | Critical — orphaned cross-references break card-to-customer lookups |

### REF-03: Card Cross-Reference → Card

| Attribute    | Value                                                        |
|:-------------|:-------------------------------------------------------------|
| **Check**    | Every `CARDXREF.XREF-CARD-NUM` exists in `CARDDAT.CARD-NUM` |
| **SQL**      | `SELECT x.xref_card_num FROM card_cross_references x LEFT JOIN cards c ON x.xref_card_num = c.card_number WHERE c.card_number IS NULL` |
| **Tolerance**| 0 violations                                                 |
| **Severity** | Critical — cross-reference without a card record is data corruption |

### REF-04: Transaction → Card

| Attribute    | Value                                                        |
|:-------------|:-------------------------------------------------------------|
| **Check**    | Every `TRANSACT.TRAN-CARD-NUM` exists in `CARDDAT.CARD-NUM` |
| **SQL**      | `SELECT t.transaction_id FROM transactions t LEFT JOIN cards c ON t.card_number = c.card_number WHERE c.card_number IS NULL AND t.card_number IS NOT NULL` |
| **Tolerance**| 0 violations                                                 |
| **Severity** | High — transactions referencing unknown cards indicate posting errors |

### REF-05: Category Balance → Account

| Attribute    | Value                                                        |
|:-------------|:-------------------------------------------------------------|
| **Check**    | Every `TCATBALF.TRANCAT-ACCT-ID` exists in `ACCTDAT.ACCT-ID` |
| **SQL**      | `SELECT cb.account_id FROM category_balances cb LEFT JOIN accounts a ON cb.account_id = a.account_id WHERE a.account_id IS NULL` |
| **Tolerance**| 0 violations                                                 |
| **Severity** | High — orphaned category balances affect interest calculation |

---

## 2. Financial Balance Checks

### FIN-01: Transaction Amount Summation

| Attribute    | Value                                                        |
|:-------------|:-------------------------------------------------------------|
| **Check**    | Sum of posted transaction amounts by account matches net balance change |
| **COBOL**    | After CBTRN02C: `SUM(TRAN-AMT) GROUP BY ACCT-ID` via CARDXREF lookup |
| **SQL**      | `SELECT a.account_id, a.current_balance, SUM(t.amount) as tran_total FROM accounts a JOIN card_cross_references x ON a.account_id = x.xref_acct_id JOIN transactions t ON x.xref_card_num = t.card_number GROUP BY a.account_id` |
| **Tolerance**| $0.00 per account                                            |
| **Severity** | Critical — balance mismatch means money was created or lost  |

### FIN-02: Category Balance Cross-Check

| Attribute    | Value                                                        |
|:-------------|:-------------------------------------------------------------|
| **Check**    | Sum of `TCATBALF` balances per account = sum of transactions by category for that account |
| **SQL**      | `SELECT cb.account_id, cb.type_code, cb.cat_code, cb.balance, SUM(t.amount) as computed FROM category_balances cb JOIN transactions t ON ... WHERE cb.balance != SUM(t.amount) GROUP BY cb.account_id, cb.type_code, cb.cat_code` |
| **Tolerance**| $0.00 per category per account                               |
| **Severity** | Critical — category balance drives interest calculation in CBACT04C |

### FIN-03: Account Balance vs Credit Limit

| Attribute    | Value                                                        |
|:-------------|:-------------------------------------------------------------|
| **Check**    | No `ACCTDAT.ACCT-CURR-BAL` exceeds `ACCT-CREDIT-LIMIT` by more than 10% |
| **SQL**      | `SELECT account_id, current_balance, credit_limit FROM accounts WHERE current_balance > credit_limit * 1.10` |
| **Tolerance**| 10% (accounts may temporarily exceed limit due to pending transactions) |
| **Severity** | Medium — indicates possible posting anomaly                  |

### FIN-04: Interest Rate Validity

| Attribute    | Value                                                        |
|:-------------|:-------------------------------------------------------------|
| **Check**    | All `DISCGRP.DIS-INT-RATE` values are non-negative           |
| **SQL**      | `SELECT * FROM disclosure_groups WHERE interest_rate < 0`    |
| **Tolerance**| 0 violations                                                 |
| **Severity** | High — negative interest rate would credit instead of debit  |

### FIN-05: Interest Calculation Verification

| Attribute    | Value                                                        |
|:-------------|:-------------------------------------------------------------|
| **Check**    | Computed interest per account matches: `DISCGRP.DIS-INT-RATE × TCATBALF.TRAN-CAT-BAL / 12` |
| **Legacy**   | CBACT04C computes and applies interest; result visible in `ACCTDAT.ACCT-CURR-BAL` change |
| **SQL**      | `SELECT a.account_id, SUM(dg.interest_rate * cb.balance / 12) as expected_interest FROM accounts a JOIN disclosure_groups dg ON a.group_id = dg.group_id JOIN category_balances cb ON a.account_id = cb.account_id AND dg.type_code = cb.type_code AND dg.cat_code = cb.cat_code GROUP BY a.account_id` |
| **Tolerance**| $0.01 per account (rounding)                                 |
| **Severity** | Critical — interest miscalculation has direct revenue impact |
| **Note**     | Must use `BigDecimal` with `HALF_EVEN` rounding to match COBOL behavior |

---

## 3. Record Count Checks

### CNT-01 through CNT-05: Entity Parity

| Check ID | Entity             | Source (VSAM)     | Target (DB Table)          |
|:---------|:-------------------|:------------------|:---------------------------|
| CNT-01   | Accounts           | ACCTDAT           | `accounts`                 |
| CNT-02   | Cards              | CARDDAT           | `cards`                    |
| CNT-03   | Customers          | CUSTDAT           | `customers`                |
| CNT-04   | Transactions       | TRANSACT          | `transactions`             |
| CNT-05   | Cross-References   | CARDXREF          | `card_cross_references`    |

**Tolerance:** 0 (exact match required)

**Verification query:**
```sql
SELECT 'accounts' as entity, COUNT(*) FROM accounts
UNION ALL SELECT 'cards', COUNT(*) FROM cards
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'transactions', COUNT(*) FROM transactions
UNION ALL SELECT 'card_cross_references', COUNT(*) FROM card_cross_references;
```

### CNT-06: Daily Transaction Posting Count

| Attribute    | Value                                                        |
|:-------------|:-------------------------------------------------------------|
| **Check**    | Number of DALYTRAN records processed = number of new TRANSACT records created by CBTRN02C |
| **Pre-run**  | `COUNT(*)` of TRANSACT before batch                          |
| **Post-run** | `COUNT(*)` of TRANSACT after batch − before = `COUNT(*)` of DALYTRAN |
| **Tolerance**| 0 (every daily transaction must be posted)                   |
| **Severity** | Critical — missing transactions means lost payments          |

---

## 4. Data Quality Checks

### DQ-01: Account Status Values

| Attribute    | Value                                                        |
|:-------------|:-------------------------------------------------------------|
| **Check**    | All `ACCTDAT.ACCT-ACTIVE-STATUS` ∈ `{'Y', 'N'}`            |
| **SQL**      | `SELECT * FROM accounts WHERE active_status NOT IN ('Y', 'N')` |
| **Severity** | High — unknown status breaks conditional logic in all account programs |

### DQ-02: Card Status Values

| Attribute    | Value                                                        |
|:-------------|:-------------------------------------------------------------|
| **Check**    | All `CARDDAT.CARD-ACTIVE-STATUS` ∈ `{'Y', 'N'}`            |
| **SQL**      | `SELECT * FROM cards WHERE active_status NOT IN ('Y', 'N')` |
| **Severity** | High — affects card authorization decisions                  |

### DQ-03: Date Format Validity

| Attribute    | Value                                                        |
|:-------------|:-------------------------------------------------------------|
| **Check**    | All date fields parse as valid `YYYY-MM-DD`                  |
| **Fields**   | `ACCT-OPEN-DATE`, `ACCT-EXPIRAION-DATE`, `ACCT-REISSUE-DATE`, `CARD-EXPIRAION-DATE`, `CUST-DOB-YYYY-MM-DD`, `TRAN-ORIG-TS`, `TRAN-PROC-TS` |
| **SQL**      | `SELECT * FROM accounts WHERE open_date IS NOT NULL AND open_date::text !~ '^\d{4}-\d{2}-\d{2}$'` |
| **Severity** | Medium — invalid dates break date arithmetic in CSUTLDTC     |

### DQ-04: Account ID Format

| Attribute    | Value                                                        |
|:-------------|:-------------------------------------------------------------|
| **Check**    | All `ACCT-ID` values are exactly 11 digits, zero-padded      |
| **SQL**      | `SELECT * FROM accounts WHERE account_id::text !~ '^\d{11}$'` |
| **Severity** | High — VSAM key lookup requires exact-length keys            |

### DQ-05: SSN Validity

| Attribute    | Value                                                        |
|:-------------|:-------------------------------------------------------------|
| **Check**    | No `CUST-SSN` equals `000000000` (invalid placeholder)      |
| **SQL**      | `SELECT * FROM customers WHERE ssn = '000000000'`           |
| **Severity** | Medium — indicates incomplete customer record                |

---

## 5. Per-Batch-Job Validation Specifications

### JOB-01: POSTTRAN (CBTRN02C — Transaction Posting)

| Phase         | Check                                                     |
|:--------------|:----------------------------------------------------------|
| **Pre-run**   | `COUNT(DALYTRAN)` > 0 (input exists)                      |
| **Pre-run**   | `COUNT(TRANSACT)` = N (baseline)                           |
| **Pre-run**   | Snapshot ACCTDAT balances for all accounts in DALYTRAN     |
| **Post-run**  | `COUNT(TRANSACT)` = N + `COUNT(DALYTRAN)`                 |
| **Post-run**  | For each account: new balance = old balance + SUM(posted transaction amounts) |
| **Post-run**  | TCATBALF updated for each category in posted transactions  |
| **Post-run**  | REF-04 passes (all new TRAN-CARD-NUMs exist in CARDDAT)   |
| **Post-run**  | FIN-01 passes (transaction sums match balance changes)     |

### JOB-02: INTCALC (CBACT04C — Interest Calculation)

| Phase         | Check                                                     |
|:--------------|:----------------------------------------------------------|
| **Pre-run**   | Snapshot ACCTDAT.ACCT-CURR-BAL for all accounts           |
| **Pre-run**   | Snapshot TCATBALF balances by account/type/category        |
| **Post-run**  | For each account: balance change = SUM(rate × category_balance / 12) |
| **Post-run**  | FIN-05 passes (computed interest matches actual change)    |
| **Post-run**  | TCATBALF updated with interest amounts per category        |
| **Post-run**  | No negative balances created (unless account was already negative) |

### JOB-03: CREASTMT (CBSTM03A — Statement Generation)

| Phase         | Check                                                     |
|:--------------|:----------------------------------------------------------|
| **Pre-run**   | TRANSACT has records for statement period                  |
| **Post-run**  | One statement file generated per account with transactions |
| **Post-run**  | Statement total matches SUM(TRAN-AMT) for that account and period |
| **Post-run**  | Customer name/address on statement matches CUSTDAT         |
| **Post-run**  | Opening/closing balance on statement matches ACCTDAT snapshots |

### JOB-04: TRANREPT (CBTRN03C — Transaction Report)

| Phase         | Check                                                     |
|:--------------|:----------------------------------------------------------|
| **Pre-run**   | DATEPARM file specifies valid date range                   |
| **Post-run**  | Report grand total matches SUM(TRAN-AMT) for date range   |
| **Post-run**  | Report account totals match SUM(TRAN-AMT) GROUP BY account |
| **Post-run**  | All transaction types in report exist in TRANTYPE           |
| **Post-run**  | All transaction categories in report exist in TRANCATG      |

### JOB-05: CBEXPORT (Data Export)

| Phase         | Check                                                     |
|:--------------|:----------------------------------------------------------|
| **Pre-run**   | Source file counts: CUSTDAT, ACCTDAT, CARDXREF, TRANSACT, CARDDAT |
| **Post-run**  | EXPORT file record count = SUM of all source file counts   |
| **Post-run**  | Record type distribution matches source counts             |
| **Post-run**  | Random sample: 10 records per type parsed and field-compared to source |

### JOB-06: CBIMPORT (Data Import)

| Phase         | Check                                                     |
|:--------------|:----------------------------------------------------------|
| **Pre-run**   | EXPORT file exists and is parseable                        |
| **Post-run**  | Target file counts match EXPORT record type counts         |
| **Post-run**  | REF-01 through REF-05 pass on imported data               |
| **Post-run**  | Random sample: 10 records per type field-compared to EXPORT source |
| **Post-run**  | ERROR file has 0 records (all imports succeeded)           |

### JOB-07: CLOSEFIL / OPENFIL (File Control)

| Phase         | Check                                                     |
|:--------------|:----------------------------------------------------------|
| **Pre-run**   | CICS region is active (for CLOSEFIL) or batch is complete (for OPENFIL) |
| **Post-run**  | CLOSEFIL: all VSAM files closed to CICS (CEMT status = CLOSED) |
| **Post-run**  | OPENFIL: all VSAM files reopened (CEMT status = OPEN, ENABLED) |
| **Post-run**  | CICS online transactions resume successfully               |

### JOB-08: COMBTRAN (Transaction Sort/Merge)

| Phase         | Check                                                     |
|:--------------|:----------------------------------------------------------|
| **Pre-run**   | Input files exist (DALYTRAN + existing TRANSACT subset)    |
| **Post-run**  | Output is sorted by TRAN-ID ascending                      |
| **Post-run**  | No records lost: output count = SUM of input counts        |
| **Post-run**  | No duplicate TRAN-IDs in output                            |

---

## 6. Baseline Validation Results

The test harness has been run against the provided ASCII sample data.
All 19 checks pass on the baseline dataset:

```
Reconciliation Results: 19 passed, 0 failed

  [PASS] REF-01 Every CARDXREF.XREF-ACCT-ID exists in ACCTDAT.ACCT-ID
  [PASS] REF-02 Every CARDXREF.XREF-CUST-ID exists in CUSTDAT.CUST-ID
  [PASS] REF-03 Every CARDXREF.XREF-CARD-NUM exists in CARDDAT.CARD-NUM
  [PASS] REF-04 Every TRANSACTION.TRAN-CARD-NUM exists in CARDDAT.CARD-NUM
  [PASS] REF-05 Every TCATBALF.TRANCAT-ACCT-ID exists in ACCTDAT.ACCT-ID
  [PASS] FIN-01 Transaction amounts by card are computable and non-null
  [PASS] FIN-02 Category balance sums by account are computable
  [PASS] FIN-03 No account balance exceeds credit limit by more than 10%
  [PASS] FIN-04 All disclosure group interest rates are non-negative
  [PASS] CNT-01 accounts (ACCTDAT) record count is non-zero
  [PASS] CNT-02 cards (CARDDAT) record count is non-zero
  [PASS] CNT-03 customers (CUSTDAT) record count is non-zero
  [PASS] CNT-04 transactions (DAILYTRAN) record count is non-zero
  [PASS] CNT-05 cross-references (CARDXREF) record count is non-zero
  [PASS] DQ-01  All ACCTDAT.ACCT-ACTIVE-STATUS in {'Y', 'N'}
  [PASS] DQ-02  All CARDDAT.CARD-ACTIVE-STATUS in {'Y', 'N'}
  [PASS] DQ-03  All account dates are valid YYYY-MM-DD format
  [PASS] DQ-04  All ACCT-IDs are 11-digit numeric
  [PASS] DQ-05  No CUST-SSN equals 000000000
```

**Dataset summary:**
- 50 accounts, 50 cards, 50 customers, 50 cross-references
- 300 daily transactions, 50 category balances, 51 disclosure groups
- 7 transaction types, 18 transaction categories
- Total: 626 records across 9 entities

---

## 7. Running the Checks

### Against Golden Files (Pre-Migration Baseline)

```bash
# Generate golden files from ASCII data
python test-harness/generate_golden_files.py

# Run reconciliation checks
python test-harness/reconciliation_checks.py \
  --golden-dir golden-files/ \
  --report reconciliation_report.json
```

### Against Modernized Database (Post-Migration)

Extend `reconciliation_checks.py` with a database adapter:

```python
# Example: PostgreSQL adapter
import psycopg2

class DatabaseReconciliationRunner(ReconciliationRunner):
    def __init__(self, db_connection_string: str) -> None:
        self.conn = psycopg2.connect(db_connection_string)
        # Load from database instead of golden files
        self.accounts = self._query("SELECT * FROM accounts")
        self.cards = self._query("SELECT * FROM cards")
        # ... etc
```

### Against Both (Parallel-Run Comparison)

```bash
# Compare golden (legacy) with database (modern)
python test-harness/reconciliation_checks.py \
  --golden-dir golden-files/ \
  --report legacy_baseline.json

python test-harness/reconciliation_checks.py \
  --db-url postgresql://host/carddemo \
  --report modern_state.json

# Diff the two reports
python test-harness/compare_golden_files.py \
  --golden legacy_baseline.json \
  --actual modern_state.json
```
