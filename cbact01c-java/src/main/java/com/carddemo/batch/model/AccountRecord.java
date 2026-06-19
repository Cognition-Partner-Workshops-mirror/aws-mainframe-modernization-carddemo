package com.carddemo.batch.model;

import java.math.BigDecimal;

/**
 * Mirrors the COBOL ACCOUNT-RECORD from copybook CVACT01Y (RECLN 300).
 *
 * Each field maps directly to a PIC clause in the copybook:
 *   ACCT-ID                PIC 9(11)
 *   ACCT-ACTIVE-STATUS     PIC X(01)
 *   ACCT-CURR-BAL          PIC S9(10)V99
 *   ACCT-CREDIT-LIMIT      PIC S9(10)V99
 *   ACCT-CASH-CREDIT-LIMIT PIC S9(10)V99
 *   ACCT-OPEN-DATE         PIC X(10)
 *   ACCT-EXPIRAION-DATE    PIC X(10)
 *   ACCT-REISSUE-DATE      PIC X(10)
 *   ACCT-CURR-CYC-CREDIT   PIC S9(10)V99
 *   ACCT-CURR-CYC-DEBIT    PIC S9(10)V99
 *   ACCT-ADDR-ZIP          PIC X(10)
 *   ACCT-GROUP-ID          PIC X(10)
 *   FILLER                 PIC X(178)
 */
public record AccountRecord(
    String accountId,          // PIC 9(11) — 11-char zero-padded
    String activeStatus,       // PIC X(01) — 'Y' or 'N'
    BigDecimal currentBalance, // PIC S9(10)V99 — signed decimal
    BigDecimal creditLimit,    // PIC S9(10)V99
    BigDecimal cashCreditLimit,// PIC S9(10)V99
    String openDate,           // PIC X(10) — YYYY-MM-DD
    String expirationDate,     // PIC X(10) — YYYY-MM-DD
    String reissueDate,        // PIC X(10) — YYYY-MM-DD
    BigDecimal currentCycleCredit, // PIC S9(10)V99
    BigDecimal currentCycleDebit,  // PIC S9(10)V99
    String addressZip,         // PIC X(10)
    String groupId             // PIC X(10)
) {

    /** COBOL record length from CVACT01Y */
    public static final int RECORD_LENGTH = 300;
}
