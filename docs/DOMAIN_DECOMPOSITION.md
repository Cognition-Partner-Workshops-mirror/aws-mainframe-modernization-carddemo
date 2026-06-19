# CardDemo Domain Decomposition

> Bounded context identification and extraction seam analysis for decomposing
> the monolithic CardDemo COBOL/CICS application into modern microservices.

---

## 1. Bounded Context Map

The CardDemo application decomposes into **7 bounded contexts** based on
data ownership, business capability, and coupling analysis.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CardDemo Application                             │
│                                                                         │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
│  │  Identity &  │   │   Account   │   │    Card     │                   │
│  │  Access Mgmt │   │   Context   │   │   Context   │                   │
│  │             │   │             │   │             │                   │
│  │ COSGN00C    │   │ COACTVWC    │   │ COCRDLIC    │                   │
│  │ COUSR00C    │   │ COACTUPC    │   │ COCRDSLC    │                   │
│  │ COUSR01C    │   │ COBIL00C    │   │ COCRDUPC    │                   │
│  │ COUSR02C    │   │ CBACT04C    │   │ CBACT02C    │                   │
│  │ COUSR03C    │   │ CBACT01C    │   │ CBACT03C    │                   │
│  │             │   │             │   │             │                   │
│  │ Owns:       │   │ Owns:       │   │ Owns:       │                   │
│  │  USRSEC     │   │  ACCTDAT    │   │  CARDDAT    │                   │
│  └──────┬──────┘   │  TCATBALF   │   │  CARDXREF   │                   │
│         │          │  DISCGRP    │   │  CARDAIX    │                   │
│         │ auth     └──────┬──────┘   │  CXACAIX    │                   │
│         │ token           │          └──────┬──────┘                   │
│         ▼                 │ acct-id         │ card-num                 │
│  ┌──────────────┐         │                 │                          │
│  │  Navigation  │         ▼                 ▼                          │
│  │   Context    │   ┌─────────────────────────┐                        │
│  │              │   │   Customer Context       │                        │
│  │ COMEN01C     │   │                         │                        │
│  │ COADM01C     │   │ (extracted from         │                        │
│  │              │   │  COACTUPC + reads in     │                        │
│  │ Owns:        │   │  COACTVWC, COCRDSLC,    │                        │
│  │  COMEN02Y    │   │  COPAUS0C, CBSTM03A)    │                        │
│  │  COADM02Y    │   │                         │                        │
│  │ (menu config)│   │ Owns: CUSTDAT            │                        │
│  └──────────────┘   └────────────┬────────────┘                        │
│                                  │ cust-id                             │
│                                  ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐           │
│  │             Transaction Context                          │           │
│  │                                                         │           │
│  │ COTRN00C, COTRN01C, COTRN02C (online)                  │           │
│  │ CBTRN01C, CBTRN02C (batch posting)                     │           │
│  │ CBTRN03C (reporting)                                   │           │
│  │ CBSTM03A + CBSTM03B (statements)                      │           │
│  │ CORPT00C (report requests)                             │           │
│  │ COMBTRAN (JCL SORT)                                    │           │
│  │                                                         │           │
│  │ Owns: TRANSACT, DALYTRAN, TRANTYPE, TRANCATG           │           │
│  └─────────────────────────────────────────────────────────┘           │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────┐           │
│  │         Authorization Context (IMS-DB2-MQ)               │           │
│  │                                                         │           │
│  │ COPAUA0C, COPAUS0C, COPAUS1C, COPAUS2C (online)        │           │
│  │ CBPAUP0C (batch purge)                                 │           │
│  │ PAUDBLOD, PAUDBUNL, DBUNLDGS (IMS utilities)          │           │
│  │                                                         │           │
│  │ Owns: IMS Auth DB (CIPAUSMY + CIPAUDTY segments)       │           │
│  │        MQ request/reply queues                          │           │
│  └─────────────────────────────────────────────────────────┘           │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────┐           │
│  │         Reference Data Context (DB2)                     │           │
│  │                                                         │           │
│  │ COTRTLIC, COTRTUPC (online CRUD)                       │           │
│  │ COBTUPDT (batch maintenance)                           │           │
│  │                                                         │           │
│  │ Owns: DB2 TRAN_TYPE, TRAN_CAT tables                   │           │
│  │        VSAM: TRANTYPE, TRANCATG (read replicas)        │           │
│  └─────────────────────────────────────────────────────────┘           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Bounded Context Details

### 2.1 Identity & Access Management Context

| Attribute           | Value                                                    |
|:--------------------|:---------------------------------------------------------|
| **Programs**        | COSGN00C, COUSR00C, COUSR01C, COUSR02C, COUSR03C        |
| **Data Owned**      | USRSEC (user credentials and roles)                      |
| **Upstream Deps**   | None                                                     |
| **Downstream Deps** | All other contexts (via CDEMO-USER-ID, CDEMO-USER-TYPE in COMMAREA) |
| **Coupling Type**   | Authentication token passed through COMMAREA to all programs |
| **Extraction Ease** | **Easy** — self-contained CRUD on single VSAM file       |

**Extraction seam:** The COMMAREA fields `CDEMO-USER-ID` and `CDEMO-USER-TYPE`
are the integration contract. Replace USRSEC READ in COSGN00C with an IdP
authentication call. All downstream programs only check `CDEMO-USER-TYPE`
(Admin vs User) — replace with JWT claims.

### 2.2 Navigation Context

| Attribute           | Value                                                    |
|:--------------------|:---------------------------------------------------------|
| **Programs**        | COMEN01C, COADM01C                                       |
| **Data Owned**      | Menu configuration (COMEN02Y, COADM02Y copybooks)       |
| **Upstream Deps**   | Identity context (user type determines menu)              |
| **Downstream Deps** | All functional contexts (via XCTL dispatch)               |
| **Coupling Type**   | Table-driven XCTL dispatch — loose coupling               |
| **Extraction Ease** | **Easy** — becomes frontend routing configuration         |

**Extraction seam:** Menu option tables in COMEN02Y and COADM02Y already
define the program-to-function mapping. This becomes a frontend router or
API gateway routing table. The XCTL dispatch pattern maps directly to
client-side navigation or server-side forwarding.

### 2.3 Account Context

| Attribute           | Value                                                    |
|:--------------------|:---------------------------------------------------------|
| **Programs**        | COACTVWC, COACTUPC*, COBIL00C, CBACT04C, CBACT01C, COACCT01 |
| **Data Owned**      | ACCTDAT, TCATBALF, DISCGRP                               |
| **Upstream Deps**   | Identity (user session), Customer (CUSTDAT reads), Card (CARDXREF lookups) |
| **Downstream Deps** | Transaction (TRANSACT writes from COBIL00C), Reporting (ACCTDAT reads) |
| **Coupling Type**   | Tight — COACTUPC writes to both ACCTDAT and CUSTDAT      |
| **Extraction Ease** | **Hard** — COACTUPC spans Account + Customer contexts     |

*COACTUPC is a **context boundary violation** — it updates both Account and
Customer data in a single program. This must be split during extraction.

**Extraction seam:** Account read operations (COACTVWC) are clean — single
READ on ACCTDAT. Account update operations in COACTUPC need to be split:
account fields (balance, limits, dates, status) stay in Account context;
customer fields (name, address, phone, SSN) move to Customer context.
COBIL00C's cross-context write (ACCTDAT REWRITE + TRANSACT WRITE) becomes
a saga or choreographed event.

### 2.4 Card Context

| Attribute           | Value                                                    |
|:--------------------|:---------------------------------------------------------|
| **Programs**        | COCRDLIC, COCRDSLC, COCRDUPC, CBACT02C, CBACT03C        |
| **Data Owned**      | CARDDAT, CARDXREF, CARDAIX, CXACAIX                     |
| **Upstream Deps**   | Account (CARD-ACCT-ID foreign key), Customer (XREF-CUST-ID) |
| **Downstream Deps** | Transaction (TRAN-CARD-NUM links transactions to cards)   |
| **Coupling Type**   | Foreign key references — loose data coupling              |
| **Extraction Ease** | **Medium** — clean CRUD but cross-reference joins Account + Customer |

**Extraction seam:** CARDXREF (cross-reference) is the junction table linking
Card→Account→Customer. This entity could live in either Card or Account
context. Recommendation: Card context owns CARDXREF since the primary key
is CARD-NUM. The alternate index CXACAIX (by account) becomes a query in
the Card Service called by the Account Service.

### 2.5 Customer Context

| Attribute           | Value                                                    |
|:--------------------|:---------------------------------------------------------|
| **Programs**        | None standalone — extracted from COACTUPC, read by COACTVWC, COCRDSLC, COPAUS0C, CBSTM03A |
| **Data Owned**      | CUSTDAT                                                  |
| **Upstream Deps**   | None                                                     |
| **Downstream Deps** | Account, Card (via XREF-CUST-ID), Authorization, Reporting |
| **Coupling Type**   | Read-heavy from other contexts; writes only from COACTUPC |
| **Extraction Ease** | **Medium** — clean entity but update logic is embedded in COACTUPC |

**Extraction seam:** Customer reads are always by CUST-ID (direct key
access) — trivial to front with a Customer API. The challenge is
extracting customer update logic from COACTUPC (approximately lines
2000–3500 of that 4,236-line program). After extraction, COACTUPC calls
the Customer Service API for customer updates instead of directly
writing to CUSTDAT.

### 2.6 Transaction Context

| Attribute           | Value                                                    |
|:--------------------|:---------------------------------------------------------|
| **Programs**        | COTRN00C, COTRN01C, COTRN02C, CBTRN01C, CBTRN02C, CBTRN03C, CBSTM03A/B, CORPT00C, COMBTRAN |
| **Data Owned**      | TRANSACT, DALYTRAN                                       |
| **Upstream Deps**   | Account (ACCTDAT for balance updates), Card (TRAN-CARD-NUM), Reference Data (TRANTYPE, TRANCATG) |
| **Downstream Deps** | Reporting (reads TRANSACT), Account (balance updates)    |
| **Coupling Type**   | Tight — CBTRN02C writes to ACCTDAT and TCATBALF (Account context) |
| **Extraction Ease** | **Hard** — batch posting crosses context boundaries       |

**Extraction seam:** Online transaction operations (list/view/add) are
clean — they operate on TRANSACT. The batch posting pipeline
(DALYTRAN→CBTRN02C→TRANSACT+ACCTDAT+TCATBALF) crosses into Account
context. This becomes an event: Transaction Service publishes
"TransactionPosted" events → Account Service subscribes to update
balances and category totals.

### 2.7 Authorization Context

| Attribute           | Value                                                    |
|:--------------------|:---------------------------------------------------------|
| **Programs**        | COPAUA0C, COPAUS0C, COPAUS1C, COPAUS2C, CBPAUP0C, PAUDBLOD, PAUDBUNL, DBUNLDGS |
| **Data Owned**      | IMS Auth DB, MQ queues, DB2 auth tables                  |
| **Upstream Deps**   | Account (ACCTDAT), Card (CARDDAT), Customer (CUSTDAT) — all read-only |
| **Downstream Deps** | None direct                                              |
| **Coupling Type**   | Reads from Account/Card/Customer; owns IMS/MQ/DB2 stack  |
| **Extraction Ease** | **Medium** — already has MQ-based integration boundary    |

**Extraction seam:** The MQ request/reply pattern is already an async
integration boundary. COPAUA0C reads from MQ request queue, processes
authorization, writes to IMS DB, and sends MQ reply. This maps directly
to a modern message-driven Authorization Service. The IMS hierarchical
model (summary→detail) becomes two relational tables with a foreign key.

---

## 3. Context Coupling Analysis

### 3.1 Coupling Matrix

Shows inter-context data dependencies. `R` = reads from, `W` = writes to,
`RW` = reads and writes.

| From \ To         | Identity | Navigation | Account | Card | Customer | Transaction | Authorization | Ref Data |
|:-------------------|:--------:|:----------:|:-------:|:----:|:--------:|:-----------:|:-------------:|:--------:|
| **Identity**       | —        |            |         |      |          |             |               |          |
| **Navigation**     | R        | —          |         |      |          |             |               |          |
| **Account**        | R        |            | —       |      | **RW**   | W           |               | R        |
| **Card**           | R        |            | R       | —    | R        |             |               |          |
| **Customer**       | R        |            |         |      | —        |             |               |          |
| **Transaction**    | R        |            | **W**   | R    |          | —           |               | R        |
| **Authorization**  | R        |            | R       | R    | R        |             | —             |          |
| **Ref Data**       | R        |            |         |      |          |             |               | —        |

### 3.2 Critical Coupling Points (Context Boundary Violations)

| # | Violation                        | Programs          | Description                                               | Resolution Strategy                          |
|:--|:---------------------------------|:------------------|:----------------------------------------------------------|:---------------------------------------------|
| 1 | Account → Customer write         | COACTUPC          | Single program writes to both ACCTDAT and CUSTDAT         | Split into two API calls: Account.update() + Customer.update() |
| 2 | Transaction → Account write      | CBTRN02C, COBIL00C| Batch posting and bill pay write to ACCTDAT + TCATBALF    | Event-driven: publish TransactionPosted → Account subscribes |
| 3 | Account → Transaction write      | COBIL00C          | Bill payment creates a transaction record                  | Account Service calls Transaction Service API |
| 4 | Authorization → 3 contexts read  | COPAUS0C, COPAUA0C| Reads ACCTDAT, CARDDAT, CUSTDAT for auth decisions        | API calls to Account, Card, Customer services |

---

## 4. Extraction Seam Analysis

### 4.1 Natural Seams (Low-Effort Extraction)

These seams already exist in the architecture and require minimal refactoring.

| Seam                        | Current Mechanism                          | Target Mechanism                    |
|:----------------------------|:-------------------------------------------|:------------------------------------|
| Menu dispatch               | COMEN02Y/COADM02Y table → XCTL            | API gateway routing / SPA router    |
| User authentication         | USRSEC READ → COMMAREA population          | IdP authentication → JWT token      |
| MQ request/reply            | MQGET → process → MQPUT                    | Message broker consume → produce    |
| DB2 SQL access              | EXEC SQL within CICS programs              | JPA/JDBC within REST controllers    |
| Batch job orchestration     | JCL step sequencing                        | Workflow engine (Step Functions, Airflow) |

### 4.2 Synthetic Seams (Require Extraction Work)

These seams must be created by splitting existing programs.

| Seam to Create              | Current State                              | Work Required                       |
|:----------------------------|:-------------------------------------------|:------------------------------------|
| Account/Customer split      | COACTUPC handles both                      | Extract customer update logic (~1,500 lines) into Customer Service; COACTUPC calls Customer API |
| Transaction posting event   | CBTRN02C writes ACCTDAT directly           | CBTRN02C publishes event; Account Service subscribes and updates balances |
| Validation service          | CSUTLDPY + CSLKPCDY inlined in 4 programs  | Extract to shared Validation Service; expose as API |
| Card cross-reference API    | Direct VSAM READ on CARDXREF/CXACAIX       | Card Service exposes query endpoints; other services call API |

### 4.3 Anti-Corruption Layer (ACL) Design

During the strangler fig transition, an ACL bridges old and new systems.

```
┌────────────────────────────────────────────────────────────────┐
│                    Anti-Corruption Layer                        │
│                                                                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │ CICS Adapter  │    │ VSAM Adapter │    │  MQ Adapter  │     │
│  │              │    │              │    │              │     │
│  │ Translates   │    │ Mirrors VSAM │    │ Bridges MQ   │     │
│  │ COMMAREA ↔   │    │ records ↔    │    │ messages ↔   │     │
│  │ REST/JSON    │    │ DB entities  │    │ events       │     │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘     │
│         │                   │                   │              │
│         ▼                   ▼                   ▼              │
│  ┌─────────────────────────────────────────────────────┐      │
│  │              Modern Service Layer                    │      │
│  │  Account | Card | Customer | Transaction | Auth     │      │
│  └─────────────────────────────────────────────────────┘      │
│                            │                                   │
│                            ▼                                   │
│  ┌─────────────────────────────────────────────────────┐      │
│  │           Relational Database (PostgreSQL)           │      │
│  │  accounts | cards | customers | transactions | ...   │      │
│  └─────────────────────────────────────────────────────┘      │
└────────────────────────────────────────────────────────────────┘

Key ACL patterns:
1. CICS programs → ACL → REST API → new service (online transition)
2. VSAM file → Change Data Capture → event → new DB (data sync)
3. MQ queue → ACL → modern broker topic (authorization module)
4. Batch JCL → ACL → workflow orchestrator (batch transition)
```

---

## 5. Target Service Architecture

### 5.1 Service Inventory

| Service                | Source Context   | API Style    | Data Store             | Key Entities                        |
|:-----------------------|:-----------------|:-------------|:-----------------------|:------------------------------------|
| **Identity Service**   | Identity & Access| REST + OAuth | Identity Provider (IdP)| Users, Roles, Permissions           |
| **Account Service**    | Account          | REST         | PostgreSQL             | Account, CategoryBalance, DisclosureGroup |
| **Card Service**       | Card             | REST         | PostgreSQL             | Card, CardCrossReference            |
| **Customer Service**   | Customer         | REST         | PostgreSQL (encrypted) | Customer (with PII encryption)      |
| **Transaction Service**| Transaction      | REST + Events| PostgreSQL + Broker    | Transaction, DailyTransaction       |
| **Authorization Svc**  | Authorization    | Events       | PostgreSQL + Broker    | AuthSummary, AuthDetail             |
| **Reference Data Svc** | Reference Data   | REST (cached)| PostgreSQL             | TransactionType, TransactionCategory|
| **Reporting Service**  | Reporting        | REST (async) | Read replicas + S3     | Statement, TransactionReport        |
| **Validation Service** | Cross-cutting    | REST (shared)| Config/DB              | PhoneAreaCode, StateCode, ZipPrefix |

### 5.2 Event Contracts

| Event                    | Publisher            | Subscriber(s)            | Payload                                    |
|:-------------------------|:---------------------|:-------------------------|:-------------------------------------------|
| `TransactionPosted`      | Transaction Service  | Account Service          | `{tranId, acctId, amount, typeCode, catCode}` |
| `AccountBalanceUpdated`  | Account Service      | Authorization Service    | `{acctId, newBalance, creditLimit}`        |
| `AuthorizationDecided`   | Authorization Service| Transaction Service      | `{authId, cardNum, approved, amount}`      |
| `CustomerUpdated`        | Customer Service     | Account Service (cache)  | `{custId, name, address}`                  |
| `CardStatusChanged`      | Card Service         | Authorization Service    | `{cardNum, activeStatus, expiryDate}`      |

---

## 6. Data Migration Strategy

### 6.1 VSAM → Relational Mapping

| VSAM Dataset | Record Size | Target Table(s)              | Key Mapping                                |
|:-------------|:------------|:-----------------------------|:-------------------------------------------|
| ACCTDAT      | 300 bytes   | `accounts`                   | `ACCT-ID` → `account_id BIGINT PK`        |
| CARDDAT      | 150 bytes   | `cards`                      | `CARD-NUM` → `card_number VARCHAR(16) PK`  |
| CUSTDAT      | 500 bytes   | `customers`                  | `CUST-ID` → `customer_id BIGINT PK`       |
| CARDXREF     | 50 bytes    | `card_cross_references`      | `XREF-CARD-NUM` → FK to cards              |
| USRSEC       | 80 bytes    | Identity Provider (Keycloak) | `SEC-USR-ID` → IdP username                |
| TRANSACT     | 350 bytes   | `transactions`               | `TRAN-ID` → `transaction_id VARCHAR(16) PK`|
| DALYTRAN     | 350 bytes   | `daily_transactions` (staging)| Sequence → auto-increment                 |
| DISCGRP      | 50 bytes    | `disclosure_groups`          | Composite key → composite PK               |
| TCATBALF     | 50 bytes    | `category_balances`          | Composite key → composite PK               |
| TRANTYPE     | 60 bytes    | `transaction_types`          | `TRAN-TYPE` → `type_code VARCHAR(2) PK`   |
| TRANCATG     | 60 bytes    | `transaction_categories`     | Composite key → composite PK               |

### 6.2 Numeric Type Mapping

| COBOL PIC              | Storage    | Java Type                | PostgreSQL Type       |
|:-----------------------|:-----------|:-------------------------|:----------------------|
| `9(11)`                | Zoned Dec  | `long`                   | `BIGINT`              |
| `S9(10)V99`            | Zoned Dec  | `BigDecimal(12,2)`       | `NUMERIC(12,2)`       |
| `S9(10)V99 COMP-3`     | Packed Dec | `BigDecimal(12,2)`       | `NUMERIC(12,2)`       |
| `S9(09) COMP`          | Binary     | `int`                    | `INTEGER`             |
| `X(nn)`                | Display    | `String`                 | `VARCHAR(nn)`         |
| `9(03)`                | Zoned Dec  | `int`                    | `SMALLINT`            |
