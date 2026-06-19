# CardDemo Application Inventory

> Comprehensive catalog of all COBOL programs, copybooks, JCL jobs, and BMS maps
> in the AWS Mainframe Modernization CardDemo application.

## Executive Summary

| Artifact Type       | Count | Location                              |
|:--------------------|------:|:--------------------------------------|
| COBOL Programs      |    44 | `app/cbl/`, `app/app-*/cbl/`          |
| Copybooks (Data)    |    30 | `app/cpy/`, `app/app-*/cpy/`          |
| Copybooks (BMS)     |    22 | `app/cpy-bms/`, `app/app-*/cpy-bms/`  |
| BMS Maps            |    21 | `app/bms/`, `app/app-*/bms/`          |
| JCL Jobs            |    46 | `app/jcl/`, `app/app-*/jcl/`          |
| Sample JCL          |     9 | `samples/jcl/`                        |
| **Total Artifacts** |**172**|                                       |

---

## 1. COBOL Programs — Online (CICS)

These programs run under CICS transaction processing and drive the interactive
3270 terminal screens. All follow the naming convention `CO*C` (COBOL Online).

| Program    | Lines | Trans ID | Function                            | Module       | Classification       |
|:-----------|------:|:---------|:------------------------------------|:-------------|:---------------------|
| COSGN00C   |   260 | CC00     | User sign-on / authentication       | Core         | Security             |
| COMEN01C   |   308 | CM00     | Main menu dispatcher                | Core         | Navigation           |
| COADM01C   |   288 | CA00     | Admin menu dispatcher               | Core         | Navigation / Admin   |
| COACTVWC   |   941 | CAVW     | Account view (read-only)            | Core         | Account Mgmt         |
| COACTUPC   | 4,236 | CAUP     | Account update (full CRUD)          | Core         | Account Mgmt         |
| COCRDLIC   | 1,459 | CCLI     | Credit card list (browse/select)    | Core         | Card Mgmt            |
| COCRDSLC   |   887 | CCDL     | Credit card detail view             | Core         | Card Mgmt            |
| COCRDUPC   | 1,560 | CCUP     | Credit card update                  | Core         | Card Mgmt            |
| COTRN00C   |   699 | CT00     | Transaction list (browse)           | Core         | Transaction Mgmt     |
| COTRN01C   |   330 | CT01     | Transaction detail view             | Core         | Transaction Mgmt     |
| COTRN02C   |   783 | CT02     | Transaction add (new entry)         | Core         | Transaction Mgmt     |
| CORPT00C   |   649 | CR00     | Transaction report request          | Core         | Reporting            |
| COBIL00C   |   572 | CB00     | Bill payment processing             | Core         | Payments             |
| COUSR00C   |   695 | CU00     | User list (security admin)          | Core         | User Admin           |
| COUSR01C   |   299 | CU01     | User add (security admin)           | Core         | User Admin           |
| COUSR02C   |   414 | CU02     | User update (security admin)        | Core         | User Admin           |
| COUSR03C   |   359 | CU03     | User delete (security admin)        | Core         | User Admin           |
| COPAUS0C   | 1,032 | CPVS     | Pending authorization summary       | IMS-DB2-MQ   | Authorization        |
| COPAUS1C   |   604 | CPVD     | Pending authorization details       | IMS-DB2-MQ   | Authorization        |
| COPAUS2C   |   244 | —        | Pending authorization sub-screen    | IMS-DB2-MQ   | Authorization        |
| COPAUA0C   | 1,026 | CP00     | Process authorization requests (MQ) | IMS-DB2-MQ   | Authorization        |
| COTRTLIC   | 2,098 | CTLI     | Transaction type list/update (DB2)  | DB2-TranType | Reference Data       |
| COTRTUPC   | 1,702 | CTTU     | Transaction type add/edit (DB2)     | DB2-TranType | Reference Data       |
| COACCT01   |   620 | CDRA     | Account inquiry via MQ              | VSAM-MQ      | MQ Integration       |
| CODATE01   |   524 | CDRD     | System date inquiry via MQ          | VSAM-MQ      | MQ Integration       |

## 2. COBOL Programs — Batch

Batch programs are invoked via JCL and follow the `CB*C` naming convention.
They perform nightly/periodic processing against VSAM and sequential files.

| Program    | Lines | Job      | Function                                  | Module       | Classification       |
|:-----------|------:|:---------|:------------------------------------------|:-------------|:---------------------|
| CBACT01C   |   430 | —        | Account file read/load utility            | Core         | Data Load            |
| CBACT02C   |   178 | —        | Card file read/load utility               | Core         | Data Load            |
| CBACT03C   |   178 | —        | Cross-reference file read utility         | Core         | Data Load            |
| CBACT04C   |   652 | INTCALC  | Interest calculation engine               | Core         | Financial Calc       |
| CBCUS01C   |   178 | —        | Customer file read/load utility           | Core         | Data Load            |
| CBTRN01C   |   494 | —        | Transaction file sequential read          | Core         | Transaction Proc     |
| CBTRN02C   |   731 | POSTTRAN | Transaction posting / processing          | Core         | Transaction Proc     |
| CBTRN03C   |   649 | TRANREPT | Transaction report generation             | Core         | Reporting            |
| CBSTM03A   |   924 | CREASTMT | Statement generation (text + HTML)        | Core         | Reporting            |
| CBSTM03B   |   230 | —        | File I/O subroutine (called by CBSTM03A)  | Core         | Utility / Subroutine |
| CBEXPORT   |   582 | CBEXPORT | Multi-entity data export                  | Core         | Data Export          |
| CBIMPORT   |   487 | CBIMPORT | Multi-entity data import                  | Core         | Data Import          |
| COBSWAIT   |    41 | WAITSTEP | Timer wait utility (wraps MVSWAIT)        | Core         | Utility              |
| CSUTLDTC   |   157 | —        | Date validation subroutine (calls CEEDAYS)| Core         | Utility / Subroutine |
| CBPAUP0C   |   386 | CBPAUP0J | Purge expired authorizations              | IMS-DB2-MQ   | Authorization        |
| PAUDBLOD   |   369 | LOADPADB | IMS DB load utility                       | IMS-DB2-MQ   | Data Load            |
| PAUDBUNL   |   317 | UNLDPADB | IMS DB unload utility                     | IMS-DB2-MQ   | Data Extract         |
| DBUNLDGS   |   366 | UNLDGSAM | GSAM unload utility                       | IMS-DB2-MQ   | Data Extract         |
| COBTUPDT   |   237 | MNTTRDB2 | Batch transaction type maintenance (DB2)  | DB2-TranType | Reference Data       |

## 3. Copybooks — Data Structures

These copybooks define the record layouts for VSAM files, IMS segments,
DB2 host variables, communication areas, and shared working storage.

| Copybook   | Lines | Entity / Purpose                             | Record Len | Module       |
|:-----------|------:|:---------------------------------------------|:-----------|:-------------|
| CVACT01Y   |    20 | Account master record                        | 300 bytes  | Core         |
| CVACT02Y   |    14 | Card master record                           | 150 bytes  | Core         |
| CVACT03Y   |    11 | Card-Customer-Account cross-reference        | 50 bytes   | Core         |
| CVCUS01Y   |    26 | Customer master record                       | 500 bytes  | Core         |
| CUSTREC    |    26 | Customer record (tab-formatted variant)      | 500 bytes  | Core         |
| CVCRD01Y   |    46 | Credit card working area / COMMAREA fields   | Variable   | Core         |
| CVTRA01Y   |    13 | Transaction category balance                 | 50 bytes   | Core         |
| CVTRA02Y   |    13 | Disclosure group (interest rate rules)       | 50 bytes   | Core         |
| CVTRA03Y   |    10 | Transaction type reference                   | 60 bytes   | Core         |
| CVTRA04Y   |    12 | Transaction category type                    | 60 bytes   | Core         |
| CVTRA05Y   |    21 | Transaction record (online/master)           | 350 bytes  | Core         |
| CVTRA06Y   |    21 | Daily transaction record                     | 350 bytes  | Core         |
| CVTRA07Y   |    73 | Transaction report layout                    | Variable   | Core         |
| COSTM01    |    38 | Transaction record (keyed by card + tran ID) | 350 bytes  | Core         |
| CVEXPORT   |   103 | Multi-record export layout (REDEFINES)       | 500 bytes  | Core         |
| COCOM01Y   |    47 | Application COMMAREA (inter-program comms)   | Variable   | Core         |
| COMEN02Y   |   101 | Main menu option table (11 entries)          | Variable   | Core         |
| COADM02Y   |    62 | Admin menu option table (6 entries)          | Variable   | Core         |
| CSUSR01Y   |    26 | User security record                         | 80 bytes   | Core         |
| CSDAT01Y   |    58 | Current date/time working storage             | Variable   | Core         |
| COTTL01Y   |    27 | Screen title literals                        | Variable   | Core         |
| CSMSG01Y   |    24 | Common application messages                  | Variable   | Core         |
| CSMSG02Y   |    35 | Abend handling data area                     | Variable   | Core         |
| CSUTLDWY   |    89 | Date validation working storage              | Variable   | Core         |
| CSUTLDPY   |   375 | Date validation procedure division (inline)  | N/A        | Core         |
| CSSETATY   |    30 | BMS field attribute setter (COPY REPLACING)  | N/A        | Core         |
| CSSTRPFY   |    85 | PFKey-to-COMMAREA mapping (EVALUATE)         | N/A        | Core         |
| CSLKPCDY   | 1,318 | Lookup codes (phone area, state, zip)        | N/A        | Core         |
| CODATECN   |    52 | Date format conversion record                | Variable   | Core         |
| UNUSED1Y   |    10 | Unused placeholder record                    | 80 bytes   | Core         |
| CCPAURQY   |    36 | Pending authorization MQ request             | Variable   | IMS-DB2-MQ   |
| CCPAURLY   |     — | Pending authorization MQ reply               | Variable   | IMS-DB2-MQ   |
| CCPAUERY   |     — | Pending authorization error layout           | Variable   | IMS-DB2-MQ   |
| CIPAUDTY   |    54 | IMS segment: authorization details           | Variable   | IMS-DB2-MQ   |
| CIPAUSMY   |    31 | IMS segment: authorization summary           | Variable   | IMS-DB2-MQ   |
| IMSFUNCS   |     — | IMS function codes                           | N/A        | IMS-DB2-MQ   |
| PADFLPCB   |     — | IMS PCB: auth detail full-function DB        | N/A        | IMS-DB2-MQ   |
| PASFLPCB   |     — | IMS PCB: auth summary full-function DB       | N/A        | IMS-DB2-MQ   |
| PAUTBPCB   |     — | IMS PCB: auth table PCB                      | N/A        | IMS-DB2-MQ   |
| CSDB2RWY   |    46 | DB2 common working storage                   | Variable   | DB2-TranType |
| CSDB2RPY   |    89 | DB2 common procedures (priming query, msgs)  | N/A        | DB2-TranType |

## 4. BMS Map Sources

BMS (Basic Mapping Support) files define the 3270 terminal screen layouts.
Each `.bms` file has a corresponding BMS copybook (`.cpy`) in `cpy-bms/`.

| BMS Map    | Copybook   | Screen Purpose                     | Module       |
|:-----------|:-----------|:-----------------------------------|:-------------|
| COSGN00    | COSGN00    | Sign-on screen                     | Core         |
| COMEN01    | COMEN01    | Main menu                          | Core         |
| COADM01    | COADM01    | Admin menu                         | Core         |
| COACTVW    | COACTVW    | Account view                       | Core         |
| COACTUP    | COACTUP    | Account update                     | Core         |
| COCRDLI    | COCRDLI    | Credit card list                   | Core         |
| COCRDSL    | COCRDSL    | Credit card detail                 | Core         |
| COCRDUP    | COCRDUP    | Credit card update                 | Core         |
| COTRN00    | COTRN00    | Transaction list                   | Core         |
| COTRN01    | COTRN01    | Transaction view                   | Core         |
| COTRN02    | COTRN02    | Transaction add                    | Core         |
| CORPT00    | CORPT00    | Transaction report request         | Core         |
| COBIL00    | COBIL00    | Bill payment                       | Core         |
| COUSR00    | COUSR00    | User list                          | Core         |
| COUSR01    | COUSR01    | User add                           | Core         |
| COUSR02    | COUSR02    | User update                        | Core         |
| COUSR03    | COUSR03    | User delete                        | Core         |
| COPAU00    | COPAU00    | Pending authorization summary      | IMS-DB2-MQ   |
| COPAU01    | COPAU01    | Pending authorization details      | IMS-DB2-MQ   |
| COTRTLI    | COTRTLI    | Transaction type list (DB2)        | DB2-TranType |
| COTRTUP    | COTRTUP    | Transaction type update (DB2)      | DB2-TranType |

## 5. JCL Jobs — Application

| Job        | Program/Utility | Purpose                                       | Module       |
|:-----------|:----------------|:----------------------------------------------|:-------------|
| DUSRSECJ   | IEBGENER        | Initial load of user security VSAM file       | Core         |
| CLOSEFIL   | IEFBR14         | Close VSAM files held open by CICS            | Core         |
| OPENFIL    | IEFBR14         | Open VSAM files for CICS access               | Core         |
| ACCTFILE   | IDCAMS          | Define/load Account master VSAM KSDS          | Core         |
| CARDFILE   | IDCAMS          | Define/load Card master VSAM KSDS             | Core         |
| CUSTFILE   | IDCAMS          | Define/load Customer master VSAM KSDS         | Core         |
| XREFFILE   | IDCAMS          | Define/load Card-Xref VSAM KSDS               | Core         |
| TRANFILE   | IDCAMS          | Define/load Transaction master VSAM KSDS      | Core         |
| TRANBKP    | IDCAMS          | Backup/refresh Transaction master              | Core         |
| TRANIDX    | IDCAMS          | Define alternate index on transaction file     | Core         |
| DISCGRP    | IDCAMS          | Load Disclosure Group reference VSAM           | Core         |
| TCATBALF   | IDCAMS          | Load Transaction Category Balance VSAM         | Core         |
| TRANCATG   | IDCAMS          | Load Transaction Category types VSAM           | Core         |
| TRANTYPE   | IDCAMS          | Load Transaction Type reference VSAM           | Core         |
| DEFGDGB    | IDCAMS          | Define Generation Data Group bases             | Core         |
| DEFGDGD    | IDCAMS          | Define additional GDG bases (DB2)              | Core         |
| ESDSRRDS   | IDCAMS          | Create ESDS and RRDS VSAM files (demo)         | Core         |
| DEFCUST    | IDCAMS          | Define Customer VSAM KSDS (alternative)        | Core         |
| POSTTRAN   | CBTRN02C        | Core transaction posting batch                 | Core         |
| INTCALC    | CBACT04C        | Interest calculation batch                     | Core         |
| COMBTRAN   | SORT            | Combine daily + system transactions            | Core         |
| CREASTMT   | CBSTM03A        | Generate account statements (text + HTML)      | Core         |
| TRANREPT   | CBTRN03C        | Generate transaction report                    | Core         |
| WAITSTEP   | COBSWAIT        | Timer wait step for job scheduling             | Core         |
| CBADMCDJ   | —               | Admin card processing JCL                      | Core         |
| CBEXPORT   | CBEXPORT        | Multi-entity data export                       | Core         |
| CBIMPORT   | CBIMPORT        | Multi-entity data import                       | Core         |
| DALYREJS   | —               | Daily rejection processing                     | Core         |
| PRTCATBL   | —               | Print category balance report                  | Core         |
| READACCT   | —               | Read/dump Account file utility                 | Core         |
| READCARD   | —               | Read/dump Card file utility                    | Core         |
| READCUST   | —               | Read/dump Customer file utility                | Core         |
| READXREF   | —               | Read/dump Cross-reference file utility         | Core         |
| REPTFILE   | —               | Report file utility                            | Core         |
| FTPJCL     | FTP             | FTP file transfer                              | Core         |
| TXT2PDF1   | TXT2PDF         | Convert text to PDF                            | Core         |
| INTRDRJ1   | IEBGENER        | Internal reader job 1                          | Core         |
| INTRDRJ2   | IEBGENER        | Internal reader job 2                          | Core         |
| CREADB21   | DSNTEP4         | Create DB2 database and load tables            | DB2-TranType |
| TRANEXTR   | DSNTIAUL        | Extract transaction types from DB2             | DB2-TranType |
| MNTTRDB2   | COBTUPDT        | Batch DB2 transaction type maintenance         | DB2-TranType |
| CBPAUP0J   | CBPAUP0C        | Purge expired pending authorizations           | IMS-DB2-MQ   |
| DBPAUTP0   | —               | DB2 pending auth table creation                | IMS-DB2-MQ   |
| LOADPADB   | PAUDBLOD        | Load IMS pending authorization DB              | IMS-DB2-MQ   |
| UNLDPADB   | PAUDBUNL        | Unload IMS pending authorization DB            | IMS-DB2-MQ   |
| UNLDGSAM   | DBUNLDGS        | Unload GSAM file                               | IMS-DB2-MQ   |

## 6. JCL Jobs — Samples / Build

| Job        | Purpose                                                |
|:-----------|:-------------------------------------------------------|
| BATCMP     | Compile batch COBOL programs                           |
| BMSCMP     | Compile BMS map sources                                |
| CICCMP     | Compile CICS online COBOL programs                     |
| CICDBCMP   | Compile CICS + DB2 programs                            |
| IMSMQCMP   | Compile IMS + MQ programs                              |
| LISTCAT    | IDCAMS LISTCAT utility for VSAM catalog                |
| RACFCMDS   | RACF security commands for resource setup              |
| REPRTEST   | IDCAMS REPRO test utility                              |
| SORTTEST   | SORT utility test                                      |

## 7. Module Classification Summary

| Module          | Description                                           | Programs | Copybooks |
|:----------------|:------------------------------------------------------|---------:|----------:|
| **Core**        | Base credit card management (VSAM + CICS + JCL)      |       32 |        30 |
| **IMS-DB2-MQ**  | Pending authorization with IMS, DB2, MQ integration   |        8 |        11 |
| **DB2-TranType**| Transaction type maintenance using DB2                |        3 |         4 |
| **VSAM-MQ**     | Account/date inquiry via MQ channels                  |        2 |         0 |

## 8. Technology Stack Used

| Technology     | Usage                                                          |
|:---------------|:---------------------------------------------------------------|
| COBOL          | All 44 programs; business logic and data processing            |
| CICS           | 25 online programs; EXEC CICS for terminal I/O and file access |
| VSAM KSDS      | Primary data storage (account, card, customer, transaction)    |
| VSAM AIX       | Alternate indexes for card-by-account and xref-by-account      |
| JCL            | 46 batch jobs for data management, processing, and reporting   |
| BMS            | 21 screen maps for 3270 terminal interface                     |
| DB2            | Optional: transaction type reference tables                    |
| IMS DB         | Optional: hierarchical authorization data (GSAM + full-function)|
| MQ             | Optional: asynchronous authorization requests and inquiries    |
| SORT           | JCL SORT utility for combining transaction files               |
| IDCAMS         | VSAM dataset definition, load, backup, and alternate indexes   |
| Assembler      | MVSWAIT (timer), COBDATFT (date formatter) utilities           |
| RACF           | Security administration (sample JCL provided)                  |
