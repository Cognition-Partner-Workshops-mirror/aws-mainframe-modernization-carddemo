"""
Superset Datasource Configuration Script
=========================================
Registers the Oracle database connection and creates virtual datasets
for balance rollup reporting. Uses the Superset REST API.

Datasets created:
1. "Balance Rollup by Address" - Aggregated by KEY_1 (Address), Year, Month
2. "Balance Rollup by All 16 Keys" - Full detail view with all keys
3. "Monthly Trend by Address" - Monthly totals for trend analysis

NOTE: When key names change in KEY_CONFIGURATION, update the column aliases
in the SQL queries below to match the new key names. Refer to the
KEY_CONFIGURATION table for current key-to-name mappings.
"""

import requests
import time
import sys

SUPERSET_URL = "http://localhost:8088"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

# Oracle connection string matching the docker-compose Oracle XE service
ORACLE_SQLALCHEMY_URI = "oracle+oracledb://system:oracle@oracle-xe:1521/XEPDB1"
DATABASE_NAME = "OracleBalanceDB"


def wait_for_superset():
    """Wait for Superset API to be available."""
    max_retries = 30
    for i in range(max_retries):
        try:
            resp = requests.get(f"{SUPERSET_URL}/health", timeout=5)
            if resp.status_code == 200:
                print("Superset is ready.")
                return True
        except requests.exceptions.ConnectionError:
            pass
        print(f"Waiting for Superset... ({i+1}/{max_retries})")
        time.sleep(2)
    print("ERROR: Superset did not become available.")
    return False


def get_auth_token():
    """Authenticate and get an access token from Superset."""
    payload = {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD,
        "provider": "db",
        "refresh": True
    }
    resp = requests.post(
        f"{SUPERSET_URL}/api/v1/security/login",
        json=payload,
        timeout=10
    )
    if resp.status_code == 200:
        return resp.json()["access_token"]
    print(f"Auth failed: {resp.status_code} - {resp.text}")
    sys.exit(1)


def get_csrf_token(headers):
    """Get CSRF token required for write operations."""
    resp = requests.get(
        f"{SUPERSET_URL}/api/v1/security/csrf_token/",
        headers=headers,
        timeout=10
    )
    if resp.status_code == 200:
        return resp.json()["result"]
    return None


def register_database(headers):
    """Register the Oracle database connection in Superset."""
    csrf = get_csrf_token(headers)
    if csrf:
        headers["X-CSRFToken"] = csrf
        headers["Referer"] = SUPERSET_URL

    payload = {
        "database_name": DATABASE_NAME,
        "sqlalchemy_uri": ORACLE_SQLALCHEMY_URI,
        "expose_in_sqllab": True,
        "allow_ctas": False,
        "allow_cvas": False,
        "allow_dml": False,
        "allow_run_async": True,
        "extra": '{"allows_virtual_table_explore": true}'
    }

    # Check if database already exists
    resp = requests.get(
        f"{SUPERSET_URL}/api/v1/database/",
        headers=headers,
        timeout=10
    )
    if resp.status_code == 200:
        databases = resp.json().get("result", [])
        for db in databases:
            if db.get("database_name") == DATABASE_NAME:
                print(f"Database '{DATABASE_NAME}' already registered (id={db['id']}).")
                return db["id"]

    # Create new database connection
    resp = requests.post(
        f"{SUPERSET_URL}/api/v1/database/",
        headers=headers,
        json=payload,
        timeout=30
    )
    if resp.status_code in (200, 201):
        db_id = resp.json()["id"]
        print(f"Database '{DATABASE_NAME}' registered successfully (id={db_id}).")
        return db_id
    else:
        print(f"Failed to register database: {resp.status_code} - {resp.text}")
        return None


def create_dataset(headers, db_id, dataset_name, sql):
    """Create a virtual dataset (saved query) in Superset."""
    csrf = get_csrf_token(headers)
    if csrf:
        headers["X-CSRFToken"] = csrf
        headers["Referer"] = SUPERSET_URL

    payload = {
        "database": db_id,
        "schema": "SYSTEM",
        "table_name": dataset_name,
        "sql": sql,
        "is_managed_externally": False
    }

    resp = requests.post(
        f"{SUPERSET_URL}/api/v1/dataset/",
        headers=headers,
        json=payload,
        timeout=30
    )
    if resp.status_code in (200, 201):
        ds_id = resp.json()["id"]
        print(f"Dataset '{dataset_name}' created (id={ds_id}).")
        return ds_id
    elif resp.status_code == 422:
        print(f"Dataset '{dataset_name}' may already exist, skipping.")
        return None
    else:
        print(f"Failed to create dataset '{dataset_name}': {resp.status_code} - {resp.text}")
        return None


def main():
    """Main setup flow: wait for API, authenticate, register DB, create datasets."""

    # Wait briefly for Superset's internal API to be ready
    # (called from docker-init.sh after superset init)
    time.sleep(5)

    if not wait_for_superset():
        print("Proceeding anyway - datasets may need manual creation.")
        sys.exit(0)

    token = get_auth_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Register Oracle database
    db_id = register_database(headers)
    if not db_id:
        print("Could not register database. Exiting.")
        sys.exit(1)

    # Dataset 1: Balance Rollup by Address
    # NOTE: KEY_1 is aliased as "ADDRESS" based on KEY_CONFIGURATION.
    # Update this alias if KEY_1's meaning changes in KEY_CONFIGURATION.
    sql_rollup_by_address = """
SELECT KEY_1 AS ADDRESS, BALANCE_YEAR, BALANCE_MONTH,
       SUM(DAY_0_BALANCE) AS PREV_MONTH_TOTAL,
       SUM(DAY_1_BALANCE) AS DAY_1, SUM(DAY_2_BALANCE) AS DAY_2,
       SUM(DAY_3_BALANCE) AS DAY_3, SUM(DAY_4_BALANCE) AS DAY_4,
       SUM(DAY_5_BALANCE) AS DAY_5, SUM(DAY_6_BALANCE) AS DAY_6,
       SUM(DAY_7_BALANCE) AS DAY_7, SUM(DAY_8_BALANCE) AS DAY_8,
       SUM(DAY_9_BALANCE) AS DAY_9, SUM(DAY_10_BALANCE) AS DAY_10,
       SUM(DAY_11_BALANCE) AS DAY_11, SUM(DAY_12_BALANCE) AS DAY_12,
       SUM(DAY_13_BALANCE) AS DAY_13, SUM(DAY_14_BALANCE) AS DAY_14,
       SUM(DAY_15_BALANCE) AS DAY_15, SUM(DAY_16_BALANCE) AS DAY_16,
       SUM(DAY_17_BALANCE) AS DAY_17, SUM(DAY_18_BALANCE) AS DAY_18,
       SUM(DAY_19_BALANCE) AS DAY_19, SUM(DAY_20_BALANCE) AS DAY_20,
       SUM(DAY_21_BALANCE) AS DAY_21, SUM(DAY_22_BALANCE) AS DAY_22,
       SUM(DAY_23_BALANCE) AS DAY_23, SUM(DAY_24_BALANCE) AS DAY_24,
       SUM(DAY_25_BALANCE) AS DAY_25, SUM(DAY_26_BALANCE) AS DAY_26,
       SUM(DAY_27_BALANCE) AS DAY_27, SUM(DAY_28_BALANCE) AS DAY_28,
       SUM(DAY_29_BALANCE) AS DAY_29, SUM(DAY_30_BALANCE) AS DAY_30,
       SUM(DAY_31_BALANCE) AS DAY_31,
       SUM(DAY_1_BALANCE + DAY_2_BALANCE + DAY_3_BALANCE + DAY_4_BALANCE +
           DAY_5_BALANCE + DAY_6_BALANCE + DAY_7_BALANCE + DAY_8_BALANCE +
           DAY_9_BALANCE + DAY_10_BALANCE + DAY_11_BALANCE + DAY_12_BALANCE +
           DAY_13_BALANCE + DAY_14_BALANCE + DAY_15_BALANCE + DAY_16_BALANCE +
           DAY_17_BALANCE + DAY_18_BALANCE + DAY_19_BALANCE + DAY_20_BALANCE +
           DAY_21_BALANCE + DAY_22_BALANCE + DAY_23_BALANCE + DAY_24_BALANCE +
           DAY_25_BALANCE + DAY_26_BALANCE + DAY_27_BALANCE + DAY_28_BALANCE +
           DAY_29_BALANCE + DAY_30_BALANCE + DAY_31_BALANCE) AS MONTH_TOTAL
FROM DAILY_BALANCES
GROUP BY KEY_1, BALANCE_YEAR, BALANCE_MONTH
ORDER BY KEY_1, BALANCE_YEAR, BALANCE_MONTH
""".strip()

    # Dataset 2: Balance Rollup by All 16 Keys (full detail view)
    # All KEY columns retain their positional names; refer to KEY_CONFIGURATION
    # for human-readable labels when building charts.
    sql_all_keys = """
SELECT KEY_1, KEY_2, KEY_3, KEY_4, KEY_5, KEY_6, KEY_7, KEY_8,
       KEY_9, KEY_10, KEY_11, KEY_12, KEY_13, KEY_14, KEY_15, KEY_16,
       BALANCE_YEAR, BALANCE_MONTH,
       DAY_0_BALANCE, DAY_1_BALANCE, DAY_2_BALANCE, DAY_3_BALANCE,
       DAY_4_BALANCE, DAY_5_BALANCE, DAY_6_BALANCE, DAY_7_BALANCE,
       DAY_8_BALANCE, DAY_9_BALANCE, DAY_10_BALANCE, DAY_11_BALANCE,
       DAY_12_BALANCE, DAY_13_BALANCE, DAY_14_BALANCE, DAY_15_BALANCE,
       DAY_16_BALANCE, DAY_17_BALANCE, DAY_18_BALANCE, DAY_19_BALANCE,
       DAY_20_BALANCE, DAY_21_BALANCE, DAY_22_BALANCE, DAY_23_BALANCE,
       DAY_24_BALANCE, DAY_25_BALANCE, DAY_26_BALANCE, DAY_27_BALANCE,
       DAY_28_BALANCE, DAY_29_BALANCE, DAY_30_BALANCE, DAY_31_BALANCE
FROM DAILY_BALANCES
""".strip()

    # Dataset 3: Monthly Trend by Address
    # Used for line charts showing balance trends over months.
    sql_monthly_trend = """
SELECT KEY_1 AS ADDRESS, BALANCE_YEAR, BALANCE_MONTH,
       SUM(DAY_1_BALANCE + DAY_2_BALANCE + DAY_3_BALANCE + DAY_4_BALANCE +
           DAY_5_BALANCE + DAY_6_BALANCE + DAY_7_BALANCE + DAY_8_BALANCE +
           DAY_9_BALANCE + DAY_10_BALANCE + DAY_11_BALANCE + DAY_12_BALANCE +
           DAY_13_BALANCE + DAY_14_BALANCE + DAY_15_BALANCE + DAY_16_BALANCE +
           DAY_17_BALANCE + DAY_18_BALANCE + DAY_19_BALANCE + DAY_20_BALANCE +
           DAY_21_BALANCE + DAY_22_BALANCE + DAY_23_BALANCE + DAY_24_BALANCE +
           DAY_25_BALANCE + DAY_26_BALANCE + DAY_27_BALANCE + DAY_28_BALANCE +
           DAY_29_BALANCE + DAY_30_BALANCE + DAY_31_BALANCE) AS MONTH_TOTAL
FROM DAILY_BALANCES
GROUP BY KEY_1, BALANCE_YEAR, BALANCE_MONTH
ORDER BY BALANCE_YEAR, BALANCE_MONTH
""".strip()

    # Create all three datasets
    create_dataset(headers, db_id, "Balance Rollup by Address", sql_rollup_by_address)
    create_dataset(headers, db_id, "Balance Rollup by All 16 Keys", sql_all_keys)
    create_dataset(headers, db_id, "Monthly Trend by Address", sql_monthly_trend)

    print("\n=== Datasource configuration complete ===")


if __name__ == "__main__":
    main()
