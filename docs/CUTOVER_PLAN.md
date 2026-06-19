# CardDemo Cutover Plan

> Phased migration sequence from lowest-risk to highest-risk, with entry/exit
> criteria, parallel-run strategy, and rollback procedures for each phase.

---

## Migration Principles

1. **Lowest risk first** — start with isolated, read-only, or non-financial modules
2. **Parallel run** — every phase runs old and new systems simultaneously with output comparison before cutover
3. **Reversible** — every phase has a documented rollback procedure
4. **Data sync** — bidirectional replication between VSAM and target DB during transition
5. **Feature parity** — no phase is complete until functional equivalence is verified
6. **Open-source stack** — PostgreSQL, Keycloak, RabbitMQ/Kafka, GitHub Actions for CI/CD

---

## Phase Overview

```
Phase 0        Phase 1         Phase 2         Phase 3         Phase 4
Foundation     Quick Wins      Core CRUD       Financial       Complex
(Infra)        (Low Risk)      (Medium Risk)   (High Risk)     Integration
                                                               
 ┌──────┐     ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
 │ ACL  │     │ Identity │    │ Card     │    │ Tran     │    │ Auth     │
 │ Data │     │ Ref Data │    │ Customer │    │ Posting  │    │ IMS/MQ   │
 │ Sync │     │ Reports  │    │ Account  │    │ Interest │    │ Batch    │
 │ CI/CD│     │ Nav      │    │          │    │ Billing  │    │ Decommis │
 └──────┘     └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                               
 Weeks 1-4     Weeks 5-12     Weeks 13-24    Weeks 25-36     Weeks 37-48
```

---

## Phase 0: Foundation (Weeks 1–4)

**Objective:** Establish infrastructure, CI/CD, data sync, and the anti-corruption layer (ACL).

### Deliverables

| # | Deliverable                        | Description                                                      |
|:--|:-----------------------------------|:-----------------------------------------------------------------|
| 1 | Target database schema             | PostgreSQL schema for all VSAM entities (see DOMAIN_DECOMPOSITION.md §6.1) |
| 2 | Data sync pipeline                 | Bidirectional replication: VSAM ↔ PostgreSQL via CDC or batch extract/load |
| 3 | Anti-corruption layer (ACL)        | CICS adapter translating COMMAREA ↔ REST/JSON; VSAM adapter mirroring records |
| 4 | CI/CD pipeline                     | GitHub Actions: build, test, deploy for each new microservice    |
| 5 | Monitoring & observability         | Prometheus + Grafana for new services; log aggregation (ELK/Loki)|
| 6 | Shared validation library          | Extract CSUTLDPY (date) + CSLKPCDY (phone/state/ZIP) into a reusable Java library |
| 7 | Test harness                       | Parallel-run comparator: captures CICS transaction outputs and new API responses, diffs results |

### Entry Criteria
- Modernization blueprint approved
- Target cloud/on-prem environment provisioned
- Development team onboarded

### Exit Criteria
- [ ] PostgreSQL schema deployed with all tables from VSAM mapping
- [ ] Data sync pipeline verified: VSAM→PostgreSQL load + incremental sync working
- [ ] ACL deployed and routing at least one test transaction through new stack
- [ ] CI/CD pipeline running: build + unit test + deploy for a sample service
- [ ] Shared validation library published with 100% test coverage
- [ ] Test harness capturing and comparing at least one CICS transaction pair

### Rollback
No production impact — all work is on the new stack. Remove by tearing down new infrastructure.

---

## Phase 1: Quick Wins — Low Risk (Weeks 5–12)

**Objective:** Migrate isolated, low-risk modules that don't touch financial data.

### 1A: Identity & Access Management (Weeks 5–7)

| Item                    | Detail                                                          |
|:------------------------|:----------------------------------------------------------------|
| **Programs replaced**   | COSGN00C, COUSR00C, COUSR01C, COUSR02C, COUSR03C               |
| **Strategy**            | Rewrite                                                          |
| **Target**              | Keycloak (open-source IdP) with RBAC                            |
| **Data migration**      | Export USRSEC → create Keycloak users (force password reset — existing passwords are plaintext) |
| **Integration**         | ACL intercepts COSGN00C sign-on → authenticates via Keycloak → populates COMMAREA with JWT claims |
| **Risk**                | Low — self-contained; no financial data                          |

**Parallel run:** Both USRSEC and Keycloak active. COSGN00C authenticates
against both; log discrepancies. New user CRUD operations write to both
USRSEC and Keycloak. After 2-week parallel run with zero discrepancies,
cut over to Keycloak-only.

**Rollback:** Re-enable USRSEC READ in COSGN00C; disable Keycloak integration.

### 1B: Reference Data Service (Weeks 6–8)

| Item                    | Detail                                                          |
|:------------------------|:----------------------------------------------------------------|
| **Programs replaced**   | COTRTLIC, COTRTUPC, COBTUPDT                                   |
| **Strategy**            | Refactor                                                         |
| **Target**              | Reference Data REST API (Spring Boot + PostgreSQL)              |
| **Data migration**      | Export DB2 TRAN_TYPE + TRAN_CAT → PostgreSQL tables; eliminate VSAM copies (TRANTYPE, TRANCATG) |
| **Integration**         | Batch programs (CBTRN03C) read from PostgreSQL via JDBC; online programs call REST API via ACL |
| **Risk**                | Low — read-heavy reference data with infrequent updates          |

**Parallel run:** New API and old DB2/VSAM serve simultaneously. All reads
compared for 1 week. Writes go to both. Cutover when parity confirmed.

**Rollback:** Re-enable DB2/VSAM access paths; disable REST API routing.

### 1C: Reporting & Statements (Weeks 8–12)

| Item                    | Detail                                                          |
|:------------------------|:----------------------------------------------------------------|
| **Programs replaced**   | CORPT00C, CBTRN03C, CBSTM03A, CBSTM03B                        |
| **Strategy**            | Rewrite                                                          |
| **Target**              | Reporting Service: database queries → HTML/PDF via Thymeleaf or JasperReports |
| **Data migration**      | Reports read from PostgreSQL (populated by Phase 0 data sync)   |
| **Integration**         | CORPT00C's TD queue write → replaced with REST API call to trigger report |
| **Risk**                | Low — output-only; no data mutation                              |

**Parallel run:** Generate reports from both old (CBTRN03C batch) and new
(Reporting Service) for 2 billing cycles. Diff outputs field-by-field.
GDG statement files compared with new S3/timestamped output.

**Rollback:** Re-enable JCL batch report jobs (TRANREPT, CREASTMT).

### 1D: Navigation (Weeks 5–6)

| Item                    | Detail                                                          |
|:------------------------|:----------------------------------------------------------------|
| **Programs replaced**   | COMEN01C, COADM01C                                              |
| **Strategy**            | Part of frontend build                                           |
| **Target**              | SPA frontend router (React/Angular) or API gateway routing       |
| **Data migration**      | Menu tables (COMEN02Y, COADM02Y) → frontend routing config      |
| **Risk**                | Low — pure navigation; no data access                            |

**Rollback:** Re-enable CICS menu programs.

### Phase 1 Exit Criteria
- [ ] All users authenticating via Keycloak for 2+ weeks with zero auth failures
- [ ] Reference data API serving all TRANTYPE/TRANCATG queries with 100% parity
- [ ] Reports generated from new system matching old system output for 2 billing cycles
- [ ] Navigation routing via new frontend/gateway for all menu paths
- [ ] Legacy programs (COSGN00C, COUSR*, COTRTLIC, COTRTUPC, CORPT00C, CBTRN03C, CBSTM03A/B) decommissioned

---

## Phase 2: Core CRUD — Medium Risk (Weeks 13–24)

**Objective:** Migrate the core entity management (Card, Customer, Account) — these
involve data mutation but not financial calculations.

### 2A: Card Service (Weeks 13–17)

| Item                    | Detail                                                          |
|:------------------------|:----------------------------------------------------------------|
| **Programs replaced**   | COCRDLIC, COCRDSLC, COCRDUPC, CBACT02C, CBACT03C               |
| **Strategy**            | Strangler Fig                                                    |
| **Target**              | Card Service REST API (Spring Boot + PostgreSQL)                |
| **Data migration**      | CARDDAT + CARDXREF → `cards` + `card_cross_references` tables   |
| **Integration**         | ACL intercepts CICS card transactions → routes to Card Service   |
| **Risk**                | Medium — COCRDUPC mutates card data; CVV handling is PCI-sensitive |

**Key steps:**
1. Deploy Card Service with read-only endpoints (replacing COCRDLIC, COCRDSLC)
2. Parallel run reads for 2 weeks — compare VSAM reads with API responses
3. Enable write operations (replacing COCRDUPC) behind feature flag
4. Parallel run writes for 2 weeks — write to both VSAM and PostgreSQL, compare
5. Cut over to Card Service only; decommission CICS card programs

**Parallel run:** Dual-write to VSAM and PostgreSQL for all card updates.
Nightly reconciliation job compares CARDDAT with `cards` table.

**Rollback:** Disable Card Service routing in ACL; re-enable CICS card programs.
PostgreSQL→VSAM sync restores any records written only to new system.

### 2B: Customer Service (Weeks 15–19)

| Item                    | Detail                                                          |
|:------------------------|:----------------------------------------------------------------|
| **Programs replaced**   | Customer logic extracted from COACTUPC; reads from COACTVWC, COCRDSLC, COPAUS0C |
| **Strategy**            | Refactor                                                         |
| **Target**              | Customer Service REST API with PII encryption (Spring Boot + PostgreSQL with pgcrypto) |
| **Data migration**      | CUSTDAT → `customers` table with encrypted SSN, DOB, government ID |
| **Integration**         | COACTUPC's customer update section → calls Customer Service API via ACL |
| **Risk**                | Medium — PII handling; extraction from COACTUPC monolith         |

**Key steps:**
1. Deploy Customer Service with read-only endpoints
2. Modify COACTUPC (via ACL) to call Customer Service for reads — verify parity
3. Extract customer update logic from COACTUPC; implement in Customer Service
4. Parallel run: COACTUPC writes to both CUSTDAT and Customer Service
5. Cut over customer updates to Customer Service only

**Rollback:** Re-enable direct CUSTDAT access in COACTUPC via ACL routing.

### 2C: Account Service (Weeks 18–24)

| Item                    | Detail                                                          |
|:------------------------|:----------------------------------------------------------------|
| **Programs replaced**   | COACTVWC, COACTUPC (account portion only), COACCT01             |
| **Strategy**            | Strangler Fig                                                    |
| **Target**              | Account Service REST API (Spring Boot + PostgreSQL)             |
| **Data migration**      | ACCTDAT + DISCGRP + TCATBALF → `accounts` + `disclosure_groups` + `category_balances` |
| **Integration**         | ACL routes account transactions to Account Service               |
| **Risk**                | Medium — balance data is financially sensitive but this phase handles CRUD only (not calculations) |

**Key steps:**
1. Deploy Account Service with read-only endpoints (replacing COACTVWC)
2. Parallel run reads for 2 weeks
3. Enable account update operations (replacing COACTUPC's account section)
4. Parallel run writes for 2 weeks — dual-write with reconciliation
5. Account MQ inquiry (COACCT01) → Account Service API
6. Decommission CICS account programs

**Note:** COBIL00C (bill payment) and CBACT04C (interest calculation) are
NOT included in this phase — they involve financial calculations and move
to Phase 3.

**Rollback:** Disable Account Service routing; re-enable CICS account programs.

### Phase 2 Exit Criteria
- [ ] Card Service handling all card CRUD with PCI-compliant CVV tokenization
- [ ] Customer Service handling all customer CRUD with encrypted PII
- [ ] Account Service handling account view/update with balance accuracy verified
- [ ] All dual-write reconciliation reports showing zero discrepancies for 2+ weeks
- [ ] COACTUPC monolith fully decomposed (account + customer portions extracted)
- [ ] Legacy programs decommissioned: COCRDLIC, COCRDSLC, COCRDUPC, COACTVWC, COACTUPC, COACCT01

---

## Phase 3: Financial Processing — High Risk (Weeks 25–36)

**Objective:** Migrate the financial core — transaction posting, interest calculation,
and bill payment. These are the highest-risk modules due to monetary impact.

### 3A: Transaction Service — Online (Weeks 25–28)

| Item                    | Detail                                                          |
|:------------------------|:----------------------------------------------------------------|
| **Programs replaced**   | COTRN00C, COTRN01C, COTRN02C                                   |
| **Strategy**            | Refactor                                                         |
| **Target**              | Transaction Service REST API + event publishing                 |
| **Data migration**      | TRANSACT → `transactions` table                                 |
| **Risk**                | Medium-High — transaction creation directly affects financial records |

**Key steps:**
1. Transaction list/view (COTRN00C, COTRN01C) → read-only API endpoints
2. Replace VSAM browse pagination with keyset pagination queries
3. Transaction add (COTRN02C) → POST endpoint with sequence-generated IDs
4. Parallel run: all transactions written to both VSAM and PostgreSQL
5. Financial reconciliation: sum of transaction amounts must match between systems

### 3B: Transaction Posting — Batch (Weeks 28–32)

| Item                    | Detail                                                          |
|:------------------------|:----------------------------------------------------------------|
| **Programs replaced**   | CBTRN02C, CBTRN01C, COMBTRAN (JCL SORT)                        |
| **Strategy**            | Refactor                                                         |
| **Target**              | Event-driven posting pipeline (message broker + Transaction Service + Account Service) |
| **Data migration**      | DALYTRAN → `daily_transactions` staging table; SORT → SQL query  |
| **Risk**                | **High** — CBTRN02C is the #2 hotspot (score 28/30); touches 6 files; financial accuracy critical |

**Key steps:**
1. Replace DALYTRAN sequential file with message queue or staging table
2. Implement posting logic: validate → post to `transactions` → publish `TransactionPosted` event
3. Account Service subscribes to `TransactionPosted` → updates balance + category totals
4. **Extended parallel run (4 weeks):** Run both old (CBTRN02C) and new posting pipeline nightly
5. Compare: account balances, category balances, transaction counts must match exactly
6. Run through a full billing cycle before cutover

**Critical validation:**
- `SUM(TRAN-AMT)` by account must match between old TRANSACT and new `transactions`
- `ACCT-CURR-BAL` must match between old ACCTDAT and new `accounts.current_balance`
- `TRAN-CAT-BAL` must match between old TCATBALF and new `category_balances.balance`

### 3C: Interest Calculation (Weeks 30–34)

| Item                    | Detail                                                          |
|:------------------------|:----------------------------------------------------------------|
| **Programs replaced**   | CBACT04C                                                         |
| **Strategy**            | Refactor                                                         |
| **Target**              | Interest Calculation Service (BigDecimal arithmetic)            |
| **Data migration**      | DISCGRP interest rates already in PostgreSQL from Phase 2C       |
| **Risk**                | **High** — financial calculation; COMP-3 decimal precision; affects every account |

**Key steps:**
1. Implement interest calculation using `BigDecimal` with `HALF_EVEN` rounding (banker's rounding)
2. Run both old (CBACT04C) and new calculator on same account set
3. Compare: interest amounts must match to the cent for every account
4. Extended parallel run through 2 billing cycles (8 weeks of data)
5. Cutover only after 100% match rate

### 3D: Bill Payment (Weeks 32–36)

| Item                    | Detail                                                          |
|:------------------------|:----------------------------------------------------------------|
| **Programs replaced**   | COBIL00C                                                         |
| **Strategy**            | Strangler Fig                                                    |
| **Target**              | Account Service + Transaction Service (saga pattern)            |
| **Risk**                | **High** — atomic multi-entity update (debit account + create transaction) |

**Key steps:**
1. Implement as saga: Account Service debits → Transaction Service records → compensate on failure
2. Parallel run: process payments through both old and new systems
3. Reconcile: payment amounts and resulting balances must match
4. Cutover after 2-week parallel run with zero discrepancies

### Phase 3 Exit Criteria
- [ ] Transaction posting pipeline producing identical results to CBTRN02C for 4+ weeks
- [ ] Interest calculation matching CBACT04C output to the cent for 2 billing cycles
- [ ] Bill payment saga producing identical balance changes for 2+ weeks
- [ ] All financial reconciliation reports at 100% match rate
- [ ] Legacy batch jobs decommissioned: POSTTRAN, INTCALC, COMBTRAN
- [ ] Legacy online programs decommissioned: COTRN00C, COTRN01C, COTRN02C, COBIL00C

---

## Phase 4: Complex Integration & Decommission (Weeks 37–48)

**Objective:** Migrate the multi-technology authorization module and decommission
the mainframe.

### 4A: Authorization Service (Weeks 37–42)

| Item                    | Detail                                                          |
|:------------------------|:----------------------------------------------------------------|
| **Programs replaced**   | COPAUA0C, COPAUS0C, COPAUS1C, COPAUS2C, CBPAUP0C, PAUDBLOD, PAUDBUNL, DBUNLDGS |
| **Strategy**            | Refactor                                                         |
| **Target**              | Authorization Service (event-driven, PostgreSQL, message broker) |
| **Data migration**      | IMS DB (summary+detail segments) → `auth_summaries` + `auth_details` tables |
| **Risk**                | **High** — multi-technology (CICS+IMS+DB2+MQ); fraud detection implications |

**Key steps:**
1. Map IMS hierarchical model to relational tables
2. Replace MQ request/reply with modern message broker (RabbitMQ/Kafka)
3. Implement authorization state machine: Pending→Approved/Declined→Matched/Expired
4. Replace DL/I calls with JPA repository operations
5. Migrate batch purge (CBPAUP0C) to scheduled job with TTL-based expiration
6. Parallel run: process authorizations through both systems for 4 weeks

### 4B: Data Export/Import (Weeks 40–43)

| Item                    | Detail                                                          |
|:------------------------|:----------------------------------------------------------------|
| **Programs replaced**   | CBEXPORT, CBIMPORT                                               |
| **Strategy**            | Rewrite                                                          |
| **Target**              | ETL service or database export utilities                         |
| **Risk**                | Low — batch utility; not customer-facing                         |

### 4C: Full Decommission (Weeks 43–48)

| Step | Action                                                    | Week |
|:-----|:----------------------------------------------------------|:-----|
| 1    | Disable ACL VSAM adapter (stop VSAM writes)              | 43   |
| 2    | Final VSAM→PostgreSQL reconciliation                     | 43   |
| 3    | Remove CICS region from production                        | 44   |
| 4    | Archive VSAM datasets to cold storage                     | 45   |
| 5    | Remove ACL CICS adapter                                   | 46   |
| 6    | Decommission mainframe LPAR (if no other workloads)      | 48   |
| 7    | Archive JCL, COBOL source, BMS maps to version control    | 48   |

### Phase 4 Exit Criteria
- [ ] Authorization Service handling all authorization workflows for 4+ weeks
- [ ] All VSAM datasets archived; no active CICS transactions
- [ ] Mainframe LPAR decommissioned or repurposed
- [ ] All 44 COBOL programs decommissioned
- [ ] Full application running on modern stack with zero mainframe dependencies

---

## Parallel-Run Reconciliation Strategy

| Check                          | Frequency | Tolerance | Automated? |
|:-------------------------------|:----------|:----------|:-----------|
| Record count (per entity)      | Nightly   | 0         | Yes        |
| Account balance comparison     | Nightly   | $0.00     | Yes        |
| Transaction sum by account     | Nightly   | $0.00     | Yes        |
| Category balance comparison    | Nightly   | $0.00     | Yes        |
| Interest calculation per acct  | Per cycle | $0.00     | Yes        |
| Customer PII field match       | Nightly   | 0 diffs   | Yes        |
| Auth decision parity           | Real-time | 0 diffs   | Yes        |
| Report output diff             | Per run   | 0 diffs   | Semi-auto  |

---

## Timeline Summary

| Phase | Weeks  | Modules                                    | Risk   | Programs Migrated |
|:------|:-------|:-------------------------------------------|:-------|------------------:|
| 0     | 1–4    | Foundation (infra, ACL, data sync, CI/CD)  | None   |                 0 |
| 1     | 5–12   | Identity, Ref Data, Reports, Navigation    | Low    |                14 |
| 2     | 13–24  | Card, Customer, Account (CRUD only)        | Medium |                12 |
| 3     | 25–36  | Transaction posting, Interest, Bill pay    | High   |                10 |
| 4     | 37–48  | Authorization, Export/Import, Decommission | High   |                 8 |
| **Total** | **48 weeks** |                                       |        |            **44** |
