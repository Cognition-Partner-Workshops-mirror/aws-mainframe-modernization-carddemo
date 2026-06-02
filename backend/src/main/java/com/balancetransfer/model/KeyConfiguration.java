package com.balancetransfer.model;

import jakarta.persistence.*;
import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * Entity representing a row in KEY_CONFIGURATION table.
 * Maps KEY_1..KEY_16 column positions to human-readable labels.
 * Used by the UI and Superset reports to display meaningful column headers.
 */
@Entity
@Table(name = "KEY_CONFIGURATION")
public class KeyConfiguration implements Serializable {

    @Id
    @Column(name = "KEY_ID")
    private Integer keyId;

    @Column(name = "KEY_NAME", nullable = false, length = 100)
    private String keyName;

    @Column(name = "KEY_DESCRIPTION", length = 500)
    private String keyDescription;

    @Column(name = "IS_ACTIVE", length = 1)
    private String isActive;

    @Column(name = "CREATED_DATE")
    private LocalDateTime createdDate;

    @Column(name = "UPDATED_DATE")
    private LocalDateTime updatedDate;

    public KeyConfiguration() {}

    public Integer getKeyId() { return keyId; }
    public void setKeyId(Integer keyId) { this.keyId = keyId; }

    public String getKeyName() { return keyName; }
    public void setKeyName(String keyName) { this.keyName = keyName; }

    public String getKeyDescription() { return keyDescription; }
    public void setKeyDescription(String keyDescription) { this.keyDescription = keyDescription; }

    public String getIsActive() { return isActive; }
    public void setIsActive(String isActive) { this.isActive = isActive; }

    public LocalDateTime getCreatedDate() { return createdDate; }
    public void setCreatedDate(LocalDateTime createdDate) { this.createdDate = createdDate; }

    public LocalDateTime getUpdatedDate() { return updatedDate; }
    public void setUpdatedDate(LocalDateTime updatedDate) { this.updatedDate = updatedDate; }
}
