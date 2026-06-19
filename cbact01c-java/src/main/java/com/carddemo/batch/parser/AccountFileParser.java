package com.carddemo.batch.parser;

import com.carddemo.batch.model.AccountRecord;

import java.io.BufferedReader;
import java.io.IOException;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * Parses the ACCTFILE (VSAM KSDS exported to ASCII) into AccountRecord objects.
 *
 * Handles EBCDIC zoned-decimal overpunch encoding for signed numeric fields
 * (PIC S9(n)V99), where the last byte encodes both the digit and sign.
 *
 * Mirrors the COBOL: READ ACCTFILE-FILE INTO ACCOUNT-RECORD
 */
public final class AccountFileParser {

    /** Positive overpunch: last byte → (digit, positive sign) */
    private static final Map<Character, Integer> OVERPUNCH_POSITIVE = Map.ofEntries(
        Map.entry('{', 0), Map.entry('A', 1), Map.entry('B', 2),
        Map.entry('C', 3), Map.entry('D', 4), Map.entry('E', 5),
        Map.entry('F', 6), Map.entry('G', 7), Map.entry('H', 8),
        Map.entry('I', 9)
    );

    /** Negative overpunch: last byte → (digit, negative sign) */
    private static final Map<Character, Integer> OVERPUNCH_NEGATIVE = Map.ofEntries(
        Map.entry('}', 0), Map.entry('J', 1), Map.entry('K', 2),
        Map.entry('L', 3), Map.entry('M', 4), Map.entry('N', 5),
        Map.entry('O', 6), Map.entry('P', 7), Map.entry('Q', 8),
        Map.entry('R', 9)
    );

    private AccountFileParser() {
        // Utility class — no instantiation
    }

    /**
     * Parse all account records from the given ASCII data file.
     *
     * @param inputPath path to the ACCTFILE ASCII export (e.g., acctdata.txt)
     * @return immutable list of parsed AccountRecord objects
     * @throws IOException if the file cannot be read
     */
    public static List<AccountRecord> parseFile(Path inputPath) throws IOException {
        List<AccountRecord> records = new ArrayList<>();

        try (BufferedReader reader = Files.newBufferedReader(inputPath)) {
            String line;
            while ((line = reader.readLine()) != null) {
                // Skip blank lines
                if (line.isBlank()) {
                    continue;
                }

                // Pad short lines to the expected record length
                if (line.length() < AccountRecord.RECORD_LENGTH) {
                    line = padRight(line, AccountRecord.RECORD_LENGTH);
                }

                records.add(parseLine(line));
            }
        }

        return Collections.unmodifiableList(records);
    }

    /**
     * Parse a single fixed-width line into an AccountRecord.
     *
     * Field offsets match CVACT01Y copybook:
     *   Offset  0: ACCT-ID              PIC 9(11)       — 11 bytes
     *   Offset 11: ACCT-ACTIVE-STATUS   PIC X(01)       —  1 byte
     *   Offset 12: ACCT-CURR-BAL        PIC S9(10)V99   — 12 bytes
     *   Offset 24: ACCT-CREDIT-LIMIT    PIC S9(10)V99   — 12 bytes
     *   Offset 36: ACCT-CASH-CREDIT-LIMIT PIC S9(10)V99 — 12 bytes
     *   Offset 48: ACCT-OPEN-DATE       PIC X(10)       — 10 bytes
     *   Offset 58: ACCT-EXPIRAION-DATE  PIC X(10)       — 10 bytes
     *   Offset 68: ACCT-REISSUE-DATE    PIC X(10)       — 10 bytes
     *   Offset 78: ACCT-CURR-CYC-CREDIT PIC S9(10)V99   — 12 bytes
     *   Offset 90: ACCT-CURR-CYC-DEBIT  PIC S9(10)V99   — 12 bytes
     *   Offset 102: ACCT-ADDR-ZIP       PIC X(10)       — 10 bytes
     *   Offset 112: ACCT-GROUP-ID       PIC X(10)       — 10 bytes
     *   Offset 122: FILLER              PIC X(178)      — 178 bytes
     */
    public static AccountRecord parseLine(String line) {
        return new AccountRecord(
            extractAlpha(line, 0, 11),                           // ACCT-ID
            extractAlpha(line, 11, 1),                           // ACCT-ACTIVE-STATUS
            decodeSignedDecimal(line, 12, 12, 2),    // ACCT-CURR-BAL
            decodeSignedDecimal(line, 24, 12, 2),    // ACCT-CREDIT-LIMIT
            decodeSignedDecimal(line, 36, 12, 2),    // ACCT-CASH-CREDIT-LIMIT
            extractAlpha(line, 48, 10),                          // ACCT-OPEN-DATE
            extractAlpha(line, 58, 10),                          // ACCT-EXPIRAION-DATE
            extractAlpha(line, 68, 10),                          // ACCT-REISSUE-DATE
            decodeSignedDecimal(line, 78, 12, 2),    // ACCT-CURR-CYC-CREDIT
            decodeSignedDecimal(line, 90, 12, 2),    // ACCT-CURR-CYC-DEBIT
            extractAlpha(line, 102, 10),                         // ACCT-ADDR-ZIP
            extractAlpha(line, 112, 10)                          // ACCT-GROUP-ID
        );
    }

    /**
     * Extract an alphanumeric field, trimming trailing spaces.
     */
    private static String extractAlpha(String line, int offset, int length) {
        if (offset + length > line.length()) {
            return "";
        }
        return line.substring(offset, offset + length).stripTrailing();
    }

    /**
     * Decode an EBCDIC zoned-decimal overpunch field to BigDecimal.
     *
     * The last character of a signed field encodes both the final digit
     * and the sign (positive or negative). See the OVERPUNCH maps above.
     *
     * @param line          the full record line
     * @param offset        starting position of the field
     * @param length        total field length in bytes
     * @param decimalPlaces number of implied decimal places (V99 = 2)
     * @return the decoded BigDecimal value
     */
    public static BigDecimal decodeSignedDecimal(String line, int offset,
                                                  int length, int decimalPlaces) {
        String raw = line.substring(offset, offset + length);
        if (raw.isBlank()) {
            return BigDecimal.ZERO;
        }

        char lastChar = raw.charAt(raw.length() - 1);
        String digitsBeforeLast = raw.substring(0, raw.length() - 1);
        int lastDigit;
        boolean negative;

        // Determine the last digit and sign from the overpunch character
        if (OVERPUNCH_POSITIVE.containsKey(lastChar)) {
            lastDigit = OVERPUNCH_POSITIVE.get(lastChar);
            negative = false;
        } else if (OVERPUNCH_NEGATIVE.containsKey(lastChar)) {
            lastDigit = OVERPUNCH_NEGATIVE.get(lastChar);
            negative = true;
        } else if (Character.isDigit(lastChar)) {
            lastDigit = Character.getNumericValue(lastChar);
            negative = false;
        } else {
            // Fallback: treat unknown characters as zero
            lastDigit = 0;
            negative = false;
        }

        // Build the full digit string and apply the implied decimal point
        String allDigits = digitsBeforeLast + lastDigit;
        BigDecimal value = new BigDecimal(allDigits);

        // Shift decimal point left by the number of implied decimal places (V99 → /100)
        if (decimalPlaces > 0) {
            value = value.movePointLeft(decimalPlaces);
        }

        if (negative) {
            value = value.negate();
        }

        return value;
    }

    /**
     * Right-pad a string with spaces to the given length.
     */
    private static String padRight(String s, int length) {
        if (s.length() >= length) {
            return s;
        }
        return s + " ".repeat(length - s.length());
    }
}
