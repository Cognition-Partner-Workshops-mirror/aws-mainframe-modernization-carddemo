-- ============================================================
-- Seed data for KEY_CONFIGURATION table.
-- These names map KEY_1..KEY_16 to human-readable labels.
-- Update these when business requirements change key meanings.
-- ============================================================

INSERT INTO KEY_CONFIGURATION (KEY_ID, KEY_NAME, KEY_DESCRIPTION, IS_ACTIVE) VALUES
(1, 'Address', 'Primary address or location identifier', 'Y');
INSERT INTO KEY_CONFIGURATION (KEY_ID, KEY_NAME, KEY_DESCRIPTION, IS_ACTIVE) VALUES
(2, 'Account Type', 'Type of account (Savings, Checking, etc.)', 'Y');
INSERT INTO KEY_CONFIGURATION (KEY_ID, KEY_NAME, KEY_DESCRIPTION, IS_ACTIVE) VALUES
(3, 'Currency', 'Currency code (USD, EUR, GBP, etc.)', 'Y');
INSERT INTO KEY_CONFIGURATION (KEY_ID, KEY_NAME, KEY_DESCRIPTION, IS_ACTIVE) VALUES
(4, 'Region', 'Geographic region code', 'Y');
INSERT INTO KEY_CONFIGURATION (KEY_ID, KEY_NAME, KEY_DESCRIPTION, IS_ACTIVE) VALUES
(5, 'Branch', 'Branch office identifier', 'Y');
INSERT INTO KEY_CONFIGURATION (KEY_ID, KEY_NAME, KEY_DESCRIPTION, IS_ACTIVE) VALUES
(6, 'Department', 'Department or cost center', 'Y');
INSERT INTO KEY_CONFIGURATION (KEY_ID, KEY_NAME, KEY_DESCRIPTION, IS_ACTIVE) VALUES
(7, 'Product', 'Product or service category', 'Y');
INSERT INTO KEY_CONFIGURATION (KEY_ID, KEY_NAME, KEY_DESCRIPTION, IS_ACTIVE) VALUES
(8, 'Sub-Product', 'Sub-category of the product', 'Y');
INSERT INTO KEY_CONFIGURATION (KEY_ID, KEY_NAME, KEY_DESCRIPTION, IS_ACTIVE) VALUES
(9, 'Client Segment', 'Client classification (Retail, Corporate, etc.)', 'Y');
INSERT INTO KEY_CONFIGURATION (KEY_ID, KEY_NAME, KEY_DESCRIPTION, IS_ACTIVE) VALUES
(10, 'Risk Rating', 'Risk classification level', 'Y');
INSERT INTO KEY_CONFIGURATION (KEY_ID, KEY_NAME, KEY_DESCRIPTION, IS_ACTIVE) VALUES
(11, 'Channel', 'Transaction channel (Online, Branch, ATM)', 'Y');
INSERT INTO KEY_CONFIGURATION (KEY_ID, KEY_NAME, KEY_DESCRIPTION, IS_ACTIVE) VALUES
(12, 'Officer', 'Assigned relationship officer', 'Y');
INSERT INTO KEY_CONFIGURATION (KEY_ID, KEY_NAME, KEY_DESCRIPTION, IS_ACTIVE) VALUES
(13, 'Portfolio', 'Investment portfolio identifier', 'N');
INSERT INTO KEY_CONFIGURATION (KEY_ID, KEY_NAME, KEY_DESCRIPTION, IS_ACTIVE) VALUES
(14, 'Counterparty', 'Trading counterparty reference', 'N');
INSERT INTO KEY_CONFIGURATION (KEY_ID, KEY_NAME, KEY_DESCRIPTION, IS_ACTIVE) VALUES
(15, 'GL Code', 'General ledger account code', 'N');
INSERT INTO KEY_CONFIGURATION (KEY_ID, KEY_NAME, KEY_DESCRIPTION, IS_ACTIVE) VALUES
(16, 'Custom Field', 'Reserved for future use', 'N');

COMMIT;
