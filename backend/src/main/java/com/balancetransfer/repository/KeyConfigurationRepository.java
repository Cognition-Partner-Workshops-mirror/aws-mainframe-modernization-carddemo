package com.balancetransfer.repository;

import com.balancetransfer.model.KeyConfiguration;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * Repository for KEY_CONFIGURATION table.
 * Provides access to key name mappings for UI column headers.
 */
@Repository
public interface KeyConfigurationRepository extends JpaRepository<KeyConfiguration, Integer> {

    List<KeyConfiguration> findByIsActive(String isActive);
}
