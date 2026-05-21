# CardDemo — Gap Analysis

## Methodology

This analysis evaluates the CardDemo codebase against seven modern engineering best-practice categories. Each gap is rated by:

- **Severity**: Critical / High / Medium / Low
- **Effort**: Small (< 1 week) / Medium (1–4 weeks) / Large (> 4 weeks)

The assessment accounts for the fact that CardDemo is a *mainframe COBOL/CICS application designed for migration testing*, not a modern cloud-native service. Gaps are framed in terms of what would need to be addressed during or after modernization.

---

## 1. Code Organization

### 1.1 Flat program directory structure
**Severity: Medium | Effort: Small**

All 31 core COBOL programs reside in a single `app/cbl/` directory with no sub-grouping by function. Batch programs (CB*) and online programs (CO*) are distinguished only by naming convention. While this is standard on z/OS (partitioned datasets are flat), it creates confusion when onboarding engineers unfamiliar with mainframe conventions.

### 1.2 Naming conventions are implicit, not documented
**Severity: Low | Effort: Small**

The codebase uses consistent prefixes (CB=batch, CO=online CICS, CV=VSAM copybook, CS=shared copybook, COMEN=menu, COSGN=sign-on) but these are not documented anywhere in the repository. New contributors must infer the naming system.

### 1.3 Optional modules are well-separated
**Positive Finding**

The three optional extensions (IMS-DB2-MQ, DB2 Transaction Types, VSAM-MQ) are cleanly separated into `app/app-*/` directories with their own `cbl/`, `cpy/`, `bms/`, `jcl/`, and `README.md` files. This is a good modular pattern.

### 1.4 No shared utility library
**Severity: Medium | Effort: Medium**

Common functionality (date handling, input validation, error message formatting) is duplicated across programs. While `CSUTLDTC` and `CODATECN` provide some shared date utilities, validation logic in `COACTUPC` (4,236 lines) is entirely inline and not reusable by other programs.

### 1.5 Inconsistent source formatting
**Severity: Low | Effort: Small**

COBOL source files use mixed formatting styles: some use fixed-format columns with sequence numbers (CBACT01C), others use free-format indentation (COSGN00C). Some files use uppercase (CBSTM03B.CBL), others lowercase extensions (CBACT01C.cbl). The `CUSTREC.cpy` copybook contains tab characters that break compilation.

### 1.6 Dead / unused code
**Severity: Low | Effort: Small**

`UNUSED1Y.cpy` exists as an explicitly unused copybook. Several copybook fields use `FILLER` for padding, which is normal for COBOL but creates large opaque record areas that are difficult to interpret.

---

## 2. Error Handling

### 2.1 No centralized error handling framework
**Severity: High | Effort: Medium**

Each program implements its own error handling pattern independently. Online programs check `WS-RESP-CD` after CICS commands but handle errors inline. Batch programs check file-status codes individually. There is no shared error-handling paragraph, copybook, or subroutine.

### 2.2 Inconsistent file-status checking
**Severity: High | Effort: Medium**

Batch programs check VSAM file-status codes (e.g., `DALYTRAN-STATUS`, `TRANFILE-STATUS`) but the rigor varies. Some programs perform detailed EVALUATE on status codes; others only check for `'00'` (success) and fall through on unexpected codes without logging or aborting.

### 2.3 Silent failures in batch processing
**Severity: Critical | Effort: Medium**

`CBTRN02C` (transaction posting) writes rejected records to a reject file (`DALYREJS`) but does not set a non-zero return code or raise an ABEND when validation failures exceed a threshold. A batch run could process zero valid transactions and still appear to succeed.

### 2.4 CICS RESP code handling is minimal
**Severity: Medium | Effort: Small**

Online programs typically check for RESP code 0 (success) and 13 (NOTFND) but do not handle other common conditions like DUPKEY (14), INVREQ (16), IOERR (17), or LENGERR (22). Unexpected CICS conditions could cause unhandled abends.

### 2.5 No structured error messages or codes
**Severity: Medium | Effort: Medium**

Error messages are hardcoded inline strings (e.g., `'Please enter User ID ...'`, `'User not found. Try again ...'`). There is no message catalog, error code system, or externalized message resource. The shared `CSMSG01Y` copybook contains only two generic messages.

---

## 3. Testing

### 3.1 No automated test suite
**Severity: Critical | Effort: Large**

The repository contains zero test files — no unit tests, integration tests, or regression tests. There is no test framework, test harness, or test data generation tooling. This is common for legacy mainframe applications but is the single largest gap for modernization.

### 3.2 No test data generation or management
**Severity: High | Effort: Medium**

Sample data files in `app/data/` are static snapshots. There is no mechanism to generate fresh test data, reset test environments, or validate data integrity across files (e.g., ensuring cross-reference records match account and card records).

### 3.3 No compilation verification in CI
**Severity: High | Effort: Small**

The repository has no CI/CD pipeline configuration (no `.github/workflows/`, no `Jenkinsfile`, no `buildspec.yml`). Compilation errors (like the existing CBEXPORT/CBIMPORT failures and CBSTM03A tab issue) are not caught automatically.

### 3.4 Batch programs are not independently testable
**Severity: Medium | Effort: Medium**

Batch programs read from VSAM KSDS files that require specific dataset definitions and indexed file organization. Running batch programs outside z/OS requires converting flat ASCII data to Berkeley DB indexed files, which is not automated.

---

## 4. Security

### 4.1 Plaintext password storage
**Severity: Critical | Effort: Small**

User passwords are stored in plaintext in the USRSEC VSAM file (CSUSR01Y: `SEC-USR-PWD PIC X(08)`). The sign-on program (COSGN00C) performs direct string comparison: `IF SEC-USR-PWD = WS-USER-PWD`. No hashing, salting, or encryption is used.

### 4.2 Hardcoded default credentials
**Severity: High | Effort: Small**

The README documents default credentials (`ADMIN001/PASSWORD`, `USER0001/PASSWORD`) that are loaded from sample data files. These credentials are committed to the repository and would be present in any deployment using the sample data.

### 4.3 No password complexity or lockout policy
**Severity: High | Effort: Small**

Passwords are limited to 8 characters (`PIC X(08)`) with no complexity requirements. There is no account lockout mechanism after failed login attempts; users can retry indefinitely. No password expiration or rotation policy exists.

### 4.4 SSN stored without encryption
**Severity: Critical | Effort: Medium**

Customer Social Security Numbers are stored in plaintext (`CUST-SSN PIC 9(09)` in CVCUS01Y). This data flows through batch programs (CBCUS01C, CBEXPORT) and online screens without masking or encryption, violating PCI-DSS and privacy regulations.

### 4.5 No input sanitization for CICS screens
**Severity: Medium | Effort: Medium**

While COACTUPC performs extensive field-level validation (phone number format, alpha-only, yes/no), most online programs do minimal input validation. BMS maps define field lengths but there is no systematic sanitization against injection or buffer overflow patterns.

### 4.6 RACF security relies on external configuration
**Severity: Low | Effort: Small**

Application-level security is handled by the USRSEC file, not RACF. A sample `RACFCMDS.jcl` exists in `samples/jcl/` but RACF integration is not part of the core application. In a modernized environment, this would need to map to IAM/OIDC.

---

## 5. API Design

### 5.1 No REST API or service interface
**Severity: High | Effort: Large**

All business functionality is exposed exclusively through 3270 terminal screens (BMS maps + CICS transactions). There are no REST endpoints, SOAP services, or any HTTP-based interface. Modernization requires extracting business logic into callable services.

### 5.2 Tightly coupled UI and business logic
**Severity: High | Effort: Large**

Online COBOL programs (e.g., COACTUPC at 4,236 lines) mix screen handling (SEND MAP, RECEIVE MAP), business validation, VSAM I/O, and navigation control in a single program. The pseudo-conversational pattern embeds state management in the COMMAREA structure, making it difficult to extract business logic independently.

### 5.3 COMMAREA as implicit API contract
**Severity: Medium | Effort: Medium**

The CARDDEMO-COMMAREA (COCOM01Y) serves as the inter-program data contract but carries minimal context: source/target transaction IDs, user identity, account/card/customer IDs, and last map info. Business data is passed indirectly via VSAM reads in the target program, not through the COMMAREA.

### 5.4 No API documentation or OpenAPI specification
**Severity: Medium | Effort: Medium**

Transaction IDs and their functions are documented only in the README tables. There is no machine-readable API specification. The MQ message formats (request/response) for optional modules are documented in markdown but not as formal schemas.

### 5.5 No pagination metadata in list screens
**Severity: Low | Effort: Small**

List screens (COCRDLIC, COTRN00C, COUSR00C) implement manual pagination using PF7/PF8 keys for forward/backward browsing. There is no total count, page number, or result-set metadata displayed to the user.

---

## 6. Observability

### 6.1 No structured logging
**Severity: High | Effort: Medium**

Programs use DISPLAY statements for batch output and BMS error message fields for online feedback. There is no logging framework, log levels, timestamps on log entries, or structured log format. Batch programs write to SYSOUT but with ad-hoc formatting.

### 6.2 No health checks
**Severity: Medium | Effort: Small**

There is no health check transaction, monitoring program, or heartbeat mechanism. CICS region health is typically monitored externally, but the application provides no self-diagnostic capability.

### 6.3 No metrics or counters
**Severity: Medium | Effort: Medium**

Batch programs do not emit record counts, processing times, or throughput metrics in a machine-parseable format. While CBTRN02C maintains counters for processed/rejected records, these are written to SYSOUT as unstructured text.

### 6.4 No distributed tracing
**Severity: Low | Effort: Large**

Cross-program execution (XCTL chains, MQ request/response, batch job sequences) has no correlation ID or trace context. The Control-M scheduler provides job-level dependency tracking but no intra-job tracing.

### 6.5 No audit trail
**Severity: High | Effort: Medium**

User actions (account updates, card changes, user management) are not logged to an audit file. Transaction records capture financial activity but not who initiated the change or from which terminal. There is no change-tracking or before/after image capture.

---

## 7. Resilience

### 7.1 No retry logic for I/O operations
**Severity: High | Effort: Medium**

VSAM file operations in both batch and online programs have no retry mechanism. If a CICS READ or WRITE fails with a transient error (IOERR, LOADING), the operation fails immediately. Batch file I/O failures cause immediate program termination.

### 7.2 No circuit breaker or fallback patterns
**Severity: Medium | Effort: Large**

MQ-based operations (authorization processing, account extraction) have no timeout, circuit breaker, or fallback behavior. If the MQ queue is unavailable, the CICS trigger program will fail without graceful degradation.

### 7.3 Batch jobs lack idempotency
**Severity: High | Effort: Medium**

Re-running batch jobs (e.g., POSTTRAN) without re-initializing data can result in duplicate postings. The daily transaction file is processed sequentially without checking if records have already been posted. The TRANBKP job (backup before posting) provides a recovery point but not idempotent replay.

### 7.4 No graceful degradation for optional modules
**Severity: Medium | Effort: Small**

If DB2, IMS, or MQ subsystems are unavailable, the corresponding menu options are still displayed. Selecting them would result in an abend rather than a user-friendly error message. The menu copybooks (COMEN02Y, COADM02Y) have hardcoded option counts.

### 7.5 Single-threaded batch processing
**Severity: Low | Effort: Large**

All batch programs process files sequentially in a single thread. For large transaction volumes, there is no partitioning, parallel processing, or checkpointing. Job restart requires re-processing from the beginning.

---

## Summary Table

| # | Category | Gap | Severity | Effort |
|:--|:---------|:----|:---------|:-------|
| 1.1 | Code Organization | Flat program directory structure | Medium | Small |
| 1.2 | Code Organization | Naming conventions undocumented | Low | Small |
| 1.4 | Code Organization | No shared utility library | Medium | Medium |
| 1.5 | Code Organization | Inconsistent source formatting | Low | Small |
| 1.6 | Code Organization | Dead/unused code | Low | Small |
| 2.1 | Error Handling | No centralized error handling framework | High | Medium |
| 2.2 | Error Handling | Inconsistent file-status checking | High | Medium |
| 2.3 | Error Handling | Silent failures in batch processing | Critical | Medium |
| 2.4 | Error Handling | CICS RESP code handling is minimal | Medium | Small |
| 2.5 | Error Handling | No structured error messages/codes | Medium | Medium |
| 3.1 | Testing | No automated test suite | Critical | Large |
| 3.2 | Testing | No test data generation | High | Medium |
| 3.3 | Testing | No compilation verification in CI | High | Small |
| 3.4 | Testing | Batch programs not independently testable | Medium | Medium |
| 4.1 | Security | Plaintext password storage | Critical | Small |
| 4.2 | Security | Hardcoded default credentials | High | Small |
| 4.3 | Security | No password complexity/lockout | High | Small |
| 4.4 | Security | SSN stored without encryption | Critical | Medium |
| 4.5 | Security | No input sanitization | Medium | Medium |
| 4.6 | Security | RACF relies on external config | Low | Small |
| 5.1 | API Design | No REST API or service interface | High | Large |
| 5.2 | API Design | Tightly coupled UI and business logic | High | Large |
| 5.3 | API Design | COMMAREA as implicit API contract | Medium | Medium |
| 5.4 | API Design | No API documentation / OpenAPI spec | Medium | Medium |
| 5.5 | API Design | No pagination metadata | Low | Small |
| 6.1 | Observability | No structured logging | High | Medium |
| 6.2 | Observability | No health checks | Medium | Small |
| 6.3 | Observability | No metrics or counters | Medium | Medium |
| 6.4 | Observability | No distributed tracing | Low | Large |
| 6.5 | Observability | No audit trail | High | Medium |
| 7.1 | Resilience | No retry logic for I/O | High | Medium |
| 7.2 | Resilience | No circuit breaker / fallback | Medium | Large |
| 7.3 | Resilience | Batch jobs lack idempotency | High | Medium |
| 7.4 | Resilience | No graceful degradation for optional modules | Medium | Small |
| 7.5 | Resilience | Single-threaded batch processing | Low | Large |

### Severity Distribution

| Severity | Count |
|:---------|------:|
| Critical | 4 |
| High | 14 |
| Medium | 12 |
| Low | 5 |

### Top Critical Items

1. **Plaintext password storage** (4.1) — Direct compliance violation
2. **SSN stored without encryption** (4.4) — PCI-DSS / privacy violation
3. **No automated test suite** (3.1) — Blocks safe modernization
4. **Silent failures in batch processing** (2.3) — Data integrity risk
