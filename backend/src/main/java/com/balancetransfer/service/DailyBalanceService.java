package com.balancetransfer.service;

import com.balancetransfer.model.DailyBalance;
import com.balancetransfer.repository.DailyBalanceRepository;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * Service layer for daily balance operations.
 * Caches frequently accessed queries in Redis.
 */
@Service
public class DailyBalanceService {

    private final DailyBalanceRepository repository;

    public DailyBalanceService(DailyBalanceRepository repository) {
        this.repository = repository;
    }

    @Cacheable(value = "balances", key = "'all'")
    public List<DailyBalance> findAll() {
        return repository.findAll();
    }

    @Cacheable(value = "balances", key = "#key1")
    public List<DailyBalance> findByAddress(String key1) {
        return repository.findByKey1(key1);
    }

    @Cacheable(value = "balances", key = "#year + '-' + #month")
    public List<DailyBalance> findByYearAndMonth(Integer year, Integer month) {
        return repository.findByBalanceYearAndBalanceMonth(year, month);
    }

    @Cacheable(value = "balances", key = "#key1 + '-' + #year + '-' + #month")
    public List<DailyBalance> findByAddressAndPeriod(String key1, Integer year, Integer month) {
        return repository.findByKey1AndBalanceYearAndBalanceMonth(key1, year, month);
    }

    public List<DailyBalance> findByFilters(String key1, String key2, String key3,
                                             String key4, String key5,
                                             Integer year, Integer month) {
        return repository.findByFilters(key1, key2, key3, key4, key5, year, month);
    }

    @Cacheable(value = "addresses")
    public List<String> getDistinctAddresses() {
        return repository.findDistinctAddresses();
    }

    @Cacheable(value = "years")
    public List<Integer> getDistinctYears() {
        return repository.findDistinctYears();
    }

    public DailyBalance save(DailyBalance balance) {
        return repository.save(balance);
    }
}
