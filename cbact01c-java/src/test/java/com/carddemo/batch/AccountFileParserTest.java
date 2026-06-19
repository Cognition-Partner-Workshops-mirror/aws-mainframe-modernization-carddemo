package com.carddemo.batch;

import com.carddemo.batch.model.AccountRecord;
import com.carddemo.batch.parser.AccountFileParser;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.io.IOException;
import java.math.BigDecimal;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for the AccountFileParser, verifying that it correctly parses
 * fixed-width ASCII records using CVACT01Y copybook layout with
 * EBCDIC zoned-decimal overpunch decoding.
 */
class AccountFileParserTest {

    /**
     * Path to the 3-record test file extracted from acctdata.txt.
     */
    private static final Path TEST_FILE = Path.of(
        "src/test/resources/test_acctdata.txt"
    );

    @Nested
    @DisplayName("Overpunch Decoding")
    class OverpunchDecoding {

        @Test
        @DisplayName("Positive zero: '{' decodes as +0")
        void positiveZeroOverpunch() {
            // "00000001940{" with S9(10)V99 → 194.00
            // 11 digits before '{' = 00000001940, '{' = +0 → full = 000000019400 → 194.00
            BigDecimal result = AccountFileParser.decodeSignedDecimal(
                "00000001940{", 0, 12, 2
            );
            assertEquals(new BigDecimal("194.00"), result);
        }

        @Test
        @DisplayName("Negative zero: '}' decodes as -0 (which is 0)")
        void negativeZeroOverpunch() {
            // "0000009190}" → 00000091900 → -919.00
            BigDecimal result = AccountFileParser.decodeSignedDecimal(
                "0000009190}", 0, 11, 2
            );
            assertEquals(new BigDecimal("-919.00"), result);
        }

        @Test
        @DisplayName("Positive 7: 'G' decodes correctly")
        void positiveSevenOverpunch() {
            // "0000005047G" with S9(09)V99 → 504.77
            BigDecimal result = AccountFileParser.decodeSignedDecimal(
                "0000005047G", 0, 11, 2
            );
            assertEquals(new BigDecimal("504.77"), result);
        }

        @ParameterizedTest
        @DisplayName("All positive overpunch characters decode correctly")
        @CsvSource({
            "'{', 0", "'A', 1", "'B', 2", "'C', 3", "'D', 4",
            "'E', 5", "'F', 6", "'G', 7", "'H', 8", "'I', 9"
        })
        void allPositiveOverpunchChars(char overpunch, int expectedDigit) {
            // Build a 12-char field: "00000000000" + overpunch
            String field = "00000000000" + overpunch;
            BigDecimal result = AccountFileParser.decodeSignedDecimal(field, 0, 12, 2);
            // Expected: 0.0<expectedDigit> (last digit is in the decimal part)
            BigDecimal expected = new BigDecimal("0.0" + expectedDigit);
            assertEquals(expected, result,
                "Overpunch '" + overpunch + "' should decode to digit " + expectedDigit);
        }

        @ParameterizedTest
        @DisplayName("All negative overpunch characters decode correctly")
        @CsvSource({
            "'}', 0", "'J', 1", "'K', 2", "'L', 3", "'M', 4",
            "'N', 5", "'O', 6", "'P', 7", "'Q', 8", "'R', 9"
        })
        void allNegativeOverpunchChars(char overpunch, int expectedDigit) {
            String field = "00000000000" + overpunch;
            BigDecimal result = AccountFileParser.decodeSignedDecimal(field, 0, 12, 2);
            BigDecimal expected = new BigDecimal("-0.0" + expectedDigit);
            assertEquals(expected, result,
                "Overpunch '" + overpunch + "' should decode to negative digit " + expectedDigit);
        }

        @Test
        @DisplayName("All-zero field with '{' overpunch → 0.00")
        void allZeroField() {
            BigDecimal result = AccountFileParser.decodeSignedDecimal(
                "00000000000{", 0, 12, 2
            );
            assertEquals(new BigDecimal("0.00"), result);
        }
    }

    @Nested
    @DisplayName("File Parsing")
    class FileParsing {

        @Test
        @DisplayName("Parses 3-record test file correctly")
        void parseTestFile() throws IOException {
            List<AccountRecord> records = AccountFileParser.parseFile(TEST_FILE);

            // Verify record count
            assertEquals(3, records.size(), "Should parse 3 records");
        }

        @Test
        @DisplayName("First record: account 00000000001")
        void firstRecord() throws IOException {
            List<AccountRecord> records = AccountFileParser.parseFile(TEST_FILE);
            AccountRecord acct1 = records.get(0);

            // Verify all fields match the raw data for account 1
            assertEquals("00000000001", acct1.accountId());
            assertEquals("Y", acct1.activeStatus());
            assertEquals(new BigDecimal("194.00"), acct1.currentBalance());
            assertEquals(new BigDecimal("2020.00"), acct1.creditLimit());
            assertEquals(new BigDecimal("1020.00"), acct1.cashCreditLimit());
            assertEquals("2014-11-20", acct1.openDate());
            assertEquals("2025-05-20", acct1.expirationDate());
            assertEquals("2025-05-20", acct1.reissueDate());
            assertEquals(new BigDecimal("0.00"), acct1.currentCycleCredit());
            assertEquals(new BigDecimal("0.00"), acct1.currentCycleDebit());
        }

        @Test
        @DisplayName("Second record: account 00000000002")
        void secondRecord() throws IOException {
            List<AccountRecord> records = AccountFileParser.parseFile(TEST_FILE);
            AccountRecord acct2 = records.get(1);

            assertEquals("00000000002", acct2.accountId());
            assertEquals("Y", acct2.activeStatus());
            assertEquals(new BigDecimal("158.00"), acct2.currentBalance());
            assertEquals(new BigDecimal("6130.00"), acct2.creditLimit());
            assertEquals(new BigDecimal("5448.00"), acct2.cashCreditLimit());
            assertEquals("2013-06-19", acct2.openDate());
            assertEquals("2024-08-11", acct2.expirationDate());
            assertEquals("2024-08-11", acct2.reissueDate());
        }

        @Test
        @DisplayName("Third record: account 00000000003")
        void thirdRecord() throws IOException {
            List<AccountRecord> records = AccountFileParser.parseFile(TEST_FILE);
            AccountRecord acct3 = records.get(2);

            assertEquals("00000000003", acct3.accountId());
            assertEquals("Y", acct3.activeStatus());
            assertEquals(new BigDecimal("147.00"), acct3.currentBalance());
            assertEquals(new BigDecimal("4909.00"), acct3.creditLimit());
            assertEquals(new BigDecimal("538.00"), acct3.cashCreditLimit());
            assertEquals("2013-08-23", acct3.openDate());
            assertEquals("2024-01-10", acct3.expirationDate());
            assertEquals("2024-01-10", acct3.reissueDate());
        }
    }

    @Nested
    @DisplayName("Single Line Parsing")
    class SingleLineParsing {

        @Test
        @DisplayName("Handles line shorter than 300 chars by padding")
        void shortLinePadded() {
            // Minimal valid line: just the key fields, short enough to need padding
            String shortLine = "00000000001Y00000001940{00000020200{00000010200{"
                + "2014-11-202025-05-202025-05-2000000000000{00000000000{A000000000";
            AccountRecord rec = AccountFileParser.parseLine(
                shortLine + " ".repeat(300 - shortLine.length())
            );
            assertEquals("00000000001", rec.accountId());
            assertEquals(new BigDecimal("194.00"), rec.currentBalance());
        }
    }
}
