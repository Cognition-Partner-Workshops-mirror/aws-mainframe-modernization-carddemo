package com.balancetransfer.repository;

import com.balancetransfer.model.DailyBalance;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * Repository for DAILY_BALANCES table operations.
 * Provides filtered queries by key, year, and month combinations.
 */
@Repository
public interface DailyBalanceRepository extends JpaRepository<DailyBalance, Long> {

    List<DailyBalance> findByKey1(String key1);

    List<DailyBalance> findByBalanceYearAndBalanceMonth(Integer year, Integer month);

    List<DailyBalance> findByKey1AndBalanceYearAndBalanceMonth(String key1, Integer year, Integer month);

    @Query("SELECT DISTINCT d.key1 FROM DailyBalance d ORDER BY d.key1")
    List<String> findDistinctAddresses();

    @Query("SELECT DISTINCT d.balanceYear FROM DailyBalance d ORDER BY d.balanceYear")
    List<Integer> findDistinctYears();

    @Query("SELECT d FROM DailyBalance d WHERE " +
           "(:key1 IS NULL OR d.key1 = :key1) AND " +
           "(:key2 IS NULL OR d.key2 = :key2) AND " +
           "(:key3 IS NULL OR d.key3 = :key3) AND " +
           "(:key4 IS NULL OR d.key4 = :key4) AND " +
           "(:key5 IS NULL OR d.key5 = :key5) AND " +
           "(:year IS NULL OR d.balanceYear = :year) AND " +
           "(:month IS NULL OR d.balanceMonth = :month)")
    List<DailyBalance> findByFilters(
            @Param("key1") String key1,
            @Param("key2") String key2,
            @Param("key3") String key3,
            @Param("key4") String key4,
            @Param("key5") String key5,
            @Param("year") Integer year,
            @Param("month") Integer month);
}
