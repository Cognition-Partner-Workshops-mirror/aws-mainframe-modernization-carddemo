# CardDemo Hotspot Report

> Top 10 modules prioritized by complexity, risk, and business impact for
> modernization planning. Metrics derived from static analysis of the COBOL source.

---

## Scoring Methodology

Each module is scored across three dimensions (1–10 scale):

| Dimension          | Factors Considered                                                                |
|:-------------------|:----------------------------------------------------------------------------------|
| **Complexity**     | Line count, number of PERFORMs, EVALUATE/IF branching, file I/O count, copybook deps |
| **Risk**           | Data mutation (REWRITE/DELETE), security sensitivity, multi-file updates, PII handling, error paths |
| **Business Impact**| Revenue-critical path, user-facing frequency, downstream dependencies, data integrity role |

**Priority Score** = Complexity + Risk + Business Impact (max 30)

---

## Top 10 Hotspot Modules

### Rank 1: COACTUPC — Account Update (Online)

| Metric            | Value     | Details                                                              |
|:------------------|:----------|:---------------------------------------------------------------------|
| Lines             | 4,236     | Largest program in the entire codebase                               |
| PERFORMs          | 64        | High internal subroutine count                                       |
| EVALUATEs         | 20        | Complex branching logic                                              |
| IF Statements     | 168       | Extremely high conditional density                                   |
| Files Accessed    | 2 (RW)    | ACCTDAT (READ+REWRITE), CUSTDAT (READ+REWRITE)                      |
| Copybooks Used    | 12+       | CSUTLDWY, CSUTLDPY, CSSETATY, CSLKPCDY + all common                 |
| **Complexity**    | **10**    |                                                                      |
| **Risk**          | **9**     | Mutates two master files; handles PII (SSN, address); inline date validation; extensive field-level error handling |
| **Business Impact**| **9**    | Core account maintenance — directly affects balances, limits, customer data |
| **Priority Score**| **28/30** |                                                                      |

**Modernization concerns:** Monolithic program with 4,200+ lines. Contains
embedded date validation (CSUTLDPY/CSUTLDWY copybooks inlined as procedure
division code), phone/state/ZIP lookup tables (CSLKPCDY — 1,318 lines of
hardcoded data), and BMS field attribute manipulation (CSSETATY with
COPY REPLACING). Recommend decomposing into: (1) account service,
(2) customer service, (3) validation library.

---

### Rank 2: CBTRN02C — Transaction Posting (Batch)

| Metric            | Value     | Details                                                              |
|:------------------|:----------|:---------------------------------------------------------------------|
| Lines             | 731       |                                                                      |
| PERFORMs          | 61        | Dense procedural flow                                                |
| EVALUATEs         | 0         |                                                                      |
| IF Statements     | 48        |                                                                      |
| Files Accessed    | 6         | Reads: DALYTRAN, CARDXREF, TRANSACT, ACCTDAT, DISCGRP, TCATBALF; Writes: TRANSACT, ACCTDAT, TCATBALF |
| **Complexity**    | **8**     |                                                                      |
| **Risk**          | **10**    | Mutates 3 master files in a single batch run; financial posting logic; no inherent rollback mechanism |
| **Business Impact**| **10**   | Core nightly processing — every transaction flows through this program; failure blocks all downstream reporting and statements |
| **Priority Score**| **28/30** |                                                                      |

**Modernization concerns:** Financial posting engine touching 6 files with
3 being mutated. Includes interest rate lookups via DISCGRP and running
balance updates in TCATBALF. Sequential file processing pattern with
DALYTRAN as input. Critical to implement idempotency and transaction
boundaries during modernization.

---

### Rank 3: CBACT04C — Interest Calculation (Batch)

| Metric            | Value     | Details                                                              |
|:------------------|:----------|:---------------------------------------------------------------------|
| Lines             | 652       |                                                                      |
| PERFORMs          | 56        |                                                                      |
| EVALUATEs         | 0         |                                                                      |
| IF Statements     | 43        |                                                                      |
| Files Accessed    | 3         | Reads: ACCTDAT, DISCGRP, TCATBALF; Writes: ACCTDAT, TCATBALF        |
| **Complexity**    | **7**     |                                                                      |
| **Risk**          | **10**    | Directly modifies account balances; interest calculation logic affects every account; financial accuracy is critical |
| **Business Impact**| **9**    | Interest charges are revenue-generating; errors compound over billing cycles |
| **Priority Score**| **26/30** |                                                                      |

**Modernization concerns:** Financial calculation engine using disclosure
group interest rates applied per category balance. Uses COMP and COMP-3
arithmetic for precision. Migration must preserve exact decimal behavior
(COBOL `S9(10)V99` ≠ IEEE floating point). Recommend BigDecimal or
fixed-point arithmetic in target platform.

---

### Rank 4: COCRDUPC — Credit Card Update (Online)

| Metric            | Value     | Details                                                              |
|:------------------|:----------|:---------------------------------------------------------------------|
| Lines             | 1,560     |                                                                      |
| PERFORMs          | 26        |                                                                      |
| EVALUATEs         | 16        |                                                                      |
| IF Statements     | 74        |                                                                      |
| Files Accessed    | 1 (RW)    | CARDDAT (READ+REWRITE)                                               |
| **Complexity**    | **8**     |                                                                      |
| **Risk**          | **8**     | Mutates card master; handles CVV and expiration date; includes inline date validation and lookup tables |
| **Business Impact**| **8**    | Card maintenance affects payment processing capability               |
| **Priority Score**| **24/30** |                                                                      |

**Modernization concerns:** Second-largest online program. Contains same
inlined validation patterns as COACTUPC (CSUTLDPY, CSLKPCDY, CSSETATY).
Handles sensitive card data (CVV). Recommend extracting card service with
PCI-DSS-compliant data handling in target.

---

### Rank 5: COCRDLIC — Credit Card List (Online)

| Metric            | Value     | Details                                                              |
|:------------------|:----------|:---------------------------------------------------------------------|
| Lines             | 1,459     |                                                                      |
| PERFORMs          | 34        |                                                                      |
| EVALUATEs         | 18        |                                                                      |
| IF Statements     | 61        |                                                                      |
| Files Accessed    | 2         | CARDDAT (STARTBR, READNEXT, READPREV, ENDBR), CARDAIX (via AIX)     |
| **Complexity**    | **8**     | Complex browse logic with forward/backward pagination via STARTBR/READNEXT/READPREV/ENDBR |
| **Risk**          | **5**     | Read-only file access; no data mutation                              |
| **Business Impact**| **7**    | Primary card browsing interface; gateway to card detail/update screens |
| **Priority Score**| **20/30** |                                                                      |

**Modernization concerns:** VSAM browse pagination pattern
(STARTBR→READNEXT→ENDBR) with bidirectional scrolling is a common
migration challenge. The alternate index access (CARDAIX) needs equivalent
secondary index in target database. Cross-screen XCTL flow to
COCRDSLC/COCRDUPC must be preserved.

---

### Rank 6: CBSTM03A — Statement Generation (Batch)

| Metric            | Value     | Details                                                              |
|:------------------|:----------|:---------------------------------------------------------------------|
| Lines             | 924       |                                                                      |
| PERFORMs          | 29        |                                                                      |
| EVALUATEs         | 9         |                                                                      |
| IF Statements     | 15        |                                                                      |
| Files Accessed    | 4+ (R)    | TRANSACT (sorted), CARDXREF, ACCTDAT, CUSTDAT → writes GDG statement files |
| Calls             | CBSTM03B  | Delegates file I/O to subroutine                                     |
| **Complexity**    | **7**     | Multi-file reads, report formatting, GDG output, subroutine call     |
| **Risk**          | **6**     | Read-only on source files; generates output GDG members (text + HTML)|
| **Business Impact**| **8**    | Customer-facing statements; regulatory compliance artifact           |
| **Priority Score**| **21/30** |                                                                      |

**Modernization concerns:** Generates both text and HTML statement formats.
Uses GDG (Generation Data Group) for versioned output — needs equivalent
file versioning in target. CALL to CBSTM03B for I/O isolation is a good
pattern to preserve. Report layout logic (column positioning, page breaks)
is tightly coupled to 132-column print format.

---

### Rank 7: COTRTLIC — Transaction Type List (Online/DB2)

| Metric            | Value     | Details                                                              |
|:------------------|:----------|:---------------------------------------------------------------------|
| Lines             | 2,098     |                                                                      |
| PERFORMs          | 63        |                                                                      |
| EVALUATEs         | 32        |                                                                      |
| IF Statements     | 88        |                                                                      |
| Files Accessed    | DB2       | SELECT from TRAN_TYPE, TRAN_CAT tables                               |
| **Complexity**    | **9**     | High line count, embedded SQL, complex EVALUATE chains               |
| **Risk**          | **4**     | Read-only DB2 access; reference data only                            |
| **Business Impact**| **5**    | Admin-only reference data management; not customer-facing            |
| **Priority Score**| **18/30** |                                                                      |

**Modernization concerns:** Embedded SQL (`EXEC SQL ... END-EXEC`) mixed
with CICS terminal handling. DB2 host variable mapping and SQLCA error
handling patterns differ from VSAM programs. DSNTIAC message formatting
via CALL adds DB2-specific dependency.

---

### Rank 8: COTRN02C — Transaction Add (Online)

| Metric            | Value     | Details                                                              |
|:------------------|:----------|:---------------------------------------------------------------------|
| Lines             | 783       |                                                                      |
| PERFORMs          | 61        | Very high for its line count — dense procedural flow                 |
| EVALUATEs         | 26        |                                                                      |
| IF Statements     | 14        |                                                                      |
| Files Accessed    | 3         | TRANSACT (STARTBR, READPREV, ENDBR, WRITE), CXACAIX (READ), ACCTDAT (READ) |
| Calls             | CSUTLDTC  | Date validation subroutine                                           |
| **Complexity**    | **7**     | High PERFORM density; multi-file coordination; date validation calls |
| **Risk**          | **7**     | Creates new transaction records; generates unique TRAN-ID via READPREV on TRANSACT |
| **Business Impact**| **8**    | Direct transaction creation — data entry path for all manual transactions |
| **Priority Score**| **22/30** |                                                                      |

**Modernization concerns:** Unique ID generation pattern uses READPREV on
TRANSACT file to find highest existing ID, then increments. This pattern
needs replacement with a sequence generator. Cross-reference lookup via
CXACAIX alternate index validates card-to-account mapping before write.

---

### Rank 9: COPAUS0C — Pending Authorization Summary (Online/IMS)

| Metric            | Value     | Details                                                              |
|:------------------|:----------|:---------------------------------------------------------------------|
| Lines             | 1,032     |                                                                      |
| PERFORMs          | 46        |                                                                      |
| EVALUATEs         | 22        |                                                                      |
| IF Statements     | 25        |                                                                      |
| Files Accessed    | 3 VSAM + IMS | ACCTDAT, CARDDAT, CUSTDAT (CICS READ) + IMS DL/I calls          |
| **Complexity**    | **8**     | Multi-technology: CICS + IMS DL/I + VSAM                            |
| **Risk**          | **6**     | Read-only across all access methods                                  |
| **Business Impact**| **6**    | Authorization monitoring; fraud detection workflow                   |
| **Priority Score**| **20/30** |                                                                      |

**Modernization concerns:** Spans three data access technologies
(CICS VSAM, IMS DL/I hierarchical, MQ). The IMS PCB (Program Communication
Block) and SSA (Segment Search Argument) patterns require specific migration
handling. Most complex integration point in the application.

---

### Rank 10: CBTRN03C — Transaction Report (Batch)

| Metric            | Value     | Details                                                              |
|:------------------|:----------|:---------------------------------------------------------------------|
| Lines             | 649       |                                                                      |
| PERFORMs          | 72        | Highest PERFORM count relative to size in codebase                   |
| EVALUATEs         | 4         |                                                                      |
| IF Statements     | 38        |                                                                      |
| Files Accessed    | 5 (R) + 1 (W) | TRANSACT, CARDXREF, TRANTYPE, TRANCATG, DATEPARM → Report file |
| **Complexity**    | **7**     | 72 PERFORMs in 649 lines = very high procedural density              |
| **Risk**          | **4**     | Read-only on source files; generates output report                   |
| **Business Impact**| **7**    | Daily transaction report — operational visibility and audit trail    |
| **Priority Score**| **18/30** |                                                                      |

**Modernization concerns:** Five input files with reference data lookups
(TRANTYPE, TRANCATG). Report layout uses CVTRA07Y copybook with fixed-width
column formatting (133-char line width). Page/account/grand totals with
running accumulators. Date parameter file controls report date range.

---

## Priority Matrix Summary

| Rank | Program  | Type   | Lines | Complexity | Risk | Impact | **Total** | Key Concern                                    |
|-----:|:---------|:-------|------:|-----------:|-----:|-------:|----------:|:-----------------------------------------------|
|    1 | COACTUPC | Online | 4,236 |         10 |    9 |      9 |    **28** | Monolithic; dual-file mutation; PII             |
|    2 | CBTRN02C | Batch  |   731 |          8 |   10 |     10 |    **28** | Financial posting; 6-file I/O; no rollback      |
|    3 | CBACT04C | Batch  |   652 |          7 |   10 |      9 |    **26** | Interest calculation; decimal precision          |
|    4 | COCRDUPC | Online | 1,560 |          8 |    8 |      8 |    **24** | Card data mutation; CVV handling                 |
|    5 | COTRN02C | Online |   783 |          7 |    7 |      8 |    **22** | Transaction creation; unique ID generation       |
|    6 | CBSTM03A | Batch  |   924 |          7 |    6 |      8 |    **21** | Statement generation; GDG output; dual format    |
|    7 | COCRDLIC | Online | 1,459 |          8 |    5 |      7 |    **20** | VSAM browse pagination; AIX access               |
|    8 | COPAUS0C | Online | 1,032 |          8 |    6 |      6 |    **20** | Multi-technology (CICS+IMS+VSAM+MQ)             |
|    9 | COTRTLIC | Online | 2,098 |          9 |    4 |      5 |    **18** | Embedded SQL; DB2 integration                    |
|   10 | CBTRN03C | Batch  |   649 |          7 |    4 |      7 |    **18** | 5-file report; high PERFORM density              |

---

## Cross-Cutting Risk Themes

### 1. Plaintext Password Storage (CSUSR01Y)
`SEC-USR-PWD PIC X(08)` stores passwords in plaintext within the USRSEC VSAM
file. Affects: COSGN00C, COUSR00C, COUSR01C, COUSR02C, COUSR03C. Modernization
must introduce hashing/encryption.

### 2. Hardcoded Lookup Tables (CSLKPCDY — 1,318 lines)
Phone area codes, US state codes, and ZIP prefix validation are embedded as
COBOL `88`-level VALUE clauses. Used by COACTUPC and COCRDUPC. Must be
externalized to a database or configuration service.

### 3. Inlined Procedure Division Copybooks (CSUTLDPY — 375 lines)
Date validation logic is COPY'd into the Procedure Division of multiple
programs (COACTUPC, COCRDUPC, COTRN02C, CORPT00C). This creates code
duplication at compile time. Modernize as a shared validation service.

### 4. COMP/COMP-3 Numeric Precision
The export layout (CVEXPORT) and IMS segments (CIPAUDTY, CIPAUSMY) use
packed decimal and binary formats. Financial calculations in CBACT04C and
CBTRN02C rely on COBOL's exact decimal arithmetic (`S9(10)V99`). Migration
to Java/C# must use BigDecimal equivalents, not floating-point.

### 5. VSAM Browse Pagination Pattern
Programs using STARTBR→READNEXT/READPREV→ENDBR (COCRDLIC, COTRN00C,
COUSR00C, COBIL00C) implement cursor-based pagination. This maps to
database cursor or keyset pagination in target — offset-based pagination
will not produce equivalent behavior.

### 6. GDG (Generation Data Group) File Versioning
Statement generation (CBSTM03A/CREASTMT JCL) outputs to GDG datasets that
maintain N generations. The target platform needs equivalent file versioning
or timestamped object storage.

---

## Recommended Modernization Sequence

Based on priority scores and dependency analysis:

| Phase | Programs                              | Rationale                                                     |
|:------|:--------------------------------------|:--------------------------------------------------------------|
| **1** | CBTRN02C, CBACT04C                    | Financial core — must get right first; batch is easier to test in isolation |
| **2** | COACTUPC, COCRDUPC                    | Largest online programs; extract shared validation services first |
| **3** | COTRN02C, COCRDLIC, CBSTM03A         | Transaction CRUD and card browsing; statement generation       |
| **4** | COPAUS0C, COTRTLIC, CBTRN03C          | Multi-technology integration and reporting; defer complexity   |
| **5** | Remaining 34 programs                 | Smaller utilities, menus, and data load programs               |
