package com.carddemo.batch.processor;

import com.carddemo.batch.formatter.DateFormatter;
import com.carddemo.batch.model.AccountRecord;
import com.carddemo.batch.model.ArrayRecord;
import com.carddemo.batch.model.ArrayRecord.BalanceEntry;
import com.carddemo.batch.model.OutputAccountRecord;
import com.carddemo.batch.model.VariableLengthRecord;
import com.carddemo.batch.parser.AccountFileParser;

import java.io.BufferedWriter;
import java.io.IOException;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Java equivalent of the COBOL batch program CBACT01C.
 *
 * Reads an account data file (ACCTFILE), processes each record, and writes
 * three output files:
 *
 *   1. OUT-FILE:  flat account records with date reformatting and debit defaulting
 *   2. ARRY-FILE: array-structured records (5 balance/debit slots per account)
 *   3. VBRC-FILE: variable-length records (two per account — short and long)
 *
 * This class preserves the exact COBOL business logic, including:
 *   - COBDATFT date conversion (YYYY-MM-DD → YYYYMMDD for reissue date)
 *   - Default debit of 2525.00 when input cycle debit is zero
 *   - Hardcoded array slot values (1005.00, 1525.00, -1025.00, -2500.00)
 */
public final class AccountFileProcessor {

    /** Default debit value when ACCT-CURR-CYC-DEBIT is zero (from COBOL line 237) */
    private static final BigDecimal DEFAULT_DEBIT = new BigDecimal("2525.00");

    /** Hardcoded debit for array slot 1 (from COBOL line 256) */
    private static final BigDecimal ARRAY_DEBIT_SLOT1 = new BigDecimal("1005.00");

    /** Hardcoded debit for array slot 2 (from COBOL line 258) */
    private static final BigDecimal ARRAY_DEBIT_SLOT2 = new BigDecimal("1525.00");

    /** Hardcoded balance for array slot 3 (from COBOL line 259) */
    private static final BigDecimal ARRAY_BAL_SLOT3 = new BigDecimal("-1025.00");

    /** Hardcoded debit for array slot 3 (from COBOL line 260) */
    private static final BigDecimal ARRAY_DEBIT_SLOT3 = new BigDecimal("-2500.00");

    private final Path inputPath;
    private final Path outFilePath;
    private final Path arrayFilePath;
    private final Path vbrcFilePath;

    /**
     * Construct a processor with explicit file paths.
     *
     * @param inputPath     path to the input ACCTFILE (acctdata.txt)
     * @param outFilePath   path for the flat output file
     * @param arrayFilePath path for the array-structured output file
     * @param vbrcFilePath  path for the variable-length record output file
     */
    public AccountFileProcessor(Path inputPath, Path outFilePath,
                                Path arrayFilePath, Path vbrcFilePath) {
        this.inputPath = inputPath;
        this.outFilePath = outFilePath;
        this.arrayFilePath = arrayFilePath;
        this.vbrcFilePath = vbrcFilePath;
    }

    /**
     * Execute the batch processing — mirrors the COBOL PROCEDURE DIVISION main loop.
     *
     * @return a ProcessingResult with counts and the output records for verification
     * @throws IOException if any file operation fails
     */
    public ProcessingResult process() throws IOException {
        System.out.println("START OF EXECUTION OF PROGRAM CBACT01C");

        // Read all input records (mirrors 0000-ACCTFILE-OPEN + read loop)
        List<AccountRecord> inputRecords = AccountFileParser.parseFile(inputPath);

        List<OutputAccountRecord> outputRecords = new ArrayList<>();
        List<ArrayRecord> arrayRecords = new ArrayList<>();
        List<VariableLengthRecord> vbrcRecords = new ArrayList<>();

        // Process each record (mirrors PERFORM UNTIL END-OF-FILE = 'Y')
        for (AccountRecord acct : inputRecords) {
            // Display the record (mirrors 1100-DISPLAY-ACCT-RECORD)
            displayAccountRecord(acct);

            // Build and collect output record (mirrors 1300-POPUL-ACCT-RECORD)
            OutputAccountRecord outRec = buildOutputRecord(acct);
            outputRecords.add(outRec);

            // Build and collect array record (mirrors 1400-POPUL-ARRAY-RECORD)
            ArrayRecord arrRec = buildArrayRecord(acct);
            arrayRecords.add(arrRec);

            // Build and collect variable-length records (mirrors 1500-POPUL-VBRC-RECORD)
            VariableLengthRecord.Type1 vb1 = buildVbrcType1(acct);
            VariableLengthRecord.Type2 vb2 = buildVbrcType2(acct);
            vbrcRecords.add(vb1);
            vbrcRecords.add(vb2);
        }

        // Write all output files
        writeOutputFile(outputRecords);
        writeArrayFile(arrayRecords);
        writeVbrcFile(vbrcRecords);

        System.out.println("END OF EXECUTION OF PROGRAM CBACT01C");

        return new ProcessingResult(
            inputRecords.size(),
            Collections.unmodifiableList(outputRecords),
            Collections.unmodifiableList(arrayRecords),
            Collections.unmodifiableList(vbrcRecords)
        );
    }

    /**
     * Build the flat output record — mirrors 1300-POPUL-ACCT-RECORD.
     *
     * Key transformations:
     *   1. Reissue date: YYYY-MM-DD → YYYYMMDD via DateFormatter (COBDATFT equivalent)
     *   2. Cycle debit: if zero, default to 2525.00
     */
    public OutputAccountRecord buildOutputRecord(AccountRecord acct) {
        // Convert reissue date from YYYY-MM-DD to YYYYMMDD (mirrors CALL 'COBDATFT')
        String reformattedReissueDate = reformatReissueDate(acct.reissueDate());

        // Default debit to 2525.00 when zero (mirrors lines 236-238)
        BigDecimal cycleDebit = acct.currentCycleDebit();
        if (cycleDebit.compareTo(BigDecimal.ZERO) == 0) {
            cycleDebit = DEFAULT_DEBIT;
        }

        return new OutputAccountRecord(
            acct.accountId(),
            acct.activeStatus(),
            acct.currentBalance(),
            acct.creditLimit(),
            acct.cashCreditLimit(),
            acct.openDate(),
            acct.expirationDate(),
            reformattedReissueDate,
            acct.currentCycleCredit(),
            cycleDebit,
            acct.groupId()
        );
    }

    /**
     * Build the array record — mirrors 1400-POPUL-ARRAY-RECORD.
     *
     * Populates 5 balance/debit slots:
     *   Slot 1: balance = acct balance, debit = 1005.00
     *   Slot 2: balance = acct balance, debit = 1525.00
     *   Slot 3: balance = -1025.00,     debit = -2500.00
     *   Slots 4-5: zeroed (from INITIALIZE)
     */
    public ArrayRecord buildArrayRecord(AccountRecord acct) {
        List<BalanceEntry> entries = List.of(
            new BalanceEntry(acct.currentBalance(), ARRAY_DEBIT_SLOT1),
            new BalanceEntry(acct.currentBalance(), ARRAY_DEBIT_SLOT2),
            new BalanceEntry(ARRAY_BAL_SLOT3, ARRAY_DEBIT_SLOT3),
            new BalanceEntry(BigDecimal.ZERO, BigDecimal.ZERO),
            new BalanceEntry(BigDecimal.ZERO, BigDecimal.ZERO)
        );
        return new ArrayRecord(acct.accountId(), entries);
    }

    /**
     * Build variable-length Type1 record — mirrors 1500-POPUL-VBRC-RECORD (VB1 part).
     */
    public VariableLengthRecord.Type1 buildVbrcType1(AccountRecord acct) {
        return new VariableLengthRecord.Type1(acct.accountId(), acct.activeStatus());
    }

    /**
     * Build variable-length Type2 record — mirrors 1500-POPUL-VBRC-RECORD (VB2 part).
     *
     * The reissue year is extracted from WS-ACCT-REISSUE-YYYY, which is populated
     * when the reissue date is moved to WS-REISSUE-DATE (a REDEFINES overlay).
     */
    public VariableLengthRecord.Type2 buildVbrcType2(AccountRecord acct) {
        String reissueYear = DateFormatter.extractYear(acct.reissueDate());
        return new VariableLengthRecord.Type2(
            acct.accountId(),
            acct.currentBalance(),
            acct.creditLimit(),
            reissueYear
        );
    }

    /**
     * Reformat the reissue date — replaces the CALL 'COBDATFT' assembler invocation.
     *
     * COBOL sets CODATECN-TYPE = '2' and CODATECN-OUTTYPE = '2', which tells COBDATFT
     * to convert YYYY-MM-DD → YYYYMMDD.
     *
     * If the date is blank or too short, returns it as-is (COBOL would get garbage
     * from the assembler in this case, but we handle it gracefully).
     */
    private String reformatReissueDate(String reissueDate) {
        if (reissueDate == null || reissueDate.isBlank() || reissueDate.length() < 10) {
            return reissueDate != null ? reissueDate : "";
        }
        return DateFormatter.stripDashes(reissueDate);
    }

    /**
     * Display account record fields — mirrors 1100-DISPLAY-ACCT-RECORD.
     */
    private void displayAccountRecord(AccountRecord acct) {
        System.out.println("ACCT-ID                 :" + acct.accountId());
        System.out.println("ACCT-ACTIVE-STATUS      :" + acct.activeStatus());
        System.out.println("ACCT-CURR-BAL           :" + acct.currentBalance());
        System.out.println("ACCT-CREDIT-LIMIT       :" + acct.creditLimit());
        System.out.println("ACCT-CASH-CREDIT-LIMIT  :" + acct.cashCreditLimit());
        System.out.println("ACCT-OPEN-DATE          :" + acct.openDate());
        System.out.println("ACCT-EXPIRAION-DATE     :" + acct.expirationDate());
        System.out.println("ACCT-REISSUE-DATE       :" + acct.reissueDate());
        System.out.println("ACCT-CURR-CYC-CREDIT    :" + acct.currentCycleCredit());
        System.out.println("ACCT-CURR-CYC-DEBIT     :" + acct.currentCycleDebit());
        System.out.println("ACCT-GROUP-ID           :" + acct.groupId());
        System.out.println("-------------------------------------------------");
    }

    // --- File writers (mirror 1350, 1450, 1550, 1575 paragraphs) ---

    /**
     * Write flat output records — mirrors 1350-WRITE-ACCT-RECORD.
     * Outputs one JSON object per line for easy comparison and testing.
     */
    private void writeOutputFile(List<OutputAccountRecord> records) throws IOException {
        try (BufferedWriter writer = Files.newBufferedWriter(outFilePath)) {
            for (OutputAccountRecord rec : records) {
                writer.write(formatOutputRecord(rec));
                writer.newLine();
            }
        }
    }

    /**
     * Write array records — mirrors 1450-WRITE-ARRY-RECORD.
     */
    private void writeArrayFile(List<ArrayRecord> records) throws IOException {
        try (BufferedWriter writer = Files.newBufferedWriter(arrayFilePath)) {
            for (ArrayRecord rec : records) {
                writer.write(formatArrayRecord(rec));
                writer.newLine();
            }
        }
    }

    /**
     * Write variable-length records — mirrors 1550/1575 write paragraphs.
     */
    private void writeVbrcFile(List<VariableLengthRecord> records) throws IOException {
        try (BufferedWriter writer = Files.newBufferedWriter(vbrcFilePath)) {
            for (VariableLengthRecord rec : records) {
                writer.write(formatVbrcRecord(rec));
                writer.newLine();
            }
        }
    }

    /**
     * Format a flat output record as a pipe-delimited string.
     * Pipe-delimited chosen over fixed-width for readability and testability.
     */
    static String formatOutputRecord(OutputAccountRecord rec) {
        return String.join("|",
            rec.accountId(),
            rec.activeStatus(),
            rec.currentBalance().toPlainString(),
            rec.creditLimit().toPlainString(),
            rec.cashCreditLimit().toPlainString(),
            rec.openDate(),
            rec.expirationDate(),
            rec.reissueDate(),
            rec.currentCycleCredit().toPlainString(),
            rec.currentCycleDebit().toPlainString(),
            rec.groupId()
        );
    }

    /**
     * Format an array record as a pipe-delimited string.
     */
    static String formatArrayRecord(ArrayRecord rec) {
        StringBuilder sb = new StringBuilder();
        sb.append(rec.accountId());
        for (BalanceEntry entry : rec.entries()) {
            sb.append("|")
              .append(entry.currentBalance().toPlainString())
              .append(",")
              .append(entry.currentCycleDebit().toPlainString());
        }
        return sb.toString();
    }

    /**
     * Format a variable-length record as a pipe-delimited string with a type prefix.
     */
    static String formatVbrcRecord(VariableLengthRecord rec) {
        // Using instanceof checks instead of pattern-matching switch
        // (pattern switch requires Java 21; this targets Java 17)
        if (rec instanceof VariableLengthRecord.Type1 t1) {
            return "VB1|" + t1.accountId() + "|" + t1.activeStatus();
        } else if (rec instanceof VariableLengthRecord.Type2 t2) {
            return "VB2|" + t2.accountId() + "|" +
                t2.currentBalance().toPlainString() + "|" +
                t2.creditLimit().toPlainString() + "|" +
                t2.reissueYear();
        }
        throw new IllegalArgumentException("Unknown record type: " + rec.getClass());
    }

    /**
     * Results of processing — used by tests to verify output.
     */
    public record ProcessingResult(
        int recordCount,
        List<OutputAccountRecord> outputRecords,
        List<ArrayRecord> arrayRecords,
        List<VariableLengthRecord> vbrcRecords
    ) {}

    /**
     * CLI entry point — mirrors COBOL PROCEDURE DIVISION.
     *
     * Usage: java AccountFileProcessor <acctfile> <outfile> <arryfile> <vbrcfile>
     */
    public static void main(String[] args) throws IOException {
        if (args.length < 4) {
            System.err.println("Usage: AccountFileProcessor <acctfile> <outfile> <arryfile> <vbrcfile>");
            System.exit(1);
        }

        AccountFileProcessor processor = new AccountFileProcessor(
            Path.of(args[0]),
            Path.of(args[1]),
            Path.of(args[2]),
            Path.of(args[3])
        );

        ProcessingResult result = processor.process();
        System.out.println("Processed " + result.recordCount() + " account records.");
    }
}
