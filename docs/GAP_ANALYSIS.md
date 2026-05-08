# CardDemo Engineering Standards Gap Analysis

## Overview

This document evaluates the CardDemo COBOL/CICS mainframe application against seven engineering standards categories. Each gap is assigned a unique ID, severity rating (Critical/High/Medium/Low), and effort estimate (Small/Medium/Large).

---

## 1. Code Organization

### GAP-ORG-01: Monolithic Program Structure with Embedded Business Logic
- **Severity**: High
- **Effort**: Large
- **Description**: Online CICS programs combine UI handling (BMS map send/receive), input validation, business logic, and data access in a single program. For example, `COCRDUPC.cbl` (1561 lines) handles map display, field validation, file reads, record locking, and file rewrites all in one program.
- **Evidence** (`app/cbl/COCRDUPC.cbl`):
  - Lines 1-100: Working storage with mixed UI, validation, and data fields
  - Lines 400-600: BMS map receive interleaved with validation logic
  - Lines 800-1000: VSAM file access mixed with business rule checks
  - Lines 1200-1500: Update logic with embedded error message formatting

### GAP-ORG-02: Inconsistent Naming Conventions Across Programs
- **Severity**: Medium
- **Effort**: Medium
- **Description**: Program naming follows a pattern (`CO` prefix for online, `CB` prefix for batch) but internal paragraph/section naming is inconsistent. Some programs use numeric prefixes (e.g., `1000-PROCESS-INPUTS`, `9000-READ-ACCT`) while others use descriptive names (e.g., `PROCESS-ENTER-KEY`, `SEND-TRNVIEW-SCREEN`). Copybooks mix formats: some use sequence numbers (`COADM02Y.cpy`) while others do not.
- **Evidence**:
  - `COBIL00C.cbl`: Uses `1000-SEND-MAP`, `2000-PROC-INPUTS`, `9100-GETCARD-BYACCTID`
  - `COTRN01C.cbl`: Uses `PROCESS-ENTER-KEY`, `SEND-TRNVIEW-SCREEN`, `RECEIVE-TRNVIEW-SCREEN`
  - `COADM02Y.cpy`: Contains COBOL sequence numbers; `COMEN02Y.cpy`: Does not

### GAP-ORG-03: Duplicated Data Structure Definitions
- **Severity**: Medium
- **Effort**: Small
- **Description**: The Customer record structure is defined in both `CVCUS01Y.cpy` and `CUSTREC.cpy` with identical fields but slightly different formatting (tabs vs. spaces). This creates maintenance risk if one copy is updated without the other.
- **Evidence**:
  - `app/cpy/CVCUS01Y.cpy`: Uses consistent spacing, field `CUST-DOB-YYYY-MM-DD`
  - `app/cpy/CUSTREC.cpy`: Uses tab indentation, field `CUST-DOB-YYYYMMDD` (different name for same field)

### GAP-ORG-04: Missing Modular Separation for Common Operations
- **Severity**: Medium
- **Effort**: Medium
- **Description**: Common operations like VSAM file status checking, error message formatting, and date validation are repeated across programs rather than centralized. While `CSUTLDTC` exists for date validation, most programs implement their own file status handling inline.
- **Evidence**:
  - VSAM file status check pattern repeated in `COBIL00C.cbl` (lines 440-470), `COTRN02C.cbl` (lines 600-630), `CBTRN02C.cbl` (lines 500-530)
  - Error message construction with `STRING` repeated across `COUSR01C.cbl` (line 200), `COCRDUPC.cbl` (line 900), `COBIL00C.cbl` (line 350)

### GAP-ORG-05: No Separation of Configuration from Code
- **Severity**: Medium
- **Effort**: Medium
- **Description**: Menu options, screen titles, and application constants are hardcoded in copybooks (`COMEN02Y.cpy`, `COADM02Y.cpy`, `COTTL01Y.cpy`, `CSMSG01Y.cpy`) rather than externalized. Adding a new menu option requires modifying copybook source, recompiling, and redeploying all programs that include it.
- **Evidence**:
  - `app/cpy/COMEN02Y.cpy`: 11 menu options hardcoded with program names
  - `app/cpy/COADM02Y.cpy`: 6 admin options hardcoded
  - `app/cpy/COTTL01Y.cpy`: Screen titles hardcoded
  - `app/cpy/CSMSG01Y.cpy`: Error messages hardcoded (only 2 common messages)

---

## 2. Error Handling

### GAP-ERR-01: Inconsistent CICS Error Handling Strategy
- **Severity**: High
- **Effort**: Medium
- **Description**: Some programs use `EXEC CICS HANDLE ABEND` with a label for centralized error handling, while others check `RESP` and `RESP2` inline. A few programs mix both approaches. There is no standard error handling framework.
- **Evidence**:
  - `COSGN00C.cbl`: Uses `HANDLE ABEND LABEL(ABEND-ROUTINE)` (line ~60)
  - `COBIL00C.cbl`: Uses inline `RESP(WS-RESP-CD) RESP2(WS-REAS-CD)` checking (lines 440-470)
  - `COCRDUPC.cbl`: Uses both `HANDLE CONDITION` for some operations and inline `RESP` for others

### GAP-ERR-02: Missing File Status Validation in Some Programs
- **Severity**: High
- **Effort**: Small
- **Description**: While batch programs (`CBTRN02C`, `CBACT04C`) consistently check file status after every I/O operation, some online programs only check for specific expected conditions (NORMAL, NOTFND) and fall through to a generic error for all others, potentially masking I/O errors.
- **Evidence**:
  - `COBIL00C.cbl`: Checks `DFHRESP(NORMAL)` and `DFHRESP(NOTFND)` but uses generic `MOVE` for other conditions
  - `CBTRN02C.cbl` (batch): Comprehensive file status checking after every OPEN, READ, WRITE, CLOSE with specific handling per status code

### GAP-ERR-03: ABEND Handling Does Not Log Diagnostic Context
- **Severity**: Medium
- **Effort**: Small
- **Description**: ABEND handlers in online programs display a generic error message to the user but do not write diagnostic information (program state, last file operation, variable values) to a log or transient data queue. This makes production debugging difficult.
- **Evidence**:
  - `COSGN00C.cbl`: ABEND-ROUTINE moves a generic message and sends the map — no logging
  - `COMEN01C.cbl`: Similar pattern — error message to screen only, no TD WRITE

### GAP-ERR-04: No Retry Logic for Transient Failures
- **Severity**: Medium
- **Effort**: Medium
- **Description**: VSAM file operations that could experience transient failures (record lock contention, buffer exhaustion) are attempted once and fail immediately. There is no retry with backoff pattern for operations like `READ UPDATE`.
- **Evidence**:
  - `COCRDUPC.cbl`: `EXEC CICS READ UPDATE` with immediate error handling on failure
  - `COBIL00C.cbl`: Single attempt for account balance update

---

## 3. Testing

### GAP-TST-01: Zero Automated Test Coverage
- **Severity**: Critical
- **Effort**: Large
- **Description**: The repository contains no automated tests of any kind — no unit tests, no integration tests, no regression test scripts. There are no test frameworks, test data generators, or test execution JCL. The only verification mechanism is manual testing via 3270 terminal interaction.
- **Evidence**:
  - No `test/`, `tests/`, `spec/`, or `tst/` directories in the repository
  - No test-related JCL jobs in `app/jcl/`
  - No test framework references in any source file
  - README.md describes manual setup and verification only

### GAP-TST-02: No Test Data Management Strategy
- **Severity**: High
- **Effort**: Medium
- **Description**: Sample data files in `app/data/` are provided as flat files but there is no mechanism to reset data to a known state, generate test data programmatically, or manage test data lifecycle. Repeated testing corrupts the base dataset with no automated reset.
- **Evidence**:
  - `app/data/ASCII/` and `app/data/EBCDIC/` contain static sample data
  - No data reset JCL or programs exist
  - No data generation utilities

### GAP-TST-03: No Batch Job Output Validation
- **Severity**: High
- **Effort**: Medium
- **Description**: Batch programs (`CBTRN02C`, `CBACT04C`, `CBSTM03A`) produce output files and set return codes, but there is no automated verification that output is correct. The daily transaction posting program (`CBTRN02C`) writes rejected records to `DALYREJS` but nothing validates the rejections file or verifies posted record accuracy.
- **Evidence**:
  - `CBTRN02C.cbl`: Sets `RETURN-CODE = 4` on rejects but no downstream validation
  - JCL jobs in `app/jcl/` contain no `COND` parameter checking between steps (beyond basic RC checks)

---

## 4. Security

### GAP-SEC-01: Plaintext Password Storage
- **Severity**: Critical
- **Effort**: Medium
- **Description**: User passwords are stored in plaintext in the `USRSEC` VSAM file. The `SEC-USR-PWD` field is defined as `PIC X(08)` — an 8-character cleartext string. Authentication in `COSGN00C` performs a direct string comparison. There is no hashing, salting, or encryption.
- **Evidence** (`app/cpy/CSUSR01Y.cpy`, line 21):
  ```cobol
  05 SEC-USR-PWD                PIC X(08).
  ```
  `COSGN00C.cbl` (line ~130): Direct comparison of input password with stored plaintext value.

### GAP-SEC-02: No Password Complexity or Rotation Policies
- **Severity**: High
- **Effort**: Small
- **Description**: The 8-character password field has no complexity requirements enforced in code. No password history, expiration date, or lockout mechanism exists. User creation (`COUSR01C`) accepts any 8-character value.
- **Evidence**:
  - `COUSR01C.cbl`: Validates password is not empty but no complexity checks
  - `CSUSR01Y.cpy`: No password history fields, no last-change date field, no failed-attempt counter

### GAP-SEC-03: SSN and PII Stored Without Encryption
- **Severity**: Critical
- **Effort**: Large
- **Description**: Customer Social Security Numbers (`CUST-SSN`, PIC 9(09)) and government-issued IDs (`CUST-GOVT-ISSUED-ID`, PIC X(20)) are stored in plaintext in the `CUSTDAT` VSAM file. No field-level encryption or masking is applied at rest or in transit.
- **Evidence** (`app/cpy/CVCUS01Y.cpy`, lines 17-18):
  ```cobol
  05  CUST-SSN                     PIC 9(09).
  05  CUST-GOVT-ISSUED-ID          PIC X(20).
  ```

### GAP-SEC-04: CVV Stored in Persistent Data File
- **Severity**: Critical
- **Effort**: Medium
- **Description**: Card CVV codes are stored persistently in the `CARDDAT` VSAM file (`CARD-CVV-CD`, PIC 9(03)). PCI DSS prohibits storing CVV/CVC data after authorization. The card record retains CVV for the lifetime of the record.
- **Evidence** (`app/cpy/CVACT02Y.cpy`, line 7):
  ```cobol
  05  CARD-CVV-CD                  PIC 9(03).
  ```

### GAP-SEC-05: No Audit Trail for Security-Sensitive Operations
- **Severity**: High
- **Effort**: Medium
- **Description**: There is no audit logging for sign-on attempts (successful or failed), user creation/modification/deletion, account updates, or bill payments. Failed login attempts are not counted or recorded.
- **Evidence**:
  - `COSGN00C.cbl`: Failed login displays error message but does not log the attempt
  - `COUSR01C.cbl`: User creation has no audit write
  - `COBIL00C.cbl`: Bill payments modify account balance with no audit record beyond the transaction file

### GAP-SEC-06: No Input Sanitization for Injection-Style Attacks
- **Severity**: Medium
- **Effort**: Small
- **Description**: While COBOL/CICS is less susceptible to traditional injection attacks (SQL injection, XSS), the statement generation program (`CBSTM03A`) generates HTML output with inline customer data. Customer names, addresses, and transaction descriptions are embedded directly in HTML without encoding.
- **Evidence**:
  - `CBSTM03A.CBL`: HTML generation with embedded data (lines 600-900) — customer names and merchant descriptions are placed directly into HTML tags without HTML entity encoding

### GAP-SEC-07: No Session Timeout or Inactivity Lockout
- **Severity**: Medium
- **Effort**: Small
- **Description**: The CICS pseudo-conversational design naturally has session awareness via COMMAREA, but there is no inactivity timeout checking. A signed-in user's session (identified by COMMAREA data) persists indefinitely until the user explicitly signs out or the CICS region is recycled.
- **Evidence**:
  - No timestamp field in `COCOM01Y.cpy` COMMAREA for last-activity tracking
  - No timeout check in `COMEN01C.cbl` or `COADM01C.cbl` main menu programs

---

## 5. API Design

### GAP-API-01: Tightly Coupled Program Navigation via Hardcoded XCTL
- **Severity**: High
- **Effort**: Large
- **Description**: Inter-program navigation is implemented via `EXEC CICS XCTL PROGRAM(literal)` with program names hardcoded throughout the source. Adding or renaming a program requires changes across multiple source files. Menu option arrays in copybooks (`COMEN02Y.cpy`, `COADM02Y.cpy`) mitigate this partially but the arrays themselves are compile-time constants.
- **Evidence**:
  - `COSGN00C.cbl`: `EXEC CICS XCTL PROGRAM('COADM01C')` and `PROGRAM('COMEN01C')` hardcoded
  - `COMEN01C.cbl`: Uses table-driven dispatch from `COMEN02Y.cpy` but falls back to hardcoded program names for signon
  - `COBIL00C.cbl`: Returns to `COMEN01C` via hardcoded XCTL

### GAP-API-02: COMMAREA Size Limitations and No Versioning
- **Severity**: Medium
- **Effort**: Medium
- **Description**: The shared COMMAREA structure (`COCOM01Y.cpy`) is a fixed-layout structure with no version field. Any change to the COMMAREA layout requires simultaneous recompilation and deployment of all programs that use it. There is no forward/backward compatibility mechanism.
- **Evidence** (`app/cpy/COCOM01Y.cpy`):
  - No version identifier field in the structure
  - 48 bytes of general info + customer info + account info + additional context
  - Every online program includes this copybook and depends on its exact layout

### GAP-API-03: No External API or Service Interface
- **Severity**: High
- **Effort**: Large
- **Description**: All interaction is via 3270 terminal screens (BMS maps). There is no REST API, web service, MQ-based API, or any programmatic interface for external system integration. This makes modernization (e.g., adding a web frontend) extremely difficult without building a complete integration layer.
- **Evidence**:
  - 17 BMS map files define the entire user interface
  - No COMMAREA-based service programs designed for external callers
  - No CICS web service definitions (PIPELINE, URIMAP)

### GAP-API-04: Inconsistent Error Response Format
- **Severity**: Medium
- **Effort**: Small
- **Description**: Error messages displayed to users vary widely in format and detail level. Some programs show technical CICS response codes, others show user-friendly messages, and some simply display "Unknown Error."
- **Evidence**:
  - `COCRDUPC.cbl`: Displays `RESP: nnnn REAS: nnnn` technical codes to users
  - `COBIL00C.cbl`: Displays user-friendly "Nothing to pay for the Account" message
  - `COUSR01C.cbl`: Uses `STRING` to construct detailed "User ID already exists" messages

---

## 6. Observability

### GAP-OBS-01: No Logging Framework or Structured Logging
- **Severity**: High
- **Effort**: Medium
- **Description**: Programs produce no structured log output. There are no CICS `WRITEQ TD` calls to transient data queues, no `WTO` (Write to Operator) messages in batch programs, and no application-level logging to any destination. The only diagnostic output is counter displays in batch programs.
- **Evidence**:
  - `CBTRN02C.cbl`: Uses `DISPLAY` for final counts only — no per-record logging
  - `CBACT04C.cbl`: `DISPLAY` for interest calculation totals only
  - Online programs: No `WRITEQ TD` or logging of any kind

### GAP-OBS-02: No Performance Metrics or Instrumentation
- **Severity**: Medium
- **Effort**: Medium
- **Description**: Programs do not capture timing data, transaction throughput counts, or resource utilization metrics. There is no mechanism to detect slow transactions, identify performance degradation, or measure batch job duration at the application level.
- **Evidence**:
  - No `EXEC CICS ASKTIME`/`FORMATTIME` calls for timing instrumentation
  - No counter variables for operation tracking in online programs
  - Batch programs track record counts but not elapsed time

### GAP-OBS-03: No Health Check or Heartbeat Mechanism
- **Severity**: Medium
- **Effort**: Small
- **Description**: There is no CICS transaction or program that can be called to verify application health (file accessibility, key record counts, last batch execution time). Operational monitoring relies entirely on CICS region-level metrics.
- **Evidence**:
  - No health-check program exists in `app/cbl/`
  - No monitoring-related JCL in `app/jcl/`
  - CICS resources (CSD file) defines application programs but no monitoring transactions

---

## 7. Resilience

### GAP-RES-01: No Graceful Degradation for File Unavailability
- **Severity**: High
- **Effort**: Medium
- **Description**: If any VSAM file becomes unavailable (closed, damaged, or in use by batch), online programs will ABEND or display a cryptic error. There is no circuit-breaker pattern, fallback behavior, or user-friendly "system temporarily unavailable" response.
- **Evidence**:
  - `COBIL00C.cbl`: CICS file commands have RESP checking but no fallback for FILENOTFOUND or DISABLED conditions
  - `COACTVWC.cbl`: Reads multiple files (ACCTDAT, CARDDAT, CUSTDAT) — failure of any one aborts the entire operation

### GAP-RES-02: No Transaction Rollback for Multi-File Updates
- **Severity**: Critical
- **Effort**: Large
- **Description**: Operations that update multiple files (bill payment updates both `TRANSACT` and `ACCTDAT`; daily posting updates `TRANSACT`, `ACCTDAT`, and `TCATBAL`) do not use CICS syncpoint or any compensating transaction pattern. If the second write fails after the first succeeds, data is left in an inconsistent state.
- **Evidence**:
  - `COBIL00C.cbl` (bill payment): Writes to `TRANSACT` (line ~380), then updates `ACCTDAT` (line ~420). If the account update fails, the transaction record is orphaned.
  - `CBTRN02C.cbl` (daily posting): Updates `TRANSACT` then `TCATBAL` — no rollback if second update fails

### GAP-RES-03: Single Points of Failure in Batch Chain
- **Severity**: High
- **Effort**: Medium
- **Description**: Batch processing follows a strict sequential chain (transaction posting -> interest calculation -> statement generation). If any job fails midway, there is no restart/recovery mechanism beyond re-running the entire job. JCL jobs do not use checkpoint/restart facilities.
- **Evidence**:
  - `app/jcl/` job definitions: No `SYSCHK` DD or `RD=R` parameter for restart
  - `CBTRN02C.cbl`: Processes entire file sequentially with no intermediate commit points
  - No GDG (Generation Data Group) definitions for historical data versioning

### GAP-RES-04: No Duplicate Transaction Detection
- **Severity**: High
- **Effort**: Medium
- **Description**: The daily transaction posting program (`CBTRN02C`) does not check whether a transaction has already been posted. If the daily file is reprocessed (e.g., after a job scheduling error), duplicate transactions will be written to `TRANSACT` and balances will be double-counted.
- **Evidence**:
  - `CBTRN02C.cbl`: Validates card number and account exist but does not check for duplicate `TRAN-ID` in `TRANSACT` before writing
  - No idempotency token or processing-date flag in the daily transaction record

### GAP-RES-05: No Data Backup or Recovery Procedures
- **Severity**: High
- **Effort**: Medium
- **Description**: The repository contains no backup JCL, no REPRO export procedures, and no point-in-time recovery strategy. VSAM files are the single source of truth with no secondary copy or journal.
- **Evidence**:
  - No backup-related JCL in `app/jcl/` (38 jobs, none for backup/recovery)
  - No VSAM journaling configuration
  - No REPRO or EXPORT commands in any JCL

---

## Summary Table

| ID | Category | Description | Severity | Effort |
|----|----------|-------------|----------|--------|
| GAP-ORG-01 | Code Organization | Monolithic programs with embedded business logic | High | Large |
| GAP-ORG-02 | Code Organization | Inconsistent naming conventions | Medium | Medium |
| GAP-ORG-03 | Code Organization | Duplicated data structure definitions | Medium | Small |
| GAP-ORG-04 | Code Organization | Missing modular separation for common operations | Medium | Medium |
| GAP-ORG-05 | Code Organization | No separation of configuration from code | Medium | Medium |
| GAP-ERR-01 | Error Handling | Inconsistent CICS error handling strategy | High | Medium |
| GAP-ERR-02 | Error Handling | Missing file status validation in some programs | High | Small |
| GAP-ERR-03 | Error Handling | ABEND handling does not log diagnostic context | Medium | Small |
| GAP-ERR-04 | Error Handling | No retry logic for transient failures | Medium | Medium |
| GAP-TST-01 | Testing | Zero automated test coverage | Critical | Large |
| GAP-TST-02 | Testing | No test data management strategy | High | Medium |
| GAP-TST-03 | Testing | No batch job output validation | High | Medium |
| GAP-SEC-01 | Security | Plaintext password storage | Critical | Medium |
| GAP-SEC-02 | Security | No password complexity or rotation policies | High | Small |
| GAP-SEC-03 | Security | SSN and PII stored without encryption | Critical | Large |
| GAP-SEC-04 | Security | CVV stored in persistent data file | Critical | Medium |
| GAP-SEC-05 | Security | No audit trail for security-sensitive operations | High | Medium |
| GAP-SEC-06 | Security | No input sanitization for HTML output | Medium | Small |
| GAP-SEC-07 | Security | No session timeout or inactivity lockout | Medium | Small |
| GAP-API-01 | API Design | Tightly coupled program navigation | High | Large |
| GAP-API-02 | API Design | COMMAREA size limitations and no versioning | Medium | Medium |
| GAP-API-03 | API Design | No external API or service interface | High | Large |
| GAP-API-04 | API Design | Inconsistent error response format | Medium | Small |
| GAP-OBS-01 | Observability | No logging framework or structured logging | High | Medium |
| GAP-OBS-02 | Observability | No performance metrics or instrumentation | Medium | Medium |
| GAP-OBS-03 | Observability | No health check or heartbeat mechanism | Medium | Small |
| GAP-RES-01 | Resilience | No graceful degradation for file unavailability | High | Medium |
| GAP-RES-02 | Resilience | No transaction rollback for multi-file updates | Critical | Large |
| GAP-RES-03 | Resilience | Single points of failure in batch chain | High | Medium |
| GAP-RES-04 | Resilience | No duplicate transaction detection | High | Medium |
| GAP-RES-05 | Resilience | No data backup or recovery procedures | High | Medium |

### Severity Distribution

| Severity | Count |
|----------|-------|
| Critical | 5 |
| High | 15 |
| Medium | 11 |
| Low | 0 |
| **Total** | **31** |

### Effort Distribution

| Effort | Count |
|--------|-------|
| Small | 8 |
| Medium | 16 |
| Large | 7 |
| **Total** | **31** |
