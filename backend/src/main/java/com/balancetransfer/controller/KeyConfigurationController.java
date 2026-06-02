package com.balancetransfer.controller;

import com.balancetransfer.model.KeyConfiguration;
import com.balancetransfer.service.KeyConfigurationService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * REST controller for key configuration data.
 * Provides key name mappings to the frontend for dynamic column headers.
 */
@RestController
@RequestMapping("/api/keys")
@CrossOrigin(origins = "*")
public class KeyConfigurationController {

    private final KeyConfigurationService service;

    public KeyConfigurationController(KeyConfigurationService service) {
        this.service = service;
    }

    /** Get all key configurations (for Superset dataset column aliasing). */
    @GetMapping
    public ResponseEntity<List<KeyConfiguration>> getAll() {
        return ResponseEntity.ok(service.findAll());
    }

    /** Get only active key configurations (for UI display). */
    @GetMapping("/active")
    public ResponseEntity<List<KeyConfiguration>> getActive() {
        return ResponseEntity.ok(service.findActive());
    }
}
