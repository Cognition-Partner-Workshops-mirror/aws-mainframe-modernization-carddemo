package com.carddemo.batch.model;

import java.math.BigDecimal;

/**
 * Mirrors the two variable-length records written per account by paragraphs
 * 1550-WRITE-VB1-RECORD and 1575-WRITE-VB2-RECORD.
 *
 * The COBOL program writes to a RECORDING MODE V file, producing two records
 * per input account:
 *
 *   Type 1 (12 bytes): VBRC-REC1
 *     VB1-ACCT-ID              PIC 9(11)
 *     VB1-ACCT-ACTIVE-STATUS   PIC X(01)
 *
 *   Type 2 (39 bytes): VBRC-REC2
 *     VB2-ACCT-ID              PIC 9(11)
 *     VB2-ACCT-CURR-BAL        PIC S9(10)V99
 *     VB2-ACCT-CREDIT-LIMIT    PIC S9(10)V99
 *     VB2-ACCT-REISSUE-YYYY    PIC X(04)
 */
public sealed interface VariableLengthRecord {

    /** Short record: account ID + active status (12 bytes in COBOL) */
    record Type1(
        String accountId,
        String activeStatus
    ) implements VariableLengthRecord {
        public static final int RECORD_LENGTH = 12;
    }

    /** Long record: account ID + balance + credit limit + reissue year (39 bytes in COBOL) */
    record Type2(
        String accountId,
        BigDecimal currentBalance,
        BigDecimal creditLimit,
        String reissueYear  // 4-char YYYY extracted from reissue date
    ) implements VariableLengthRecord {
        public static final int RECORD_LENGTH = 39;
    }
}
