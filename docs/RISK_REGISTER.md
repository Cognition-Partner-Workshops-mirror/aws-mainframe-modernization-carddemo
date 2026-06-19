# CardDemo Modernization Risk Register

> Top risks for the CardDemo COBOL-to-modern migration, with likelihood,
> impact, mitigations, and contingency plans.

---

## Risk Scoring

| Dimension    | Scale                                          |
|:-------------|:-----------------------------------------------|
| Likelihood   | 1 (Rare) – 2 (Unlikely) – 3 (Possible) – 4 (Likely) – 5 (Almost Certain) |
| Impact       | 1 (Negligible) – 2 (Minor) – 3 (Moderate) – 4 (Major) – 5 (Severe) |
| **Risk Score** | Likelihood × Impact (max 25)                  |

---

## Risk Summary Table

| # | Risk                                         | Likelihood | Impact | Score | Phase(s) | Category       |
|--:|:---------------------------------------------|:----------:|:------:|:-----:|:---------|:---------------|
| 1 | Financial calculation precision loss          | 4          | 5      | **20**| 3        | Technical      |
| 2 | Transaction posting data inconsistency       | 3          | 5      | **15**| 3        | Data Integrity |
| 3 | Plaintext password migration exposure        | 3          | 5      | **15**| 1        | Security       |
| 4 | COACTUPC decomposition defects               | 4          | 4      | **16**| 2        | Technical      |
| 5 | VSAM-to-relational data loss during sync     | 3          | 4      | **12**| 0, 2     | Data Integrity |
| 6 | VSAM browse pagination semantic mismatch     | 4          | 3      | **12**| 2        | Functional     |
| 7 | IMS hierarchical-to-relational mapping errors| 3          | 4      | **12**| 4        | Technical      |
| 8 | Batch window exceeded during parallel run    | 3          | 3      | **9** | 3        | Operational    |
| 9 | GDG file versioning loss                     | 2          | 3      | **6** | 1        | Operational    |
|10 | Skills gap — COBOL domain knowledge          | 4          | 3      | **12**| All      | Organizational |
|11 | Hardcoded validation table staleness         | 3          | 3      | **9** | 0        | Data Integrity |
|12 | PCI-DSS compliance gaps in card service      | 3          | 5      | **15**| 2        | Compliance     |
|13 | MQ message format incompatibility            | 3          | 3      | **9** | 4        | Integration    |
|14 | Dual-write conflict during parallel run      | 3          | 4      | **12**| 2, 3     | Data Integrity |
|15 | Scope creep from undocumented business rules | 4          | 3      | **12**| All      | Project Mgmt   |

---

## Detailed Risk Analysis

### Risk 1: Financial Calculation Precision Loss

| Attribute       | Detail                                                                |
|:----------------|:----------------------------------------------------------------------|
| **Description** | COBOL `S9(10)V99` with COMP-3 storage provides exact decimal arithmetic. Java `double`/`float` would introduce IEEE 754 rounding errors. Even `BigDecimal` with wrong rounding mode or scale could produce different results. |
| **Affected**    | CBACT04C (interest), CBTRN02C (posting), COBIL00C (bill pay)         |
| **Likelihood**  | 4 (Likely) — developers commonly default to floating-point           |
| **Impact**      | 5 (Severe) — financial miscalculations affect revenue and compliance |
| **Risk Score**  | **20**                                                                |

**Mitigations:**
1. **Mandate BigDecimal** — enforce via static analysis rules; ban `double`/`float` for monetary fields
2. **Match COBOL rounding** — use `RoundingMode.HALF_EVEN` (banker's rounding) with `scale(2)`
3. **Penny-perfect testing** — parallel-run comparator must match to $0.00 for every account, every cycle
4. **Code review gate** — all financial calculation PRs require review by someone who has read CBACT04C and CBTRN02C

**Contingency:** If precision differences are found in parallel run, halt cutover and audit all BigDecimal operations. Trace the specific COBOL COMPUTE statements to their Java equivalents line by line.

---

### Risk 2: Transaction Posting Data Inconsistency

| Attribute       | Detail                                                                |
|:----------------|:----------------------------------------------------------------------|
| **Description** | CBTRN02C reads 6 files and writes 3 (TRANSACT, ACCTDAT, TCATBALF) in a single batch run with no explicit transaction boundaries. In the new system, posting becomes a distributed operation across Transaction Service and Account Service. Network partitions, partial failures, or event ordering issues could cause data to diverge. |
| **Affected**    | CBTRN02C → Transaction Service + Account Service (Phase 3B)          |
| **Likelihood**  | 3 (Possible) — distributed systems introduce partial failure modes   |
| **Impact**      | 5 (Severe) — account balances out of sync with transaction history   |
| **Risk Score**  | **15**                                                                |

**Mitigations:**
1. **Saga pattern with compensating transactions** — if Account Service update fails, compensate by reversing the transaction record
2. **Idempotency keys** — every posted transaction carries a unique ID; replay-safe
3. **Outbox pattern** — Transaction Service writes event to DB in same transaction as the record; relay publishes asynchronously
4. **Nightly reconciliation** — compare `SUM(amount)` by account between `transactions` and `accounts.current_balance`
5. **Extended parallel run** — 4 weeks minimum before cutover

**Contingency:** If discrepancies found, run a reconciliation batch that replays all transactions from `daily_transactions` staging table and recomputes balances from scratch. The staging table serves as the source of truth.

---

### Risk 3: Plaintext Password Migration Exposure

| Attribute       | Detail                                                                |
|:----------------|:----------------------------------------------------------------------|
| **Description** | USRSEC stores passwords in plaintext (`SEC-USR-PWD PIC X(08)`). During migration, these passwords will be read from VSAM and could be logged, stored in migration scripts, or exposed in transit. Post-migration, all users must reset passwords since plaintext cannot be hashed retroactively. |
| **Affected**    | COSGN00C, COUSR00C–03C → Keycloak migration (Phase 1A)              |
| **Likelihood**  | 3 (Possible) — migration scripts could inadvertently log passwords   |
| **Impact**      | 5 (Severe) — credential exposure; regulatory violation                |
| **Risk Score**  | **15**                                                                |

**Mitigations:**
1. **Never extract passwords** — create Keycloak users WITHOUT passwords; force reset via email
2. **If passwords must be migrated** — hash immediately upon VSAM read; never write plaintext to log, file, or database
3. **Audit migration scripts** — security review before execution
4. **Rotate all service accounts** — during migration, assume all existing credentials are compromised
5. **Enable MFA** — Keycloak supports TOTP; require for admin users

**Contingency:** If plaintext exposure is detected, trigger immediate forced password reset for all users and file security incident report.

---

### Risk 4: COACTUPC Decomposition Defects

| Attribute       | Detail                                                                |
|:----------------|:----------------------------------------------------------------------|
| **Description** | COACTUPC (4,236 lines, 168 IF statements) is a monolith that must be split into Account Service and Customer Service. The interleaved validation logic (CSUTLDPY for dates, CSLKPCDY for phone/state/ZIP, CSSETATY for BMS attributes) makes surgical extraction error-prone. Business rules embedded in deeply nested IF/EVALUATE chains may be missed. |
| **Affected**    | COACTUPC → Account Service + Customer Service (Phase 2B, 2C)        |
| **Likelihood**  | 4 (Likely) — 4,236 lines with 168 conditionals is hard to decompose without missing logic |
| **Impact**      | 4 (Major) — account/customer updates could silently lose validation  |
| **Risk Score**  | **16**                                                                |

**Mitigations:**
1. **Map every EVALUATE/IF path** — create decision table from COACTUPC before writing any new code
2. **Extract validation first** — build and test Validation Service (CSUTLDPY + CSLKPCDY) independently before decomposing COACTUPC
3. **Regression test suite** — capture every valid/invalid input combination from COACTUPC's BMS screen into test cases
4. **Screen recording** — record all CICS terminal interactions during parallel run to capture exact input/output sequences
5. **Incremental extraction** — read path first (week 1–2), then field-by-field validation (week 3–4), then write path (week 5–6)

**Contingency:** If decomposition produces too many defects, fall back to replatforming COACTUPC as a single service (preserve monolithic structure in Java) and decompose post-migration.

---

### Risk 5: VSAM-to-Relational Data Loss During Sync

| Attribute       | Detail                                                                |
|:----------------|:----------------------------------------------------------------------|
| **Description** | VSAM records have implicit characteristics (record length padding, unsigned packed decimal edge cases, EBCDIC↔ASCII encoding) that could be lost or corrupted during data sync. COMP-3 sign nibbles, REDEFINES unions (CVEXPORT has 5 entity types in one 500-byte record), and alternate index relationships could be incorrectly migrated. |
| **Affected**    | Phase 0 data sync pipeline; all subsequent phases                     |
| **Likelihood**  | 3 (Possible) — encoding/type conversion is a known migration pitfall  |
| **Impact**      | 4 (Major) — corrupt data in target database undermines all downstream phases |
| **Risk Score**  | **12**                                                                |

**Mitigations:**
1. **Field-by-field validation** — compare every field of every record between VSAM and PostgreSQL after initial load
2. **Checksum records** — compute hash of each VSAM record and compare with hash of corresponding DB row
3. **Special handling for COMP-3** — use proven EBCDIC→ASCII conversion libraries; test with boundary values (max positive, max negative, zero)
4. **REDEFINES handling** — CVEXPORT's discriminator field must drive type-specific parsing
5. **Alternate index verification** — verify CXACAIX and CARDAIX relationships are preserved as secondary indexes

**Contingency:** If data corruption is found, re-run sync from VSAM (source of truth) with corrected conversion logic. Never modify VSAM data based on PostgreSQL state during migration.

---

### Risk 6: VSAM Browse Pagination Semantic Mismatch

| Attribute       | Detail                                                                |
|:----------------|:----------------------------------------------------------------------|
| **Description** | COCRDLIC, COTRN00C, COUSR00C use STARTBR/READNEXT/READPREV for bidirectional cursor-based browsing. If modernized with offset-based pagination (`LIMIT/OFFSET`), records inserted or deleted between page requests will cause items to be skipped or duplicated. |
| **Affected**    | Card list, Transaction list, User list (Phases 2A, 3A, 1A)          |
| **Likelihood**  | 4 (Likely) — offset pagination is the default in most REST frameworks |
| **Impact**      | 3 (Moderate) — users see missing or duplicate records during browsing |
| **Risk Score**  | **12**                                                                |

**Mitigations:**
1. **Keyset pagination** — implement `WHERE key > :last_key ORDER BY key LIMIT :size` instead of OFFSET
2. **Specify in API contract** — REST API must document cursor-based pagination from day one
3. **Test with concurrent writes** — insert/delete records during browse operations and verify no items are skipped or duplicated
4. **Preserve READPREV semantics** — keyset pagination with `WHERE key < :first_key ORDER BY key DESC` for backward navigation

**Contingency:** If keyset pagination introduces complexity, use OFFSET as interim solution with a known-issue annotation; fix before Phase 3 cutover.

---

### Risk 7: IMS Hierarchical-to-Relational Mapping Errors

| Attribute       | Detail                                                                |
|:----------------|:----------------------------------------------------------------------|
| **Description** | IMS uses hierarchical segments (CIPAUSMY parent → CIPAUDTY children) with DL/I navigation (GU, GN, GNP). Mapping to relational tables may lose the implicit ordering of child segments or the positional semantics of GN (Get Next) within a parent. SSA (Segment Search Argument) qualification translates to WHERE clauses but the behavior on segment boundaries differs. |
| **Affected**    | Authorization module (Phase 4A): COPAUA0C, COPAUS0C, CBPAUP0C        |
| **Likelihood**  | 3 (Possible) — IMS-to-relational is a well-studied problem but edge cases persist |
| **Impact**      | 4 (Major) — incorrect authorization decisions affect fraud detection  |
| **Risk Score**  | **12**                                                                |

**Mitigations:**
1. **Preserve parent-child order** — add `sequence_number` column to `auth_details` to maintain segment ordering
2. **Map DL/I calls explicitly** — create a mapping table: each GU/GN/ISRT/DLET → equivalent SQL
3. **Test with IMS test data** — load PAUDBLOD test data into both IMS and PostgreSQL; compare GU/GN results with SELECT results
4. **SSA→WHERE mapping** — document every SSA qualification and its SQL equivalent

**Contingency:** If mapping proves too complex, consider using an open-source hierarchical-to-relational middleware or maintaining a document store (PostgreSQL JSONB) for authorization records during transition.

---

### Risk 8: Batch Window Exceeded During Parallel Run

| Attribute       | Detail                                                                |
|:----------------|:----------------------------------------------------------------------|
| **Description** | During Phase 3 parallel run, both old and new batch processes run nightly. CBTRN02C (posting) + CBACT04C (interest) + reconciliation could exceed the available batch window, delaying CICS region restart and affecting online availability. |
| **Affected**    | Phase 3 parallel run (Weeks 25–36)                                    |
| **Likelihood**  | 3 (Possible) — doubling batch workload is significant                 |
| **Impact**      | 3 (Moderate) — delayed online availability; potential SLA breach      |
| **Risk Score**  | **9**                                                                  |

**Mitigations:**
1. **Stagger execution** — run old batch first (it has the tighter dependency on CICS files), then new batch on PostgreSQL (independent)
2. **New batch on separate infrastructure** — new batch runs on its own compute; no contention with mainframe
3. **Optimize reconciliation** — use database-side comparison (PostgreSQL FDW or export-based) rather than record-by-record
4. **Weekend full reconciliation** — do field-by-field comparison on weekends; nightly runs check aggregates only

**Contingency:** If batch window is consistently exceeded, reduce parallel-run scope to a subset of accounts (sampling) rather than full population.

---

### Risk 9: GDG File Versioning Loss

| Attribute       | Detail                                                                |
|:----------------|:----------------------------------------------------------------------|
| **Description** | CBSTM03A outputs statements to GDG (Generation Data Group) datasets that maintain N generations of statements. The GDG model has no direct equivalent in cloud storage. If versioning is not implemented, historical statements become inaccessible. |
| **Affected**    | Statement generation (Phase 1C)                                       |
| **Likelihood**  | 2 (Unlikely) — well-understood problem with known solutions           |
| **Impact**      | 3 (Moderate) — regulatory requirement to maintain historical statements |
| **Risk Score**  | **6**                                                                  |

**Mitigations:**
1. **S3 versioned buckets** — each statement generation writes to `s3://statements/{account}/{YYYY-MM}/statement.html`
2. **Database tracking** — `statement_generations` table tracks generation number, date, and storage path
3. **Pre-migration archive** — export all existing GDG members to cloud storage before decommission

**Contingency:** If versioning is lost, re-generate historical statements from transaction history (all data is preserved in `transactions` table).

---

### Risk 10: Skills Gap — COBOL Domain Knowledge

| Attribute       | Detail                                                                |
|:----------------|:----------------------------------------------------------------------|
| **Description** | Understanding COBOL business logic (especially financial calculations, VSAM access patterns, CICS transaction flow, IMS DL/I navigation) requires specialized knowledge that may not exist on the modernization team. Misinterpreting COBOL semantics leads to silent business logic errors. |
| **Affected**    | All phases                                                            |
| **Likelihood**  | 4 (Likely) — COBOL expertise is scarce in modern development teams   |
| **Impact**      | 3 (Moderate) — slower progress and increased defect rate             |
| **Risk Score**  | **12**                                                                |

**Mitigations:**
1. **Reference documentation** — use APPLICATION_INVENTORY.md, DATA_DICTIONARY.md, DEPENDENCY_MAP.md, HOTSPOT_REPORT.md as onboarding material
2. **COBOL reading sessions** — schedule code walkthroughs of top hotspot programs (COACTUPC, CBTRN02C, CBACT04C)
3. **Pair programming** — pair COBOL-experienced developer with Java developer during extraction
4. **AI-assisted analysis** — use LLM-based code analysis tools for COBOL→English translation of complex paragraphs
5. **Decision table extraction** — convert EVALUATE/IF chains to tabular decision tables before coding

**Contingency:** If COBOL expertise is unavailable, consider engaging a mainframe modernization consultancy for the first 2 phases to establish patterns.

---

### Risk 11: Hardcoded Validation Table Staleness

| Attribute       | Detail                                                                |
|:----------------|:----------------------------------------------------------------------|
| **Description** | CSLKPCDY contains 1,318 lines of hardcoded phone area codes, US state codes, and ZIP prefix validations. These are compiled into programs and cannot be updated without recompilation. The data may already be stale (new area codes, ZIP code changes). |
| **Affected**    | Phase 0 (Validation Service extraction)                               |
| **Likelihood**  | 3 (Possible) — area codes change periodically                        |
| **Impact**      | 3 (Moderate) — valid entries rejected; invalid entries accepted       |
| **Risk Score**  | **9**                                                                  |

**Mitigations:**
1. **Externalize to database** — load lookup data into PostgreSQL reference tables
2. **Refresh from authoritative sources** — US area codes from NANPA; ZIP codes from USPS; state codes from FIPS
3. **Automated refresh** — scheduled job to update reference data from public APIs

**Contingency:** Accept current data as baseline; flag discrepancies for manual review during Phase 2 testing.

---

### Risk 12: PCI-DSS Compliance Gaps in Card Service

| Attribute       | Detail                                                                |
|:----------------|:----------------------------------------------------------------------|
| **Description** | COCRDUPC stores CVV codes in plaintext in CARDDAT (`CARD-CVV-CD PIC 9(03)`). The Card Service must handle card numbers and CVV codes in a PCI-DSS-compliant manner. Failure to implement proper tokenization, encryption, and access controls could result in compliance violations. |
| **Affected**    | Card Service (Phase 2A)                                               |
| **Likelihood**  | 3 (Possible) — PCI requirements are well-known but easy to miss      |
| **Impact**      | 5 (Severe) — compliance violation; potential fines; data breach risk  |
| **Risk Score**  | **15**                                                                |

**Mitigations:**
1. **Tokenize card numbers** — store tokens in application database; actual PANs in a dedicated card vault
2. **Never store CVV** — CVV should only be used for real-time authorization; do not persist
3. **Encrypt at rest** — use PostgreSQL pgcrypto or application-level encryption for card data
4. **Network segmentation** — Card Service runs in an isolated network segment with restricted access
5. **PCI-DSS assessment** — engage QSA (Qualified Security Assessor) before Phase 2A go-live

**Contingency:** If PCI compliance cannot be achieved in-house, use a third-party payment processor for card data storage and expose only tokens to the application.

---

### Risk 13: MQ Message Format Incompatibility

| Attribute       | Detail                                                                |
|:----------------|:----------------------------------------------------------------------|
| **Description** | The MQ-based authorization module (COACCT01, CODATE01) uses COBOL copybook-defined message formats (CCPAURQY — fixed-width, EBCDIC-encoded). The new Authorization Service must either parse these legacy messages or migrate external systems to a new format simultaneously. |
| **Affected**    | Authorization Service (Phase 4A)                                      |
| **Likelihood**  | 3 (Possible) — external systems may not be able to change simultaneously |
| **Impact**      | 3 (Moderate) — authorization processing blocked until format resolved |
| **Risk Score**  | **9**                                                                  |

**Mitigations:**
1. **Message adapter** — ACL translates EBCDIC fixed-width → JSON at the queue level
2. **Dual-format support** — new Authorization Service accepts both legacy and modern formats during transition
3. **Coordinate with external systems** — negotiate format migration timeline early in Phase 3
4. **Schema registry** — document message formats in an open-source schema registry (e.g., Apicurio)

**Contingency:** If external systems cannot change, maintain the message adapter permanently as a translation layer.

---

### Risk 14: Dual-Write Conflict During Parallel Run

| Attribute       | Detail                                                                |
|:----------------|:----------------------------------------------------------------------|
| **Description** | During parallel run phases, both old and new systems write to their respective data stores. If the same record is updated through both paths (e.g., CICS user updates ACCTDAT while new API updates PostgreSQL), the reconciliation will show false discrepancies. Worse, if bidirectional sync is active, conflicting writes could overwrite each other. |
| **Affected**    | Phases 2 and 3 (all dual-write scenarios)                             |
| **Likelihood**  | 3 (Possible) — during transition, some users may use old system while others use new |
| **Impact**      | 4 (Major) — data divergence; trust in reconciliation undermined      |
| **Risk Score**  | **12**                                                                |

**Mitigations:**
1. **Single writer** — during parallel run, old system is the primary writer; new system is read-only + shadow-write
2. **One-directional sync** — VSAM→PostgreSQL only during parallel run; never PostgreSQL→VSAM
3. **Timestamp comparison** — reconciliation uses last-modified timestamps to determine which write is authoritative
4. **User cohort migration** — move users to new system in cohorts; each user writes to only one system

**Contingency:** If conflicts are detected, VSAM is always the source of truth during parallel run. Overwrite PostgreSQL from VSAM and investigate the conflict source.

---

### Risk 15: Scope Creep from Undocumented Business Rules

| Attribute       | Detail                                                                |
|:----------------|:----------------------------------------------------------------------|
| **Description** | COBOL programs may contain business rules that are not documented anywhere except in the code itself. During modernization, these rules may be discovered late (e.g., special handling for certain account types, edge cases in interest calculation, conditional transaction routing). Each discovery requires analysis and re-work. |
| **Affected**    | All phases — especially Phase 3 (financial logic)                     |
| **Likelihood**  | 4 (Likely) — legacy systems commonly have undocumented rules          |
| **Impact**      | 3 (Moderate) — schedule delays; rework                                |
| **Risk Score**  | **12**                                                                |

**Mitigations:**
1. **Pre-migration code analysis** — use HOTSPOT_REPORT.md to identify complex programs; analyze before coding
2. **Decision table extraction** — convert every EVALUATE and nested IF chain to a decision table before implementation
3. **Subject matter expert interviews** — consult business users who use the system daily
4. **Test-driven discovery** — run comprehensive test scenarios through old system first; capture all outputs as expected results
5. **Budget 20% contingency** — expect undocumented rules to add ~20% to estimated effort

**Contingency:** Maintain a "discovered rules" backlog. When a new rule is found, document it, add a test case, and schedule implementation. Do not let discoveries block the critical path.

---

## Risk Heat Map

```
Impact ▲
  5    │  [R9]              [R3,R12]    [R1]
       │                    [R2]
  4    │        [R5,R6,R7]  [R4,R14]
       │        [R10,R15]
  3    │  [R9]  [R8,R11]
       │        [R13]
  2    │
       │
  1    │
       └────────────────────────────────────▶
         1        2        3        4        5
                        Likelihood

Legend: Top-right quadrant = highest priority
  R1  = Financial precision loss (Score 20)
  R4  = COACTUPC decomposition (Score 16)
  R2  = Transaction posting inconsistency (Score 15)
  R3  = Plaintext password exposure (Score 15)
  R12 = PCI-DSS compliance gaps (Score 15)
```

---

## Risk Response Summary

| Risk Score | Count | Response Strategy                                            |
|:----------:|:-----:|:-------------------------------------------------------------|
| 15–20      | 4     | **Mitigate aggressively** — dedicated mitigation actions in project plan; gate reviews before phase cutover |
| 10–14      | 7     | **Mitigate** — include in phase planning; monitor actively   |
| 6–9        | 4     | **Accept with monitoring** — known risks with viable contingencies; review monthly |
