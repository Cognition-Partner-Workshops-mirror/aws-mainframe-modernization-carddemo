# COBOL Copybook Parsing Validation Results

**Generated:** 2026-05-07 14:36:16 UTC

## Executive Summary

| Metric | Value |
|--------|-------|
| Datasets Validated | 3 |
| Total Checks | 18 |
| Passed | 18 |
| Failed | 0 |
| Overall | **PASS** |

## Account Records

- **Copybook:** `CVACT01Y.cpy`
- **Data file:** `acctdata.txt`
- **Record length:** 300 bytes
- **Fields:** 13 (including FILLER)
- **Raw row count:** 50

### Validation Checks

| Status | Check | Expected | Actual |
|--------|-------|----------|--------|
| PASS | File exists | True | True |
| PASS | Raw line count | > 0 | 50 |
| PASS | Record length matches copybook | 300 | {300} |
| PASS | First record parseable | 12 fields (excluding FILLER) | 12 fields parsed |
| PASS | Field lengths sum to record length | 300 | 300 |
| PASS | No blank ACCT-ID (primary identifier) | 0 blank IDs | 0 blank IDs out of 50 records |

### First Record (Parsed Sample)

| Field | Parsed Value |
|-------|-------------|
| `ACCT-ID` | `1` |
| `ACCT-ACTIVE-STATUS` | `Y` |
| `ACCT-CURR-BAL` | `194.00` |
| `ACCT-CREDIT-LIMIT` | `2020.00` |
| `ACCT-CASH-CREDIT-LIMIT` | `1020.00` |
| `ACCT-OPEN-DATE` | `2014-11-20` |
| `ACCT-EXPIRAION-DATE` | `2025-05-20` |
| `ACCT-REISSUE-DATE` | `2025-05-20` |
| `ACCT-CURR-CYC-CREDIT` | `0.00` |
| `ACCT-CURR-CYC-DEBIT` | `0.00` |
| `ACCT-ADDR-ZIP` | `A000000000` |
| `ACCT-GROUP-ID` | `` |

## Customer Records

- **Copybook:** `CUSTREC.cpy`
- **Data file:** `custdata.txt`
- **Record length:** 500 bytes
- **Fields:** 19 (including FILLER)
- **Raw row count:** 50

### Validation Checks

| Status | Check | Expected | Actual |
|--------|-------|----------|--------|
| PASS | File exists | True | True |
| PASS | Raw line count | > 0 | 50 |
| PASS | Record length matches copybook | 500 | {500} |
| PASS | First record parseable | 18 fields (excluding FILLER) | 18 fields parsed |
| PASS | Field lengths sum to record length | 500 | 500 |
| PASS | No blank CUST-ID (primary identifier) | 0 blank IDs | 0 blank IDs out of 50 records |

### First Record (Parsed Sample)

| Field | Parsed Value |
|-------|-------------|
| `CUST-ID` | `1` |
| `CUST-FIRST-NAME` | `Immanuel` |
| `CUST-MIDDLE-NAME` | `Madeline` |
| `CUST-LAST-NAME` | `Kessler` |
| `CUST-ADDR-LINE-1` | `618 Deshaun Route` |
| `CUST-ADDR-LINE-2` | `Apt. 802` |
| `CUST-ADDR-LINE-3` | `Altenwerthshire` |
| `CUST-ADDR-STATE-CD` | `NC` |
| `CUST-ADDR-COUNTRY-CD` | `USA` |
| `CUST-ADDR-ZIP` | `12546` |
| `CUST-PHONE-NUM-1` | `(908)119-8310` |
| `CUST-PHONE-NUM-2` | `(373)693-8684` |
| `CUST-SSN` | `020973888` |
| `CUST-GOVT-ISSUED-ID` | `00000000000049368437` |
| `CUST-DOB-YYYYMMDD` | `1961-06-08` |
| `CUST-EFT-ACCOUNT-ID` | `0053581756` |
| `CUST-PRI-CARD-HOLDER-IND` | `Y` |
| `CUST-FICO-CREDIT-SCORE` | `274` |

## Card Records

- **Copybook:** `CVACT02Y.cpy`
- **Data file:** `carddata.txt`
- **Record length:** 150 bytes
- **Fields:** 7 (including FILLER)
- **Raw row count:** 50

### Validation Checks

| Status | Check | Expected | Actual |
|--------|-------|----------|--------|
| PASS | File exists | True | True |
| PASS | Raw line count | > 0 | 50 |
| PASS | Record length matches copybook | 150 | {150} |
| PASS | First record parseable | 6 fields (excluding FILLER) | 6 fields parsed |
| PASS | Field lengths sum to record length | 150 | 150 |
| PASS | No blank CARD-NUM (primary identifier) | 0 blank IDs | 0 blank IDs out of 50 records |

### First Record (Parsed Sample)

| Field | Parsed Value |
|-------|-------------|
| `CARD-NUM` | `0500024453765740` |
| `CARD-ACCT-ID` | `50` |
| `CARD-CVV-CD` | `747` |
| `CARD-EMBOSSED-NAME` | `Aniya Von` |
| `CARD-EXPIRAION-DATE` | `2023-03-09` |
| `CARD-ACTIVE-STATUS` | `Y` |
