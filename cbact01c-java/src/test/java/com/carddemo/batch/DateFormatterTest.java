package com.carddemo.batch;

import com.carddemo.batch.formatter.DateFormatter;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for the DateFormatter, verifying equivalence with the COBDATFT
 * assembler subroutine that converts between YYYYMMDD and YYYY-MM-DD.
 */
class DateFormatterTest {

    @Test
    @DisplayName("Type 2→2: YYYY-MM-DD → YYYYMMDD (strip dashes)")
    void type2ToType2StripsDashes() {
        // This is the exact conversion CBACT01C performs on the reissue date
        assertEquals("20250520", DateFormatter.formatDate("2025-05-20", "2", "2"));
    }

    @Test
    @DisplayName("Type 1→1: YYYYMMDD → YYYY-MM-DD (insert dashes)")
    void type1ToType1InsertsDashes() {
        assertEquals("2025-05-20", DateFormatter.formatDate("20250520", "1", "1"));
    }

    @Test
    @DisplayName("Type 1→2: invalid combination throws exception")
    void type1ToType2Throws() {
        // COBDATFT assembler branches to GOTOERR for type 1 in + type 2 out
        assertThrows(IllegalArgumentException.class,
            () -> DateFormatter.formatDate("20250520", "1", "2"));
    }

    @Test
    @DisplayName("Type 2→1: invalid combination throws exception")
    void type2ToType1Throws() {
        // COBDATFT assembler branches to GOTOERR for type 2 in + type 1 out
        assertThrows(IllegalArgumentException.class,
            () -> DateFormatter.formatDate("2025-05-20", "2", "1"));
    }

    @Test
    @DisplayName("Invalid input type throws exception")
    void invalidInputTypeThrows() {
        assertThrows(IllegalArgumentException.class,
            () -> DateFormatter.formatDate("20250520", "3", "1"));
    }

    @Test
    @DisplayName("stripDashes convenience method")
    void stripDashesConvenience() {
        assertEquals("20240811", DateFormatter.stripDashes("2024-08-11"));
        assertEquals("20130619", DateFormatter.stripDashes("2013-06-19"));
    }

    @Test
    @DisplayName("extractYear returns first 4 characters")
    void extractYearReturnsYyyy() {
        assertEquals("2025", DateFormatter.extractYear("2025-05-20"));
        assertEquals("2013", DateFormatter.extractYear("2013-08-23"));
    }

    @Test
    @DisplayName("extractYear handles null/short input gracefully")
    void extractYearHandlesEdgeCases() {
        assertEquals("    ", DateFormatter.extractYear(null));
        assertEquals("    ", DateFormatter.extractYear(""));
        assertEquals("    ", DateFormatter.extractYear("20"));
    }

    @Test
    @DisplayName("Round-trip: YYYY-MM-DD → YYYYMMDD → YYYY-MM-DD")
    void roundTrip() {
        String original = "2025-05-20";
        String compact = DateFormatter.formatDate(original, "2", "2");
        String restored = DateFormatter.formatDate(compact, "1", "1");
        assertEquals(original, restored, "Round-trip should preserve the date");
    }
}
