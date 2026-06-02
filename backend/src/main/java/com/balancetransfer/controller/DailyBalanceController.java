package com.balancetransfer.controller;

import com.balancetransfer.model.DailyBalance;
import com.balancetransfer.service.DailyBalanceService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * REST controller for daily balance data.
 * Provides endpoints for the Angular AG Grid frontend to query and filter balances.
 */
@RestController
@RequestMapping("/api/balances")
@CrossOrigin(origins = "*")
public class DailyBalanceController {

    private final DailyBalanceService service;

    public DailyBalanceController(DailyBalanceService service) {
        this.service = service;
    }

    /** Get all balance records (used by AG Grid for initial load). */
    @GetMapping
    public ResponseEntity<List<DailyBalance>> getAll() {
        return ResponseEntity.ok(service.findAll());
    }

    /** Get balances filtered by address (KEY_1). */
    @GetMapping("/by-address/{address}")
    public ResponseEntity<List<DailyBalance>> getByAddress(@PathVariable String address) {
        return ResponseEntity.ok(service.findByAddress(address));
    }

    /** Get balances for a specific year and month. */
    @GetMapping("/by-period/{year}/{month}")
    public ResponseEntity<List<DailyBalance>> getByPeriod(
            @PathVariable Integer year, @PathVariable Integer month) {
        return ResponseEntity.ok(service.findByYearAndMonth(year, month));
    }

    /** Get balances filtered by multiple criteria (used for AG Grid filtering). */
    @GetMapping("/filter")
    public ResponseEntity<List<DailyBalance>> getByFilters(
            @RequestParam(required = false) String key1,
            @RequestParam(required = false) String key2,
            @RequestParam(required = false) String key3,
            @RequestParam(required = false) String key4,
            @RequestParam(required = false) String key5,
            @RequestParam(required = false) Integer year,
            @RequestParam(required = false) Integer month) {
        return ResponseEntity.ok(service.findByFilters(key1, key2, key3, key4, key5, year, month));
    }

    /** Get list of distinct addresses for filter dropdowns. */
    @GetMapping("/addresses")
    public ResponseEntity<List<String>> getAddresses() {
        return ResponseEntity.ok(service.getDistinctAddresses());
    }

    /** Get list of distinct years for filter dropdowns. */
    @GetMapping("/years")
    public ResponseEntity<List<Integer>> getYears() {
        return ResponseEntity.ok(service.getDistinctYears());
    }

    /** Create or update a balance record. */
    @PostMapping
    public ResponseEntity<DailyBalance> save(@RequestBody DailyBalance balance) {
        return ResponseEntity.ok(service.save(balance));
    }
}
