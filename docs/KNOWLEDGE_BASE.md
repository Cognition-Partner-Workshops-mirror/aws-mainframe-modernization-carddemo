# CardDemo — Architecture Knowledge Base

## 1. Architecture Overview

### 1.1 System Summary

CardDemo is a mainframe credit card management application built on IBM z/OS. It simulates a production-grade environment for testing AWS and partner migration/modernization tooling. The application manages credit card accounts, customers, transactions, bill payments, reporting, and user security through two complementary processing models:

- **Online (CICS)** — 3270-terminal-based interactive transactions using pseudo-conversational design
- **Batch (JCL)** — Scheduled and ad-hoc batch jobs for data loading, transaction posting, interest calculation, statement generation, and data migration

### 1.2 Core Technology Stack

| Layer | Technology | Purpose |
|:------|:-----------|:--------|
| Language | COBOL | All business logic (batch and online) |
| Transaction Monitor | CICS | Online transaction processing, screen management, pseudo-conversational control |
| Data Storage | VSAM KSDS (with AIX) | Primary indexed data store for all entities |
| Batch Orchestration | JCL | Job definitions for batch programs; executed via z/OS JES |
| Job Scheduling | Control-M | Daily, weekly, monthly batch cycles |
| Security | RACF | Mainframe-level security; app-level user/password in VSAM |
| Screen Layout | BMS Maps | 3270 terminal screen definitions |
| Assembly Utilities | ASSEMBLER | Timer control (MVSWAIT), date conversion (COBDATFT) |

### 1.3 Optional Extension Stack

| Technology | Module | Purpose |
|:-----------|:-------|:--------|
| DB2 | Transaction Type Mgmt | Relational storage for transaction type/category reference data |
| IMS DB | Pending Authorizations | Hierarchical database for authorization storage |
| IBM MQ | Auth Processing / VSAM-MQ | Asynchronous request/response messaging |

### 1.4 High-Level Architecture Diagram (Textual)

```
┌──────────────────────────────────────────────────────────────────┐
│                         z/OS LPAR                                │
│                                                                  │
│  ┌──────────────┐    ┌─────────────────────────────────────────┐ │
│  │  3270 Terminal│───▶│              CICS Region                │ │
│  │  (User/Admin)│    │  ┌──────┐ ┌──────┐ ┌──────┐ ┌────────┐ │ │
│  └──────────────┘    │  │COSGN │ │COMEN │ │COADM │ │CO*     │ │ │
│                      │  │00C   │ │01C   │ │01C   │ │(online)│ │ │
│                      │  └──┬───┘ └──┬───┘ └──┬───┘ └──┬─────┘ │ │
│                      │     │        │        │        │        │ │
│                      │     ▼        ▼        ▼        ▼        │ │
│                      │  ┌──────────────────────────────┐       │ │
│                      │  │    VSAM KSDS Files (FCT)     │       │ │
│                      │  │ ACCTDAT CARDDAT CUSTDAT       │       │ │
│                      │  │ CCXREF  TRANSACT USRSEC       │       │ │
│                      │  │ DISCGRP TRANCATG TRANTYPE     │       │ │
│                      │  │ TCATBAL CARDAIX  CXACAIX      │       │ │
│                      │  └──────────────────────────────┘       │ │
│                      └─────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Batch Subsystem (JES)                     │ │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ │ │
│  │  │CBTRN02C│ │CBACT04C│ │CBSTM03A│ │CBTRN03C│ │CBEXPORT/ │ │ │
│  │  │PostTran│ │IntCalc │ │Stmts   │ │Reports │ │CBIMPORT  │ │ │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └──────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─── Optional ───────────────────────────────────────────────┐  │
│  │  DB2 (Tran Types)   IMS DB (Auths)   MQ (Auth/Acct Ext)   │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 1.5 Communication Patterns

| Pattern | Where Used | Mechanism |
|:--------|:-----------|:----------|
| Pseudo-conversational | All online CICS programs | EXEC CICS RETURN TRANSID with COMMAREA |
| Program-to-program transfer | Sign-on → Menu → Function screens | EXEC CICS XCTL (transfer control) |
| Batch sequential processing | POSTTRAN, INTCALC, CREASTMT | Read files sequentially, process, write output |
| Request/Response messaging | MQ optional modules (CDRD, CDRA, CP00) | MQ PUT/GET with correlation ID |
| Two-phase commit | IMS-DB2-MQ Authorization | IMS + DB2 coordinated updates |

---

## 2. Data Models

### 2.1 Core Entities (VSAM KSDS Files)

| Entity | Copybook | Record Length | Primary Key | CICS File Name | Description |
|:-------|:---------|:-------------|:------------|:---------------|:------------|
| Account | CVACT01Y | 300 bytes | ACCT-ID (9(11)) | ACCTDAT | Credit card account master |
| Card | CVACT02Y | 150 bytes | CARD-NUM (X(16)) | CARDDAT | Credit card details |
| Customer | CVCUS01Y | 500 bytes | CUST-ID (9(09)) | CUSTDAT | Customer demographics |
| Card Cross-Reference | CVACT03Y | 50 bytes | XREF-CARD-NUM (X(16)) | CCXREF | Links Card → Customer → Account |
| Transaction | CVTRA05Y | 350 bytes | TRAN-ID (X(16)) | TRANSACT | Online transaction records |
| Daily Transaction | CVTRA06Y | 350 bytes | DALYTRAN-ID (X(16)) | DALYTRAN | Daily batch transaction input |
| Transaction Category Balance | CVTRA01Y | 50 bytes | Composite: ACCT-ID + TYPE-CD + CAT-CD | TCATBAL | Running balance per category |
| Disclosure Group | CVTRA02Y | 50 bytes | Composite: GROUP-ID + TYPE-CD + CAT-CD | DISCGRP | Interest rate schedules |
| Transaction Type | CVTRA03Y | 60 bytes | TRAN-TYPE (X(02)) | TRANTYPE | Reference: transaction type codes |
| Transaction Category | CVTRA04Y | 60 bytes | Composite: TYPE-CD + CAT-CD | TRANCATG | Reference: transaction categories |
| User Security | CSUSR01Y | 80 bytes | SEC-USR-ID (X(08)) | USRSEC | User credentials and role |

### 2.2 Entity Relationship Summary

```
Customer (CUST-ID)
    │
    ├──< Card Cross-Reference (XREF-CARD-NUM) >──┐
    │       contains: XREF-CUST-ID, XREF-ACCT-ID │
    │                                              │
    ▼                                              ▼
Card (CARD-NUM)                           Account (ACCT-ID)
    │  CARD-ACCT-ID ──────────────────────────┘    │
    │                                              │
    ▼                                              ▼
Transaction (TRAN-CARD-NUM) ◀──────────── Tran Cat Balance (ACCT-ID)
    │                                              │
    ▼                                              ▼
Disclosure Group (GROUP-ID) ◀── Account.GROUP-ID   Tran Category
                                                   Tran Type
```

- **Card Cross-Reference (CCXREF)** is the central join entity linking Card → Customer → Account
- An Alternate Index (CARDAIX) on Card file enables lookup by account
- An Alternate Index (CXACAIX) on Cross-Reference enables lookup by account

### 2.3 Account Entity — Field Details (CVACT01Y)

| Field | PIC | Description |
|:------|:----|:------------|
| ACCT-ID | 9(11) | Unique account identifier (primary key) |
| ACCT-ACTIVE-STATUS | X(01) | 'Y'=active, 'N'=inactive |
| ACCT-CURR-BAL | S9(10)V99 | Current balance (signed, 2 decimal) |
| ACCT-CREDIT-LIMIT | S9(10)V99 | Credit limit |
| ACCT-CASH-CREDIT-LIMIT | S9(10)V99 | Cash advance limit |
| ACCT-OPEN-DATE | X(10) | Account open date |
| ACCT-EXPIRAION-DATE | X(10) | Account expiration date |
| ACCT-REISSUE-DATE | X(10) | Last reissue date |
| ACCT-CURR-CYC-CREDIT | S9(10)V99 | Current cycle credit total |
| ACCT-CURR-CYC-DEBIT | S9(10)V99 | Current cycle debit total |
| ACCT-ADDR-ZIP | X(10) | Account zip code |
| ACCT-GROUP-ID | X(10) | Disclosure group identifier |
| FILLER | X(178) | Reserved |

### 2.4 Customer Entity — Field Details (CVCUS01Y)

| Field | PIC | Description |
|:------|:----|:------------|
| CUST-ID | 9(09) | Customer identifier (primary key) |
| CUST-FIRST-NAME | X(25) | First name |
| CUST-MIDDLE-NAME | X(25) | Middle name |
| CUST-LAST-NAME | X(25) | Last name |
| CUST-ADDR-LINE-1..3 | X(50) each | Address lines |
| CUST-ADDR-STATE-CD | X(02) | State code |
| CUST-ADDR-COUNTRY-CD | X(03) | Country code |
| CUST-ADDR-ZIP | X(10) | Zip code |
| CUST-PHONE-NUM-1, -2 | X(15) each | Phone numbers |
| CUST-SSN | 9(09) | Social security number |
| CUST-GOVT-ISSUED-ID | X(20) | Government-issued ID |
| CUST-DOB-YYYY-MM-DD | X(10) | Date of birth |
| CUST-EFT-ACCOUNT-ID | X(10) | EFT account for bill payment |
| CUST-PRI-CARD-HOLDER-IND | X(01) | Primary card holder indicator |
| CUST-FICO-CREDIT-SCORE | 9(03) | FICO score |

### 2.5 Transaction Entity — Field Details (CVTRA05Y)

| Field | PIC | Description |
|:------|:----|:------------|
| TRAN-ID | X(16) | Transaction identifier (primary key) |
| TRAN-TYPE-CD | X(02) | Transaction type code (FK to TRANTYPE) |
| TRAN-CAT-CD | 9(04) | Transaction category code |
| TRAN-SOURCE | X(10) | Source system |
| TRAN-DESC | X(100) | Description |
| TRAN-AMT | S9(09)V99 | Amount (signed, 2 decimal) |
| TRAN-MERCHANT-ID | 9(09) | Merchant identifier |
| TRAN-MERCHANT-NAME | X(50) | Merchant name |
| TRAN-MERCHANT-CITY | X(50) | Merchant city |
| TRAN-MERCHANT-ZIP | X(10) | Merchant zip |
| TRAN-CARD-NUM | X(16) | Card number (FK to CARDDAT) |
| TRAN-ORIG-TS | X(26) | Origination timestamp |
| TRAN-PROC-TS | X(26) | Processing timestamp |

### 2.6 User Security Entity (CSUSR01Y)

| Field | PIC | Description |
|:------|:----|:------------|
| SEC-USR-ID | X(08) | User ID (primary key) |
| SEC-USR-FNAME | X(20) | First name |
| SEC-USR-LNAME | X(20) | Last name |
| SEC-USR-PWD | X(08) | Password (plaintext) |
| SEC-USR-TYPE | X(01) | 'A'=Admin, 'U'=Regular user |

### 2.7 Optional Extension Data Models

#### DB2 Tables (Transaction Type Management)

| Table | Columns | Description |
|:------|:--------|:------------|
| CARDDEMO.TRANSACTION_TYPE | TR_TYPE CHAR(2), TR_DESCRIPTION VARCHAR(50) | Transaction type reference |
| CARDDEMO.TRANSACTION_TYPE_CATEGORY | TRC_TYPE_CODE CHAR(2), TRC_CATEGORY_CODE INT, TRC_DESCRIPTION VARCHAR(50) | Category reference |

#### DB2 Table (Fraud Tracking — IMS-DB2-MQ)

| Table | Key Columns | Description |
|:------|:------------|:------------|
| AUTHFRDS | CARD_NUM CHAR(16), AUTH_TS TIMESTAMP | Fraud cases from authorization processing |

#### IMS DB (Pending Authorizations)

| Database | Type | PSBs | Description |
|:---------|:-----|:-----|:------------|
| DBPAUTP0 | HIDAM | PSBPAUTB, PSBPAUTL | Authorization records |
| DBPAUTX0 | HIDAM index | — | Index for authorization lookup |

---

## 3. API Surface Map (Online CICS Transactions)

### 3.1 Core Transactions

| Trans ID | BMS Map | Program | Function | User Type | COMMAREA Fields Used |
|:---------|:--------|:--------|:---------|:----------|:---------------------|
| CC00 | COSGN00 | COSGN00C | Sign-on screen | All | USER-ID, USER-TYPE, PGM-CONTEXT |
| CM00 | COMEN01 | COMEN01C | Main menu (regular user) | User | FROM/TO-PROGRAM, menu option |
| CAVW | COACTVW | COACTVWC | Account view | User | ACCT-ID |
| CAUP | COACTUP | COACTUPC | Account update | User | ACCT-ID, all account fields |
| CCLI | COCRDLI | COCRDLIC | Credit card list | User | ACCT-ID |
| CCDL | COCRDSL | COCRDSLC | Credit card detail view | User | CARD-NUM |
| CCUP | COCRDUP | COCRDUPC | Credit card update | User | CARD-NUM, card fields |
| CT00 | COTRN00 | COTRN00C | Transaction list | User | ACCT-ID, CARD-NUM |
| CT01 | COTRN01 | COTRN01C | Transaction view | User | TRAN-ID |
| CT02 | COTRN02 | COTRN02C | Transaction add | User | Account/card/transaction fields |
| CR00 | CORPT00 | CORPT00C | Transaction reports | User | Date range, report params |
| CB00 | COBIL00 | COBIL00C | Bill payment | User | ACCT-ID, payment amount |
| CA00 | COADM01 | COADM01C | Admin menu | Admin | Admin menu option |
| CU00 | COUSR00 | COUSR00C | User list | Admin | User filter |
| CU01 | COUSR01 | COUSR01C | User add | Admin | User fields |
| CU02 | COUSR02 | COUSR02C | User update | Admin | SEC-USR-ID, user fields |
| CU03 | COUSR03 | COUSR03C | User delete | Admin | SEC-USR-ID |

### 3.2 Optional Extension Transactions

| Trans ID | BMS Map | Program | Module | Function |
|:---------|:--------|:--------|:-------|:---------|
| CPVS | COPAU00 | COPAUS0C | IMS-DB2-MQ | Pending authorization summary |
| CPVD | COPAU01 | COPAUS1C | IMS-DB2-MQ | Pending authorization details |
| CP00 | — | COPAUA0C | IMS-DB2-MQ | Process authorization requests (MQ trigger) |
| CTTU | COTRTUP | COTRTUPC | DB2 Tran Type | Transaction type add/edit |
| CTLI | COTRTLI | COTRTLIC | DB2 Tran Type | Transaction type list/update/delete |
| CDRD | — | CODATE01 | VSAM-MQ | System date inquiry via MQ |
| CDRA | — | COACCT01 | VSAM-MQ | Account details inquiry via MQ |

### 3.3 Navigation Flow

```
CC00 (Sign-on)
  ├── [Admin] ──▶ CA00 (Admin Menu)
  │                 ├── CU00 (User List) ──▶ CU01/CU02/CU03
  │                 ├── CTLI (Tran Type List) [optional DB2]
  │                 └── CTTU (Tran Type Add)  [optional DB2]
  │
  └── [User] ───▶ CM00 (Main Menu)
                    ├── 1. CAVW (Account View)
                    ├── 2. CAUP (Account Update)
                    ├── 3. CCLI (Card List)
                    ├── 4. CCDL (Card View)
                    ├── 5. CCUP (Card Update)
                    ├── 6. CT00 (Transaction List)
                    ├── 7. CT01 (Transaction View)
                    ├── 8. CT02 (Transaction Add)
                    ├── 9. CR00 (Reports)
                    ├── 10. CB00 (Bill Payment)
                    └── 11. CPVS (Pending Auth) [optional IMS-DB2-MQ]
```

---

## 4. Business Logic Inventory

### 4.1 Batch Programs

| Program | JCL Job | Function | Key Logic |
|:--------|:--------|:---------|:----------|
| CBACT01C | READACCT | Read account file | Sequential read of VSAM KSDS account file, display records |
| CBACT02C | READCARD | Read card file | Sequential read of card VSAM KSDS file |
| CBACT03C | READXREF | Read cross-reference | Sequential read of card-account cross-reference file |
| CBACT04C | INTCALC | Interest calculation | Reads transaction category balances, looks up disclosure group interest rates, computes interest per account, updates account balances; called as subprogram |
| CBCUS01C | READCUST | Read customer file | Sequential read of VSAM KSDS customer file |
| CBTRN01C | POSTTRAN (prep) | Validate daily transactions | Reads daily transaction file, validates card against cross-reference |
| CBTRN02C | POSTTRAN | Post transactions | Core batch processor — reads daily transactions, validates via cross-reference, updates transaction master and account balance, writes rejects |
| CBTRN03C | TRANREPT | Transaction report | Reads transactions, looks up type/category descriptions, generates formatted report |
| CBSTM03A | CREASTMT | Statement generation | Reads transactions, generates customer statements |
| CBSTM03B | — | Statement sub-program | Helper module for statement formatting |
| COBSWAIT | WAITSTEP | Wait/timer | COBOL wrapper for MVSWAIT assembler macro |
| CSUTLDTC | — | Date utility | Date conversion and validation routines |
| CBEXPORT | CBEXPORT | Branch migration export | Reads customer/account/xref/transaction files; creates multi-record export file with REDEFINES for different record types (Customer/Account/Transaction/Xref); uses COMP/COMP-3 for storage optimization |
| CBIMPORT | CBIMPORT | Branch migration import | Reads multi-record export file; splits into normalized target files; validates data integrity using checksums |

### 4.2 Key Business Rules

| Rule | Location | Description |
|:-----|:---------|:------------|
| Transaction Posting | CBTRN02C | Daily transactions validated against card cross-reference; rejected if card not found; account balance updated; category balance updated |
| Interest Calculation | CBACT04C | Per-account calculation using disclosure group rates against transaction category balances; monthly cycle |
| Authentication | COSGN00C | User ID looked up in USRSEC VSAM file; plaintext password comparison; routes Admin to COADM01C, User to COMEN01C |
| Role-Based Access | COCOM01Y | CDEMO-USER-TYPE: 'A'=Admin (CU*, CT* admin functions), 'U'=Regular (account/card/transaction functions) |
| Account Update Validation | COACTUPC | Extensive field validation — phone number format, alpha-only fields, signed number validation, yes/no fields, mandatory field checks |
| Authorization Processing | COPAUA0C | MQ-triggered; validates card via cross-reference; applies business rules for approve/decline; stores in IMS; fraud cases to DB2 |
| Batch Purge | CBPAUP0C | Deletes expired authorizations from IMS; adjusts available credit for unmatched authorizations |

### 4.3 Batch Processing Sequence (Daily Cycle)

```
1. CLOSEFIL  — Close VSAM files in CICS
2. TRANBKP   — Backup transaction master
3. POSTTRAN   — Post daily transactions (CBTRN02C)
4. INTCALC    — Calculate interest (CBACT04C) [monthly]
5. COMBTRAN   — Merge system + daily transactions
6. CREASTMT   — Generate statements (CBSTM03A)
7. TRANIDX    — Rebuild alternate indexes
8. OPENFIL    — Reopen VSAM files in CICS
```

---

## 5. Integration Points

### 5.1 CICS Runtime Integration

| Resource | Type | Purpose |
|:---------|:-----|:--------|
| CARDDEMO.CSD | CSD definitions | Maps all CICS programs, transactions, files, and mapsets |
| FCT entries | File Control Table | 13 VSAM file definitions with KSDS and AIX paths |
| PCT entries | Program Control Table | Program-to-transaction mapping |
| COMMAREA | Memory buffer | 01 CARDDEMO-COMMAREA in COCOM01Y — passes context between programs |

### 5.2 VSAM File Definitions (from CSD)

| CICS Name | Dataset | Key Type |
|:-----------|:--------|:---------|
| ACCTDAT | AWS.M2.CARDDEMO.ACCTDATA.VSAM.KSDS | Primary KSDS |
| CARDDAT | AWS.M2.CARDDEMO.CARDDATA.VSAM.KSDS | Primary KSDS |
| CARDAIX | AWS.M2.CARDDEMO.CARDDATA.VSAM.AIX.PATH | Alternate Index path |
| CUSTDAT | AWS.M2.CARDDEMO.CUSTDATA.VSAM.KSDS | Primary KSDS |
| CCXREF | AWS.M2.CARDDEMO.CARDXREF.VSAM.KSDS | Primary KSDS |
| CXACAIX | AWS.M2.CARDDEMO.CARDXREF.VSAM.AIX.PATH | Alternate Index path |
| TRANSACT | AWS.M2.CARDDEMO.TRANSACT.VSAM.KSDS | Primary KSDS |
| USRSEC | AWS.M2.CARDDEMO.USRSEC.VSAM.KSDS | Primary KSDS |
| DISCGRP | AWS.M2.CARDDEMO.DISCGRP.VSAM.KSDS | Primary KSDS |
| TRANCATG | AWS.M2.CARDDEMO.TRANCATG.VSAM.KSDS | Primary KSDS |
| TRANTYPE | AWS.M2.CARDDEMO.TRANTYPE.VSAM.KSDS | Primary KSDS |
| TCATBAL | AWS.M2.CARDDEMO.TCATBALF.VSAM.KSDS | Primary KSDS |
| DALYTRAN | AWS.M2.CARDDEMO.DALYTRAN.PS | Sequential flat file |

### 5.3 Optional Integration Points

| Integration | Direction | Technology | Programs |
|:------------|:----------|:-----------|:---------|
| MQ Auth Request | Inbound | IBM MQ → CICS trigger | COPAUA0C |
| MQ Auth Response | Outbound | CICS → IBM MQ | COPAUA0C |
| MQ Date Inquiry | Bidirectional | MQ request/response | CODATE01 |
| MQ Account Inquiry | Bidirectional | MQ request/response | COACCT01 |
| DB2 Tran Types | CICS ↔ DB2 | Embedded static SQL | COTRTUPC, COTRTLIC |
| DB2 Fraud Records | CICS → DB2 | INSERT from auth processing | COPAUS1C |
| IMS Auth Storage | CICS → IMS | DL/I calls | COPAUA0C, COPAUS0C, COPAUS1C |

### 5.4 Job Scheduling — Control-M

| Folder | Frequency | Job Chain |
|:-------|:----------|:----------|
| DAILY-TransactionBackup | Daily (all days) | CLOSEFIL → TRANBKP → WAITSTEP → OPENFIL |
| WEEKLY-TransactionTypesDBRefresh | Saturday | MNTTRDB2 → (triggers DisclosureGroupsRefresh) |
| WEEKLY-DisclosureGroupsRefresh | Saturday (SMART) | CLOSEFIL → DISCGRP → WAITSTEP → OPENFIL (depends on MNTTRDB2) |
| WEEKLY-TransactionTypesDBRefresh | Saturday (SMART) | TRANEXTR (depends on MNTTRDB2) |
| MONTHLY-InterestCalculation | Monthly | CLOSEFIL → INTCALC → COMBTRAN → WAITSTEP → OPENFIL |

---

## 6. Build and Deployment Summary

### 6.1 Mainframe Build (Production)

Programs are compiled using standard z/OS compilation procedures. Sample JCLs are provided in `samples/jcl/`:

| JCL | Purpose |
|:----|:--------|
| BATCMP.jcl | Compile batch COBOL programs |
| BMSCMP.jcl | Compile BMS map definitions |
| CICCMP.jcl | Compile CICS online COBOL programs |
| CICDBCMP.jcl | Compile CICS programs with DB2 precompiler |
| IMSMQCMP.jcl | Compile IMS/MQ programs |

Sample compile procedures in `samples/proc/`:

| Procedure | Purpose |
|:----------|:--------|
| BUILDBAT.prc | Batch COBOL compile/link |
| BUILDONL.prc | Online CICS compile/link |
| BUILDBMS.prc | BMS map assembly |
| BLDCIDB2.prc | CICS+DB2 compile with precompiler |

### 6.2 Local/Off-Mainframe Build (GnuCOBOL)

The repository supports partial compilation using GnuCOBOL 3.1.2 for testing:

```bash
# Compile batch program as executable
cobc -x -I app/cpy/ --std=ibm-strict -o build/PROGNAME app/cbl/PROGNAME.cbl

# Compile subprogram as shared module
cobc -m -I app/cpy/ --std=ibm-strict -o build/PROGNAME.so app/cbl/PROGNAME.cbl
```

**Compilation Status:**
- 8 batch programs compile as executables: CBACT01C, CBACT02C, CBACT03C, CBCUS01C, CBTRN01C, CBTRN02C, CBTRN03C, COBSWAIT
- 3 subprograms compile as modules: CBACT04C, CBSTM03B, CSUTLDTC
- CBEXPORT/CBIMPORT fail (undefined EXPORT-SEQUENCE-NUM reference)
- CBSTM03A fails (tab characters in CUSTREC.cpy)
- Online CICS programs (CO*) cannot compile without CICS runtime (DFHBMSCA, DFHAID, EIBCALEN)

### 6.3 Deployment Pipeline

| Step | Mechanism | Notes |
|:-----|:----------|:------|
| Source upload | FTP/SFTP to mainframe PDS | `scripts/remote_compile.sh`, `scripts/upld_module.sh` |
| Compile | JCL compile jobs or procedures | Per-program compilation |
| CICS resource definition | DFHCSDUP or CEDA | CSD file in `app/csd/CARDDEMO.CSD` |
| CICS program refresh | CEMT SET PROG NEWCOPY | After recompile |
| Data initialization | JCL sequence (DUSRSECJ → OPENFIL) | 13+ JCL jobs in order |
| Job scheduling | Control-M import | `app/scheduler/CardDemo.controlm` |

### 6.4 AWS Modernization Runtimes

| Runtime | Location | Description |
|:--------|:---------|:------------|
| AWS M2 Micro Focus | `samples/m2/mf/CardDemo_runtime.zip` | Deployment package for AWS Mainframe Modernization (Micro Focus) |
| UniKix | `samples/m2/unikix/UniKix_CardDemo_runtime_v1.zip` | Deployment package for UniKix TPE |

---

## 7. Repository Structure Summary

```
aws-mainframe-modernization-carddemo/
├── README.md                          # Comprehensive system documentation
├── app/
│   ├── asm/                           # 2 assembler utilities (MVSWAIT, COBDATFT)
│   ├── bms/                           # 15 BMS map source files (screen layouts)
│   ├── cbl/                           # 31 COBOL programs (CB*=batch, CO*=online)
│   ├── cpy/                           # 30 copybooks (shared data structures)
│   ├── cpy-bms/                       # 14 BMS map copybooks
│   ├── csd/                           # CICS resource definitions (CARDDEMO.CSD)
│   ├── ctl/                           # Control files
│   ├── catlg/                         # LISTCAT output
│   ├── data/
│   │   ├── ASCII/                     # 9 sample data files (ASCII text)
│   │   └── EBCDIC/                    # 13 sample data files (EBCDIC binary)
│   ├── jcl/                           # 32 JCL batch job definitions
│   ├── maclib/                        # 2 assembler macros
│   ├── proc/                          # 2 JCL procedures
│   ├── scheduler/                     # Control-M job schedules (.ca7, .controlm)
│   ├── app-authorization-ims-db2-mq/  # Optional: IMS+DB2+MQ authorization module
│   ├── app-transaction-type-db2/      # Optional: DB2 transaction type management
│   └── app-vsam-mq/                   # Optional: MQ account extraction module
├── samples/
│   ├── jcl/                           # Sample compile JCLs
│   ├── proc/                          # Sample compile procedures
│   └── m2/                            # AWS M2 and UniKix runtime packages
├── scripts/                           # Build, deploy, and marker scripts
├── diagrams/                          # Architecture and screen diagrams (.png, .drawio)
└── docs/                              # Documentation (this directory)
```

### 7.1 File Counts

| Category | Count | Location |
|:---------|------:|:---------|
| COBOL programs (core) | 31 | `app/cbl/` |
| COBOL programs (optional) | 12 | `app/app-*/cbl/` |
| Copybooks (core) | 30 | `app/cpy/` |
| Copybooks (optional) | 10 | `app/app-*/cpy/` |
| BMS maps | 15 | `app/bms/` |
| BMS copybooks | 14 | `app/cpy-bms/` |
| JCL jobs (core) | 32 | `app/jcl/` |
| JCL jobs (optional) | 8 | `app/app-*/jcl/` |
| Data files (ASCII) | 9 | `app/data/ASCII/` |
| Data files (EBCDIC) | 13 | `app/data/EBCDIC/` |
| Assembler programs | 2 | `app/asm/` |
| Shell scripts | 8 | `scripts/` |
