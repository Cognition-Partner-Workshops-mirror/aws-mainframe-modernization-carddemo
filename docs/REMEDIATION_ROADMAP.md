# CardDemo Remediation Roadmap

## Overview

This roadmap prioritizes the 31 gaps identified in the [Gap Analysis](GAP_ANALYSIS.md) into three phases based on severity and effort. Each item includes an actionable Devin prompt that can be executed directly.

**Prioritization Logic:**
- **Phase 1 (Quick Wins)**: Critical/High severity + Small effort, or Critical severity + Medium effort — target 1-2 weeks
- **Phase 2 (Important)**: High severity + Medium effort, or structurally important Medium items — target 3-6 weeks
- **Phase 3 (Polish)**: Low severity items, Medium severity + Medium/Large effort, and large-effort structural changes — target 6-12 weeks

---

## Phase 1: Quick Wins (Weeks 1-2)

### 1.1 GAP-ERR-02: Add Comprehensive File Status Validation to Online Programs
**Severity**: High | **Effort**: Small

Add VSAM file status checking after every CICS file I/O command in online programs that currently only check for NORMAL and NOTFND conditions.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, update the online CICS programs in `app/cbl/` to add comprehensive CICS RESP code checking after every `EXEC CICS READ`, `EXEC CICS WRITE`, `EXEC CICS REWRITE`, and `EXEC CICS DELETE` command. Follow the pattern used in `app/cbl/CBTRN02C.cbl` (lines 500-530) where every file operation checks the full range of RESP codes. Start with `COBIL00C.cbl` (lines 440-470 — currently only checks NORMAL and NOTFND), then apply to `COTRN02C.cbl`, `COACTVWC.cbl`, and `COCRDSLC.cbl`. For each unhandled RESP code, add a MOVE to the error message field with the program name, paragraph name, file name, and RESP/RESP2 codes, then PERFORM the error display paragraph. Add comments explaining the changes done.

### 1.2 GAP-SEC-02: Add Password Complexity Validation
**Severity**: High | **Effort**: Small

Add password strength validation in the user creation and update programs.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, modify `app/cbl/COUSR01C.cbl` to add password complexity validation before the `EXEC CICS WRITE` to USRSEC. After the existing empty-field check (around line 150), add validation that requires: (1) minimum 8 characters (full field), (2) at least one uppercase letter (INSPECT TALLYING for A-Z), (3) at least one digit (INSPECT TALLYING for 0-9). If validation fails, move an appropriate error message like "Password must contain uppercase and digit" to the message field and skip the write. Apply the same validation to `app/cbl/COUSR02C.cbl` for the user update flow. Add comments explaining the changes done.

### 1.3 GAP-SEC-07: Add Session Inactivity Timeout
**Severity**: Medium | **Effort**: Small

Add a last-activity timestamp to the COMMAREA and check for inactivity timeout on each transaction.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, modify `app/cpy/COCOM01Y.cpy` to add a field `10 CDEMO-LAST-ACTIVITY-TS PIC X(26)` in the `CDEMO-GENERAL-INFO` group (after `CDEMO-PGM-CONTEXT` at line 29). Then modify `app/cbl/COMEN01C.cbl` and `app/cbl/COADM01C.cbl` to: (1) on every entry, call `EXEC CICS ASKTIME ABSTIME(WS-ABS-TIME)` and `EXEC CICS FORMATTIME ABSTIME(WS-ABS-TIME) YYYYMMDD(...)` to get current timestamp, (2) compare with CDEMO-LAST-ACTIVITY-TS — if difference exceeds 15 minutes (900 seconds), clear the COMMAREA and XCTL to COSGN00C (signon screen) with message "Session timed out", (3) update CDEMO-LAST-ACTIVITY-TS with current time on each successful entry. Add comments explaining the changes done.

### 1.4 GAP-SEC-06: Add HTML Entity Encoding in Statement Generation
**Severity**: Medium | **Effort**: Small

Sanitize customer data before embedding in HTML output in the statement generation program.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, modify `app/cbl/CBSTM03A.CBL` to add HTML entity encoding for customer-supplied data before it is embedded in HTML output. Create a new paragraph `9500-ENCODE-HTML-FIELD` that uses INSPECT REPLACING to convert `&` to `&amp;`, `<` to `&lt;`, `>` to `&gt;`, and `"` to `&quot;` in a working-storage buffer field. Call this paragraph before embedding `CUST-FIRST-NAME`, `CUST-LAST-NAME`, `TRAN-DESC`, and `TRAN-MERCHANT-NAME` into HTML string constructions (approximately lines 600-900 of the program). Add comments explaining the changes done.

### 1.5 GAP-ERR-03: Add Diagnostic Logging to ABEND Handlers
**Severity**: Medium | **Effort**: Small

Enhance ABEND handlers to write diagnostic context to a CICS transient data queue.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, modify the ABEND-ROUTINE paragraphs in `app/cbl/COSGN00C.cbl`, `app/cbl/COMEN01C.cbl`, `app/cbl/COACTVWC.cbl`, and `app/cbl/COBIL00C.cbl` to write diagnostic information to a CICS transient data queue before displaying the error screen. In each ABEND-ROUTINE, add: (1) format a 200-byte log record containing program name, transaction ID (EIBTRNID), terminal ID (EIBTRMID), abend code (EIBRESP), timestamp (via ASKTIME/FORMATTIME), and the last error message field value, (2) write to TDQ using `EXEC CICS WRITEQ TD QUEUE('CSMT') FROM(WS-LOG-RECORD) LENGTH(200)`, (3) then continue with existing error display logic. Define `WS-LOG-RECORD` in working storage of each program. Add comments explaining the changes done.

### 1.6 GAP-API-04: Standardize Error Response Format
**Severity**: Medium | **Effort**: Small

Create a consistent error message format across all online programs.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, create a new copybook `app/cpy/CERROR1Y.cpy` that defines a standard error message structure: `01 WS-ERROR-MSG-AREA. 05 WS-ERR-PGM PIC X(08). 05 WS-ERR-PARA PIC X(30). 05 WS-ERR-FILE PIC X(08). 05 WS-ERR-RESP PIC 9(04). 05 WS-ERR-RESP2 PIC 9(04). 05 WS-ERR-USER-MSG PIC X(50).` Also create a paragraph template for formatting user-friendly messages. Then update `app/cbl/COCRDUPC.cbl` to replace the direct RESP/RESP2 display (which currently shows technical codes to users) with the standardized format that shows only `WS-ERR-USER-MSG` on screen while logging the full technical detail via TDQ. Add comments explaining the changes done.

### 1.7 GAP-OBS-03: Add Application Health Check Transaction
**Severity**: Medium | **Effort**: Small

Create a CICS transaction that verifies application health by checking file accessibility.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, create a new COBOL program `app/cbl/COHLT00C.cbl` that implements an application health check. The program should: (1) attempt to STARTBR/ENDBR on each key VSAM file (USRSEC, ACCTDAT, CARDDAT, CUSTDAT, TRANSACT, CCXREF) to verify accessibility, (2) read one record from USRSEC to verify data readability, (3) format a BMS screen showing status of each file (OPEN/CLOSED/ERROR), total record counts where available, and current timestamp, (4) use transaction ID 'CHLT' and a simple BMS map. Set RESP checking for each file operation — mark files as RED/GREEN based on accessibility. Add comments explaining the changes done.

### 1.8 GAP-ORG-03: Consolidate Duplicated Customer Record Definitions
**Severity**: Medium | **Effort**: Small

Eliminate the duplicated Customer record structure by standardizing on one copybook.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, consolidate the duplicated Customer record structure. The record is defined in both `app/cpy/CVCUS01Y.cpy` (uses `CUST-DOB-YYYY-MM-DD`) and `app/cpy/CUSTREC.cpy` (uses `CUST-DOB-YYYYMMDD`, tab indentation). Search all `.cbl` files in `app/cbl/` for `COPY CUSTREC` and `COPY CVCUS01Y` to identify which programs use which copybook. Standardize on `CVCUS01Y.cpy` (which has consistent formatting) and update any programs that reference `CUSTREC.cpy` to use `CVCUS01Y.cpy` instead, adjusting any field name references from `CUST-DOB-YYYYMMDD` to `CUST-DOB-YYYY-MM-DD`. Add a comment at the top of `CUSTREC.cpy` marking it as deprecated. Add comments explaining the changes done.

---

## Phase 2: Important (Weeks 3-6)

### 2.1 GAP-SEC-01: Implement Password Hashing
**Severity**: Critical | **Effort**: Medium

Replace plaintext password storage with a one-way hash mechanism.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, implement password hashing for the USRSEC security file. Modify `app/cpy/CSUSR01Y.cpy` to change `SEC-USR-PWD` from `PIC X(08)` to `PIC X(64)` (to hold a hash), and add `SEC-USR-PWD-SALT PIC X(16)`. Adjust `SEC-USR-FILLER` to maintain the 80-byte record length (or extend if needed — update all programs accordingly). Create a new utility program `app/cbl/CSUTLHSH.cbl` that accepts an input string and salt, and produces a hash using a simple but effective algorithm (iterative XOR-fold with salt mixing — since mainframe COBOL lacks standard crypto libraries). Modify `app/cbl/COSGN00C.cbl` to hash the entered password with the stored salt before comparison. Modify `app/cbl/COUSR01C.cbl` and `app/cbl/COUSR02C.cbl` to generate a random salt and hash passwords on user creation/update. Add comments explaining the changes done.

### 2.2 GAP-SEC-04: Remove CVV from Persistent Storage
**Severity**: Critical | **Effort**: Medium

Remove the CVV field from the card data file to comply with PCI DSS requirements.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, remove the `CARD-CVV-CD` field from persistent storage to comply with PCI DSS. In `app/cpy/CVACT02Y.cpy`, replace `05 CARD-CVV-CD PIC 9(03)` with `05 CARD-CVV-FILLER PIC X(03)` (preserving record layout for backward compatibility). Search all programs in `app/cbl/` that reference `CARD-CVV-CD` — in `COCRDSLC.cbl` (card detail view) remove the CVV display field from the screen, in `COCRDUPC.cbl` (card update) remove CVV editing capability. If any batch program references CVV, remove those references. Add a JCL job `app/jcl/CVVCLEAN.jcl` that reads CARDDAT, blanks the CVV field in each record, and rewrites — for one-time data cleanup. Add comments explaining the changes done.

### 2.3 GAP-RES-02: Add CICS Syncpoint for Multi-File Updates
**Severity**: Critical | **Effort**: Large

Implement transaction integrity for operations that update multiple VSAM files.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, add CICS syncpoint support for multi-file update operations. In `app/cbl/COBIL00C.cbl` (bill payment): wrap the TRANSACT write (line ~380) and ACCTDAT update (line ~420) with `EXEC CICS SYNCPOINT` — if the account update fails after the transaction write, execute `EXEC CICS SYNCPOINT ROLLBACK` to undo the transaction write. In `app/cbl/CBTRN02C.cbl` (daily posting): after writing to TRANSACT and before updating TCATBAL, add a syncpoint check — if the TCATBAL update fails, log the error and set the return code, but note that batch VSAM updates may not support CICS syncpoint (if so, add compensating logic: on TCATBAL write failure, read back and delete the TRANSACT record just written). Add comments explaining the changes done.

### 2.4 GAP-SEC-05: Implement Audit Trail Logging
**Severity**: High | **Effort**: Medium

Create an audit log mechanism for security-sensitive operations.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, implement an audit trail system. Create a new copybook `app/cpy/CAUDIT1Y.cpy` defining an audit record: `01 AUDIT-RECORD. 05 AUDIT-TIMESTAMP PIC X(26). 05 AUDIT-USER-ID PIC X(08). 05 AUDIT-TERMINAL PIC X(04). 05 AUDIT-ACTION PIC X(20). 05 AUDIT-OBJECT-TYPE PIC X(10). 05 AUDIT-OBJECT-ID PIC X(20). 05 AUDIT-RESULT PIC X(10). 05 AUDIT-DETAIL PIC X(100). 05 FILLER PIC X(52).` (RECLN 250). Create `app/jcl/DEFAUDIT.jcl` to define the VSAM KSDS cluster (key = AUDIT-TIMESTAMP + AUDIT-USER-ID). Create a reusable program `app/cbl/CSUTLAUD.cbl` that accepts audit parameters via COMMAREA and writes to the audit file. Then modify `app/cbl/COSGN00C.cbl` to call CSUTLAUD on login success and failure, `app/cbl/COUSR01C.cbl` on user creation, `app/cbl/COUSR02C.cbl` on user update, `app/cbl/COUSR03C.cbl` on user deletion, and `app/cbl/COBIL00C.cbl` on bill payment. Add comments explaining the changes done.

### 2.5 GAP-TST-02: Create Test Data Management Framework
**Severity**: High | **Effort**: Medium

Build JCL procedures and programs to reset test data to a known baseline.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, create a test data management framework. Create `app/jcl/TSTINIT.jcl` that: (1) deletes and redefines all VSAM clusters (USRSEC, ACCTDAT, CARDDAT, CUSTDAT, TRANSACT, CCXREF, TCATBAL, DISCGRP) using IDCAMS DELETE/DEFINE, (2) loads baseline data from `app/data/` using IDCAMS REPRO. Create `app/jcl/TSTSNAP.jcl` that exports all VSAM files to sequential datasets (REPRO to GDG) for point-in-time snapshots. Create `app/jcl/TSTRSTR.jcl` that restores from a GDG snapshot. Create `app/cbl/CBTST01C.cbl` — a batch COBOL program that generates randomized test data: N customer records, M accounts per customer, P cards per account, Q transactions per card — parameterized via PARM. Add comments explaining the changes done.

### 2.6 GAP-TST-03: Add Batch Job Output Validation
**Severity**: High | **Effort**: Medium

Create validation programs and JCL steps that verify batch output correctness.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, add batch output validation. Create `app/cbl/CBVAL01C.cbl` — a validation program that runs after `CBTRN02C` (daily posting) and verifies: (1) total posted records + rejected records = total input records, (2) sum of posted transaction amounts matches, (3) no duplicate transaction IDs exist in TRANSACT file. Create `app/cbl/CBVAL02C.cbl` — runs after `CBACT04C` (interest calculation) and verifies: (1) all accounts with TCATBAL entries had interest computed, (2) interest amounts are within expected range (rate * balance / 12 ± 0.01). Update the relevant JCL jobs to add a validation step after the main processing step, with `COND=(4,LT)` to skip validation if the main step failed with RC > 4. Each validator should set RETURN-CODE = 0 (pass) or 8 (fail) and display detailed discrepancies. Add comments explaining the changes done.

### 2.7 GAP-RES-04: Add Duplicate Transaction Detection
**Severity**: High | **Effort**: Medium

Add idempotency checking to the daily transaction posting program.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, add duplicate transaction detection to `app/cbl/CBTRN02C.cbl`. Before writing a posted transaction to the TRANSACT file, add a READ to TRANSACT using the DALYTRAN-ID as key. If the record already exists (RESP = NORMAL), skip the transaction and increment a new counter `WS-DUPLICATE-COUNT`, writing a record to DALYREJS with reason 'DUPLICATE TRAN-ID'. Also add a processing-date check: add a field to the daily transaction record layout (`app/cpy/CVTRA06Y.cpy`) — `05 DALYTRAN-PROC-DATE PIC X(10)` (reduce FILLER by 10 bytes) — and in CBTRN02C, compare DALYTRAN-PROC-DATE against the PARM date to detect and reject stale resubmissions. Display duplicate count alongside processed/rejected counts at end of job. Add comments explaining the changes done.

### 2.8 GAP-RES-05: Create Data Backup and Recovery Procedures
**Severity**: High | **Effort**: Medium

Create backup JCL procedures for all critical VSAM files.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, create comprehensive backup and recovery procedures. Create `app/jcl/BACKUP00.jcl` — a daily backup job that uses IDCAMS REPRO to export all critical VSAM files (ACCTDAT, CARDDAT, CUSTDAT, TRANSACT, CCXREF, USRSEC, TCATBAL, DISCGRP) to sequential GDG datasets (one GDG base per file, e.g., `AWS.M2.CARDDEMO.BACKUP.ACCTDAT(+1)`). Create `app/jcl/DEFGDG.jcl` to define the GDG bases with LIMIT(7) for 7-day retention. Create `app/jcl/RECOV00.jcl` — a recovery job with 8 steps, one per file, each using IDCAMS DELETE/DEFINE followed by REPRO from the latest GDG generation. Create `app/jcl/RECOV01.jcl` — point-in-time recovery that accepts a GDG generation number via symbolic parameter. Add comments explaining the changes done.

### 2.9 GAP-OBS-01: Implement Structured Logging Framework
**Severity**: High | **Effort**: Medium

Create a centralized logging utility and integrate it across programs.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, implement a structured logging framework. Create copybook `app/cpy/CLOG01Y.cpy` defining a log record: `01 LOG-RECORD. 05 LOG-TIMESTAMP PIC X(26). 05 LOG-LEVEL PIC X(05). 05 LOG-PROGRAM PIC X(08). 05 LOG-TRANSACTION PIC X(04). 05 LOG-TERMINAL PIC X(04). 05 LOG-USER PIC X(08). 05 LOG-MESSAGE PIC X(200). 05 FILLER PIC X(45).` (300 bytes). Create `app/cbl/CSUTLLOG.cbl` — a logging utility program callable via `EXEC CICS LINK` that accepts log level and message via COMMAREA, adds timestamp (ASKTIME/FORMATTIME), EIBTRNID, EIBTRMID, and writes to a TDQ 'CDLG'. For batch programs, create a variant that uses DISPLAY or writes to a log file. Integrate into `app/cbl/COBIL00C.cbl` (log bill payments), `app/cbl/COSGN00C.cbl` (log sign-on), and `app/cbl/CBTRN02C.cbl` (log batch progress every 100 records). Add comments explaining the changes done.

### 2.10 GAP-ERR-01: Standardize CICS Error Handling Strategy
**Severity**: High | **Effort**: Medium

Create a standard error handling subroutine and migrate programs to use it consistently.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, standardize CICS error handling across all online programs. Create `app/cbl/CSUTLERR.cbl` — a reusable error handler called via `EXEC CICS LINK`. It should accept via COMMAREA: program name, paragraph name, file name, RESP code, RESP2 code, and user message. It should: (1) log the error via the logging framework (CSUTLLOG), (2) format a user-friendly message, (3) return the formatted message to the caller. Then refactor `app/cbl/COBIL00C.cbl` as a reference implementation — replace all inline `IF RESP NOT = DFHRESP(NORMAL)` blocks with calls to CSUTLERR, using inline RESP/RESP2 checking (not HANDLE CONDITION). Document the standard pattern in a comment block at the top of CSUTLERR. Add comments explaining the changes done.

### 2.11 GAP-RES-01: Add Graceful Degradation for File Unavailability
**Severity**: High | **Effort**: Medium

Implement file availability checking and user-friendly messages when files are unavailable.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, add graceful degradation when VSAM files are unavailable. Create a utility paragraph (or copybook `app/cpy/CFILCK1Y.cpy`) that attempts an `EXEC CICS INQUIRE FILE(file-name) ENABLESTATUS(ws-status)` to check if a file is enabled before attempting I/O. Modify `app/cbl/COACTVWC.cbl` (which reads ACCTDAT, CARDDAT, CUSTDAT) to check file availability first — if CUSTDAT is disabled, still display account and card info with "Customer details temporarily unavailable" instead of ABENDing. Modify `app/cbl/COMEN01C.cbl` to check critical file availability on menu entry and display a "System partially available" banner if any key file is disabled. Add comments explaining the changes done.

### 2.12 GAP-ERR-04: Add Retry Logic for Transient File Failures
**Severity**: Medium | **Effort**: Medium

Implement retry with delay for VSAM operations that may experience transient failures.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, add retry logic for transient VSAM failures. Create a copybook `app/cpy/CRETRY1Y.cpy` with retry control fields: `01 WS-RETRY-CTL. 05 WS-RETRY-COUNT PIC 9(02) VALUE 0. 05 WS-RETRY-MAX PIC 9(02) VALUE 3. 05 WS-RETRY-DELAY PIC 9(04) VALUE 1000.` Modify `app/cbl/COCRDUPC.cbl` — for the `EXEC CICS READ UPDATE` that locks the card record, wrap it in a retry loop: if RESP = DFHRESP(RECORDBUSY), increment retry count, `EXEC CICS DELAY INTERVAL(0) MILLISECS(WS-RETRY-DELAY)`, and retry up to WS-RETRY-MAX times. If still failing after 3 retries, display "Record is locked by another user. Please try again later." Apply the same pattern to `app/cbl/COBIL00C.cbl` for the account balance update. Add comments explaining the changes done.

### 2.13 GAP-RES-03: Add Checkpoint/Restart to Batch Programs
**Severity**: High | **Effort**: Medium

Add checkpoint facilities to long-running batch programs for restart capability.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, add checkpoint/restart capability to batch programs. Modify `app/cbl/CBTRN02C.cbl` to: (1) add a checkpoint counter that triggers every 500 records, (2) at each checkpoint, write the current record key and counters to a checkpoint file (define in JCL as `CKPTFILE` DD), (3) on program start, check if CKPTFILE has a record — if yes, this is a restart: read the checkpoint, reposition the input file to the saved key, and restore counters. Update `app/jcl/POSTRN00.jcl` to add the CKPTFILE DD statement. Apply the same pattern to `app/cbl/CBACT04C.cbl` for interest calculation (checkpoint every 200 accounts). Add comments explaining the changes done.

---

## Phase 3: Polish (Weeks 7-12)

### 3.1 GAP-TST-01: Build Automated Test Framework
**Severity**: Critical | **Effort**: Large

Create a comprehensive test framework for both batch and online programs.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, create an automated test framework. Create directory `app/test/`. Create `app/test/jcl/RUNTESTS.jcl` as the master test runner. Create batch test programs: (1) `app/test/cbl/TBTST01C.cbl` — tests CBTRN02C by: loading known test data via TSTINIT, running daily posting with a crafted DALYTRAN file, then calling CBVAL01C to validate output. (2) `app/test/cbl/TBTST02C.cbl` — tests CBACT04C by: setting up known TCATBAL and DISCGRP records, running interest calculation, verifying computed interest matches expected values. (3) `app/test/cbl/TBTST03C.cbl` — tests edge cases: empty input file, all-rejected input, duplicate transaction IDs. Each test program sets RETURN-CODE = 0 (all pass) or 8 (any fail), and writes test results to SYSOUT. Create `app/test/data/` with test-specific data files. Add comments explaining the changes done.

### 3.2 GAP-SEC-03: Implement Field-Level Encryption for PII
**Severity**: Critical | **Effort**: Large

Encrypt SSN and government ID fields at rest in the CUSTDAT file.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, implement field-level encryption for PII data. Create `app/cbl/CSUTLENC.cbl` — an encryption/decryption utility program that implements a symmetric cipher (XOR with a key derived from a master password stored in a secured dataset, or use ICSF callable services if available). Modify `app/cpy/CVCUS01Y.cpy` to change `CUST-SSN` from `PIC 9(09)` to `PIC X(24)` (to hold encrypted + IV) and `CUST-GOVT-ISSUED-ID` from `PIC X(20)` to `PIC X(40)` — adjust FILLER to maintain 500-byte record. Modify all programs that read CUSTDAT to call CSUTLENC for decryption after read and encryption before write. Create `app/jcl/ENCRYPT.jcl` — a one-time migration job that reads existing CUSTDAT records, encrypts SSN and GOVT-ID fields, and rewrites them. Add comments explaining the changes done.

### 3.3 GAP-ORG-01: Refactor Monolithic Programs into Layered Architecture
**Severity**: High | **Effort**: Large

Separate UI, business logic, and data access into distinct programs.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, refactor `app/cbl/COBIL00C.cbl` (bill payment — 573 lines) as a pilot for layered architecture. Split into three programs: (1) `app/cbl/COBIL00C.cbl` (UI layer) — handles BMS map send/receive, input parsing, and screen formatting only, (2) `app/cbl/COBILBIZ.cbl` (business logic layer) — validates payment eligibility, computes new balance, constructs transaction record, (3) `app/cbl/COBILDAC.cbl` (data access layer) — encapsulates all VSAM READ/WRITE/REWRITE operations for ACCTDAT, TRANSACT, and CXACAIX. The UI program calls the business program via `EXEC CICS LINK`, which in turn calls the data access program. Define COMMAREA structures for each interface in new copybooks. Document the pattern as a reference for refactoring other programs. Add comments explaining the changes done.

### 3.4 GAP-API-03: Create CICS Web Service Interface
**Severity**: High | **Effort**: Large

Expose key business functions as CICS web services for modernization enablement.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, create CICS web service wrappers for core business functions. Create `app/cbl/COWSACCT.cbl` — a CICS program that accepts a JSON-like COMMAREA request (account-id) and returns account details (balance, status, credit limit) via COMMAREA response. Create `app/cbl/COWSTRAN.cbl` — accepts card-number and date range, returns transaction list. Create `app/cbl/COWSBILL.cbl` — accepts account-id and amount, processes bill payment and returns success/failure. Each program uses COMMAREA-based request/response (not BMS maps) making them callable via CICS web service PIPELINE/URIMAP definitions or via CICS Transaction Gateway. Create DFHWS2LS-compatible copybooks for the request/response structures. Document the URIMAP and PIPELINE definitions needed (as comments or in a README) but do not create CSD entries. Add comments explaining the changes done.

### 3.5 GAP-API-01: Implement Table-Driven Program Navigation
**Severity**: High | **Effort**: Large

Replace hardcoded XCTL calls with a fully table-driven navigation framework.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, implement fully table-driven program navigation to replace hardcoded XCTL calls. Create `app/cpy/CNAV01Y.cpy` — a navigation table structure: `01 CDEMO-NAV-TABLE. 05 CDEMO-NAV-ENTRY OCCURS 30 TIMES. 10 CDEMO-NAV-FROM-PGM PIC X(08). 10 CDEMO-NAV-ACTION PIC X(10). 10 CDEMO-NAV-TO-PGM PIC X(08). 10 CDEMO-NAV-TO-TRAN PIC X(04).` Populate with all current navigation paths (signon->menu, menu->subprograms, subprogram->return). Create `app/cbl/CSUTLNAV.cbl` — a navigation utility that looks up the target program based on current program + action, and performs the XCTL. Modify `app/cbl/COSGN00C.cbl` to use CSUTLNAV instead of hardcoded `XCTL PROGRAM('COADM01C')` and `XCTL PROGRAM('COMEN01C')`. Modify `app/cbl/COBIL00C.cbl` to use CSUTLNAV for return-to-menu navigation. Add comments explaining the changes done.

### 3.6 GAP-ORG-04: Create Shared Utility Library for Common Operations
**Severity**: Medium | **Effort**: Medium

Extract repeated patterns into reusable utility programs and copybooks.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, create a shared utility library for common operations. Create `app/cbl/CSUTLFST.cbl` — a file status handler utility that accepts a file name, operation type, and RESP/RESP2 codes, and returns a formatted error message and severity level. Create `app/cbl/CSUTLMSG.cbl` — a message formatter that constructs user-friendly messages from error codes using a table of standard messages. Create `app/cpy/CFSTAT1Y.cpy` — working storage for file status tracking (file name, last operation, last RESP, last RESP2) used by all programs. Refactor `app/cbl/COBIL00C.cbl` and `app/cbl/COTRN02C.cbl` to use these utilities instead of inline file status handling. Add comments explaining the changes done.

### 3.7 GAP-ORG-02: Standardize Naming Conventions
**Severity**: Medium | **Effort**: Medium

Establish and apply consistent naming conventions across all programs.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, create a naming standards document and apply it to a pilot set of programs. Create `docs/NAMING_STANDARDS.md` documenting: (1) paragraph naming: `NNNN-VERB-OBJECT` format (e.g., `1000-PROCESS-INPUT`, `9100-READ-ACCTDAT`), (2) working storage: `WS-` prefix for local, `LK-` prefix for linkage, `FD-` prefix for file, (3) copybook naming: `Cxxxxxy.cpy` where xxxxx = module code, y = version letter, (4) program naming: existing CO/CB prefix convention is retained. Apply the naming standard to `app/cbl/COTRN01C.cbl` (which uses non-numeric paragraph names like `PROCESS-ENTER-KEY`) — rename paragraphs to numeric-prefix format while preserving all logic. Add comments explaining the changes done.

### 3.8 GAP-ORG-05: Externalize Configuration to a Configuration File
**Severity**: Medium | **Effort**: Medium

Move hardcoded menu options and application constants to an external VSAM file.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, externalize menu configuration from compile-time copybooks to a runtime VSAM file. Create `app/cpy/CVCFG01Y.cpy` — a configuration record: `01 CONFIG-RECORD. 05 CFG-KEY PIC X(20). 05 CFG-VALUE PIC X(80). 05 CFG-TYPE PIC X(10). 05 CFG-ACTIVE PIC X(01). 05 FILLER PIC X(39).` (150 bytes). Create `app/jcl/DEFCFG.jcl` to define the CONFIG VSAM cluster and load initial data (menu options, screen titles, message text) from a sequential input file. Modify `app/cbl/COMEN01C.cbl` to read menu options from the CONFIG file at startup instead of from the `COMEN02Y.cpy` compile-time array. This allows adding/removing menu options without recompilation. Add comments explaining the changes done.

### 3.9 GAP-API-02: Add COMMAREA Versioning
**Severity**: Medium | **Effort**: Medium

Add a version field to the COMMAREA to enable forward-compatible changes.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, add versioning to the COMMAREA structure. Modify `app/cpy/COCOM01Y.cpy` to add `10 CDEMO-COMMAREA-VERSION PIC 9(02) VALUE 01` as the first field in `CDEMO-GENERAL-INFO` (before `CDEMO-FROM-TRANID`). All existing fields remain unchanged. Modify `app/cbl/COMEN01C.cbl` and `app/cbl/COADM01C.cbl` to set CDEMO-COMMAREA-VERSION = 01 when initializing a new COMMAREA. Add a check at the start of each menu program: if CDEMO-COMMAREA-VERSION is not recognized (> current version), display "Please sign on again — application updated" and redirect to signon. This provides a foundation for future COMMAREA layout changes with backward compatibility. Add comments explaining the changes done.

### 3.10 GAP-OBS-02: Add Performance Instrumentation
**Severity**: Medium | **Effort**: Medium

Add timing instrumentation to key online transactions and batch programs.

**Devin Prompt:**
> In the repository `aws-mainframe-modernization-carddemo`, add performance instrumentation. Create `app/cpy/CPERF01Y.cpy` — timing fields: `01 WS-PERF. 05 WS-PERF-START PIC S9(15) COMP-3. 05 WS-PERF-END PIC S9(15) COMP-3. 05 WS-PERF-ELAPSED PIC 9(09). 05 WS-PERF-OPER PIC X(20).` Modify `app/cbl/COBIL00C.cbl` to capture `EXEC CICS ASKTIME ABSTIME(WS-PERF-START)` at transaction entry and `ABSTIME(WS-PERF-END)` at completion, compute elapsed time, and write a performance record via the logging framework (CSUTLLOG) with level 'PERF'. Modify `app/cbl/CBTRN02C.cbl` to track elapsed time for the entire batch run and per-record average, displaying timing in the final summary. Add comments explaining the changes done.

---

## Summary Timeline

| Phase | Timeframe | Items | Severity Focus | Key Deliverables |
|-------|-----------|-------|---------------|------------------|
| Phase 1 | Weeks 1-2 | 8 items | High/Medium + Small effort | File status validation, password complexity, session timeout, HTML sanitization, diagnostic logging, error format, health check, copybook dedup |
| Phase 2 | Weeks 3-6 | 13 items | Critical/High + Medium effort | Password hashing, CVV removal, syncpoint, audit trail, test data mgmt, batch validation, duplicate detection, backup/recovery, logging framework, error standardization, graceful degradation, retry logic, checkpoint/restart |
| Phase 3 | Weeks 7-12 | 10 items | Critical/High/Medium + Large effort | Test framework, PII encryption, layered architecture, web services, table-driven navigation, utility library, naming standards, config externalization, COMMAREA versioning, performance instrumentation |

## Key Metrics

| Metric | Current | Phase 1 Target | Phase 2 Target | Phase 3 Target |
|--------|---------|----------------|----------------|----------------|
| Automated test coverage | 0% | 0% | 30% (batch validation) | 60%+ (full test framework) |
| Security gaps (Critical) | 5 | 3 (-2) | 0 (-3) | 0 |
| Programs with structured logging | 0/31 | 4/31 | 15/31 | 31/31 |
| Programs with standard error handling | 0/31 | 4/31 | 15/31 | 31/31 |
| Batch jobs with checkpoint/restart | 0/8 | 0/8 | 2/8 | 8/8 |
| Batch jobs with output validation | 0/8 | 0/8 | 2/8 | 8/8 |
| PCI DSS compliance (CVV) | No | No | Yes | Yes |
| Audit trail coverage | None | None | Sign-on + CRUD + payments | All operations |
| Data backup procedures | None | None | Daily VSAM backup | Full GDG rotation |

## Total Gap Coverage

| Category | Total Gaps | Phase 1 | Phase 2 | Phase 3 |
|----------|-----------|---------|---------|---------|
| Code Organization | 5 | 1 | 0 | 4 |
| Error Handling | 4 | 2 | 2 | 0 |
| Testing | 3 | 0 | 2 | 1 |
| Security | 7 | 3 | 2 | 2 |
| API Design | 4 | 1 | 0 | 3 |
| Observability | 3 | 1 | 1 | 1 |
| Resilience | 5 | 0 | 6 | 0 |
| **Total** | **31** | **8** | **13** | **10** |
