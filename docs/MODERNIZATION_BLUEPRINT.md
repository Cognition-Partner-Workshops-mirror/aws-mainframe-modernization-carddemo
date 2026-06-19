# CardDemo Modernization Blueprint

> Strategy evaluation for modernizing the CardDemo COBOL/CICS mainframe
> credit card management application. Each functional area is assessed against
> four modernization approaches.

---

## Strategy Definitions

| Strategy          | Description                                                                                          | Typical Effort | Risk Level |
|:------------------|:-----------------------------------------------------------------------------------------------------|:---------------|:-----------|
| **Strangler Fig** | Incrementally replace modules behind an API facade; old and new coexist during transition             | Medium–High    | Low        |
| **Replatform**    | Automated code conversion (COBOL→Java) with minimal structural change; preserve existing architecture | Medium         | Medium     |
| **Refactor**      | Manual restructuring into modern patterns (services, REST APIs, relational DB) while preserving logic | High           | Medium     |
| **Rewrite**       | Clean-sheet reimplementation from business requirements; discard legacy code entirely                 | Very High      | High       |

---

## 1. Account Management

**Programs:** COACTVWC (941 lines), COACTUPC (4,236 lines), CBACT01C (430),
CBACT04C (652), COBIL00C (572), COACCT01 (620)

**Data:** ACCTDAT (VSAM KSDS, 300-byte records), DISCGRP, TCATBALF

### Strategy Assessment

| Strategy      | Fit   | Rationale                                                                                                    |
|:--------------|:------|:-------------------------------------------------------------------------------------------------------------|
| Strangler Fig | **Best** | Account operations are accessed via well-defined CICS transactions with clear inputs/outputs. An Account API facade can intercept CICS calls and route to a new Account Service while batch programs continue reading VSAM until cutover. |
| Replatform    | Fair  | COACTUPC's 4,236 lines with 168 IF statements and embedded validation (CSUTLDPY, CSLKPCDY) will produce poorly structured Java. COMP-3 arithmetic in CBACT04C needs careful decimal handling. |
| Refactor      | Good  | The account domain has clear entity boundaries (Account, Customer) but COACTUPC's monolithic structure requires significant decomposition. Embedded lookup tables (1,318 lines) must be externalized. |
| Rewrite       | Fair  | Well-understood domain, but interest calculation (CBACT04C) and bill payment (COBIL00C) have complex financial logic where bugs would have direct revenue impact. |

**Recommended Strategy:** **Strangler Fig** — Build an Account Service (REST API + relational DB) behind the CICS facade. Migrate read operations first (COACTVWC), then bill payment (COBIL00C), then the complex update path (COACTUPC). Interest calculation (CBACT04C) moves last due to financial precision requirements.

**Key Technical Challenges:**
- COACTUPC must be decomposed: account update, customer update, and validation should become separate service methods
- Interest calculation (CBACT04C) uses `S9(10)V99` COMP-3 arithmetic — must use BigDecimal in Java, not double/float
- Bill payment (COBIL00C) performs atomic multi-file updates (ACCTDAT REWRITE + TRANSACT WRITE) — needs database transaction semantics

---

## 2. Transaction Processing

**Programs:** COTRN00C (699), COTRN01C (330), COTRN02C (783), CBTRN01C (494),
CBTRN02C (731), CBTRN03C (649), COMBTRAN (JCL SORT)

**Data:** TRANSACT (KSDS, 350 bytes), DALYTRAN (sequential, 350 bytes),
TRANTYPE, TRANCATG, TCATBALF, DISCGRP

### Strategy Assessment

| Strategy      | Fit   | Rationale                                                                                                    |
|:--------------|:------|:-------------------------------------------------------------------------------------------------------------|
| Strangler Fig | Good  | Online transaction screens (list/view/add) are straightforward to front with a REST API. Batch posting (CBTRN02C) is harder — it touches 6 files with no rollback. |
| Replatform    | Poor  | CBTRN02C's 6-file I/O with implicit sequencing and CBTRN03C's 72-PERFORM report logic will produce unmaintainable converted code. COTRN02C's unique ID generation via READPREV is an anti-pattern that automated tools may not handle. |
| Refactor      | **Best** | Transaction processing has clear business rules (posting, interest, reporting) that map well to a modern event-driven architecture. The daily batch cycle (DALYTRAN→POSTTRAN→INTCALC→COMBTRAN→reports) is a natural fit for an event pipeline. |
| Rewrite       | Good  | Business rules are well-documented in the daily batch cycle. Rewrite risk is mitigated by the ability to run parallel processing and compare results. |

**Recommended Strategy:** **Refactor** — Redesign as an event-driven Transaction Service. Replace DALYTRAN sequential processing with a message queue. Replace CBTRN02C's multi-file batch with transactional database operations. Replace SORT/merge (COMBTRAN) with database queries.

**Key Technical Challenges:**
- CBTRN02C is the highest-risk program in the codebase (score 28/30) — reads 6 files, writes 3, no rollback
- Unique transaction ID generation (READPREV on TRANSACT to find max ID) must be replaced with a sequence generator
- DALYTRAN→TRANSACT posting pipeline must preserve exactly-once semantics
- Running balance updates in TCATBALF must remain atomic with transaction posting

---

## 3. Card Management

**Programs:** COCRDLIC (1,459), COCRDSLC (887), COCRDUPC (1,560),
CBACT02C (178), CBACT03C (178)

**Data:** CARDDAT (KSDS, 150 bytes), CARDXREF (KSDS, 50 bytes),
CARDAIX (alternate index), CXACAIX (alternate index)

### Strategy Assessment

| Strategy      | Fit   | Rationale                                                                                                    |
|:--------------|:------|:-------------------------------------------------------------------------------------------------------------|
| Strangler Fig | **Best** | Card operations form a cohesive bounded context with clear CRUD semantics. The COCRDLIC browse pattern (STARTBR/READNEXT/READPREV) maps directly to paginated REST queries. |
| Replatform    | Fair  | COCRDLIC's VSAM browse pagination and alternate index access will not translate cleanly. COCRDUPC has the same embedded validation bloat as COACTUPC. |
| Refactor      | Good  | Clean entity model (Card, Cross-Reference). Alternate indexes (CARDAIX, CXACAIX) map to database secondary indexes. |
| Rewrite       | Good  | Simple CRUD domain with well-understood entities. Risk is low but effort is unnecessary given existing code clarity. |

**Recommended Strategy:** **Strangler Fig** — Expose a Card Service API. The cross-reference (CVACT03Y) becomes a join table in the relational model. Replace alternate index access with SQL queries. PCI-DSS compliance requirements make this a candidate for isolated service deployment.

**Key Technical Challenges:**
- VSAM browse pagination (STARTBR/READNEXT/READPREV/ENDBR) must become keyset pagination, not offset-based
- Alternate index access (CARDAIX by account, CXACAIX by account) needs equivalent composite indexes
- CVV storage in COCRDUPC is a PCI-DSS concern — new service should use tokenization
- Cross-screen XCTL flow (list→detail→update→list) maps to SPA navigation

---

## 4. Customer Management

**Programs:** Customer data is embedded within COACTUPC (account update),
COACTVWC, COCRDSLC, COPAUS0C. CBCUS01C (178) is a batch read utility.

**Data:** CUSTDAT (KSDS, 500 bytes) — includes PII (SSN, DOB, address, phone)

### Strategy Assessment

| Strategy      | Fit   | Rationale                                                                                                    |
|:--------------|:------|:-------------------------------------------------------------------------------------------------------------|
| Strangler Fig | Good  | Customer reads are dispersed across many programs but always via direct CICS READ by CUST-ID. A Customer Service can intercept these. |
| Replatform    | Poor  | Customer management is not a standalone program — it's embedded in COACTUPC. Automated conversion would preserve this anti-pattern. |
| Refactor      | **Best** | Customer data must be extracted from COACTUPC into its own service. The 500-byte record with PII fields (SSN, DOB, government ID) needs data classification and encryption that the legacy system lacks. |
| Rewrite       | Good  | Clean entity model. PII handling requirements may mandate a clean-sheet approach anyway. |

**Recommended Strategy:** **Refactor** — Extract a Customer Service from the account update monolith. Apply data classification (PII tagging), encrypt SSN/DOB at rest, and add audit logging. The CSLKPCDY lookup tables (phone area codes, state codes, ZIP validation) become a shared Validation Service or external reference data API.

**Key Technical Challenges:**
- Customer update logic is physically embedded in COACTUPC (lines ~2000–3500) — must be surgically extracted
- PII fields (CUST-SSN, CUST-DOB, CUST-GOVT-ISSUED-ID) need encryption at rest and masking in APIs
- CSLKPCDY's 1,318 lines of hardcoded validation data must be externalized to a database or config service
- Phone/state/ZIP validation is shared with Card Update — extract as a common Validation Service

---

## 5. Reporting & Statements

**Programs:** CORPT00C (649), CBTRN03C (649), CBSTM03A (924) + CBSTM03B (230)

**Data:** Reads from TRANSACT, CARDXREF, ACCTDAT, CUSTDAT, TRANTYPE, TRANCATG,
DATEPARM. Outputs to report files (sequential) and statement GDGs (text + HTML).

### Strategy Assessment

| Strategy      | Fit   | Rationale                                                                                                    |
|:--------------|:------|:-------------------------------------------------------------------------------------------------------------|
| Strangler Fig | Fair  | Reports are batch-only and don't serve online users directly. Strangler is overkill for offline processing. |
| Replatform    | Fair  | Report formatting logic (132-column layout, page breaks, running totals) is highly mainframe-specific. Automated conversion produces unidiomatic code. |
| Refactor      | Good  | Report logic maps well to modern reporting frameworks (JasperReports, custom templating). GDG output can become cloud storage with versioning. |
| Rewrite       | **Best** | Report layouts are tightly coupled to 132-column print format and GDG file versioning — both obsolete in modern platforms. Business requirements (transaction summary, account statement) are clear and well-bounded. |

**Recommended Strategy:** **Rewrite** — Implement reports using a modern reporting framework. Transaction reports become database queries with PDF/HTML output. Statements become a templated document generator reading from the Transaction and Account databases. GDG versioning becomes object storage with timestamps.

**Key Technical Challenges:**
- CBSTM03A generates both text (132-col) and HTML statements — modern version should be HTML/PDF only
- CVTRA07Y report layout copybook defines fixed-width columns — maps to CSS/template formatting
- GDG (Generation Data Group) versioning needs cloud storage equivalent (S3 versioned buckets or timestamped paths)
- DATEPARM input file for report date ranges becomes API parameters

---

## 6. Security / User Administration

**Programs:** COSGN00C (260), COUSR00C (695), COUSR01C (299),
COUSR02C (414), COUSR03C (359)

**Data:** USRSEC (KSDS, 80 bytes) — plaintext passwords (`SEC-USR-PWD PIC X(08)`)

### Strategy Assessment

| Strategy      | Fit   | Rationale                                                                                                    |
|:--------------|:------|:-------------------------------------------------------------------------------------------------------------|
| Strangler Fig | Fair  | Sign-on is the entry point to the entire application — strangling it requires intercepting every session. |
| Replatform    | Poor  | The security model (8-char plaintext passwords, single admin/user role) is fundamentally inadequate. Converting it preserves security vulnerabilities. |
| Refactor      | Fair  | The CRUD operations (COUSR00C–03C) are straightforward but the security model needs replacement, not refactoring. |
| Rewrite       | **Best** | The entire authentication/authorization model must be replaced. Plaintext password storage, 8-character limits, and binary role model (Admin/User) are unacceptable in a modern system. |

**Recommended Strategy:** **Rewrite** — Replace with an identity provider (Keycloak, AWS Cognito, Auth0). Map the existing Admin/User roles to RBAC with fine-grained permissions. Migrate user data with password reset (existing passwords are unrecoverable since they should be hashed). The USRSEC VSAM file is eliminated entirely.

**Key Technical Challenges:**
- Existing passwords are plaintext — cannot be migrated; must force password reset
- Admin/User binary role model needs expansion to support RBAC
- COSGN00C routes to COADM01C (admin) or COMEN01C (user) based on role — modern equivalent is role-based UI routing
- All 25 online programs check `CDEMO-USER-TYPE` from COMMAREA — must be replaced with token-based claims

---

## 7. Authorization Processing (IMS-DB2-MQ Module)

**Programs:** COPAUA0C (1,026), COPAUS0C (1,032), COPAUS1C (604),
COPAUS2C (244), CBPAUP0C (386), PAUDBLOD (369), PAUDBUNL (317), DBUNLDGS (366)

**Data:** IMS hierarchical DB (CIPAUSMY summary + CIPAUDTY detail segments),
MQ request/reply queues, DB2 tables

### Strategy Assessment

| Strategy      | Fit   | Rationale                                                                                                    |
|:--------------|:------|:-------------------------------------------------------------------------------------------------------------|
| Strangler Fig | Good  | MQ-based request/reply pattern already provides a natural integration seam. New authorization service can consume from the same queues. |
| Replatform    | Poor  | IMS DL/I calls, GSAM access, and MQ API patterns are technology-specific. Automated conversion tools handle these poorly. |
| Refactor      | **Best** | The authorization domain has clear business semantics (request→approve/decline→match/expire→purge) that map to a modern event-driven workflow. IMS hierarchical model (summary→detail) maps to a simple relational parent-child. |
| Rewrite       | Good  | Complex multi-technology stack (CICS+IMS+DB2+MQ) makes rewrite attractive, but business logic in COPAUA0C is substantial. |

**Recommended Strategy:** **Refactor** — Redesign as an Authorization Service with event-driven workflow. Replace IMS hierarchical DB with relational tables (authorization_summary + authorization_detail). Replace MQ request/reply with a modern message broker (SQS, Kafka, RabbitMQ). Preserve the approve/decline/match/expire state machine.

**Key Technical Challenges:**
- IMS DL/I calls (GU, GN, ISRT, DLET) with SSA segments must be mapped to SQL operations
- COMP-3 packed decimal fields in IMS segments need BigDecimal handling
- MQ request/reply pattern needs equivalent async messaging with correlation IDs
- Batch purge (CBPAUP0C) becomes a scheduled job or TTL-based expiration

---

## 8. Reference Data (DB2 Transaction Type Module)

**Programs:** COTRTLIC (2,098), COTRTUPC (1,702), COBTUPDT (237)

**Data:** DB2 tables (TRAN_TYPE, TRAN_CAT), also mirrored in VSAM (TRANTYPE, TRANCATG)

### Strategy Assessment

| Strategy      | Fit   | Rationale                                                                                                    |
|:--------------|:------|:-------------------------------------------------------------------------------------------------------------|
| Strangler Fig | Good  | Reference data is read-heavy with infrequent updates — easy to cache and serve from a new API. |
| Replatform    | Fair  | Embedded SQL is the most portable pattern in the codebase, but the CICS terminal handling around it is not. |
| Refactor      | **Best** | Already uses DB2 — the data model can migrate directly. The CICS screen logic wrapping SQL queries becomes a simple CRUD REST API. |
| Rewrite       | Fair  | Unnecessary effort — the DB2 schema is already relational. |

**Recommended Strategy:** **Refactor** — Migrate DB2 tables to the target relational database (PostgreSQL/MySQL). Expose as a Reference Data REST API. The dual-storage pattern (DB2 + VSAM) is eliminated — VSAM copies served as a cache for programs that couldn't access DB2.

---

## Strategy Summary Matrix

| Functional Area          | Recommended Strategy | Effort  | Risk  | Priority |
|:-------------------------|:---------------------|:--------|:------|:---------|
| Security / User Admin    | Rewrite              | Medium  | Low   | 1 (first)|
| Reference Data (DB2)     | Refactor             | Low     | Low   | 2        |
| Reporting & Statements   | Rewrite              | Medium  | Low   | 3        |
| Card Management          | Strangler Fig        | Medium  | Low   | 4        |
| Customer Management      | Refactor             | High    | Medium| 5        |
| Account Management       | Strangler Fig        | High    | Medium| 6        |
| Transaction Processing   | Refactor             | V. High | High  | 7        |
| Authorization (IMS/MQ)   | Refactor             | High    | High  | 8 (last) |
