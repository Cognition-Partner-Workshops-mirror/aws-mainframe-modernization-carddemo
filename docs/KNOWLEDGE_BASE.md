# CardDemo Application Knowledge Base

## 1. Architecture Overview

### 1.1 Executive Summary

CardDemo is a mainframe-based credit card management application built with COBOL, CICS, and VSAM. It serves as an AWS Mainframe Modernization reference application, demonstrating core mainframe patterns including pseudo-conversational CICS transactions, VSAM indexed file storage, JCL batch processing, and BMS 3270 terminal screen maps.

### 1.2 Services Inventory

| Module | Type | Programs | Description |
|--------|------|----------|-------------|
| Online (CICS) | Interactive | 31 COBOL programs | Real-time transaction processing via 3270 terminals |
| Batch (JCL) | Scheduled | 38 JCL jobs, 8+ batch COBOL programs | Nightly/periodic batch processing |
| Optional: IMS-DB2-MQ | Interactive | Separate module | Authorization via IMS DB, DB2, and MQ |
| Optional: DB2 Tran Types | Admin | Separate module | Transaction type management via DB2 |
| Optional: VSAM-MQ | Integration | Separate module | VSAM-to-MQ message bridge |

### 1.3 Communication Patterns

```
                    +-----------+
                    | 3270      |
                    | Terminal  |
                    +-----+-----+
                          |
                    +-----v-----+
                    |   CICS    |
                    | Region    |
                    +-----+-----+
                          |
            +-------------+-------------+
            |             |             |
      +-----v-----+ +----v----+ +------v------+
      | Signon    | | Menu    | | Admin Menu  |
      | COSGN00C  | | COMEN01C| | COADM01C   |
      +-----------+ +----+----+ +------+------+
                         |             |
         +-------+------+------+      +---+---+---+
         |       |      |      |      |   |   |   |
      +--v-+ +--v-+ +--v-+ +--v-+  +-v-+-v-+-v-+-v-+
      |Acct| |Card| |Tran| |Bill|  |Usr|Usr|Usr|Usr|
      |View| |List| |List| |Pay |  |Lst|Add|Upd|Del|
      +----+ +----+ +----+ +----+  +---+---+---+---+
                                    (Admin Only)

      +--------------------------------------------+
      |           VSAM Data Files                   |
      | USRSEC | ACCTDAT | CARDDAT | TRANSACT |    |
      | CUSTDAT| CCXREF  | CARDAIX | CXACAIX  |    |
      +--------------------------------------------+

      +--------------------------------------------+
      |          Batch Processing (JCL)             |
      | Daily Transaction Posting (CBTRN02C)        |
      | Interest Calculation (CBACT04C)             |
      | Statement Generation (CBSTM03A)             |
      | Transaction Reports (via CORPT00C trigger)  |
      +--------------------------------------------+
```

### 1.4 Key Architectural Patterns

| Pattern | Implementation | Location |
|---------|---------------|----------|
| Pseudo-conversational CICS | `EXEC CICS RETURN TRANSID(...) COMMAREA(...)` | All online programs |
| COMMAREA state passing | `CARDDEMO-COMMAREA` (copybook `COCOM01Y`) | All online programs |
| XCTL program transfer | `EXEC CICS XCTL PROGRAM(...)` | Menu-to-subprogram navigation |
| HANDLE ABEND | `EXEC CICS HANDLE ABEND LABEL(...)` | Error recovery in most programs |
| BMS screen maps | MAP/MAPSET send/receive | All online programs |
| VSAM KSDS with AIX | Primary key + alternate index access | CARDDAT, CCXREF files |
| Batch file processing | Sequential read + indexed write | CBTRN02C, CBACT04C |
| JCL job submission from online | Extra-partition TDQ / INTRDR | CORPT00C (report generation) |

---

## 2. Data Model Documentation

### 2.1 Account Entity (`CVACT01Y.cpy` - RECLN 300)

| Field | PIC | Description |
|-------|-----|-------------|
| `ACCT-ID` | `9(11)` | Primary key - 11-digit account number |
| `ACCT-ACTIVE-STATUS` | `X(01)` | Account status flag |
| `ACCT-CURR-BAL` | `S9(10)V99` | Current balance (signed, 2 decimal) |
| `ACCT-CREDIT-LIMIT` | `S9(10)V99` | Credit limit |
| `ACCT-CASH-CREDIT-LIMIT` | `S9(10)V99` | Cash advance limit |
| `ACCT-OPEN-DATE` | `X(10)` | Account open date |
| `ACCT-EXPIRAION-DATE` | `X(10)` | Account expiration date |
| `ACCT-REISSUE-DATE` | `X(10)` | Card reissue date |
| `ACCT-CURR-CYC-CREDIT` | `S9(10)V99` | Current cycle credit total |
| `ACCT-CURR-CYC-DEBIT` | `S9(10)V99` | Current cycle debit total |
| `ACCT-ADDR-ZIP` | `X(10)` | Account holder ZIP code |
| `ACCT-GROUP-ID` | `X(10)` | Account group (for interest rate lookup) |
| `FILLER` | `X(178)` | Reserved space |

**VSAM File**: `ACCTDAT` (KSDS, key = `ACCT-ID`)

### 2.2 Card Entity (`CVACT02Y.cpy` - RECLN 150)

| Field | PIC | Description |
|-------|-----|-------------|
| `CARD-NUM` | `X(16)` | Primary key - 16-digit card number |
| `CARD-ACCT-ID` | `9(11)` | Foreign key to Account |
| `CARD-CVV-CD` | `9(03)` | CVV security code |
| `CARD-EMBOSSED-NAME` | `X(50)` | Name embossed on card |
| `CARD-EXPIRAION-DATE` | `X(10)` | Card expiration date (YYYY-MM-DD) |
| `CARD-ACTIVE-STATUS` | `X(01)` | Active status (Y/N) |
| `FILLER` | `X(59)` | Reserved space |

**VSAM File**: `CARDDAT` (KSDS, key = `CARD-NUM`)
**Alternate Index**: `CARDAIX` (key = `CARD-ACCT-ID`)

### 2.3 Customer Entity (`CVCUS01Y.cpy` / `CUSTREC.cpy` - RECLN 500)

| Field | PIC | Description |
|-------|-----|-------------|
| `CUST-ID` | `9(09)` | Primary key - 9-digit customer ID |
| `CUST-FIRST-NAME` | `X(25)` | First name |
| `CUST-MIDDLE-NAME` | `X(25)` | Middle name |
| `CUST-LAST-NAME` | `X(25)` | Last name |
| `CUST-ADDR-LINE-1` | `X(50)` | Address line 1 |
| `CUST-ADDR-LINE-2` | `X(50)` | Address line 2 |
| `CUST-ADDR-LINE-3` | `X(50)` | Address line 3 |
| `CUST-ADDR-STATE-CD` | `X(02)` | State code |
| `CUST-ADDR-COUNTRY-CD` | `X(03)` | Country code |
| `CUST-ADDR-ZIP` | `X(10)` | ZIP/postal code |
| `CUST-PHONE-NUM-1` | `X(15)` | Primary phone |
| `CUST-PHONE-NUM-2` | `X(15)` | Secondary phone |
| `CUST-SSN` | `9(09)` | Social Security Number |
| `CUST-GOVT-ISSUED-ID` | `X(20)` | Government ID |
| `CUST-DOB-YYYY-MM-DD` | `X(10)` | Date of birth |
| `CUST-EFT-ACCOUNT-ID` | `X(10)` | EFT account reference |
| `CUST-PRI-CARD-HOLDER-IND` | `X(01)` | Primary cardholder indicator |
| `CUST-FICO-CREDIT-SCORE` | `9(03)` | FICO credit score |
| `FILLER` | `X(168)` | Reserved space |

**VSAM File**: `CUSTDAT` (KSDS, key = `CUST-ID`)

### 2.4 Transaction Entity (`CVTRA05Y.cpy` - RECLN 350)

| Field | PIC | Description |
|-------|-----|-------------|
| `TRAN-ID` | `X(16)` | Primary key - 16-digit transaction ID |
| `TRAN-TYPE-CD` | `X(02)` | Transaction type code |
| `TRAN-CAT-CD` | `9(04)` | Transaction category code |
| `TRAN-SOURCE` | `X(10)` | Transaction source (e.g., POS TERM) |
| `TRAN-DESC` | `X(100)` | Transaction description |
| `TRAN-AMT` | `S9(09)V99` | Transaction amount (signed) |
| `TRAN-MERCHANT-ID` | `9(09)` | Merchant identifier |
| `TRAN-MERCHANT-NAME` | `X(50)` | Merchant name |
| `TRAN-MERCHANT-CITY` | `X(50)` | Merchant city |
| `TRAN-MERCHANT-ZIP` | `X(10)` | Merchant ZIP code |
| `TRAN-CARD-NUM` | `X(16)` | Card number used |
| `TRAN-ORIG-TS` | `X(26)` | Origination timestamp |
| `TRAN-PROC-TS` | `X(26)` | Processing timestamp |
| `FILLER` | `X(20)` | Reserved space |

**VSAM File**: `TRANSACT` (KSDS, key = `TRAN-ID`)

### 2.5 Card Cross-Reference Entity (`CVACT03Y.cpy` - RECLN 50)

| Field | PIC | Description |
|-------|-----|-------------|
| `XREF-CARD-NUM` | `X(16)` | Primary key - card number |
| `XREF-CUST-ID` | `9(09)` | Customer ID |
| `XREF-ACCT-ID` | `9(11)` | Account ID |
| `FILLER` | `X(14)` | Reserved space |

**VSAM File**: `CCXREF` (KSDS, key = `XREF-CARD-NUM`)
**Alternate Index**: `CXACAIX` (key = `XREF-ACCT-ID`)

### 2.6 User Security Entity (`CSUSR01Y.cpy` - RECLN 80)

| Field | PIC | Description |
|-------|-----|-------------|
| `SEC-USR-ID` | `X(08)` | Primary key - user login ID |
| `SEC-USR-FNAME` | `X(20)` | First name |
| `SEC-USR-LNAME` | `X(20)` | Last name |
| `SEC-USR-PWD` | `X(08)` | Password (plaintext) |
| `SEC-USR-TYPE` | `X(01)` | User type: A=Admin, U=Regular |
| `SEC-USR-FILLER` | `X(23)` | Reserved space |

**VSAM File**: `USRSEC` (KSDS, key = `SEC-USR-ID`)

### 2.7 Transaction Category Balance (`CVTRA01Y.cpy` - RECLN 50)

| Field | PIC | Description |
|-------|-----|-------------|
| `TRAN-CAT-KEY` | Composite | Compound key (below) |
| `TRANCAT-ACCT-ID` | `9(11)` | Account ID |
| `TRANCAT-TYPE-CD` | `X(02)` | Transaction type code |
| `TRANCAT-CD` | `9(04)` | Transaction category code |
| `TRAN-CAT-BAL` | `S9(09)V99` | Category balance |
| `FILLER` | `X(22)` | Reserved space |

**VSAM File**: `TCATBAL` (KSDS, key = `TRAN-CAT-KEY`)

### 2.8 Disclosure Group / Interest Rate (`CVTRA02Y.cpy` - RECLN 50)

| Field | PIC | Description |
|-------|-----|-------------|
| `DIS-GROUP-KEY` | Composite | Compound key (below) |
| `DIS-ACCT-GROUP-ID` | `X(10)` | Account group ID |
| `DIS-TRAN-TYPE-CD` | `X(02)` | Transaction type code |
| `DIS-TRAN-CAT-CD` | `9(04)` | Transaction category code |
| `DIS-INT-RATE` | `S9(04)V99` | Interest rate |
| `FILLER` | `X(28)` | Reserved space |

**VSAM File**: `DISCGRP` (KSDS, key = `DIS-GROUP-KEY`)

### 2.9 Daily Transaction (`CVTRA06Y.cpy` - RECLN 350)

Same structure as Transaction Entity (`CVTRA05Y`) but prefixed with `DALYTRAN-` instead of `TRAN-`. Used as input to daily batch posting job.

**File**: `DALYTRAN` (Sequential)

### 2.10 Entity Relationship Summary

```
  CUSTOMER (1) ----< (N) CARD-XREF >---- (1) ACCOUNT
       |                    |
       |              CARD-NUM (FK)
       |                    |
       |              (1) CARD (N) >---- (1) ACCOUNT
       |
       +--- CUST-ID
       
  ACCOUNT (1) ----< (N) TRANSACTION
       |
       +----< (N) TRAN-CAT-BALANCE
       |
       +---- ACCT-GROUP-ID ----> DISCLOSURE-GROUP (interest rates)
       
  USER-SECURITY (standalone - authentication only)
```

---

## 3. Transaction / API Surface Map

### 3.1 Online CICS Transactions (Regular User Menu)

| # | Transaction | Program | Map/Mapset | Function | Key Files |
|---|------------|---------|------------|----------|-----------|
| - | CC00 | COSGN00C | COSGN0A/COSGN00 | User Sign-on | USRSEC |
| - | CM00 | COMEN01C | COMEN1A/COMEN01 | Main Menu | - |
| 1 | CA00 | COACTVWC | COACTVW/COACTVW | Account View | ACCTDAT, CARDDAT, CUSTDAT, CARDAIX, CXACAIX |
| 2 | CA00 | COACTUPC | COACTUP/COACTUP | Account Update | ACCTDAT, CUSTDAT, CARDAIX, CXACAIX |
| 3 | CCLI | COCRDLIC | COCRDLI/COCRDLI | Credit Card List | CARDDAT, CARDAIX |
| 4 | CCDL | COCRDSLC | COCRDSL/COCRDSL | Credit Card View | CARDDAT, CARDAIX, CXACAIX |
| 5 | CCUP | COCRDUPC | COCRDUP/COCRDUP | Credit Card Update | CARDDAT, CARDAIX |
| 6 | CT00 | COTRN00C | COTRN0A/COTRN00 | Transaction List | TRANSACT |
| 7 | CT01 | COTRN01C | COTRN1A/COTRN01 | Transaction View | TRANSACT |
| 8 | CT02 | COTRN02C | COTRN2A/COTRN02 | Transaction Add | TRANSACT, CCXREF, CXACAIX, ACCTDAT |
| 9 | CR00 | CORPT00C | CORPT0A/CORPT00 | Transaction Reports | TRANSACT (submits batch JCL) |
| 10 | CB00 | COBIL00C | COBIL0A/COBIL00 | Bill Payment | TRANSACT, ACCTDAT, CXACAIX |
| 11 | - | COPAUS0C | - | Pending Auth View | (optional module) |

### 3.2 Online CICS Transactions (Admin Menu)

| # | Transaction | Program | Function | Key Files |
|---|------------|---------|----------|-----------|
| - | CA00 | COADM01C | Admin Menu | - |
| 1 | CU00 | COUSR00C | User List | USRSEC |
| 2 | CU01 | COUSR01C | User Add | USRSEC |
| 3 | CU00 | COUSR02C | User Update | USRSEC |
| 4 | CU00 | COUSR03C | User Delete | USRSEC |
| 5 | - | COTRTLIC | Tran Type List/Update (DB2) | DB2 tables |
| 6 | - | COTRTUPC | Tran Type Maintenance (DB2) | DB2 tables |

### 3.3 Batch Programs

| Program | JCL Job | Function | Input Files | Output Files |
|---------|---------|----------|-------------|--------------|
| CBTRN01C | TRANPROC | Transaction file load | Sequential input | TRANSACT (indexed) |
| CBTRN02C | POSTRN00 | Daily transaction posting | DALYTRAN | TRANSACT, ACCTDAT, TCATBAL, DALYREJS |
| CBTRN03C | INTRCALC | Transaction category balance | TRANSACT | TCATBAL |
| CBACT01C | Various | Account file operations | ACCTDAT | Various |
| CBACT02C | Various | Account data processing | ACCTDAT | Various |
| CBACT03C | Various | Account/Card cross-ref | CCXREF | Various |
| CBACT04C | INTCALC | Interest calculation | TCATBAL, DISCGRP, ACCTDAT | TRANSACT (interest entries) |
| CBSTM03A | STMTGEN | Statement generation (text + HTML) | TRANSACT, CCXREF, CUSTDAT, ACCTDAT | STMTFILE, HTMLFILE |
| CBSTM03B | STMTGEN | Statement file I/O subroutine | Called by CBSTM03A | - |
| CSUTLDTC | Various | Date validation utility | Called by COTRN02C, CORPT00C | - |
| CSUTLDPY | Various | Date utility (leap year) | Called by various | - |

### 3.4 Key Navigation Flows

**Sign-on Flow:**
```
COSGN00C (CC00) --> validates user against USRSEC
  |-- Admin user (type 'A') --> COADM01C (Admin Menu)
  |-- Regular user (type 'U') --> COMEN01C (Main Menu)
```

**Transaction View Flow:**
```
COMEN01C (Menu) --> option 6 --> COTRN00C (Transaction List)
  --> select 'S' on a row --> COTRN01C (Transaction View)
  --> PF3 returns to COTRN00C
  --> PF3 returns to COMEN01C
```

**Bill Payment Flow:**
```
COMEN01C (Menu) --> option 10 --> COBIL00C (Bill Payment)
  --> Enter account ID --> reads ACCTDAT for balance
  --> Confirm 'Y' --> reads CXACAIX for card number
  --> Creates new TRANSACT record (type '02', cat 2)
  --> Updates ACCTDAT balance (balance - payment amount)
```

**Report Generation Flow:**
```
COMEN01C (Menu) --> option 9 --> CORPT00C (Report Screen)
  --> Select Monthly/Yearly/Custom dates
  --> Validates dates via CSUTLDTC
  --> Submits JCL to internal reader (INTRDR TDQ)
  --> JCL executes TRANREPT procedure
```

---

## 4. Key Business Logic Inventory

### 4.1 Authentication (COSGN00C)

1. User enters User ID and Password on signon screen
2. Program reads `USRSEC` file by `SEC-USR-ID` key
3. If record found, compares entered password with `SEC-USR-PWD`
4. If match, sets `CDEMO-USER-TYPE` from `SEC-USR-TYPE`
5. Routes to `COADM01C` (admin) or `COMEN01C` (regular user)
6. Password stored and compared in plaintext (8 chars max)

### 4.2 Bill Payment (COBIL00C)

1. User enters Account ID
2. Program reads `ACCTDAT` to get current balance
3. If balance <= 0, rejects with "nothing to pay"
4. User confirms with 'Y'
5. Reads `CXACAIX` to resolve card number for account
6. Reads last transaction ID from `TRANSACT` (HIGH-VALUES browse) to generate next ID
7. Creates new transaction record: type '02', category 2, source 'POS TERM', description 'BILL PAYMENT - ONLINE'
8. Writes transaction to `TRANSACT`
9. Updates `ACCTDAT`: `ACCT-CURR-BAL = ACCT-CURR-BAL - TRAN-AMT`

### 4.3 Daily Transaction Posting (CBTRN02C)

1. Opens 6 files: DALYTRAN (input), TRANSACT (output), XREF, DALYREJS (rejects), ACCOUNT, TCATBAL
2. Reads daily transaction file sequentially
3. For each record:
   a. Validates card number exists in XREF file (`1500-A-LOOKUP-XREF`)
   b. Validates account exists in ACCOUNT file (`1500-B-LOOKUP-ACCT`)
   c. If valid: posts to TRANSACT and updates TCATBAL
   d. If invalid: writes to DALYREJS with failure reason
4. Displays final counts: processed vs. rejected
5. Sets RETURN-CODE = 4 if any rejects occurred

### 4.4 Interest Calculation (CBACT04C)

1. Reads TCATBAL file sequentially (grouped by account)
2. For each account group:
   a. Looks up account data from ACCTDAT
   b. Looks up card cross-reference from XREF
   c. For each category balance, looks up interest rate from DISCGRP
   d. Computes monthly interest: `balance * rate / 12`
   e. Accumulates total interest per account
3. Updates account balance: `ACCT-CURR-BAL + total interest`
4. Resets cycle credit/debit counters to zero
5. Writes interest charge transaction to TRANSACT output

### 4.5 Statement Generation (CBSTM03A)

1. Uses mainframe control block addressing (PSA -> TCB -> TIOT) to enumerate DD names
2. Uses ALTER/GO TO pattern for dynamic file dispatch
3. Reads cross-reference file to iterate by card
4. For each card: looks up customer and account data
5. Generates two output formats:
   a. Plain text statement (80-char fixed-width)
   b. HTML statement with inline CSS styling
6. Includes: customer name/address, account details, transaction summary, totals
7. Uses 2-dimensional array (`WS-TRNX-TABLE`: 51 cards x 10 transactions)
8. Calls subroutine `CBSTM03B` for file I/O operations

### 4.6 Card Update (COCRDUPC)

1. User selects card from list or enters account/card number
2. Program reads `CARDAIX` or `CARDDAT` to retrieve card details
3. Displays current values; user modifies fields
4. Validates: card name (alpha only), status (Y/N), expiry month (1-12), expiry year (1950-2099)
5. Compares new values against old values stored in program COMMAREA
6. If changes detected, requires F5 confirmation
7. Locks record for update (`EXEC CICS READ UPDATE`)
8. Verifies record unchanged since last read (optimistic concurrency)
9. Rewrites card record with updated values

---

## 5. Integration Points

### 5.1 Core VSAM File System

| File DD Name | VSAM Type | Key | Record Length | Used By |
|-------------|-----------|-----|---------------|---------|
| USRSEC | KSDS | SEC-USR-ID (X(08)) | 80 | COSGN00C, COUSR00C-03C |
| ACCTDAT | KSDS | ACCT-ID (9(11)) | 300 | Most online & batch programs |
| CARDDAT | KSDS | CARD-NUM (X(16)) | 150 | Card management programs |
| CARDAIX | AIX on CARDDAT | CARD-ACCT-ID (9(11)) | - | Card lookup by account |
| CUSTDAT | KSDS | CUST-ID (9(09)) | 500 | Account view, statements |
| TRANSACT | KSDS | TRAN-ID (X(16)) | 350 | Transaction programs, batch |
| CCXREF | KSDS | XREF-CARD-NUM (X(16)) | 50 | Card-to-account resolution |
| CXACAIX | AIX on CCXREF | XREF-ACCT-ID (9(11)) | - | Account-to-card resolution |
| DALYTRAN | Sequential | - | 350 | Daily transaction input |
| DALYREJS | Sequential | - | 430 | Rejected transactions |
| TCATBAL | KSDS | Composite (17 bytes) | 50 | Category balance tracking |
| DISCGRP | KSDS | Composite (16 bytes) | 50 | Interest rate lookup |

### 5.2 Optional Module: IMS DB2 MQ Authorization

- **Purpose**: Real-time credit card authorization
- **Technology**: IMS DB for hierarchical data, DB2 for relational queries, MQ for message queuing
- **Location**: `app-authorization-ims-db2-mq/`
- **Integration**: Separate CICS region or IMS region; communicates via MQ messages

### 5.3 Optional Module: DB2 Transaction Types

- **Purpose**: Admin maintenance of transaction type codes
- **Technology**: DB2 relational database
- **Location**: `app-transaction-type-db2/`
- **Programs**: COTRTLIC (list/update), COTRTUPC (maintenance)
- **Integration**: Referenced in admin menu (COADM02Y options 5-6)

### 5.4 Optional Module: VSAM-MQ Bridge

- **Purpose**: Bridge VSAM file operations to MQ message queue
- **Location**: `app-vsam-mq/`
- **Integration**: Enables event-driven processing of VSAM updates

### 5.5 Job Scheduling

| Scheduler | Location | Purpose |
|-----------|----------|---------|
| Control-M | `app/scheduler/Control-M/` | Enterprise job scheduling definitions |
| CA7 | `app/scheduler/CA7/` | Alternative job scheduling definitions |

### 5.6 External Dependencies

- **CICS Transaction Server**: Runtime environment for all online programs
- **VSAM (IDCAMS)**: File creation, alternate index definition, catalog management
- **JES2/JES3**: Job entry subsystem for batch execution
- **RACF**: External security (referenced in README but not implemented in application code; security is via USRSEC file)
- **Internal Reader (INTRDR)**: Used by CORPT00C to submit batch JCL from online
- **SORT/DFSORT**: Used in JCL for data sorting operations

---

## 6. Build and Deployment Pipeline Summary

### 6.1 Compilation

- **No automated build system** (no Makefile, Gradle, Maven, or CI/CD pipeline in the repository)
- COBOL programs are compiled on the mainframe using the COBOL compiler
- BMS maps are assembled using the CICS map assembler
- JCL procedures reference compiled load modules in `AWS.M2.CARDDEMO.LOADLIB`

### 6.2 Dataset Layout

Programs and data are deployed to mainframe datasets following the naming convention:
```
AWS.M2.CARDDEMO.COBOL    - COBOL source
AWS.M2.CARDDEMO.COPY     - Copybooks
AWS.M2.CARDDEMO.JCL      - JCL procedures
AWS.M2.CARDDEMO.BMS      - BMS source maps
AWS.M2.CARDDEMO.LOADLIB  - Compiled load modules
AWS.M2.CARDDEMO.DATA     - Data files
```

### 6.3 Deployment Steps (from README)

1. Create mainframe datasets (PDS and VSAM)
2. Upload COBOL source, copybooks, JCL, BMS maps
3. Run DEFVSAM JCL to define VSAM clusters and alternate indexes
4. Compile COBOL programs and assemble BMS maps
5. Upload sample data (ASCII or EBCDIC format)
6. Define CICS resources (programs, transactions, files, maps)
7. Install CICS resource group

### 6.4 Sample Data

| Directory | Format | Purpose |
|-----------|--------|---------|
| `app/data/ASCII/` | ASCII | Sample datasets for non-mainframe environments |
| `app/data/EBCDIC/` | EBCDIC | Sample datasets for mainframe deployment |

### 6.5 Assembler Programs

| Program | Location | Purpose |
|---------|----------|---------|
| MVSWAIT | `app/asm/MVSWAIT.asm` | Wait/delay utility |
| COBDATFT | `app/asm/COBDATFT.asm` | Date formatting utility |
