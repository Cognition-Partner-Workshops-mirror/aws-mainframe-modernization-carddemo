package com.carddemo.batch.formatter;

/**
 * Replaces the COBDATFT assembler subroutine for date format conversion.
 *
 * The original assembler handles two transformations:
 *   Type 1 in → Type 1 out: YYYYMMDD → YYYY-MM-DD (insert dashes)
 *   Type 2 in → Type 2 out: YYYY-MM-DD → YYYYMMDD (strip dashes)
 *
 * CBACT01C calls COBDATFT with type=2 / outtype=2, which strips dashes
 * from the reissue date: "2025-05-20" → "20250520".
 *
 * Invalid combinations (type 1 + outtype 2, type 2 + outtype 1) produce
 * an error message in the COBOL program — we throw IllegalArgumentException.
 */
public final class DateFormatter {

    private DateFormatter() {
        // Utility class — no instantiation
    }

    /**
     * Convert a date string between YYYYMMDD and YYYY-MM-DD formats.
     *
     * @param inputDate  the date string to convert
     * @param inputType  "1" for YYYYMMDD input, "2" for YYYY-MM-DD input
     * @param outputType "1" for YYYY-MM-DD output, "2" for YYYYMMDD output
     * @return the reformatted date string
     * @throws IllegalArgumentException if the type combination is invalid
     */
    public static String formatDate(String inputDate, String inputType,
                                    String outputType) {
        return switch (inputType) {
            // Type 1: YYYYMMDD input → must produce YYYY-MM-DD output
            case "1" -> {
                if ("2".equals(outputType)) {
                    throw new IllegalArgumentException(
                        "INVALID INPUT: type 1 in cannot produce type 2 out");
                }
                // YYYYMMDD → YYYY-MM-DD: insert dashes at positions 4 and 6
                String yyyy = inputDate.substring(0, 4);
                String mm = inputDate.substring(4, 6);
                String dd = inputDate.substring(6, 8);
                yield yyyy + "-" + mm + "-" + dd;
            }

            // Type 2: YYYY-MM-DD input → must produce YYYYMMDD output
            case "2" -> {
                if ("1".equals(outputType)) {
                    throw new IllegalArgumentException(
                        "INVALID INPUT: type 2 in cannot produce type 1 out");
                }
                // YYYY-MM-DD → YYYYMMDD: strip dashes
                String yyyy = inputDate.substring(0, 4);
                String mm = inputDate.substring(5, 7);
                String dd = inputDate.substring(8, 10);
                yield yyyy + mm + dd;
            }

            default -> throw new IllegalArgumentException(
                "INVALID INPUT: unknown input type '" + inputType + "'");
        };
    }

    /**
     * Convenience method matching CBACT01C's specific usage:
     * convert YYYY-MM-DD → YYYYMMDD (type 2 → type 2).
     *
     * @param dateWithDashes date in YYYY-MM-DD format
     * @return date in YYYYMMDD format
     */
    public static String stripDashes(String dateWithDashes) {
        return formatDate(dateWithDashes, "2", "2");
    }

    /**
     * Extract the 4-character year from a YYYY-MM-DD date string.
     * Used to populate VB2-ACCT-REISSUE-YYYY in the variable-length record.
     *
     * @param dateWithDashes date in YYYY-MM-DD format
     * @return 4-character year string
     */
    public static String extractYear(String dateWithDashes) {
        if (dateWithDashes == null || dateWithDashes.length() < 4) {
            return "    ";
        }
        return dateWithDashes.substring(0, 4);
    }
}
