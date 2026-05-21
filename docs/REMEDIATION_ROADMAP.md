# CardDemo — Remediation Roadmap

This roadmap prioritizes the gaps identified in [GAP_ANALYSIS.md](./GAP_ANALYSIS.md) into three phases. Each item includes an actionable Devin prompt that can be executed directly.

---

## Phase 1 — Quick Wins (High Severity / Low Effort)

These items address critical or high-severity gaps that can be resolved with relatively small effort. Target: complete within 1–2 weeks.

---

### 1.1 Fix Compilation Errors (Gap 3.3)

Fix the three programs that currently fail to compile with GnuCOBOL: CBEXPORT (undefined EXPORT-SEQUENCE-NUM), CBIMPORT (same), and CBSTM03A (tab characters in CUSTREC.cpy).

**Devin Prompt:**
```
Fix compilation errors in the CardDemo repository. Three programs currently fail to compile with GnuCOBOL:
1. CBEXPORT.cbl and CBIMPORT.cbl — fail due to EXPORT-SEQUENCE-NUM usage as a VSAM key but it is defined as COMP (binary) which may not work as an indexed key. Investigate the CVEXPORT.cpy copybook and the FILE-CONTROL sections. Either change the key definition or adjust the file organization.
2. CBSTM03A.CBL — fails because CUSTREC.cpy contains tab characters. Replace tabs with spaces in CUSTREC.cpy while preserving column alignment.
After fixing, verify all 14 batch programs compile successfully using: cobc -x -I app/cpy/ --std=ibm-strict for executables and cobc -m for modules. Create a PR with the fixes.
```

### 1.2 Add CI Pipeline for Compilation Verification (Gap 3.3)

Set up a GitHub Actions workflow that compiles all batch programs on every push and PR to catch regressions.

**Devin Prompt:**
```
Create a GitHub Actions CI workflow for the CardDemo repository that:
1. Installs GnuCOBOL (gnucobol package via apt)
2. Compiles all batch programs as executables: CBACT01C, CBACT02C, CBACT03C, CBCUS01C, CBTRN01C, CBTRN02C, CBTRN03C, COBSWAIT
3. Compiles subprograms as modules: CBACT04C, CBSTM03B, CSUTLDTC
4. Reports compilation errors clearly in the CI output
5. Runs on push to main and on pull requests
Place the workflow in .github/workflows/compile.yml. Use the existing compile commands: cobc -x -I app/cpy/ --std=ibm-strict for executables and cobc -m -I app/cpy/ --std=ibm-strict for modules.
```

### 1.3 Remove Plaintext Passwords from Sample Data (Gap 4.1, 4.2)

Replace the default PASSWORD values with hashed equivalents and document the hashing approach.

**Devin Prompt:**
```
Address the plaintext password security gap in CardDemo:
1. In app/cpy/CSUSR01Y.cpy, add a comment noting that SEC-USR-PWD should be hashed in production
2. Create a new COBOL utility program app/cbl/CSECRYPT.cbl that implements a simple one-way hash (e.g., XOR-based obfuscation suitable for the COBOL PIC X(08) field) for password storage
3. Update COSGN00C.cbl to call the hash utility before comparing passwords
4. Update the README.md security section to document that default credentials exist for demo purposes only and must be changed in production
5. Add a SECURITY.md file documenting the authentication flow and known limitations
Create a PR with these changes.
```

### 1.4 Add Password Policy Controls (Gap 4.3)

Implement basic password complexity and account lockout in the sign-on program.

**Devin Prompt:**
```
Add password policy controls to CardDemo's sign-on program (COSGN00C.cbl):
1. Add a failed-login counter to the USRSEC record by using 2 bytes from the existing FILLER in CSUSR01Y.cpy (SEC-USR-FILLER has 23 bytes)
2. In COSGN00C.cbl, increment the counter on failed login attempts
3. Lock the account (refuse login) after 3 consecutive failed attempts
4. Reset the counter on successful login
5. Add a minimum password length check (at least 6 characters, rejecting all-spaces)
6. Add appropriate error messages for locked accounts and weak passwords
Ensure existing compilation of COSGN00C still works (it uses CICS, so just verify the COBOL syntax is valid). Create a PR.
```

### 1.5 Document Naming Conventions (Gap 1.2)

Create a developer guide documenting the codebase naming conventions.

**Devin Prompt:**
```
Create a CONTRIBUTING.md enhancement or a new docs/NAMING_CONVENTIONS.md file for the CardDemo repository that documents:
1. Program naming: CB* = batch programs, CO* = online CICS programs
2. Copybook naming: CV* = VSAM record layouts, CS* = shared structures, CO* = online screen copybooks, COMEN/COADM = menu options
3. File naming: uppercase .CBL/.CPY = older files, lowercase .cbl/.cpy = newer convention
4. JCL naming: matches the batch job purpose (ACCTFILE, CARDFILE, POSTTRAN, etc.)
5. CICS transaction IDs: CC00=signon, CM00=menu, CA*=account, CC*=card, CT*=transaction, CB*=bill, CR*=report, CU*=user
6. BMS map naming: matches the CICS transaction/program name
Create a PR with this documentation.
```

### 1.6 Fix Inconsistent Source Formatting (Gap 1.5)

Standardize COBOL source formatting and fix the tab character issue.

**Devin Prompt:**
```
Standardize COBOL source formatting in the CardDemo repository:
1. Replace all tab characters with spaces in app/cpy/CUSTREC.cpy (this currently breaks compilation of CBSTM03A)
2. Normalize all .CBL/.CPY file extensions to lowercase (.cbl/.cpy) via git mv for consistency
3. Ensure all COBOL source files use consistent indentation (spaces only, no tabs)
4. Add an .editorconfig file with settings for COBOL files: indent_style=space, indent_size=7, charset=utf-8, trim_trailing_whitespace=true
Create a PR with these changes.
```

---

## Phase 2 — Important (High Severity / Medium Effort)

These items address significant architectural and quality gaps. Target: complete within 1–2 months.

---

### 2.1 Create Centralized Error Handling Framework (Gap 2.1, 2.2, 2.4, 2.5)

Build shared error-handling copybooks and paragraphs that all programs can use.

**Devin Prompt:**
```
Create a centralized error handling framework for CardDemo:
1. Create app/cpy/CSERRHND.cpy — shared error handling data structure with:
   - Error code (PIC X(08))
   - Error severity (PIC X(01): 'I'=info, 'W'=warning, 'E'=error, 'F'=fatal)
   - Error message (PIC X(80))
   - Program name, paragraph name, timestamp
   - VSAM file status code and CICS RESP/RESP2 codes
2. Create app/cpy/CSERRMSG.cpy — message catalog with coded error messages (e.g., ERR-VSAM-NOTFND, ERR-VSAM-DUPKEY, ERR-CICS-IOERR)
3. Refactor COSGN00C.cbl to use the new error handling copybook as a reference implementation
4. Refactor CBTRN02C.cbl to use the framework for batch error handling, including: proper return code setting (MOVE 8 TO RETURN-CODE on critical errors), threshold checking for rejected records
5. Document the error handling pattern in docs/ERROR_HANDLING.md
Create a PR.
```

### 2.2 Add Batch Return Code and Threshold Handling (Gap 2.3)

Ensure batch programs set meaningful return codes and fail on excessive errors.

**Devin Prompt:**
```
Add return code and error threshold handling to CardDemo batch programs:
1. In CBTRN02C.cbl (transaction posting):
   - Track counts: total read, successfully posted, rejected, errors
   - Set RETURN-CODE to 0 (all OK), 4 (some rejects but within threshold), 8 (too many rejects), 12 (fatal I/O error)
   - Add a configurable rejection threshold (e.g., if rejects > 10% of total, set RC=8)
   - Display summary counts at end of processing
2. In CBACT04C.cbl (interest calculation):
   - Set RETURN-CODE to 0 on success, 8 on file errors, 12 on calculation errors
   - Display processed account count
3. Ensure all STOP RUN statements pass the return code
4. Update JCL POSTTRAN.jcl and INTCALC.jcl to check COND codes and halt the job chain on errors
Create a PR.
```

### 2.3 Add SSN and PII Masking (Gap 4.4)

Implement data masking for sensitive fields in online display and batch output.

**Devin Prompt:**
```
Implement PII masking for the CardDemo application:
1. Create app/cpy/CSMASKPY.cpy — shared masking utility data area
2. Create app/cbl/CSMASKUT.cbl — utility subprogram with paragraphs for:
   - MASK-SSN: Display only last 4 digits (e.g., ***-**-1234)
   - MASK-CARD-NUM: Display only last 4 digits (e.g., ****-****-****-5678)
   - MASK-PHONE: Mask middle digits
3. Update online programs that display customer data (COACTVWC, COACTUPC) to call the masking utility before sending data to the BMS map
4. Update batch report programs (CBTRN03C, CBSTM03A) to mask sensitive fields in printed output
5. Document the masking approach in docs/SECURITY.md
Create a PR.
```

### 2.4 Implement Structured Logging (Gap 6.1, 6.3)

Replace ad-hoc DISPLAY statements with a consistent logging framework.

**Devin Prompt:**
```
Implement structured logging for CardDemo batch programs:
1. Create app/cpy/CSLOGGER.cpy — logging data structure with:
   - Log level (PIC X(01): 'D'=debug, 'I'=info, 'W'=warn, 'E'=error)
   - Timestamp (from FUNCTION CURRENT-DATE)
   - Program name, paragraph name
   - Message text (PIC X(200))
   - Numeric counters for records processed/rejected/errors
2. Create a WRITE-LOG paragraph pattern that formats output as: YYYY-MM-DD HH:MM:SS [LEVEL] PROGRAM.PARAGRAPH - Message
3. Refactor CBTRN02C.cbl to use the logging framework:
   - Log INFO at start/end with record counts
   - Log WARN for each rejected record (with reason)
   - Log ERROR for I/O failures
4. Refactor CBACT04C.cbl similarly
5. Add a summary log entry at the end of each program with total counts in key=value format for machine parsing
Create a PR.
```

### 2.5 Add Audit Trail for User Actions (Gap 6.5)

Log all data modification operations to an audit VSAM file.

**Devin Prompt:**
```
Add an audit trail to CardDemo online programs:
1. Create app/cpy/CVAUDT01.cpy — audit record layout:
   - AUDIT-TIMESTAMP PIC X(26)
   - AUDIT-USER-ID PIC X(08)
   - AUDIT-PROGRAM PIC X(08)
   - AUDIT-TRANS-ID PIC X(04)
   - AUDIT-ACTION PIC X(01) (C=create, U=update, D=delete, R=read)
   - AUDIT-ENTITY PIC X(08) (ACCOUNT, CARD, CUSTOMER, USER, TRAN)
   - AUDIT-KEY PIC X(16)
   - AUDIT-DETAILS PIC X(200)
2. Create JCL to define a VSAM KSDS file for audit records
3. Add audit writes to: COACTUPC (account update), COCRDUPC (card update), COUSR01C (user add), COUSR02C (user update), COUSR03C (user delete), COTRN02C (transaction add), COBIL00C (bill payment)
4. Update the CSD to include the audit file definition
Create a PR.
```

### 2.6 Create Test Data Generator (Gap 3.2)

Build a utility to generate consistent test data across all entity files.

**Devin Prompt:**
```
Create a test data generation utility for CardDemo:
1. Create a Python script scripts/generate_test_data.py that:
   - Generates consistent test records for all VSAM entities (accounts, cards, customers, cross-references, transactions, user security)
   - Ensures referential integrity: every card has a valid account, every cross-reference links valid card/customer/account
   - Generates configurable number of records (default: 100 accounts, 200 cards, 150 customers, 500 transactions)
   - Outputs both ASCII flat files (for app/data/ASCII/) and can be used to create VSAM-loadable sequential files
   - Includes edge cases: expired cards, inactive accounts, zero-balance accounts, high-balance accounts near credit limit
2. Create scripts/validate_test_data.py that checks cross-file referential integrity
3. Add a README section in docs/ explaining how to use the test data tools
Create a PR.
```

### 2.7 Add Batch Idempotency Controls (Gap 7.3)

Make batch jobs safe to re-run without causing duplicate processing.

**Devin Prompt:**
```
Add idempotency controls to CardDemo batch programs:
1. In CBTRN02C.cbl (transaction posting):
   - Before writing to TRANSACT, check if TRAN-ID already exists (READ with RIDFLD)
   - If duplicate found, skip the record and log a warning instead of re-posting
   - Add a run-date tracking mechanism: write a control record with the processing date to prevent same-day re-runs
2. In CBACT04C.cbl (interest calculation):
   - Add a last-calculated-date field check against account records
   - Skip accounts already processed for the current period
3. Create app/cpy/CSRUNCTL.cpy — run control record for tracking batch execution dates
4. Create JCL and VSAM definition for the run control file
Create a PR.
```

### 2.8 Add Retry Logic for VSAM I/O (Gap 7.1)

Implement retry patterns for transient I/O errors in both batch and online programs.

**Devin Prompt:**
```
Add retry logic for VSAM I/O operations in CardDemo:
1. Create app/cpy/CSRETRY.cpy — retry control data area:
   - RETRY-COUNT PIC 9(02) (current attempt)
   - RETRY-MAX PIC 9(02) VALUE 3 (max attempts)
   - RETRY-WAIT-MS PIC 9(05) VALUE 100 (wait between retries)
   - RETRY-STATUS PIC X(01) ('S'=success, 'F'=failed after all retries)
2. Create a reusable retry paragraph pattern for CICS READ/WRITE/REWRITE operations that retries on RESP codes: IOERR(17), LOADING(26)
3. Refactor COSGN00C.cbl as a reference implementation for online retry
4. For batch programs (CBTRN02C), add retry on file-status codes '92' (logic error) and '93' (resource unavailable)
5. Log each retry attempt with the attempt number and error code
Create a PR.
```

---

## Phase 3 — Polish (Medium/Low Severity, Strategic)

These items are strategic improvements that enable full modernization. Target: 3–6 months.

---

### 3.1 Extract Business Logic into Callable Services (Gap 5.1, 5.2)

Separate business logic from CICS screen handling to enable future REST API exposure.

**Devin Prompt:**
```
Refactor CardDemo to separate business logic from UI handling. Start with the Account View function as a proof-of-concept:
1. Create app/cbl/CSACTVW.cbl — a pure business logic subprogram that:
   - Accepts account ID via LINKAGE SECTION
   - Reads account data from VSAM
   - Reads associated cards via cross-reference
   - Returns account details and card list via LINKAGE SECTION
   - Performs all validation and error handling
   - Has NO CICS screen commands (no SEND MAP, RECEIVE MAP, BMS references)
2. Refactor COACTVWC.cbl to call CSACTVW as a subprogram (EXEC CICS LINK) and only handle screen I/O
3. Create app/cpy/CSACTVWY.cpy — the LINKAGE SECTION data contract (effectively an API definition)
4. Document the pattern in docs/SERVICE_EXTRACTION.md for other programs to follow
5. Include a mapping table of which online programs should be extracted next (priority order: Account Update, Card operations, Transaction operations)
Create a PR.
```

### 3.2 Build Automated Test Suite (Gap 3.1)

Create a test framework for batch programs using GnuCOBOL.

**Devin Prompt:**
```
Create an automated test framework for CardDemo batch programs:
1. Create a test directory structure: tests/batch/, tests/data/, tests/expected/
2. Create tests/batch/test_cbtrn02c.sh — integration test for transaction posting:
   - Set up test VSAM-equivalent indexed files using GnuCOBOL file handling
   - Create minimal test data: 1 account, 1 card, 1 cross-reference, 5 daily transactions (3 valid, 2 invalid)
   - Run CBTRN02C
   - Verify: 3 records in transaction master, 2 records in reject file, account balance updated correctly
3. Create tests/batch/test_cbact04c.sh — test for interest calculation:
   - Set up test data with known balances and interest rates
   - Run CBACT04C
   - Verify calculated interest matches expected values
4. Create a test runner script tests/run_all_tests.sh
5. Add the test suite to the GitHub Actions CI workflow
6. Document the testing approach in docs/TESTING.md
Create a PR.
```

### 3.3 Add Health Check Transaction (Gap 6.2)

Create a CICS transaction for application health monitoring.

**Devin Prompt:**
```
Create a health check transaction for CardDemo:
1. Create app/cbl/COHLTH00.cbl — CICS health check program that:
   - Attempts to READ from each VSAM file (ACCTDAT, CARDDAT, CUSTDAT, CCXREF, TRANSACT, USRSEC)
   - Reports status of each file (OK/FAIL) with CICS RESP code
   - Checks if the CICS region can process transactions
   - Returns a summary: all-OK or list of failed components
   - Outputs results as a structured message (suitable for monitoring tools)
2. Create the BMS map COHLTH00.bms for displaying health status on 3270
3. Define transaction CCHK in the CSD
4. Add to the CARDDEMO.CSD file
5. Document the health check in docs/OPERATIONS.md
Create a PR.
```

### 3.4 Add OpenAPI-Style API Documentation (Gap 5.4)

Create machine-readable documentation of the transaction API surface.

**Devin Prompt:**
```
Create API documentation for CardDemo's CICS transactions:
1. Create docs/api/transactions.yaml — an OpenAPI-style YAML document (adapted for CICS) that describes each transaction:
   - Transaction ID, program name, function
   - Input fields (from BMS map copybooks and COMMAREA)
   - Output fields (from BMS map copybooks)
   - Error conditions and messages
   - Required user type (Admin/User)
2. Create docs/api/data-models.yaml — YAML description of all VSAM record layouts (from copybooks) with field names, types, lengths, and descriptions
3. Create docs/api/mq-messages.yaml — MQ message format descriptions for the optional modules
4. Generate a human-readable docs/API_REFERENCE.md from the YAML files
Create a PR.
```

### 3.5 Add Graceful Degradation for Optional Modules (Gap 7.4)

Make menu options dynamically reflect available subsystems.

**Devin Prompt:**
```
Add graceful degradation for optional modules in CardDemo:
1. Create app/cpy/CSMODSTY.cpy — module status flags:
   - MOD-DB2-AVAILABLE PIC X(01) VALUE 'N'
   - MOD-IMS-AVAILABLE PIC X(01) VALUE 'N'
   - MOD-MQ-AVAILABLE PIC X(01) VALUE 'N'
2. Create app/cbl/CSMODCHK.cbl — module availability checker that:
   - Tests DB2 connectivity (attempt a simple SQL SELECT)
   - Tests IMS availability
   - Tests MQ queue availability
   - Returns status flags
3. Update COMEN01C.cbl to call CSMODCHK and:
   - Grey out / skip menu options for unavailable modules
   - Display "(unavailable)" next to disabled options
   - Show a user-friendly message if an unavailable option is selected
4. Update COADM01C.cbl similarly for admin menu
5. Make the module check results cacheable in the COMMAREA to avoid repeated checks
Create a PR.
```

### 3.6 Implement Distributed Tracing (Gap 6.4)

Add correlation IDs to cross-program execution flows.

**Devin Prompt:**
```
Add correlation ID tracking to CardDemo:
1. Add a CDEMO-CORRELATION-ID PIC X(16) field to the CARDDEMO-COMMAREA (COCOM01Y.cpy) using space from existing FILLER or extending the area
2. In COSGN00C.cbl, generate a unique correlation ID on successful login (use timestamp + user ID combination)
3. Pass the correlation ID through all XCTL and LINK calls via COMMAREA
4. Include the correlation ID in all log messages and error outputs
5. For batch programs, generate a correlation ID at program start using timestamp + job name
6. For MQ messages, include the correlation ID in the MQ message header (MQMD CorrelId field)
7. Document the tracing approach in docs/OBSERVABILITY.md
Create a PR.
```

---

## Phase Summary

| Phase | Items | Focus | Timeline |
|:------|------:|:------|:---------|
| Phase 1 | 6 | Quick wins: compilation fixes, CI, security hardening, documentation | 1–2 weeks |
| Phase 2 | 8 | Important: error handling, logging, audit, test data, idempotency, retry | 1–2 months |
| Phase 3 | 6 | Polish: service extraction, test suite, health checks, API docs, tracing | 3–6 months |

### Critical Path

```
Phase 1.1 (Fix Compilation) ──▶ Phase 1.2 (CI Pipeline) ──▶ Phase 2.6 (Test Data) ──▶ Phase 3.2 (Test Suite)
Phase 1.3 (Password Hashing) ──▶ Phase 2.3 (PII Masking)
Phase 2.1 (Error Framework) ──▶ Phase 2.2 (Return Codes) ──▶ Phase 2.4 (Logging) ──▶ Phase 3.6 (Tracing)
Phase 3.1 (Service Extraction) ──▶ Phase 3.4 (API Docs)
```
