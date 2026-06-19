# CardDemo Data Dictionary

> Business-friendly extraction of all data entities from COBOL copybook PIC clauses.
> Each entity maps to a VSAM file, IMS segment, DB2 table, or communication area.

---

## 1. Account Master (`CVACT01Y` — 300 bytes, VSAM KSDS)

The core financial account record. One account can have multiple cards.

| Field                    | PIC Clause         | Type        | Length | Business Description                              |
|:-------------------------|:-------------------|:------------|-------:|:--------------------------------------------------|
| `ACCT-ID`                | `9(11)`            | Numeric     |     11 | Unique account identifier (primary key)            |
| `ACCT-ACTIVE-STATUS`     | `X(01)`            | Alpha       |      1 | Account active flag (`Y`/`N`)                      |
| `ACCT-CURR-BAL`          | `S9(10)V99`        | Signed Dec  |     12 | Current account balance (dollars.cents)             |
| `ACCT-CREDIT-LIMIT`      | `S9(10)V99`        | Signed Dec  |     12 | Maximum credit limit                               |
| `ACCT-CASH-CREDIT-LIMIT` | `S9(10)V99`        | Signed Dec  |     12 | Maximum cash advance limit                         |
| `ACCT-OPEN-DATE`         | `X(10)`            | Date String |     10 | Account opening date (`YYYY-MM-DD`)                |
| `ACCT-EXPIRAION-DATE`    | `X(10)`            | Date String |     10 | Account expiration date (`YYYY-MM-DD`)             |
| `ACCT-REISSUE-DATE`      | `X(10)`            | Date String |     10 | Last card reissue date                             |
| `ACCT-CURR-CYC-CREDIT`   | `S9(10)V99`        | Signed Dec  |     12 | Current billing cycle credit total                 |
| `ACCT-CURR-CYC-DEBIT`    | `S9(10)V99`        | Signed Dec  |     12 | Current billing cycle debit total                  |
| `ACCT-ADDR-ZIP`          | `X(10)`            | Alpha       |     10 | Account holder ZIP code                            |
| `ACCT-GROUP-ID`          | `X(10)`            | Alpha       |     10 | Disclosure/interest rate group identifier          |
| FILLER                   | `X(178)`           | —           |    178 | Reserved space                                     |

**Key relationships:** Linked to Card via `CARD-ACCT-ID`; linked to Customer
via Cross-Reference (`XREF-ACCT-ID`); group rates looked up via `ACCT-GROUP-ID`
in Disclosure Group file.

---

## 2. Card Master (`CVACT02Y` — 150 bytes, VSAM KSDS)

Physical credit card record. Primary key is the 16-digit card number.

| Field                    | PIC Clause    | Type      | Length | Business Description                           |
|:-------------------------|:-------------|:----------|-------:|:-----------------------------------------------|
| `CARD-NUM`               | `X(16)`       | Alpha     |     16 | Credit card number (primary key)                |
| `CARD-ACCT-ID`           | `9(11)`       | Numeric   |     11 | Owning account ID (foreign key to Account)      |
| `CARD-CVV-CD`            | `9(03)`       | Numeric   |      3 | Card verification value (CVV)                   |
| `CARD-EMBOSSED-NAME`     | `X(50)`       | Alpha     |     50 | Cardholder name as printed on card              |
| `CARD-EXPIRAION-DATE`    | `X(10)`       | Date      |     10 | Card expiration date (`YYYY-MM-DD`)             |
| `CARD-ACTIVE-STATUS`     | `X(01)`       | Alpha     |      1 | Card active flag (`Y`/`N`)                      |
| FILLER                   | `X(59)`       | —         |     59 | Reserved space                                  |

**Key relationships:** `CARD-ACCT-ID` → Account Master; cards also appear
in Cross-Reference for customer linkage.

---

## 3. Card Cross-Reference (`CVACT03Y` — 50 bytes, VSAM KSDS)

Links cards to their owning customer and account. Primary key is card number.

| Field              | PIC Clause  | Type     | Length | Business Description                            |
|:-------------------|:-----------|:---------|-------:|:------------------------------------------------|
| `XREF-CARD-NUM`    | `X(16)`     | Alpha    |     16 | Credit card number (primary key)                 |
| `XREF-CUST-ID`     | `9(09)`     | Numeric  |      9 | Customer ID (foreign key to Customer)            |
| `XREF-ACCT-ID`     | `9(11)`     | Numeric  |     11 | Account ID (foreign key to Account)              |
| FILLER             | `X(14)`     | —        |     14 | Reserved space                                   |

**Key relationships:** Central junction table — joins Customer, Account, and Card.
Accessed via alternate index `CXACAIX` (by account ID).

---

## 4. Customer Master (`CVCUS01Y` — 500 bytes, VSAM KSDS)

Full customer profile with demographics, contact info, and credit scoring.

| Field                       | PIC Clause  | Type      | Length | Business Description                        |
|:----------------------------|:-----------|:----------|-------:|:--------------------------------------------|
| `CUST-ID`                   | `9(09)`     | Numeric   |      9 | Unique customer ID (primary key)             |
| `CUST-FIRST-NAME`           | `X(25)`     | Alpha     |     25 | Customer first name                          |
| `CUST-MIDDLE-NAME`          | `X(25)`     | Alpha     |     25 | Customer middle name                         |
| `CUST-LAST-NAME`            | `X(25)`     | Alpha     |     25 | Customer last name                           |
| `CUST-ADDR-LINE-1`          | `X(50)`     | Alpha     |     50 | Street address line 1                        |
| `CUST-ADDR-LINE-2`          | `X(50)`     | Alpha     |     50 | Street address line 2                        |
| `CUST-ADDR-LINE-3`          | `X(50)`     | Alpha     |     50 | City / locality                              |
| `CUST-ADDR-STATE-CD`        | `X(02)`     | Alpha     |      2 | US state code (validated via CSLKPCDY)       |
| `CUST-ADDR-COUNTRY-CD`      | `X(03)`     | Alpha     |      3 | Country code                                 |
| `CUST-ADDR-ZIP`             | `X(10)`     | Alpha     |     10 | ZIP / postal code (validated via CSLKPCDY)   |
| `CUST-PHONE-NUM-1`          | `X(15)`     | Alpha     |     15 | Primary phone `(NNN)NNN-NNNN`                |
| `CUST-PHONE-NUM-2`          | `X(15)`     | Alpha     |     15 | Secondary phone                              |
| `CUST-SSN`                  | `9(09)`     | Numeric   |      9 | Social Security Number (PII)                 |
| `CUST-GOVT-ISSUED-ID`       | `X(20)`     | Alpha     |     20 | Government-issued ID (passport, DL, etc.)    |
| `CUST-DOB-YYYY-MM-DD`       | `X(10)`     | Date      |     10 | Date of birth                                |
| `CUST-EFT-ACCOUNT-ID`       | `X(10)`     | Alpha     |     10 | Linked electronic funds transfer account     |
| `CUST-PRI-CARD-HOLDER-IND`  | `X(01)`     | Alpha     |      1 | Primary cardholder indicator (`Y`/`N`)       |
| `CUST-FICO-CREDIT-SCORE`    | `9(03)`     | Numeric   |      3 | FICO credit score (300–850)                  |
| FILLER                      | `X(168)`    | —         |    168 | Reserved space                               |

---

## 5. Transaction Record (`CVTRA05Y` — 350 bytes, VSAM KSDS)

Individual credit card transactions. Used for both online (TRANSACT) and
master transaction files.

| Field                    | PIC Clause      | Type       | Length | Business Description                          |
|:-------------------------|:---------------|:-----------|-------:|:----------------------------------------------|
| `TRAN-ID`                | `X(16)`         | Alpha      |     16 | Unique transaction identifier (primary key)    |
| `TRAN-TYPE-CD`           | `X(02)`         | Alpha      |      2 | Transaction type code (FK → CVTRA03Y)          |
| `TRAN-CAT-CD`            | `9(04)`         | Numeric    |      4 | Transaction category code (FK → CVTRA04Y)      |
| `TRAN-SOURCE`            | `X(10)`         | Alpha      |     10 | Originating source (POS, ATM, Online, etc.)    |
| `TRAN-DESC`              | `X(100)`        | Alpha      |    100 | Transaction description/narrative              |
| `TRAN-AMT`               | `S9(09)V99`     | Signed Dec |     11 | Transaction amount (positive=debit)            |
| `TRAN-MERCHANT-ID`       | `9(09)`         | Numeric    |      9 | Merchant identifier                            |
| `TRAN-MERCHANT-NAME`     | `X(50)`         | Alpha      |     50 | Merchant business name                         |
| `TRAN-MERCHANT-CITY`     | `X(50)`         | Alpha      |     50 | Merchant city                                  |
| `TRAN-MERCHANT-ZIP`      | `X(10)`         | Alpha      |     10 | Merchant ZIP code                              |
| `TRAN-CARD-NUM`          | `X(16)`         | Alpha      |     16 | Card number used for this transaction          |
| `TRAN-ORIG-TS`           | `X(26)`         | Timestamp  |     26 | Original transaction timestamp                 |
| `TRAN-PROC-TS`           | `X(26)`         | Timestamp  |     26 | Processing/posting timestamp                   |
| FILLER                   | `X(20)`         | —          |     20 | Reserved space                                 |

---

## 6. Daily Transaction Record (`CVTRA06Y` — 350 bytes)

Same structure as CVTRA05Y but used for daily inbound transactions before posting.

| Field                       | PIC Clause      | Type       | Length | Business Description                          |
|:----------------------------|:---------------|:-----------|-------:|:----------------------------------------------|
| `DALYTRAN-ID`               | `X(16)`         | Alpha      |     16 | Transaction ID for daily batch                 |
| `DALYTRAN-TYPE-CD`          | `X(02)`         | Alpha      |      2 | Transaction type code                          |
| `DALYTRAN-CAT-CD`           | `9(04)`         | Numeric    |      4 | Transaction category code                      |
| `DALYTRAN-SOURCE`           | `X(10)`         | Alpha      |     10 | Originating source                             |
| `DALYTRAN-DESC`             | `X(100)`        | Alpha      |    100 | Transaction description                        |
| `DALYTRAN-AMT`              | `S9(09)V99`     | Signed Dec |     11 | Transaction amount                             |
| `DALYTRAN-MERCHANT-ID`      | `9(09)`         | Numeric    |      9 | Merchant ID                                    |
| `DALYTRAN-MERCHANT-NAME`    | `X(50)`         | Alpha      |     50 | Merchant name                                  |
| `DALYTRAN-MERCHANT-CITY`    | `X(50)`         | Alpha      |     50 | Merchant city                                  |
| `DALYTRAN-MERCHANT-ZIP`     | `X(10)`         | Alpha      |     10 | Merchant ZIP                                   |
| `DALYTRAN-CARD-NUM`         | `X(16)`         | Alpha      |     16 | Card number                                    |
| `DALYTRAN-ORIG-TS`          | `X(26)`         | Timestamp  |     26 | Original timestamp                             |
| `DALYTRAN-PROC-TS`          | `X(26)`         | Timestamp  |     26 | Processing timestamp                           |
| FILLER                      | `X(20)`         | —          |     20 | Reserved space                                 |

---

## 7. Transaction Category Balance (`CVTRA01Y` — 50 bytes, VSAM KSDS)

Running balance per account, per transaction type and category combination.

| Field                 | PIC Clause    | Type       | Length | Business Description                           |
|:----------------------|:-------------|:-----------|-------:|:-----------------------------------------------|
| `TRANCAT-ACCT-ID`     | `9(11)`       | Numeric    |     11 | Account ID (composite key part 1)              |
| `TRANCAT-TYPE-CD`     | `X(02)`       | Alpha      |      2 | Transaction type (composite key part 2)        |
| `TRANCAT-CD`          | `9(04)`       | Numeric    |      4 | Category code (composite key part 3)           |
| `TRAN-CAT-BAL`        | `S9(09)V99`   | Signed Dec |     11 | Running balance for this category              |
| FILLER                | `X(22)`       | —          |     22 | Reserved space                                 |

---

## 8. Disclosure Group (`CVTRA02Y` — 50 bytes, VSAM KSDS)

Interest rate rules per account group, transaction type, and category.

| Field                 | PIC Clause    | Type       | Length | Business Description                           |
|:----------------------|:-------------|:-----------|-------:|:-----------------------------------------------|
| `DIS-ACCT-GROUP-ID`   | `X(10)`       | Alpha      |     10 | Account group (composite key part 1)           |
| `DIS-TRAN-TYPE-CD`    | `X(02)`       | Alpha      |      2 | Transaction type (composite key part 2)        |
| `DIS-TRAN-CAT-CD`     | `9(04)`       | Numeric    |      4 | Category code (composite key part 3)           |
| `DIS-INT-RATE`        | `S9(04)V99`   | Signed Dec |      6 | Annual interest rate (percentage)              |
| FILLER                | `X(28)`       | —          |     28 | Reserved space                                 |

---

## 9. Transaction Type (`CVTRA03Y` — 60 bytes, VSAM KSDS / DB2)

Reference table of transaction types (e.g., purchase, cash advance, payment).

| Field              | PIC Clause  | Type   | Length | Business Description                            |
|:-------------------|:-----------|:-------|-------:|:------------------------------------------------|
| `TRAN-TYPE`        | `X(02)`     | Alpha  |      2 | Transaction type code (primary key)              |
| `TRAN-TYPE-DESC`   | `X(50)`     | Alpha  |     50 | Descriptive name of transaction type             |
| FILLER             | `X(08)`     | —      |      8 | Reserved space                                   |

---

## 10. Transaction Category (`CVTRA04Y` — 60 bytes, VSAM KSDS / DB2)

Sub-classification of transactions within a type.

| Field                 | PIC Clause | Type    | Length | Business Description                           |
|:----------------------|:----------|:--------|-------:|:-----------------------------------------------|
| `TRAN-TYPE-CD`        | `X(02)`    | Alpha   |      2 | Parent transaction type (composite key part 1) |
| `TRAN-CAT-CD`         | `9(04)`    | Numeric |      4 | Category code (composite key part 2)           |
| `TRAN-CAT-TYPE-DESC`  | `X(50)`    | Alpha   |     50 | Description of this category                   |
| FILLER                | `X(04)`    | —       |      4 | Reserved space                                 |

---

## 11. User Security (`CSUSR01Y` — 80 bytes, VSAM KSDS)

Application-level user authentication and role data.

| Field           | PIC Clause | Type   | Length | Business Description                              |
|:----------------|:----------|:-------|-------:|:--------------------------------------------------|
| `SEC-USR-ID`    | `X(08)`    | Alpha  |      8 | User ID / login name (primary key)                 |
| `SEC-USR-FNAME` | `X(20)`    | Alpha  |     20 | User first name                                    |
| `SEC-USR-LNAME` | `X(20)`    | Alpha  |     20 | User last name                                     |
| `SEC-USR-PWD`   | `X(08)`    | Alpha  |      8 | Password (plaintext — security concern)            |
| `SEC-USR-TYPE`  | `X(01)`    | Alpha  |      1 | User type: `A` = Admin, `U` = Regular User         |
| FILLER          | `X(23)`    | —      |     23 | Reserved space                                     |

---

## 12. Application COMMAREA (`COCOM01Y`)

Shared communication area passed between all online CICS programs via XCTL.

| Field                     | PIC Clause | Type    | Length | Business Description                          |
|:--------------------------|:----------|:--------|-------:|:----------------------------------------------|
| `CDEMO-FROM-TRANID`       | `X(04)`    | Alpha   |      4 | Originating CICS transaction ID                |
| `CDEMO-FROM-PROGRAM`      | `X(08)`    | Alpha   |      8 | Originating program name                       |
| `CDEMO-TO-TRANID`         | `X(04)`    | Alpha   |      4 | Target CICS transaction ID                     |
| `CDEMO-TO-PROGRAM`        | `X(08)`    | Alpha   |      8 | Target program name                            |
| `CDEMO-USER-ID`           | `X(08)`    | Alpha   |      8 | Signed-on user ID                              |
| `CDEMO-USER-TYPE`         | `X(01)`    | Alpha   |      1 | User type (`A`=Admin, `U`=User)                |
| `CDEMO-PGM-CONTEXT`       | `9(01)`    | Numeric |      1 | 0=first entry, 1=re-entry                      |
| `CDEMO-CUST-ID`           | `9(09)`    | Numeric |      9 | Current customer context                       |
| `CDEMO-CUST-FNAME`        | `X(25)`    | Alpha   |     25 | Customer first name (cached)                   |
| `CDEMO-CUST-MNAME`        | `X(25)`    | Alpha   |     25 | Customer middle name (cached)                  |
| `CDEMO-CUST-LNAME`        | `X(25)`    | Alpha   |     25 | Customer last name (cached)                    |
| `CDEMO-ACCT-ID`           | `9(11)`    | Numeric |     11 | Current account context                        |
| `CDEMO-ACCT-STATUS`       | `X(01)`    | Alpha   |      1 | Account active status                          |
| `CDEMO-CARD-NUM`          | `9(16)`    | Numeric |     16 | Current card number context                    |
| `CDEMO-LAST-MAP`          | `X(7)`     | Alpha   |      7 | Last displayed BMS map name                    |
| `CDEMO-LAST-MAPSET`       | `X(7)`     | Alpha   |      7 | Last displayed BMS mapset name                 |

---

## 13. Multi-Record Export Layout (`CVEXPORT` — 500 bytes)

A REDEFINES-based union structure for the data export facility. The record
type field determines which overlay is active.

| Record Type | Overlay Structure          | Source Entity   |
|:------------|:---------------------------|:----------------|
| Customer    | `EXPORT-CUSTOMER-DATA`     | CVCUS01Y        |
| Account     | `EXPORT-ACCOUNT-DATA`      | CVACT01Y        |
| Transaction | `EXPORT-TRANSACTION-DATA`  | CVTRA05Y        |
| Card Xref   | `EXPORT-CARD-XREF-DATA`    | CVACT03Y        |
| Card        | `EXPORT-CARD-DATA`         | CVACT02Y        |

Common header fields across all types:

| Field                    | PIC Clause   | Type      | Length | Business Description                    |
|:-------------------------|:------------|:----------|-------:|:----------------------------------------|
| `EXPORT-REC-TYPE`        | `X(1)`       | Alpha     |      1 | Record type discriminator                |
| `EXPORT-TIMESTAMP`       | `X(26)`      | Timestamp |     26 | Export timestamp                         |
| `EXPORT-SEQUENCE-NUM`    | `9(9) COMP`  | Binary    |      4 | Sequential record number                 |
| `EXPORT-BRANCH-ID`       | `X(4)`       | Alpha     |      4 | Exporting branch                         |
| `EXPORT-REGION-CODE`     | `X(5)`       | Alpha     |      5 | Region code                              |
| `EXPORT-RECORD-DATA`     | `X(460)`     | Alpha     |    460 | Payload (REDEFINES for each entity)      |

Note: The export overlay uses COMP and COMP-3 for numeric fields (e.g.,
`EXP-ACCT-CURR-BAL PIC S9(10)V99 COMP-3`), demonstrating packed-decimal
data migration challenges.

---

## 14. Pending Authorization — IMS Detail Segment (`CIPAUDTY`)

IMS hierarchical segment for individual authorization records.

| Field                       | PIC Clause           | Type       | Length | Business Description                    |
|:----------------------------|:--------------------|:-----------|-------:|:----------------------------------------|
| `PA-AUTH-DATE-9C`           | `S9(05) COMP-3`      | Packed Dec |      3 | Authorization date (packed)              |
| `PA-AUTH-TIME-9C`           | `S9(09) COMP-3`      | Packed Dec |      5 | Authorization time (packed)              |
| `PA-AUTH-ORIG-DATE`         | `X(06)`               | Alpha      |      6 | Original date (display format)           |
| `PA-AUTH-ORIG-TIME`         | `X(06)`               | Alpha      |      6 | Original time (display format)           |
| `PA-CARD-NUM`               | `X(16)`               | Alpha      |     16 | Card number                              |
| `PA-AUTH-TYPE`              | `X(04)`               | Alpha      |      4 | Authorization type                       |
| `PA-CARD-EXPIRY-DATE`       | `X(04)`               | Alpha      |      4 | Card expiry (MMYY)                       |
| `PA-TRANSACTION-AMT`        | `S9(10)V99 COMP-3`   | Packed Dec |      7 | Requested amount                         |
| `PA-APPROVED-AMT`           | `S9(10)V99 COMP-3`   | Packed Dec |      7 | Approved amount                          |
| `PA-AUTH-RESP-CODE`         | `X(02)`               | Alpha      |      2 | Response code (`00`=Approved)            |
| `PA-MATCH-STATUS`           | `X(01)`               | Alpha      |      1 | `P`=Pending, `D`=Declined, `E`=Expired, `M`=Matched |
| `PA-AUTH-FRAUD`             | `X(01)`               | Alpha      |      1 | `F`=Fraud confirmed, `R`=Removed         |
| `PA-MERCHANT-ID`            | `X(15)`               | Alpha      |     15 | Merchant identifier                      |
| `PA-MERCHANT-NAME`          | `X(22)`               | Alpha      |     22 | Merchant name                            |

---

## 15. Pending Authorization — IMS Summary Segment (`CIPAUSMY`)

Summary-level segment per account in the IMS authorization database.

| Field                       | PIC Clause          | Type       | Length | Business Description                    |
|:----------------------------|:-------------------|:-----------|-------:|:----------------------------------------|
| `PA-ACCT-ID`                | `S9(11) COMP-3`     | Packed Dec |      6 | Account ID (root segment key)            |
| `PA-CUST-ID`                | `9(09)`              | Numeric    |      9 | Customer ID                              |
| `PA-AUTH-STATUS`            | `X(01)`              | Alpha      |      1 | Overall authorization status             |
| `PA-ACCOUNT-STATUS`         | `X(02) OCCURS 5`    | Alpha      |     10 | Status array (5 entries)                 |
| `PA-CREDIT-LIMIT`           | `S9(09)V99 COMP-3`  | Packed Dec |      6 | Credit limit                             |
| `PA-CASH-LIMIT`             | `S9(09)V99 COMP-3`  | Packed Dec |      6 | Cash advance limit                       |
| `PA-CREDIT-BALANCE`         | `S9(09)V99 COMP-3`  | Packed Dec |      6 | Credit balance                           |
| `PA-CASH-BALANCE`           | `S9(09)V99 COMP-3`  | Packed Dec |      6 | Cash balance                             |
| `PA-APPROVED-AUTH-CNT`      | `S9(04) COMP`       | Binary     |      2 | Count of approved authorizations         |
| `PA-DECLINED-AUTH-CNT`      | `S9(04) COMP`       | Binary     |      2 | Count of declined authorizations         |
| `PA-APPROVED-AUTH-AMT`      | `S9(09)V99 COMP-3`  | Packed Dec |      6 | Total approved amount                    |
| `PA-DECLINED-AUTH-AMT`      | `S9(09)V99 COMP-3`  | Packed Dec |      6 | Total declined amount                    |

---

## 16. Entity Relationship Summary

```
┌──────────────┐     1:N     ┌──────────────┐     1:N     ┌──────────────┐
│   Customer   │────────────▶│  Cross-Ref   │◀────────────│   Account    │
│  (CVCUS01Y)  │             │  (CVACT03Y)  │             │  (CVACT01Y)  │
│  PK: CUST-ID │             │  PK: CARD-NUM│             │  PK: ACCT-ID │
└──────────────┘             │  FK: CUST-ID │             └──────┬───────┘
                             │  FK: ACCT-ID │                    │
                             └──────┬───────┘                    │
                                    │ 1:1                        │ 1:N
                             ┌──────▼───────┐             ┌──────▼───────┐
                             │     Card     │             │  Tran-Cat-Bal│
                             │  (CVACT02Y)  │             │  (CVTRA01Y)  │
                             │  PK: CARD-NUM│             │  PK: ACCT+   │
                             │  FK: ACCT-ID │             │      TYPE+CAT│
                             └──────┬───────┘             └──────────────┘
                                    │ 1:N
                             ┌──────▼───────┐     N:1     ┌──────────────┐
                             │ Transaction  │────────────▶│  Tran Type   │
                             │  (CVTRA05Y)  │             │  (CVTRA03Y)  │
                             │  PK: TRAN-ID │             │  PK: TYPE-CD │
                             │  FK: CARD-NUM│             └──────────────┘
                             │  FK: TYPE-CD │     N:1     ┌──────────────┐
                             │  FK: CAT-CD  │────────────▶│  Tran Cat    │
                             └──────────────┘             │  (CVTRA04Y)  │
                                                          │  PK: TYPE+CAT│
                                                          └──────────────┘
                             ┌──────────────┐     N:1     ┌──────────────┐
                             │  Disclosure  │────────────▶│   Account    │
                             │  (CVTRA02Y)  │  (via       │  (CVACT01Y)  │
                             │  PK: GRP+    │  GROUP-ID)  │              │
                             │      TYPE+CAT│             └──────────────┘
                             └──────────────┘

              ┌──────────────────────────────────────────────────┐
              │              IMS Authorization DB                 │
              │  ┌────────────┐        ┌────────────┐           │
              │  │  Summary   │───1:N──│   Detail   │           │
              │  │ (CIPAUSMY) │        │ (CIPAUDTY) │           │
              │  │ PK: ACCT-ID│        │ PK: DATE+  │           │
              │  └────────────┘        │     TIME   │           │
              │                        └────────────┘           │
              └──────────────────────────────────────────────────┘
```

---

## 17. VSAM Dataset Inventory

| Dataset (HLQ.CARDDEMO.*)  | Copybook   | Format | LRECL | Key Field          | Key Len |
|:---------------------------|:-----------|:-------|------:|:-------------------|--------:|
| ACCTDATA (KSDS)            | CVACT01Y   | FB     |   300 | ACCT-ID            |      11 |
| CARDDATA (KSDS)            | CVACT02Y   | FB     |   150 | CARD-NUM           |      16 |
| CUSTDATA (KSDS)            | CVCUS01Y   | FB     |   500 | CUST-ID            |       9 |
| CARDXREF (KSDS)            | CVACT03Y   | FB     |    50 | XREF-CARD-NUM      |      16 |
| USRSEC (KSDS)              | CSUSR01Y   | FB     |    80 | SEC-USR-ID         |       8 |
| TRANSACT (KSDS)            | CVTRA05Y   | FB     |   350 | TRAN-ID            |      16 |
| DALYTRAN (Sequential)      | CVTRA06Y   | FB     |   350 | —                  |       — |
| DISCGRP (KSDS)             | CVTRA02Y   | FB     |    50 | Composite (16)     |      16 |
| TCATBALF (KSDS)            | CVTRA01Y   | FB     |    50 | Composite (17)     |      17 |
| TRANCATG (KSDS)            | CVTRA04Y   | FB     |    60 | Composite (6)      |       6 |
| TRANTYPE (KSDS)            | CVTRA03Y   | FB     |    60 | TRAN-TYPE          |       2 |

---

## 18. Numeric Storage Format Summary

The codebase exercises multiple COBOL numeric representations — an important
consideration for migration tooling.

| Format          | PIC Example         | Storage     | Migration Concern                    |
|:----------------|:-------------------|:------------|:-------------------------------------|
| Display Numeric | `9(11)`             | Zoned Dec   | Direct ASCII mapping                 |
| Signed Display  | `S9(10)V99`         | Zoned Dec   | Sign in last byte (EBCDIC encoding)  |
| COMP (Binary)   | `S9(09) COMP`       | 4-byte int  | Endianness conversion needed         |
| COMP-3 (Packed) | `S9(09)V99 COMP-3`  | Packed Dec  | Half-byte BCD encoding               |
| Implied Decimal | `V99` suffix        | —           | No physical decimal point            |
