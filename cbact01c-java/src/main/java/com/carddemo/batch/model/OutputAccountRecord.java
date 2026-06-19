package com.carddemo.batch.model;

import java.math.BigDecimal;

/**
 * Mirrors the COBOL OUT-ACCT-REC written by paragraph 1300-POPUL-ACCT-RECORD.
 *
 * Key differences from the input AccountRecord:
 *   - reissueDate is reformatted from YYYY-MM-DD to YYYYMMDD via COBDATFT
 *   - currentCycleDebit is replaced with 2525.00 when the input value is zero
 *   - currentCycleDebit is stored as COMP-3 (packed decimal) in COBOL;
 *     in Java we keep it as BigDecimal and handle encoding at write time
 */
public record OutputAccountRecord(
    String accountId,          // PIC 9(11)
    String activeStatus,       // PIC X(01)
    BigDecimal currentBalance, // PIC S9(10)V99
    BigDecimal creditLimit,    // PIC S9(10)V99
    BigDecimal cashCreditLimit,// PIC S9(10)V99
    String openDate,           // PIC X(10)
    String expirationDate,     // PIC X(10)
    String reissueDate,        // PIC X(10) — reformatted to YYYYMMDD
    BigDecimal currentCycleCredit, // PIC S9(10)V99
    BigDecimal currentCycleDebit,  // PIC S9(10)V99 COMP-3
    String groupId             // PIC X(10)
) {}
