# Balance Transfer Application

Full-stack balance transfer application with Oracle database, Spring Boot API, Angular + AG Grid frontend, and Apache Superset reporting dashboards.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│   Angular   │────▶│  Spring Boot │────▶│   Oracle XE   │
│  + AG Grid  │     │     API      │     │   (XEPDB1)    │
│  port:4200  │     │  port:8080   │     │  port:1521    │
└─────────────┘     └──────┬───────┘     └───────────────┘
                           │                      ▲
                           ▼                      │
                    ┌──────────────┐     ┌───────────────┐
                    │    Redis     │     │   Superset    │
                    │  port:6379   │     │  port:8088    │
                    │  DB0:Spring  │     │  Dashboards   │
                    │  DB1:Superset│     └───────────────┘
                    └──────────────┘
```

## Quick Start

```bash
cd docker
docker-compose up -d
```

Wait for Oracle XE to become healthy (~2-3 minutes on first run), then access:

| Service    | URL                        | Credentials        |
|------------|----------------------------|--------------------|
| Frontend   | http://localhost:4200       | N/A                |
| Backend    | http://localhost:8080       | N/A                |
| Superset   | http://localhost:8088       | admin / admin      |
| Oracle     | localhost:1521/XEPDB1       | system / oracle    |
| Redis      | localhost:6379              | N/A                |

## Project Structure

```
├── backend/                    Spring Boot API (Java 17, Maven)
│   ├── src/main/java/         Application source
│   ├── src/main/resources/    Configuration (application.yml)
│   ├── Dockerfile             Multi-stage build
│   └── pom.xml                Dependencies
├── frontend/                   Angular 17 + AG Grid
│   ├── src/app/               Components, services, routes
│   ├── Dockerfile             Multi-stage build with Nginx
│   └── package.json           Dependencies
├── db/                         Oracle database scripts
│   ├── 01_create_schema.sql   Table definitions
│   ├── 02_seed_key_configuration.sql  Key name mappings
│   └── 03_seed_daily_balances.sql     Sample balance data
└── docker/                     Docker Compose & Superset config
    ├── docker-compose.yml     All services orchestration
    └── superset/              Superset configuration
        ├── docker-init.sh     Bootstrap script
        ├── superset_config.py Config with Redis caching
        ├── datasource-config.py  Oracle datasource + datasets
        └── dashboards/        Pre-built dashboard exports
```

## Database Schema

### DAILY_BALANCES Table
Stores daily balance amounts identified by up to 16 configurable keys:
- `KEY_1` through `KEY_16` — Configurable identifier columns
- `BALANCE_YEAR`, `BALANCE_MONTH` — Time period
- `DAY_0_BALANCE` — Previous month-end balance
- `DAY_1_BALANCE` through `DAY_31_BALANCE` — Daily balances

### KEY_CONFIGURATION Table
Maps key positions (1-16) to human-readable names:
- `KEY_ID` — Position (1-16)
- `KEY_NAME` — Display name (e.g., "Address", "Account Type")
- `IS_ACTIVE` — Whether the key is currently in use

## Backend API

| Endpoint                              | Method | Description                    |
|---------------------------------------|--------|--------------------------------|
| `/api/balances`                       | GET    | All balance records            |
| `/api/balances/by-address/{addr}`     | GET    | Filter by address              |
| `/api/balances/by-period/{y}/{m}`     | GET    | Filter by year/month           |
| `/api/balances/filter`                | GET    | Multi-criteria filter          |
| `/api/balances/addresses`             | GET    | Distinct address list          |
| `/api/balances/years`                 | GET    | Distinct year list             |
| `/api/keys`                           | GET    | All key configurations         |
| `/api/keys/active`                    | GET    | Active keys only               |

## Reporting with Superset

### Access
- **URL**: http://localhost:8088
- **Credentials**: admin / admin

### Pre-configured Dashboards

The "Balance Rollup & Transfer Reporting" dashboard includes:

1. **Pivot Table** — "Balance Grid by Address & Month"
   - Rows = Address, Columns = Day0–Day31
   - Filterable by month/year and any of the 16 keys

2. **Bar Chart** — "Monthly Total Balances by Address"
   - X-axis = Month, Y-axis = Total balance, grouped by address

3. **Line Chart** — "Balance Trend Over 12 Months"
   - One line per address showing monthly totals across Jan–Dec

4. **Table** — "Detailed Balance View"
   - Full table with all 16 keys and all day columns
   - Pagination and search enabled

5. **Global Filters**
   - Address (KEY_1), Year, Month
   - Account Type (KEY_2), Currency (KEY_3), Region (KEY_4), Branch (KEY_5)

### Pre-configured Datasets

| Dataset Name                    | Description                                    |
|---------------------------------|------------------------------------------------|
| Balance Rollup by Address       | Aggregated by address with daily + month totals|
| Balance Rollup by All 16 Keys   | Full detail view with all keys and days        |
| Monthly Trend by Address        | Monthly totals for trend visualization         |

### Modifying Dashboards

1. Log into Superset at http://localhost:8088
2. Navigate to **Dashboards** → "Balance Rollup & Transfer Reporting"
3. Click **Edit Dashboard** (pencil icon)
4. Drag and drop charts, resize, or add new ones
5. Save when done

### Adding New Charts or Datasets

1. Go to **SQL Lab** → **SQL Editor**
2. Select "OracleBalanceDB" database
3. Write your query and save as a dataset
4. Go to **Charts** → **+ Chart** → select your dataset
5. Choose a chart type and configure

### Updating Datasets When Key Names Change

When key names change in `KEY_CONFIGURATION`:

1. Update column aliases in `/docker/superset/datasource-config.py`
2. Rebuild the Superset container:
   ```bash
   docker-compose up -d --build superset
   ```
3. Or manually edit datasets in Superset UI under **Datasets** → edit SQL

### Caching

Superset uses the shared Redis instance on **DB 1** (Spring Boot uses DB 0):
- Query results cached for 5 minutes
- Filter state cached for 10 minutes
- Avoids conflicts with the application cache

## Development

### Backend (Spring Boot)
```bash
cd backend
./mvnw spring-boot:run
```

### Frontend (Angular)
```bash
cd frontend
npm install
npm start
```
Access at http://localhost:4200

### Docker (full stack)
```bash
cd docker
docker-compose up -d --build
```

## Configuration

Key environment variables (set in docker-compose.yml):

| Variable                          | Default                                    | Service   |
|-----------------------------------|--------------------------------------------|-----------|
| `SPRING_DATASOURCE_URL`           | jdbc:oracle:thin:@oracle-xe:1521/XEPDB1   | backend   |
| `SPRING_DATASOURCE_USERNAME`      | system                                     | backend   |
| `SPRING_DATASOURCE_PASSWORD`      | oracle                                     | backend   |
| `SPRING_DATA_REDIS_HOST`          | redis                                      | backend   |
| `SPRING_DATA_REDIS_DATABASE`      | 0                                          | backend   |
| `SUPERSET_SECRET_KEY`             | (change in production)                     | superset  |
| `ORACLE_PASSWORD`                 | oracle                                     | oracle-xe |
