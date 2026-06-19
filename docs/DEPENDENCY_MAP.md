# CardDemo Dependency Map

> Call graph, data lineage, and file access patterns for the entire CardDemo
> COBOL/CICS application.

---

## 1. Online (CICS) Call Graph

All online programs communicate via `EXEC CICS XCTL` with a shared COMMAREA
(`COCOM01Y`). The sign-on program is the entry point; menus dispatch to
functional screens; each screen XCTLs back to the menu on exit.

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CICS Region                                │
│                                                                     │
│   ┌──────────┐                                                      │
│   │ COSGN00C │  (Sign-on — Trans ID: CC00)                          │
│   │          │                                                      │
│   └────┬─────┘                                                      │
│        │ XCTL (Admin→COADM01C, User→COMEN01C)                      │
│        ▼                                                            │
│   ┌──────────┐         ┌──────────┐                                 │
│   │ COMEN01C │         │ COADM01C │                                 │
│   │ Main Menu│         │Admin Menu│                                 │
│   └────┬─────┘         └────┬─────┘                                 │
│        │                    │                                       │
│        │ XCTL via           │ XCTL via                              │
│        │ COMEN02Y table     │ COADM02Y table                       │
│        ▼                    ▼                                       │
│   ┌─────────────────────────────────────────────────────────┐       │
│   │  Functional Screens (each XCTLs back to menu on exit)   │       │
│   │                                                         │       │
│   │  Main Menu targets:          Admin Menu targets:        │       │
│   │  ┌──────────┐                ┌──────────┐               │       │
│   │  │COACTVWC  │ Acct View      │COUSR00C  │ User List     │       │
│   │  │COACTUPC  │ Acct Update    │COUSR01C  │ User Add      │       │
│   │  │COCRDLIC  │ Card List      │COUSR02C  │ User Update   │       │
│   │  │COCRDSLC  │ Card Detail    │COUSR03C  │ User Delete   │       │
│   │  │COCRDUPC  │ Card Update    │COTRTLIC  │ Tran Type List│       │
│   │  │COTRN00C  │ Tran List      │COTRTUPC  │ Tran Type Upd │       │
│   │  │COTRN01C  │ Tran View      └──────────┘               │       │
│   │  │COTRN02C  │ Tran Add                                  │       │
│   │  │CORPT00C  │ Reports                                   │       │
│   │  │COBIL00C  │ Bill Pay                                  │       │
│   │  │COPAUS0C  │ Auth Summary                              │       │
│   │  └──────────┘                                           │       │
│   └─────────────────────────────────────────────────────────┘       │
│                                                                     │
│   Cross-screen XCTL flows:                                          │
│   COCRDLIC ──XCTL──▶ COCRDSLC  (list → detail)                     │
│   COCRDLIC ──XCTL──▶ COCRDUPC  (list → update)                     │
│   COCRDSLC ──XCTL──▶ COCRDLIC  (detail → back to list)             │
│   COCRDUPC ──XCTL──▶ COCRDLIC  (update → back to list)             │
│   COACTUPC ──XCTL──▶ COMEN01C  (update → back to menu)             │
│   COACTVWC ──XCTL──▶ COMEN01C  (view → back to menu)               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.1 XCTL Dispatch Detail

| Source Program | Target Program(s)        | Dispatch Mechanism                              |
|:---------------|:-------------------------|:------------------------------------------------|
| COSGN00C       | COADM01C, COMEN01C       | Hard-coded PROGRAM('COADM01C') / ('COMEN01C')  |
| COMEN01C       | (11 programs)            | Table-driven via COMEN02Y → `CDEMO-MENU-OPT-PGMNAME(WS-OPTION)` |
| COADM01C       | (6 programs)             | Table-driven via COADM02Y → `CDEMO-ADMIN-OPT-PGMNAME(WS-OPTION)` |
| All screens    | `CDEMO-TO-PROGRAM`       | Dynamic XCTL back to calling program via COMMAREA |

### 1.2 CALL Dependencies (Subroutine Invocations)

| Caller Program | Called Module  | Purpose                          | Mechanism       |
|:---------------|:--------------|:---------------------------------|:----------------|
| COTRN02C       | CSUTLDTC       | Date validation                  | `CALL 'CSUTLDTC'` |
| CORPT00C       | CSUTLDTC       | Date validation                  | `CALL 'CSUTLDTC'` |
| CBACT01C       | COBDATFT       | Date format conversion (ASM)     | `CALL 'COBDATFT'` |
| CBSTM03A       | CBSTM03B       | File I/O subroutine              | `CALL 'CBSTM03B'` |
| COBSWAIT       | MVSWAIT        | Assembler wait routine           | `CALL 'MVSWAIT'`  |
| CSUTLDPY (inline) | CSUTLDTC    | LE date validation service       | `CALL 'CSUTLDTC'` |
| COACCT01 (MQ)  | MQOPEN/MQGET/MQPUT/MQCLOSE | MQ API calls           | `CALL 'MQxxxx'`   |
| CODATE01 (MQ)  | MQOPEN/MQGET/MQPUT/MQCLOSE | MQ API calls           | `CALL 'MQxxxx'`   |
| COTRTLIC (DB2) | LIT-DSNTIAC    | DB2 message formatting           | `CALL LIT-DSNTIAC` |
| COTRTUPC (DB2) | LIT-DSNTIAC    | DB2 message formatting           | `CALL LIT-DSNTIAC` |
| All batch pgms | CEE3ABD        | LE abend handler                 | `CALL 'CEE3ABD'`  |

---

## 2. Online (CICS) Data Lineage — File Access by Program

Each cell indicates the CICS file access operations performed by that program.
`R` = READ, `W` = WRITE, `RW` = REWRITE, `D` = DELETE,
`S` = STARTBR, `N` = READNEXT, `P` = READPREV, `E` = ENDBR

| Program    | ACCTDAT | CARDDAT | CUSTDAT | CARDXREF/CXACAIX | USRSEC | TRANSACT | TCATBALF | DISCGRP |
|:-----------|:--------|:--------|:--------|:-----------------|:-------|:---------|:---------|:--------|
| COSGN00C   |         |         |         |                  | R      |          |          |         |
| COACTVWC   | R       | R       | R       |                  |        |          |          |         |
| COACTUPC   | R,RW    |         | R,RW    |                  |        |          |          |         |
| COCRDLIC   |         | S,N,P,E |         | R (CARDAIX)      |        |          |          |         |
| COCRDSLC   |         | R       | R       |                  |        |          |          |         |
| COCRDUPC   |         | R,RW    |         |                  |        |          |          |         |
| COTRN00C   |         |         |         |                  |        | S,N,P,E  |          |         |
| COTRN01C   |         |         |         |                  |        | R        |          |         |
| COTRN02C   | R       |         |         | R (CXACAIX)      |        | S,P,E,W  |          |         |
| COBIL00C   | R,RW    |         |         | S,P,E            |        | W        |          |         |
| CORPT00C   |         |         |         |                  |        |          |          |         |
| COUSR00C   |         |         |         |                  | S,N,P,E|          |          |         |
| COUSR01C   |         |         |         |                  | W      |          |          |         |
| COUSR02C   |         |         |         |                  | R,RW   |          |          |         |
| COUSR03C   |         |         |         |                  | R,D    |          |          |         |
| COPAUS0C   | R       | R       | R       |                  |        |          |          |         |
| COPAUA0C   | R       | R       | R       |                  |        |          |          |         |
| COACCT01   | R       |         |         |                  |        |          |          |         |

**Notes:**
- `CORPT00C` does not directly access VSAM; it writes to a Transient Data Queue
  (`EXEC CICS WRITEQ TD`) to trigger batch report generation.
- `COMEN01C` and `COADM01C` do not access any data files; they are pure navigational dispatchers.
- `COPAUS0C/COPAUA0C` also access IMS DB via DL/I calls (not shown above — see Section 5).

---

## 3. Batch Data Lineage — File Access by Program

Batch programs use standard COBOL `OPEN`/`READ`/`WRITE`/`CLOSE` on sequential
and indexed files.

| Program    | Input Files                                | Output Files                       | Operations                    |
|:-----------|:-------------------------------------------|:-----------------------------------|:------------------------------|
| CBACT01C   | ACCTDAT (KSDS)                             | Output report (SYSOUT)             | OPEN INPUT, READ, display     |
| CBACT02C   | CARDDAT (KSDS)                             | Output report (SYSOUT)             | OPEN INPUT, READ, display     |
| CBACT03C   | CARDXREF (KSDS)                            | Output report (SYSOUT)             | OPEN INPUT, READ, display     |
| CBCUS01C   | CUSTDAT (KSDS)                             | Output report (SYSOUT)             | OPEN INPUT, READ, display     |
| CBTRN01C   | DALYTRAN (seq), CUSTDAT, CARDXREF, CARDDAT, ACCTDAT, TRANSACT | SYSOUT                | OPEN INPUT (6 files), READ    |
| CBTRN02C   | DALYTRAN (seq), CARDXREF, TRANSACT, ACCTDAT, DISCGRP, TCATBALF | TRANSACT, ACCTDAT, TCATBALF | READ + REWRITE (posting)   |
| CBTRN03C   | TRANSACT (KSDS), CARDXREF, TRANTYPE, TRANCATG, DATEPARM | Report file (sequential)  | READ + WRITE report           |
| CBACT04C   | ACCTDAT, DISCGRP, TCATBALF                 | ACCTDAT, TCATBALF                  | READ + REWRITE (interest)     |
| CBSTM03A   | TRANSACT (sorted), CARDXREF, ACCTDAT, CUSTDAT | Statement files (text+HTML GDGs) | READ + WRITE statements      |
| CBSTM03B   | (subroutine — I/O delegated by CBSTM03A)  | —                                  | CALL interface only           |
| CBEXPORT   | CUSTDAT, ACCTDAT, CARDXREF, TRANSACT, CARDDAT | EXPORT file (sequential)        | READ all → WRITE export       |
| CBIMPORT   | EXPORT file (sequential)                   | CUSTDAT, ACCTDAT, CARDXREF, TRANSACT, CARDDAT, ERROR file | READ → WRITE entities |
| COBSWAIT   | —                                          | —                                  | CALL MVSWAIT (timer only)     |
| CSUTLDTC   | —                                          | —                                  | CALL CEEDAYS (date svc only)  |
| CBPAUP0C   | (IMS DB — auth records)                    | (IMS DB — purged records)          | DL/I GU, GN, DLET            |
| PAUDBLOD   | Sequential input                           | IMS DB                             | DL/I ISRT                     |
| PAUDBUNL   | IMS DB                                     | Sequential output                  | DL/I GU, GN → WRITE          |
| DBUNLDGS   | GSAM file                                  | Sequential output                  | READ GSAM → WRITE            |
| COBTUPDT   | (DB2 table: TRAN_TYPE)                     | (DB2 table: TRAN_TYPE)             | EXEC SQL INSERT/UPDATE        |

---

## 4. Batch Job Data Flow (JCL → Program → Files)

This shows the end-to-end data flow from JCL job submission through
program execution to file I/O.

```
    ┌───────────────────────────────────────────────────────────────┐
    │                  DAILY BATCH CYCLE                             │
    │                                                               │
    │  ┌─────────┐     ┌──────────┐     ┌──────────┐               │
    │  │ POSTTRAN │────▶│ CBTRN02C │────▶│ Updates: │               │
    │  │  (JCL)   │     │ (COBOL)  │     │ TRANSACT │               │
    │  └─────────┘     │          │     │ ACCTDAT  │               │
    │      ▲           │ Reads:   │     │ TCATBALF │               │
    │      │           │ DALYTRAN │     └──────────┘               │
    │  DALYTRAN        │ CARDXREF │                                 │
    │  (daily feed)    │ TRANSACT │                                 │
    │                  │ ACCTDAT  │                                 │
    │                  │ DISCGRP  │                                 │
    │                  │ TCATBALF │                                 │
    │                  └──────────┘                                 │
    │                                                               │
    │  ┌─────────┐     ┌──────────┐     ┌──────────┐               │
    │  │ INTCALC  │────▶│ CBACT04C │────▶│ Updates: │               │
    │  │  (JCL)   │     │ (COBOL)  │     │ ACCTDAT  │               │
    │  └─────────┘     │ Reads:   │     │ TCATBALF │               │
    │                  │ ACCTDAT  │     └──────────┘               │
    │                  │ DISCGRP  │                                 │
    │                  │ TCATBALF │                                 │
    │                  └──────────┘                                 │
    │                                                               │
    │  ┌─────────┐     ┌──────────┐     ┌──────────┐               │
    │  │CREASTMT  │────▶│CBSTM03A  │────▶│ Writes:  │               │
    │  │  (JCL)   │     │+CBSTM03B │     │ Stmt GDGs│               │
    │  └─────────┘     │ Reads:   │     │ (text+   │               │
    │                  │ TRANSACT │     │  HTML)   │               │
    │                  │ CARDXREF │     └──────────┘               │
    │                  │ ACCTDAT  │                                 │
    │                  │ CUSTDAT  │                                 │
    │                  └──────────┘                                 │
    │                                                               │
    │  ┌─────────┐     ┌──────────┐     ┌──────────┐               │
    │  │TRANREPT  │────▶│ CBTRN03C │────▶│ Writes:  │               │
    │  │  (JCL)   │     │ (COBOL)  │     │ Report   │               │
    │  └─────────┘     │ Reads:   │     │ file     │               │
    │                  │ TRANSACT │     └──────────┘               │
    │                  │ CARDXREF │                                 │
    │                  │ TRANTYPE │                                 │
    │                  │ TRANCATG │                                 │
    │                  │ DATEPARM │                                 │
    │                  └──────────┘                                 │
    │                                                               │
    │  ┌─────────┐     ┌──────────┐     ┌──────────┐               │
    │  │CBEXPORT  │────▶│ CBEXPORT │────▶│ Writes:  │               │
    │  │  (JCL)   │     │ (COBOL)  │     │ EXPORT   │               │
    │  └─────────┘     │ Reads:   │     │ file     │               │
    │                  │ CUSTDAT  │     └──────────┘               │
    │                  │ ACCTDAT  │                                 │
    │                  │ CARDXREF │                                 │
    │                  │ TRANSACT │                                 │
    │                  │ CARDDAT  │                                 │
    │                  └──────────┘                                 │
    │                                                               │
    └───────────────────────────────────────────────────────────────┘
```

### 4.1 Suggested Job Execution Order

The following represents the recommended daily batch sequence based on
data dependencies:

```
 Step 1: CLOSEFIL           (Close CICS-held files for batch access)
    │
 Step 2: POSTTRAN            (Post daily transactions → updates TRANSACT,
    │                         ACCTDAT, TCATBALF)
    │
 Step 3: INTCALC             (Calculate interest → updates ACCTDAT, TCATBALF)
    │
 Step 4: COMBTRAN            (SORT/merge daily + system transactions)
    │
 Step 5: TRANREPT            (Generate transaction report)
    │    CREASTMT            (Generate account statements)  ← can run in parallel
    │
 Step 6: OPENFIL             (Reopen VSAM files for CICS)
```

---

## 5. IMS/DB2/MQ Data Lineage (Optional Modules)

### 5.1 IMS Pending Authorization Database

```
   MQ Request Queue                 IMS Database
  ┌──────────────┐              ┌──────────────────┐
  │ Auth Request  │──MQGET──▶   │  PA Summary      │
  │ (CCPAURQY)   │   │         │  (CIPAUSMY)      │
  └──────────────┘   │         │    │              │
                     ▼         │    │ 1:N          │
              ┌──────────┐     │  ┌─▼────────────┐ │
              │ COPAUA0C │     │  │ PA Detail     │ │
              │ (online) │──DL/I─▶│ (CIPAUDTY)   │ │
              └──────────┘     │  └──────────────┘ │
                               └──────────────────┘
                                        │
              ┌──────────┐              │ DL/I GU/GN
              │ COPAUS0C │◀─────────────┘
              │ (online) │  Also reads: ACCTDAT, CARDDAT, CUSTDAT
              └──────────┘

  Batch:
  LOADPADB (PAUDBLOD) ──ISRT──▶ IMS DB (initial load from sequential)
  UNLDPADB (PAUDBUNL) ──GU/GN──▶ Sequential output (unload)
  CBPAUP0J (CBPAUP0C) ──DLET──▶ IMS DB (purge expired authorizations)
```

### 5.2 DB2 Transaction Type Module

```
  ┌──────────────┐          ┌─────────────────────┐
  │ COTRTLIC     │──SQL──▶  │  DB2 Tables:        │
  │ (list/view)  │  SELECT  │  TRAN_TYPE           │
  └──────────────┘          │  TRAN_CAT            │
                            │                     │
  ┌──────────────┐          │                     │
  │ COTRTUPC     │──SQL──▶  │  INSERT/UPDATE/     │
  │ (add/edit)   │          │  DELETE              │
  └──────────────┘          └─────────────────────┘

  Batch:
  CREADB21  (JCL) ──DSNTEP4──▶ CREATE TABLE + LOAD
  TRANEXTR  (JCL) ──DSNTIAUL──▶ UNLOAD to sequential
  MNTTRDB2 (COBTUPDT) ──SQL──▶ Batch INSERT/UPDATE
```

### 5.3 MQ Integration (VSAM-MQ Module)

```
  External System ──MQ PUT──▶ Request Queue
                                    │
                              ┌─────▼──────┐
                              │ COACCT01   │──EXEC CICS READ──▶ ACCTDAT
                              │ (Account)  │
                              │ CODATE01   │──FUNCTION CURRENT-DATE
                              │ (Date)     │
                              └─────┬──────┘
                                    │
                              MQ PUT to Reply Queue
                                    │
  External System ◀──MQ GET─────────┘
```

---

## 6. Copybook Dependency Matrix

Shows which programs COPY which copybooks. `D` = Data Division,
`P` = Procedure Division, `B` = BMS map copybook.

| Copybook   | CO-online programs        | CB-batch programs         |
|:-----------|:--------------------------|:--------------------------|
| COCOM01Y   | All 25 online programs    | —                         |
| CVACT01Y   | COACTVWC, COACTUPC, COTRN02C, COBIL00C, COPAUS0C, COPAUA0C | CBACT01C, CBACT04C, CBTRN02C, CBSTM03A, CBEXPORT, CBIMPORT |
| CVACT02Y   | COCRDLIC, COCRDSLC, COCRDUPC, COPAUS0C, COPAUA0C | CBACT02C, CBEXPORT, CBIMPORT |
| CVACT03Y   | COACTVWC, COTRN02C, COBIL00C | CBACT03C, CBTRN01C, CBTRN03C, CBSTM03A, CBEXPORT, CBIMPORT |
| CVCUS01Y   | COACTVWC, COACTUPC, COCRDSLC, COPAUS0C, COPAUA0C | CBCUS01C, CBSTM03A, CBEXPORT |
| CUSTREC    | —                         | CBIMPORT                  |
| CSUSR01Y   | COSGN00C, COUSR00C–03C   | —                         |
| CVTRA05Y   | COTRN00C–02C             | CBTRN01C, CBTRN02C, CBEXPORT, CBIMPORT |
| CVTRA06Y   | —                         | CBTRN01C, CBTRN02C        |
| CVTRA07Y   | —                         | CBTRN03C                  |
| COSTM01    | —                         | CBSTM03A                  |
| CVTRA01Y   | —                         | CBACT04C, CBTRN02C        |
| CVTRA02Y   | —                         | CBACT04C, CBTRN02C        |
| CVTRA03Y   | —                         | CBTRN03C                  |
| CVTRA04Y   | —                         | CBTRN03C                  |
| CVEXPORT   | —                         | CBEXPORT, CBIMPORT        |
| CSDAT01Y   | Most online programs      | —                         |
| COTTL01Y   | Most online programs      | —                         |
| CSMSG01Y   | Most online programs      | —                         |
| CSMSG02Y   | Most online programs      | Most batch programs       |
| CSUTLDWY   | COACTUPC, COCRDUPC, COTRN02C, CORPT00C | —            |
| CSUTLDPY   | COACTUPC, COCRDUPC, COTRN02C, CORPT00C | —            |
| CSSTRPFY   | Most online programs      | —                         |
| CSSETATY   | COACTUPC, COCRDUPC        | —                         |
| CSLKPCDY   | COACTUPC, COCRDUPC        | —                         |
| CODATECN   | —                         | CBACT01C                  |
| COMEN02Y   | COMEN01C                  | —                         |
| COADM02Y   | COADM01C                  | —                         |
| CVCRD01Y   | Most online programs      | —                         |

---

## 7. VSAM File Access Summary

Aggregated view of which operations each VSAM dataset supports across
the entire application.

| VSAM Dataset | Online R | Online W | Online RW | Online Browse | Batch R | Batch W/RW | Batch Report |
|:-------------|:--------:|:--------:|:---------:|:-------------:|:-------:|:----------:|:------------:|
| ACCTDAT      | 5 pgms   | —        | 2 pgms    | —             | 5 pgms  | 2 pgms     | 1 pgm        |
| CARDDAT      | 3 pgms   | —        | 1 pgm     | 2 pgms        | 2 pgms  | 1 pgm      | —            |
| CUSTDAT      | 4 pgms   | —        | 1 pgm     | —             | 3 pgms  | 1 pgm      | —            |
| CARDXREF     | 2 pgms   | —        | —         | 1 pgm         | 5 pgms  | 1 pgm      | —            |
| USRSEC       | 1 pgm    | 1 pgm    | 1 pgm     | 1 pgm         | —       | —          | —            |
| TRANSACT     | 1 pgm    | 2 pgms   | —         | 1 pgm         | 4 pgms  | 1 pgm      | 2 pgms       |
| DALYTRAN     | —        | —        | —         | —             | 2 pgms  | —          | —            |
| DISCGRP      | —        | —        | —         | —             | 2 pgms  | —          | —            |
| TCATBALF     | —        | —        | —         | —             | 2 pgms  | 2 pgms     | —            |
| TRANTYPE     | —        | —        | —         | —             | 1 pgm   | —          | —            |
| TRANCATG     | —        | —        | —         | —             | 1 pgm   | —          | —            |

---

## 8. Alternate Index (AIX) Relationships

| Base Dataset | AIX Name | Upgrade Set | Key Field      | Used By                     |
|:-------------|:---------|:------------|:---------------|:----------------------------|
| CARDXREF     | CXACAIX  | Yes         | XREF-ACCT-ID   | COTRN02C, COBIL00C, COCRDLIC |
| CARDDAT      | CARDAIX  | Yes         | CARD-ACCT-ID   | COCRDLIC                     |

These alternate indexes enable "read by account" access patterns on
files whose primary key is the card number.
