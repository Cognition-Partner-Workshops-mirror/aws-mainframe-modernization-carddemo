package com.balancetransfer;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;

/**
 * Main entry point for the Balance Transfer API.
 * Enables caching via Redis for improved query performance.
 */
@SpringBootApplication
@EnableCaching
public class BalanceTransferApplication {

    public static void main(String[] args) {
        SpringApplication.run(BalanceTransferApplication.class, args);
    }
}
