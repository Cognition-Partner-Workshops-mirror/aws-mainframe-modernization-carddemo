package com.carddemo.batch;

import com.carddemo.batch.model.AccountRecord;
import com.carddemo.batch.model.ArrayRecord;
import com.carddemo.batch.model.ArrayRecord.BalanceEntry;
import com.carddemo.batch.model.OutputAccountRecord;
import com.carddemo.batch.model.VariableLengthRecord;
import com.carddemo.batch.processor.AccountFileProcessor;
import com.carddemo.batch.processor.AccountFileProcessor.ProcessingResult;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for the AccountFileProcessor, verifying that the Java version
 * produces identical results to the COBOL CBACT01C program for sample inputs.
 *
 * These tests validate:
 *   1. Output record transformations (date reformatting, debit defaulting)
 *   2. Array record population (hardcoded slot values)
 *   3. Variable-length record generation (two records per account)
 *   4. End-to-end file processing with the actual acctdata.txt sample
 */
class AccountFileProcessorTest {

    private static final Path TEST_FILE = Path.of("src/test/resources/test_acctdata.txt");

    @TempDir
    Path tempDir;

    private AccountFileProcessor processor;
    private Path outFile;
    private Path arrFile;
    private Path vbrcFile;

    @BeforeEach
    void setUp() {
        outFile = tempDir.resolve("outfile.txt");
        arrFile = tempDir.resolve("arryfile.txt");
        vbrcFile = tempDir.resolve("vbrcfile.txt");
        processor = new AccountFileProcessor(TEST_FILE, outFile, arrFile, vbrcFile);
    }

    @Nested
    @DisplayName("Output Record Transformation (1300-POPUL-ACCT-RECORD)")
    class OutputRecordTransformation {

        @Test
        @DisplayName("Reissue date converted from YYYY-MM-DD to YYYYMMDD")
        void reissueDateReformatted() {
            // Account 1: reissue date = 2025-05-20 → expected YYYYMMDD = 20250520
            AccountRecord input = makeAccount("00000000001", "194.00", "2025-05-20", "0.00");
            OutputAccountRecord output = processor.buildOutputRecord(input);
            assertEquals("20250520", output.reissueDate(),
                "Reissue date should be reformatted from YYYY-MM-DD to YYYYMMDD");
        }

        @Test
        @DisplayName("Zero cycle debit defaults to 2525.00")
        void zeroCycleDebitDefaulted() {
            // When ACCT-CURR-CYC-DEBIT is zero, COBOL sets it to 2525.00 (line 237)
            AccountRecord input = makeAccount("00000000001", "194.00", "2025-05-20", "0.00");
            OutputAccountRecord output = processor.buildOutputRecord(input);
            assertEquals(new BigDecimal("2525.00"), output.currentCycleDebit(),
                "Zero debit should default to 2525.00");
        }

        @Test
        @DisplayName("Non-zero cycle debit preserved as-is")
        void nonZeroCycleDebitPreserved() {
            // When ACCT-CURR-CYC-DEBIT is non-zero, it passes through unchanged
            AccountRecord input = makeAccount("00000000001", "194.00", "2025-05-20", "500.00");
            OutputAccountRecord output = processor.buildOutputRecord(input);
            assertEquals(new BigDecimal("500.00"), output.currentCycleDebit(),
                "Non-zero debit should be preserved");
        }

        @Test
        @DisplayName("Balance, limits, and dates pass through unchanged")
        void fieldsPassThrough() {
            // Use account 1's values consistently with the makeAccount helper
            AccountRecord input = makeAccount("00000000001", "194.00", "2025-05-20", "0.00");
            OutputAccountRecord output = processor.buildOutputRecord(input);

            assertEquals("00000000001", output.accountId());
            assertEquals("Y", output.activeStatus());
            assertEquals(new BigDecimal("194.00"), output.currentBalance());
            assertEquals(new BigDecimal("2020.00"), output.creditLimit());
            assertEquals(new BigDecimal("1020.00"), output.cashCreditLimit());
            assertEquals("2014-11-20", output.openDate());
            assertEquals("2025-05-20", output.expirationDate());
        }
    }

    @Nested
    @DisplayName("Array Record Population (1400-POPUL-ARRAY-RECORD)")
    class ArrayRecordPopulation {

        @Test
        @DisplayName("Array has exactly 5 entries")
        void arrayHasFiveEntries() {
            AccountRecord input = makeAccount("00000000001", "194.00", "2025-05-20", "0.00");
            ArrayRecord arr = processor.buildArrayRecord(input);
            assertEquals(5, arr.entries().size(), "OCCURS 5 TIMES → 5 entries");
        }

        @Test
        @DisplayName("Slot 1: balance = account balance, debit = 1005.00")
        void slot1Values() {
            AccountRecord input = makeAccount("00000000001", "194.00", "2025-05-20", "0.00");
            ArrayRecord arr = processor.buildArrayRecord(input);
            BalanceEntry slot1 = arr.entries().get(0);

            assertEquals(new BigDecimal("194.00"), slot1.currentBalance(),
                "Slot 1 balance should be the account's current balance");
            assertEquals(new BigDecimal("1005.00"), slot1.currentCycleDebit(),
                "Slot 1 debit should be hardcoded 1005.00");
        }

        @Test
        @DisplayName("Slot 2: balance = account balance, debit = 1525.00")
        void slot2Values() {
            AccountRecord input = makeAccount("00000000001", "194.00", "2025-05-20", "0.00");
            ArrayRecord arr = processor.buildArrayRecord(input);
            BalanceEntry slot2 = arr.entries().get(1);

            assertEquals(new BigDecimal("194.00"), slot2.currentBalance());
            assertEquals(new BigDecimal("1525.00"), slot2.currentCycleDebit());
        }

        @Test
        @DisplayName("Slot 3: balance = -1025.00, debit = -2500.00 (hardcoded)")
        void slot3Hardcoded() {
            AccountRecord input = makeAccount("00000000001", "194.00", "2025-05-20", "0.00");
            ArrayRecord arr = processor.buildArrayRecord(input);
            BalanceEntry slot3 = arr.entries().get(2);

            assertEquals(new BigDecimal("-1025.00"), slot3.currentBalance(),
                "Slot 3 balance should be hardcoded -1025.00");
            assertEquals(new BigDecimal("-2500.00"), slot3.currentCycleDebit(),
                "Slot 3 debit should be hardcoded -2500.00");
        }

        @Test
        @DisplayName("Slots 4-5: zeroed (from INITIALIZE)")
        void slots4And5Zeroed() {
            AccountRecord input = makeAccount("00000000001", "194.00", "2025-05-20", "0.00");
            ArrayRecord arr = processor.buildArrayRecord(input);

            for (int i = 3; i < 5; i++) {
                BalanceEntry slot = arr.entries().get(i);
                assertEquals(BigDecimal.ZERO, slot.currentBalance(),
                    "Slot " + (i + 1) + " balance should be zero");
                assertEquals(BigDecimal.ZERO, slot.currentCycleDebit(),
                    "Slot " + (i + 1) + " debit should be zero");
            }
        }
    }

    @Nested
    @DisplayName("Variable-Length Record Generation (1500-POPUL-VBRC-RECORD)")
    class VariableLengthRecordGeneration {

        @Test
        @DisplayName("Type1 record: account ID + active status")
        void type1Record() {
            AccountRecord input = makeAccount("00000000001", "194.00", "2025-05-20", "0.00");
            VariableLengthRecord.Type1 vb1 = processor.buildVbrcType1(input);

            assertEquals("00000000001", vb1.accountId());
            assertEquals("Y", vb1.activeStatus());
        }

        @Test
        @DisplayName("Type2 record: account ID + balance + credit limit + reissue year")
        void type2Record() {
            AccountRecord input = makeAccount("00000000001", "194.00", "2025-05-20", "0.00");
            VariableLengthRecord.Type2 vb2 = processor.buildVbrcType2(input);

            assertEquals("00000000001", vb2.accountId());
            assertEquals(new BigDecimal("194.00"), vb2.currentBalance());
            assertEquals(new BigDecimal("2020.00"), vb2.creditLimit());
            // Reissue year extracted from "2025-05-20" → "2025"
            assertEquals("2025", vb2.reissueYear(),
                "Reissue year should be the first 4 chars of the reissue date");
        }
    }

    @Nested
    @DisplayName("End-to-End Processing")
    class EndToEnd {

        @Test
        @DisplayName("Processes 3-record test file and produces correct counts")
        void processTestFile() throws IOException {
            ProcessingResult result = processor.process();

            assertEquals(3, result.recordCount(), "Should process 3 input records");
            assertEquals(3, result.outputRecords().size(), "Should produce 3 output records");
            assertEquals(3, result.arrayRecords().size(), "Should produce 3 array records");
            // 2 variable-length records per account (Type1 + Type2) × 3 accounts = 6
            assertEquals(6, result.vbrcRecords().size(),
                "Should produce 6 VBRC records (2 per account)");
        }

        @Test
        @DisplayName("Output file is written and non-empty")
        void outputFileWritten() throws IOException {
            processor.process();

            assertTrue(Files.exists(outFile), "Output file should exist");
            List<String> lines = Files.readAllLines(outFile);
            assertEquals(3, lines.size(), "Output file should have 3 lines");

            // Verify first line contains expected fields
            String firstLine = lines.get(0);
            assertTrue(firstLine.contains("00000000001"), "Should contain account ID");
            assertTrue(firstLine.contains("194"), "Should contain balance");
            assertTrue(firstLine.contains("20250520"), "Should contain reformatted date");
            assertTrue(firstLine.contains("2525"), "Should contain defaulted debit");
        }

        @Test
        @DisplayName("Array file is written with correct structure")
        void arrayFileWritten() throws IOException {
            processor.process();

            assertTrue(Files.exists(arrFile), "Array file should exist");
            List<String> lines = Files.readAllLines(arrFile);
            assertEquals(3, lines.size(), "Array file should have 3 lines");

            // Verify hardcoded values in first line
            String firstLine = lines.get(0);
            assertTrue(firstLine.contains("1005"), "Should contain slot 1 debit");
            assertTrue(firstLine.contains("1525"), "Should contain slot 2 debit");
            assertTrue(firstLine.contains("-1025"), "Should contain slot 3 balance");
            assertTrue(firstLine.contains("-2500"), "Should contain slot 3 debit");
        }

        @Test
        @DisplayName("VBRC file has alternating Type1 and Type2 records")
        void vbrcFileWritten() throws IOException {
            processor.process();

            assertTrue(Files.exists(vbrcFile), "VBRC file should exist");
            List<String> lines = Files.readAllLines(vbrcFile);
            assertEquals(6, lines.size(), "VBRC file should have 6 lines (2 per account)");

            // Verify alternating pattern: VB1, VB2, VB1, VB2, VB1, VB2
            assertTrue(lines.get(0).startsWith("VB1|"), "Line 1 should be Type1");
            assertTrue(lines.get(1).startsWith("VB2|"), "Line 2 should be Type2");
            assertTrue(lines.get(2).startsWith("VB1|"), "Line 3 should be Type1");
            assertTrue(lines.get(3).startsWith("VB2|"), "Line 4 should be Type2");
        }

        @Test
        @DisplayName("All three accounts produce correct output record values")
        void allAccountOutputValues() throws IOException {
            ProcessingResult result = processor.process();
            List<OutputAccountRecord> outputs = result.outputRecords();

            // Account 1: reissue=20250520, debit=2525.00 (zero → default)
            OutputAccountRecord out1 = outputs.get(0);
            assertEquals("20250520", out1.reissueDate());
            assertEquals(new BigDecimal("2525.00"), out1.currentCycleDebit());

            // Account 2: reissue=20240811, debit=2525.00 (zero → default)
            OutputAccountRecord out2 = outputs.get(1);
            assertEquals("20240811", out2.reissueDate());
            assertEquals(new BigDecimal("2525.00"), out2.currentCycleDebit());

            // Account 3: reissue=20240110, debit=2525.00 (zero → default)
            OutputAccountRecord out3 = outputs.get(2);
            assertEquals("20240110", out3.reissueDate());
            assertEquals(new BigDecimal("2525.00"), out3.currentCycleDebit());
        }

        @Test
        @DisplayName("VBRC Type2 records contain correct reissue years")
        void vbrcReissueYears() throws IOException {
            ProcessingResult result = processor.process();

            // Extract Type2 records
            List<VariableLengthRecord.Type2> type2s = result.vbrcRecords().stream()
                .filter(r -> r instanceof VariableLengthRecord.Type2)
                .map(r -> (VariableLengthRecord.Type2) r)
                .toList();

            assertEquals(3, type2s.size());
            assertEquals("2025", type2s.get(0).reissueYear(), "Account 1 reissue year");
            assertEquals("2024", type2s.get(1).reissueYear(), "Account 2 reissue year");
            assertEquals("2024", type2s.get(2).reissueYear(), "Account 3 reissue year");
        }
    }

    @Nested
    @DisplayName("Full Dataset Processing")
    class FullDataset {

        @Test
        @DisplayName("Processes all 50 records from acctdata.txt")
        void processFullFile() throws IOException {
            Path fullFile = Path.of("../app/data/ASCII/acctdata.txt");
            if (!Files.exists(fullFile)) {
                // Skip if running outside the repo context
                return;
            }

            Path fullOut = tempDir.resolve("full_out.txt");
            Path fullArr = tempDir.resolve("full_arr.txt");
            Path fullVbrc = tempDir.resolve("full_vbrc.txt");

            AccountFileProcessor fullProcessor = new AccountFileProcessor(
                fullFile, fullOut, fullArr, fullVbrc
            );
            ProcessingResult result = fullProcessor.process();

            // acctdata.txt has 50 records
            assertEquals(50, result.recordCount(), "Should process all 50 accounts");
            assertEquals(50, result.outputRecords().size());
            assertEquals(50, result.arrayRecords().size());
            assertEquals(100, result.vbrcRecords().size(), "100 VBRC records (2 × 50)");

            // Every output record should have a non-blank account ID
            for (OutputAccountRecord rec : result.outputRecords()) {
                assertFalse(rec.accountId().isBlank(), "Account ID should not be blank");
            }

            // Every output record with zero input debit should have 2525.00
            // (all sample records have zero debit, so all should be defaulted)
            for (OutputAccountRecord rec : result.outputRecords()) {
                assertEquals(new BigDecimal("2525.00"), rec.currentCycleDebit(),
                    "All sample accounts have zero debit → should default to 2525.00");
            }
        }
    }

    // --- Test helper to build AccountRecord with typical values ---

    private AccountRecord makeAccount(String id, String balance,
                                      String reissueDate, String cycleDebit) {
        return new AccountRecord(
            id,
            "Y",
            new BigDecimal(balance),
            new BigDecimal("2020.00"),  // credit limit (from account 1)
            new BigDecimal("1020.00"),  // cash credit limit
            "2014-11-20",              // open date
            "2025-05-20",              // expiration date
            reissueDate,
            BigDecimal.ZERO,           // cycle credit
            new BigDecimal(cycleDebit),
            "A000000000",              // address ZIP
            ""                         // group ID
        );
    }

    private AccountRecord makeAccount(String id, String balance,
                                      String reissueDate, String cycleDebit,
                                      BigDecimal creditLimit, BigDecimal cashLimit,
                                      String openDate, String expDate) {
        return new AccountRecord(
            id, "Y", new BigDecimal(balance), creditLimit, cashLimit,
            openDate, expDate, reissueDate, BigDecimal.ZERO,
            new BigDecimal(cycleDebit), "A000000000", ""
        );
    }
}
