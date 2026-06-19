# CBACT01C Migration Notes

> Translation decisions for migrating COBOL batch program CBACT01C to Java 17+.

---

## 1. Program Overview

**CBACT01C** is a batch utility that reads the ACCTFILE (indexed VSAM KSDS) 
sequentially and writes three output files in different formats:

| Output      | COBOL Structure   | Purpose                                    |
|:------------|:------------------|:-------------------------------------------|
| OUT-FILE    | Flat sequential   | Account data with date reformatting         |
| ARRY-FILE   | Array record      | Balance/debit array (5 slots per account)   |
| VBRC-FILE   | Variable-length   | Two records per account (short + long)      |

The program demonstrates COBOL data manipulation patterns: REDEFINES overlays,
OCCURS arrays, COMP-3 packed decimal, variable-length records, and external
subroutine calls (COBDATFT assembler).

---

## 2. Translation Decisions

### 2.1 Data Structures: COBOL Copybooks → Java Records

| COBOL                | Java                          | Rationale                                |
|:---------------------|:------------------------------|:-----------------------------------------|
| `ACCOUNT-RECORD` (CVACT01Y) | `AccountRecord` record | Immutable value type; matches copybook 1:1 |
| `OUT-ACCT-REC` (FD)  | `OutputAccountRecord` record  | Separate type captures transformation    |
| `ARR-ARRAY-REC` (FD) | `ArrayRecord` record + `BalanceEntry` inner record | Nested record models OCCURS clause |
| `VBRC-REC1` / `VBRC-REC2` (WS) | `VariableLengthRecord` sealed interface with `Type1`/`Type2` records | Sealed interface enforces exhaustive handling |

**Decision:** Used Java `record` types (Java 16+) instead of classes. Records
provide immutable value semantics with built-in `equals`/`hashCode`/`toString`,
matching COBOL's fixed data structure philosophy. The sealed interface for
variable-length records replaces the COBOL pattern of multiple WS record
definitions that get MOVE'd into a shared FD.

### 2.2 Numeric Types: PIC S9(n)V99 → BigDecimal

| COBOL PIC Clause     | Java Type      | Notes                                    |
|:---------------------|:---------------|:-----------------------------------------|
| `PIC 9(11)`          | `String`       | Account ID is a key, not arithmetic      |
| `PIC S9(10)V99`      | `BigDecimal`   | Signed decimal with implied V99          |
| `PIC S9(10)V99 COMP-3` | `BigDecimal` | Packed storage is an encoding detail     |

**Decision:** All monetary fields use `BigDecimal`, never `double` or `float`.
COBOL's `PIC S9(10)V99` provides exact decimal arithmetic; `BigDecimal` is the
only Java type that preserves this precision. The distinction between DISPLAY
and COMP-3 storage formats is handled at the I/O layer, not in the domain model.

### 2.3 Overpunch Decoding

The ASCII data files use EBCDIC zoned-decimal overpunch encoding for signed
fields. The last byte of a signed field encodes both the digit value and sign:

```
Positive: { A B C D E F G H I  →  0 1 2 3 4 5 6 7 8 9
Negative: } J K L M N O P Q R  →  0 1 2 3 4 5 6 7 8 9
```

**Decision:** Implemented `decodeSignedDecimal()` in `AccountFileParser` as a
pure function with lookup maps. This replaces the implicit COBOL behavior where
the runtime automatically handles overpunch when MOVEing a zoned decimal field
into a DISPLAY or COMP field.

**Verification:** All 10 positive and 10 negative overpunch characters are
tested with parameterized JUnit tests (`AccountFileParserTest.OverpunchDecoding`).

### 2.4 COBDATFT Assembler → DateFormatter

| COBDATFT (assembler)           | DateFormatter (Java)                    |
|:-------------------------------|:----------------------------------------|
| MVC/MVI byte manipulation      | `String.substring()` + concatenation    |
| CLI branch to GOTOERR          | `IllegalArgumentException`              |
| DSECT-based parameter passing   | Method parameters                       |

**Decision:** Replaced the assembler subroutine with a pure Java utility class.
The assembler performed character-level MVC (move characters) operations to
insert/strip dashes from dates. Java's `String.substring()` is the direct
equivalent.

CBACT01C specifically uses type 2 → type 2 conversion (YYYY-MM-DD → YYYYMMDD).
The COBOL code also moves the reissue date into `WS-ACCT-REISSUE-DATE` using
a REDEFINES overlay to extract `WS-ACCT-REISSUE-YYYY` (the year portion).
In Java, this is simply `dateString.substring(0, 4)`.

### 2.5 File I/O: VSAM/Sequential → BufferedReader/Writer

| COBOL I/O                      | Java I/O                                |
|:-------------------------------|:----------------------------------------|
| `OPEN INPUT ACCTFILE-FILE`     | `Files.newBufferedReader(path)`         |
| `READ ACCTFILE-FILE INTO ...`  | `reader.readLine()` + `parseLine()`     |
| `WRITE OUT-ACCT-REC`           | `writer.write(formatOutputRecord(rec))` |
| `FILE STATUS IS ACCTFILE-STATUS` | `IOException` handling                |
| Recording Mode V (VBRC-FILE)   | Line-based output with type prefix      |

**Decision:** The COBOL program writes fixed-width records to three DD-name
files. The Java version writes pipe-delimited text files for readability and
testability. In a production deployment, the output format would be chosen
based on the downstream consumer (database, REST API, message queue, etc.).

The variable-length record file (RECORDING MODE V) is modeled as line-based
output with a `VB1|` or `VB2|` type prefix, replacing the COBOL pattern of
setting `WS-RECD-LEN` and moving data to a shared buffer.

### 2.6 Error Handling: ABEND → Exception

| COBOL Error Handling           | Java Equivalent                         |
|:-------------------------------|:----------------------------------------|
| `PERFORM 9999-ABEND-PROGRAM`  | `throw new IOException(...)` / propagate |
| `CALL 'CEE3ABD' USING ABCODE` | JVM exception + stack trace             |
| `9910-DISPLAY-IO-STATUS`      | Exception message includes status       |
| `APPL-EOF` (status 10)        | End of file = `readLine()` returns null |
| `APPL-AOK` (status 00)        | Normal control flow                     |

**Decision:** COBOL's multi-step error check pattern (set status, test 88-level,
branch to ABEND paragraph) is replaced by Java's exception mechanism. File status
code checking is implicit in `IOException` handling. The level-88 conditions
`APPL-AOK` and `APPL-EOF` map to normal flow and null-return respectively.

### 2.7 Business Logic Preservations

The following COBOL business rules are preserved exactly:

1. **Default debit:** When `ACCT-CURR-CYC-DEBIT` equals zero, the output
   record gets `2525.00` (COBOL line 237). This is likely test scaffolding
   but is preserved for behavioral equivalence.

2. **Array slot values:** Hardcoded values in the OCCURS array:
   - Slot 1: balance = input balance, debit = 1005.00
   - Slot 2: balance = input balance, debit = 1525.00  
   - Slot 3: balance = -1025.00, debit = -2500.00
   - Slots 4-5: zeroed (from INITIALIZE)

3. **VBRC record lengths:** Type1 = 12 bytes (acct-id + status),
   Type2 = 39 bytes (acct-id + balance + limit + reissue year).

4. **Reissue year extraction:** The COBOL program moves the reissue date
   to `WS-ACCT-REISSUE-DATE` (a REDEFINES of `WS-REISSUE-DATE`) and then
   reads `WS-ACCT-REISSUE-YYYY` — the first 4 bytes. This is the year
   component, which goes into `VB2-ACCT-REISSUE-YYYY`.

---

## 3. COBOL Constructs Without Direct Java Equivalents

| COBOL Construct              | How Handled in Java                        |
|:-----------------------------|:-------------------------------------------|
| `REDEFINES`                  | Separate record types or `substring()`     |
| `OCCURS n TIMES`             | `List<BalanceEntry>` with fixed size       |
| `PIC S9(n)V99 COMP-3`       | `BigDecimal` (encoding at write time)      |
| `RECORDING MODE V`           | Line-based output with type prefix         |
| `FILE STATUS`                | `IOException` (checked exception)          |
| 88-level conditions          | Named constants or enum values             |
| `CALL 'CEE3ABD'`            | `System.exit(999)` or exception propagation|
| `INITIALIZE` (zero-fill)     | `BigDecimal.ZERO` in constructor           |
| Paragraph-based flow control | Method calls                               |
| `DISPLAY` (sysout)           | `System.out.println()`                     |

---

## 4. Test Coverage

| Test Class                    | Tests | What It Validates                          |
|:------------------------------|------:|:-------------------------------------------|
| `AccountFileParserTest`       |    30 | Overpunch decoding (all 20 chars), file parsing, field extraction |
| `DateFormatterTest`           |     8 | Type 1↔2 conversions, error cases, round-trip, year extraction |
| `AccountFileProcessorTest`    |    18 | Output transformation, array population, VBRC generation, end-to-end |
| **Total**                     | **56** |                                           |

### Golden-File Equivalence

The `FullDataset` test processes all 50 records from `acctdata.txt` and
verifies:
- Record count parity (50 in → 50 out × 3 files)
- All account IDs are non-blank
- All zero-debit accounts receive the 2525.00 default

---

## 5. Project Structure

```
cbact01c-java/
├── pom.xml                          # Maven build (Java 17, JUnit 5)
├── MIGRATION_NOTES.md               # This file
├── src/main/java/com/carddemo/batch/
│   ├── model/
│   │   ├── AccountRecord.java       # Input: CVACT01Y copybook
│   │   ├── OutputAccountRecord.java # Output: OUT-ACCT-REC
│   │   ├── ArrayRecord.java         # Output: ARR-ARRAY-REC
│   │   └── VariableLengthRecord.java# Output: VBRC-REC1/REC2
│   ├── parser/
│   │   └── AccountFileParser.java   # ACCTFILE reader + overpunch decoder
│   ├── formatter/
│   │   └── DateFormatter.java       # COBDATFT replacement
│   └── processor/
│       └── AccountFileProcessor.java# Main batch logic (PROCEDURE DIVISION)
└── src/test/
    ├── java/com/carddemo/batch/
    │   ├── AccountFileParserTest.java
    │   ├── DateFormatterTest.java
    │   └── AccountFileProcessorTest.java
    └── resources/
        └── test_acctdata.txt        # 3-record test fixture from acctdata.txt
```

---

## 6. Running

```bash
# Build and test
cd cbact01c-java
mvn clean test

# Run against the full dataset
mvn exec:java -Dexec.mainClass="com.carddemo.batch.processor.AccountFileProcessor" \
  -Dexec.args="../app/data/ASCII/acctdata.txt output.txt array.txt vbrc.txt"
```

---

## 7. Limitations and Future Work

1. **Output format:** The Java version writes pipe-delimited text. A production
   migration would write to a database (PostgreSQL) or publish to a message
   broker, not to files.

2. **COMP-3 encoding:** The COBOL `OUT-ACCT-CURR-CYC-DEBIT` and
   `ARR-ACCT-CURR-CYC-DEBIT` use COMP-3 (packed decimal) storage. The Java
   version stores these as `BigDecimal` — if binary-compatible output is
   required, a COMP-3 encoder would need to be added.

3. **Variable-length records:** The COBOL VBRC-FILE uses RECORDING MODE V
   with a 4-byte Record Descriptor Word (RDW) prefix. The Java version uses
   line-based output. Binary-compatible VB output would require writing the
   RDW header.

4. **CICS integration:** CBACT01C is a pure batch program (no CICS commands).
   Online programs like COACTUPC would require additional infrastructure
   (transaction management, screen handling) not addressed here.
