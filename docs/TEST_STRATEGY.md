# CardDemo Migration Test Strategy

> Four-dimensional testing approach for validating functional equivalence
> between the legacy COBOL/CICS application and the modernized target system.

---

## Overview

Migration testing must prove that the new system produces **identical business
outcomes** to the legacy system for every input scenario. This strategy covers
four complementary testing dimensions:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Migration Test Dimensions                         │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────┐│
│  │  1. Golden    │  │ 2. Differ-   │  │ 3. Reconcil- │  │4. Con-  ││
│  │     File      │  │    ential    │  │    iation     │  │  tract  ││
│  │              │  │              │  │              │  │         ││
│  │ Known inputs │  │ Same input → │  │ Aggregate    │  │ API     ││
│  │ → expected   │  │ old vs new   │  │ invariant    │  │ schema  ││
│  │ outputs      │  │ output diff  │  │ checks       │  │ tests   ││
│  │              │  │              │  │              │  │         ││
│  │ Unit-level   │  │ Integration  │  │ System-level │  │ Inter-  ││
│  │ correctness  │  │ parity       │  │ integrity    │  │ service ││
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────┘│
│                                                                     │
│  Runs: per-commit    Runs: nightly      Runs: nightly    Runs: per ││
│        CI pipeline         parallel run       parallel     commit  ││
└─────────────────────────────────────────────────────────────────────┘
```

---

## Dimension 1: Golden-File Testing

### Purpose
Verify that the modernized parser/service produces **exact JSON output** from
known ASCII input data files. Golden files are the ground truth — they
represent what the legacy system's data looks like when correctly parsed.

### Approach

1. **Parse** each ASCII data file (`app/data/ASCII/*.txt`) using the copybook
   layout definitions from `app/cpy/*.cpy`
2. **Produce** structured JSON files (`golden-files/*.json`) with typed fields
3. **Store** golden files in version control as immutable test fixtures
4. **Assert** in CI that the modernized parser produces byte-identical JSON

### Golden File Inventory

| Source File       | Copybook  | Record Length | Records | Golden File              |
|:------------------|:----------|:-------------|--------:|:-------------------------|
| acctdata.txt      | CVACT01Y  | 300 bytes    |      50 | acctdata.golden.json     |
| carddata.txt      | CVACT02Y  | 150 bytes    |      50 | carddata.golden.json     |
| custdata.txt      | CVCUS01Y  | 500 bytes    |      50 | custdata.golden.json     |
| cardxref.txt      | CVACT03Y  | 50 bytes     |      50 | cardxref.golden.json     |
| dailytran.txt     | CVTRA05Y  | 350 bytes    |     300 | dailytran.golden.json    |
| tcatbal.txt       | CVTRA01Y  | 50 bytes     |      50 | tcatbal.golden.json      |
| discgrp.txt       | CVTRA02Y  | 50 bytes     |      51 | discgrp.golden.json      |
| trantype.txt      | CVTRA03Y  | 60 bytes     |       7 | trantype.golden.json     |
| trancatg.txt      | CVTRA04Y  | 60 bytes     |      18 | trancatg.golden.json     |

### Signed Numeric Handling

The ASCII data files use **EBCDIC zoned-decimal overpunch** encoding for
signed fields (`PIC S9(n)V99`). The last digit of a signed field encodes
both the digit value and the sign:

| Char | Digit | Sign     | Char | Digit | Sign     |
|:----:|:-----:|:---------|:----:|:-----:|:---------|
| `{`  | 0     | Positive | `}`  | 0     | Negative |
| `A`  | 1     | Positive | `J`  | 1     | Negative |
| `B`  | 2     | Positive | `K`  | 2     | Negative |
| `C`  | 3     | Positive | `L`  | 3     | Negative |
| `D`  | 4     | Positive | `M`  | 4     | Negative |
| `E`  | 5     | Positive | `N`  | 5     | Negative |
| `F`  | 6     | Positive | `O`  | 6     | Negative |
| `G`  | 7     | Positive | `P`  | 7     | Negative |
| `H`  | 8     | Positive | `Q`  | 8     | Negative |
| `I`  | 9     | Positive | `R`  | 9     | Negative |

Example: `00000001940{` for `PIC S9(10)V99` → `+0000001940.00` → `1940.00`

### Test Execution

```bash
# Generate golden files from ASCII data (one-time, stored in VCS)
python test-harness/generate_golden_files.py

# Validate modernized parser produces identical output
python test-harness/compare_golden_files.py \
  --golden golden-files/ \
  --actual <modernized-output-dir>/
```

### Pass Criteria
- Zero field-level differences between golden and actual output
- All signed numeric fields decode to identical decimal values
- All FILLER bytes are excluded from comparison
- Record counts match exactly

---

## Dimension 2: Differential Testing

### Purpose
Run the **same transaction** through both old (COBOL/CICS) and new systems,
capture outputs, and diff. This validates end-to-end functional parity for
live operations.

### Approach

```
                     ┌──────────────────┐
                     │  Test Scenario   │
                     │  (input data)    │
                     └────────┬─────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            ┌──────────────┐    ┌──────────────┐
            │ Legacy CICS  │    │  New Service  │
            │  (COBOL)     │    │  (Java/etc)   │
            └──────┬───────┘    └──────┬───────┘
                   │                   │
                   ▼                   ▼
            ┌──────────────┐    ┌──────────────┐
            │ Output A     │    │ Output B     │
            │ (VSAM state) │    │ (DB state)   │
            └──────┬───────┘    └──────┬───────┘
                   │                   │
                   └─────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │  Differential    │
                    │  Comparator      │
                    │                  │
                    │  Field-by-field  │
                    │  diff report     │
                    └──────────────────┘
```

### Test Scenarios by Functional Area

| Area                  | Scenario                                              | Input                                     | Compare                               |
|:----------------------|:------------------------------------------------------|:------------------------------------------|:--------------------------------------|
| Account View          | View account details                                  | ACCT-ID                                   | All account fields                    |
| Account Update        | Update balance, limit, dates                          | ACCT-ID + changed fields                  | ACCTDAT record before/after           |
| Card List             | Browse cards by account                               | ACCT-ID, page direction                   | Card list order and content           |
| Card Update           | Update card status                                    | CARD-NUM + changed fields                 | CARDDAT record before/after           |
| Transaction List      | Browse transactions                                   | TRAN-ID range, page direction             | Transaction list order and content    |
| Transaction Add       | Create new transaction                                | Card, amount, merchant, type              | New TRANSACT record + generated ID    |
| Bill Payment          | Process payment                                       | ACCT-ID, amount                           | ACCTDAT balance + new TRANSACT record |
| Transaction Posting   | Nightly batch posting                                 | DALYTRAN file                             | TRANSACT, ACCTDAT, TCATBALF deltas    |
| Interest Calculation  | Monthly interest calc                                 | Full ACCTDAT + DISCGRP                    | ACCTDAT balance changes per account   |
| User CRUD             | Add/update/delete user                                | User data                                 | USRSEC record state                   |
| Statement Generation  | Generate account statement                            | Date range + account                      | Statement content (field-by-field)    |
| Transaction Report    | Generate transaction report                           | Date range                                | Report totals and detail lines        |

### Comparison Rules

| Field Type        | Comparison Method                                        |
|:------------------|:---------------------------------------------------------|
| Alphanumeric      | Exact string match (trailing spaces trimmed)             |
| Zoned decimal     | Parse to BigDecimal; compare with scale(2)               |
| Packed decimal    | Parse to BigDecimal; compare with scale(2)               |
| Date fields       | Parse both as ISO-8601; compare date values              |
| Timestamps        | Parse both; allow ±1 second tolerance for PROC-TS        |
| FILLER            | Skip — not compared                                      |
| Generated IDs     | Compare format/structure, not exact value                |

---

## Dimension 3: Reconciliation Testing

### Purpose
Validate **aggregate invariants** that must hold true across the entire
database after any batch run or migration operation. These catch systemic
errors that field-level comparison might miss.

### Invariant Categories

#### 3A: Cross-Entity Referential Integrity

| Check ID | Invariant                                                          | SQL Equivalent                                                  |
|:---------|:-------------------------------------------------------------------|:----------------------------------------------------------------|
| REF-01   | Every CARDXREF.XREF-ACCT-ID exists in ACCTDAT.ACCT-ID             | `SELECT ... FROM cardxref LEFT JOIN accounts WHERE acct_id IS NULL` |
| REF-02   | Every CARDXREF.XREF-CUST-ID exists in CUSTDAT.CUST-ID             | `SELECT ... FROM cardxref LEFT JOIN customers WHERE cust_id IS NULL` |
| REF-03   | Every CARDXREF.XREF-CARD-NUM exists in CARDDAT.CARD-NUM           | `SELECT ... FROM cardxref LEFT JOIN cards WHERE card_num IS NULL` |
| REF-04   | Every TRANSACT.TRAN-CARD-NUM exists in CARDDAT.CARD-NUM            | `SELECT ... FROM transactions LEFT JOIN cards WHERE card_num IS NULL` |
| REF-05   | Every TCATBALF.TRANCAT-ACCT-ID exists in ACCTDAT.ACCT-ID          | `SELECT ... FROM category_balances LEFT JOIN accounts WHERE acct_id IS NULL` |

#### 3B: Financial Balance Invariants

| Check ID | Invariant                                                          | Tolerance |
|:---------|:-------------------------------------------------------------------|:----------|
| FIN-01   | Sum of TRANSACT amounts by account = net of debits/credits on ACCTDAT | $0.00  |
| FIN-02   | Sum of TCATBALF balances by account = ACCTDAT current cycle totals | $0.00     |
| FIN-03   | ACCTDAT.ACCT-CURR-BAL = opening balance + credits − debits        | $0.00     |
| FIN-04   | No ACCTDAT.ACCT-CURR-BAL exceeds ACCTDAT.ACCT-CREDIT-LIMIT by > 10% | 10%    |
| FIN-05   | Interest calculated matches DISCGRP rate × TCATBALF balance / 12  | $0.01     |

#### 3C: Record Count Invariants

| Check ID | Invariant                                                          |
|:---------|:-------------------------------------------------------------------|
| CNT-01   | Count of ACCTDAT records = count of accounts in target DB          |
| CNT-02   | Count of CARDDAT records = count of cards in target DB             |
| CNT-03   | Count of CUSTDAT records = count of customers in target DB         |
| CNT-04   | Count of TRANSACT records = count of transactions in target DB     |
| CNT-05   | Count of CARDXREF records = count of cross-references in target DB |
| CNT-06   | Count of DALYTRAN records processed = count of new TRANSACT records posted |

#### 3D: Data Quality Invariants

| Check ID | Invariant                                                          |
|:---------|:-------------------------------------------------------------------|
| DQ-01    | All ACCTDAT.ACCT-ACTIVE-STATUS ∈ {'Y', 'N'}                       |
| DQ-02    | All CARDDAT.CARD-ACTIVE-STATUS ∈ {'Y', 'N'}                       |
| DQ-03    | All dates are valid (parseable as YYYY-MM-DD)                      |
| DQ-04    | All ACCT-IDs are 11-digit numeric, no leading zeros trimmed        |
| DQ-05    | No CUST-SSN = 000000000 (invalid SSN)                              |

### Execution Schedule

| Phase          | Reconciliation Checks                   | Frequency      |
|:---------------|:----------------------------------------|:---------------|
| Data Migration | REF-01 to REF-05, CNT-01 to CNT-05     | After each load |
| Parallel Run   | All FIN-* checks                        | Nightly         |
| Post-Cutover   | All checks                              | Daily for 30 days, then weekly |

---

## Dimension 4: Contract Testing

### Purpose
Validate that the **API contracts** between modernized services match the
implicit contracts defined by the COBOL COMMAREA, copybook layouts, and
CICS file access patterns.

### Contract Sources

| Legacy Contract         | Modern Contract                      | Validation Method                    |
|:------------------------|:-------------------------------------|:-------------------------------------|
| COCOM01Y (COMMAREA)     | REST API request/response schemas    | OpenAPI schema validation            |
| CVACT01Y (Account rec)  | Account Service DTO                  | JSON Schema match to copybook layout |
| CVACT02Y (Card record)  | Card Service DTO                     | JSON Schema match to copybook layout |
| CVCUS01Y (Customer rec) | Customer Service DTO                 | JSON Schema match to copybook layout |
| CVTRA05Y (Transaction)  | Transaction Service DTO              | JSON Schema match to copybook layout |
| CSUSR01Y (User record)  | IdP user attributes                  | Attribute mapping test               |

### Contract Test Types

#### 4A: Schema Contract Tests

```python
# Verify that modernized Account DTO contains all fields from CVACT01Y
def test_account_dto_matches_copybook():
    copybook_fields = parse_copybook("CVACT01Y")  # 12 business fields
    dto_fields = get_dto_schema("AccountDTO")
    for field in copybook_fields:
        assert field.name in dto_fields, f"Missing field: {field.name}"
        assert field.type == dto_fields[field.name].type
```

#### 4B: Behavioral Contract Tests

| Test                            | Legacy Behavior                           | New Service Must...                    |
|:--------------------------------|:------------------------------------------|:---------------------------------------|
| Account read by ID              | CICS READ DATASET('ACCTDAT') RIDFLD(key)  | Return 200 with same fields            |
| Account not found               | CICS RESP = NOTFND                        | Return 404                             |
| Transaction add                 | WRITE to TRANSACT + auto-gen TRAN-ID      | POST returns 201 with generated ID     |
| Card browse by account          | STARTBR on CARDAIX → READNEXT             | GET with `?account_id=X&after=Y`       |
| User authentication             | READ USRSEC, compare SEC-USR-PWD          | POST /auth/token returns JWT           |
| Bill payment insufficient funds | ACCT-CURR-BAL < amount → error screen     | POST returns 400 with INSUFFICIENT_FUNDS |

#### 4C: Event Contract Tests

| Event                   | Schema Fields Required                              | Consumer(s)         |
|:------------------------|:----------------------------------------------------|:--------------------|
| TransactionPosted       | tranId, acctId, amount, typeCode, catCode, timestamp| Account Service     |
| AccountBalanceUpdated   | acctId, newBalance, creditLimit                     | Authorization Svc   |
| AuthorizationDecided    | authId, cardNum, approved, amount                   | Transaction Svc     |

---

## Test Infrastructure

### CI/CD Integration

```
┌──────────────────────────────────────────────────────────┐
│                  GitHub Actions Pipeline                   │
│                                                          │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Golden   │  │  Unit    │  │ Contract │  │ Build    │ │
│  │ File     │→ │  Tests   │→ │  Tests   │→ │ + Deploy │ │
│  │ Validate │  │          │  │          │  │          │ │
│  └─────────┘  └──────────┘  └──────────┘  └──────────┘ │
│       │                                         │        │
│       │            ┌──────────────┐              │        │
│       └───────────▶│ Differential │◀─────────────┘        │
│                    │ (nightly)    │                        │
│                    └──────┬───────┘                        │
│                           │                               │
│                    ┌──────▼───────┐                        │
│                    │ Reconciliation│                       │
│                    │ (nightly)    │                        │
│                    └──────────────┘                        │
└──────────────────────────────────────────────────────────┘
```

### Test Data Management

| Aspect                | Approach                                              |
|:----------------------|:------------------------------------------------------|
| Golden files          | Checked into `golden-files/` — immutable fixtures     |
| Differential test data| Subset of production data (anonymized)                |
| Reconciliation data   | Full parallel-run databases                           |
| Contract test data    | Minimal fixtures per test case                        |

### Reporting

All test results are written to standardized JSON reports:

```json
{
  "dimension": "golden-file",
  "timestamp": "2026-06-19T15:00:00Z",
  "entity": "acctdata",
  "records_compared": 50,
  "records_matched": 50,
  "records_failed": 0,
  "failures": []
}
```
