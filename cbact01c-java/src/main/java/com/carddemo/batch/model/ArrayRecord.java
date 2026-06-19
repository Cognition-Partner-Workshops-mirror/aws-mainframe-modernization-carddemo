package com.carddemo.batch.model;

import java.math.BigDecimal;
import java.util.List;

/**
 * Mirrors the COBOL ARR-ARRAY-REC written by paragraph 1400-POPUL-ARRAY-RECORD.
 *
 * Layout:
 *   ARR-ACCT-ID              PIC 9(11)
 *   ARR-ACCT-BAL OCCURS 5:
 *     ARR-ACCT-CURR-BAL      PIC S9(10)V99
 *     ARR-ACCT-CURR-CYC-DEBIT PIC S9(10)V99 COMP-3
 *   ARR-FILLER               PIC X(04)
 *
 * COBOL populates only slots 1-3; slots 4-5 remain initialized to zeros
 * (from INITIALIZE ARR-ARRAY-REC).
 *
 * Slot 1: balance = account balance,   debit = 1005.00 (hardcoded)
 * Slot 2: balance = account balance,   debit = 1525.00 (hardcoded)
 * Slot 3: balance = -1025.00,          debit = -2500.00 (hardcoded)
 * Slots 4-5: balance = 0.00,           debit = 0.00
 */
public record ArrayRecord(
    String accountId,
    List<BalanceEntry> entries
) {

    /**
     * A single balance/debit pair within the OCCURS 5 array.
     */
    public record BalanceEntry(
        BigDecimal currentBalance,     // PIC S9(10)V99
        BigDecimal currentCycleDebit   // PIC S9(10)V99 COMP-3
    ) {}
}
