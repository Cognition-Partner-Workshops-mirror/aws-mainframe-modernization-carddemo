#!/bin/bash
# ============================================================
# Superset Bootstrap Script
# Initializes Superset, creates admin user, installs Oracle driver,
# registers Oracle datasource, imports dashboards, and starts server.
# ============================================================

set -e

echo "=== Step 1: Upgrading Superset metadata database ==="
superset db upgrade

echo "=== Step 2: Creating admin user ==="
superset fab create-admin \
  --username admin \
  --firstname Admin \
  --lastname User \
  --email admin@local.com \
  --password admin || true

echo "=== Step 3: Initializing Superset ==="
superset init

echo "=== Step 4: Installing Oracle DB driver (oracledb) ==="
pip install oracledb --quiet

echo "=== Step 5: Registering Oracle datasource and creating datasets ==="
python /app/datasource-config.py

echo "=== Step 6: Importing pre-built dashboards ==="
# Import dashboard if the export file exists
if [ -f /app/dashboards/balance_rollup_dashboard.json ]; then
  echo "Dashboard export found, importing..."
  superset import-dashboards -p /app/dashboards/balance_rollup_dashboard.json || \
    echo "Dashboard import via CLI failed, will create programmatically..."
fi

echo "=== Step 7: Starting Superset ==="
superset run -h 0.0.0.0 -p 8088 --with-threads --reload
