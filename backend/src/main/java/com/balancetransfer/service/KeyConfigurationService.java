package com.balancetransfer.service;

import com.balancetransfer.model.KeyConfiguration;
import com.balancetransfer.repository.KeyConfigurationRepository;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * Service layer for key configuration operations.
 * Results are cached since key names change infrequently.
 */
@Service
public class KeyConfigurationService {

    private final KeyConfigurationRepository repository;

    public KeyConfigurationService(KeyConfigurationRepository repository) {
        this.repository = repository;
    }

    @Cacheable(value = "keyConfig", key = "'all'")
    public List<KeyConfiguration> findAll() {
        return repository.findAll();
    }

    @Cacheable(value = "keyConfig", key = "'active'")
    public List<KeyConfiguration> findActive() {
        return repository.findByIsActive("Y");
    }
}
