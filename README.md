[![Run Tests](https://github.com/nithyaln/legacy-crm-migration/actions/workflows/test.yml/badge.svg)](https://github.com/nithyaln/legacy-crm-migration/actions/workflows/test.yml)

# Legacy CRM Migration

Migrates a messy, denormalized legacy CRM export into a validated star-schema
Postgres warehouse — with automated reconciliation to prove zero data loss
during transformation.

## Problem

Legacy system exports are rarely clean. This project simulates a realistic
scenario: a 2,150-row CSV export containing the kinds of issues a genuine
migration has to handle —

- **Inconsistent date formats** across rows (`2024-01-15`, `15/01/2024`, `01-15-2024`)
- **Inconsistent casing/naming** for region (`US`, `us`, `United States`)
- **Duplicate records** (150 rows deliberately duplicated, simulating a re-export or sync error)
- **Missing/null values** in status and other fields

The goal: land this into a clean, analytics-ready star schema, and *prove*
— not just assert — that the migration didn't silently lose or duplicate data.

## Architecture

```mermaid
flowchart LR
    A[raw_legacy_export.csv] --> B[clean and normalize]
    B --> C[dim_customer]
    B --> D[dim_region]
    B --> E[fact_orders]
    C --> F[reconcile.py]
    D --> F
    E --> F
    F --> G[Reconciliation Report]
```

**Target schema (star schema):**
- `dim_customer` — deduplicated customers, keyed by email
- `dim_region` — normalized region values (US, EMEA, APAC, Unknown)
- `fact_orders` — one row per order, referencing both dimensions, with a
  `source_record_id` column for traceability back to the original CSV row

## Data quality issues and how they were handled

| Issue | Handling |
|---|---|
| Mixed date formats | Parsed with `pandas.to_datetime(..., format="mixed")`; unparseable dates dropped and logged |
| Inconsistent region casing/naming | Normalized via explicit mapping (`us`/`United States` → `US`) |
| Inconsistent status casing/nulls | Normalized via mapping; missing values set to `Unknown` rather than dropped |
| Duplicate records | Deduplicated on `(email, date, amount, product)` composite key |
| Financial amounts | Stored as `NUMERIC(10,2)`, not float, to avoid rounding errors on money values |

## Reconciliation results

Every migration run is validated against the raw source data — row counts
and total dollar amounts must match (within a $1 floating-point tolerance)
between source and target, or the run is flagged as a failure.

```
==================================================
RECONCILIATION REPORT
==================================================
Raw source rows (incl. duplicates):     2150
Expected unique rows after cleaning:    1998
Rows actually migrated:                 1998
Row count difference:                   0

Expected total amount (source, dedup'd): 5,012,340.55
Migrated total amount (warehouse):       5,012,340.55
Amount discrepancy:                      0.00

RESULT: PASS
==================================================
```

## Tech stack

- **Python** — pandas for cleaning/transformation, SQLAlchemy for database access
- **PostgreSQL** (hosted on [Neon](https://neon.tech)) — target warehouse
- **pytest** — unit tests on cleaning logic
- **GitHub Actions** — CI, runs the full test suite on every push

## Running it yourself

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create a .env file with your own Postgres connection string:
# DATABASE_URL=postgresql://user:pass@host/dbname

python3 generate_legacy_data.py   # generates data/raw_legacy_export.csv
python3 migrate.py                # cleans and loads into Postgres
python3 reconcile.py              # validates the migration
pytest -v                         # runs unit tests
```

## What I'd do differently in production

- Use a proper orchestrator (Airflow/Dagster) rather than a linear script,
  with retry logic and per-stage checkpointing
- Load in batches rather than row-by-row inserts, for performance at scale
- Add schema versioning/migrations (e.g. Alembic) rather than a single static `schema.sql`
- Add logging to a structured log store instead of `print()` statements

## Lessons learned

- **CI Python version must match your dependency lock file.** A `pip freeze`-generated
  `requirements.txt` can pin transitive dependencies (like `numpy`, pulled in by `pandas`)
  to versions that require a newer Python than what's specified in CI, causing installs
  to fail even though everything works locally. Fixed by aligning the CI workflow's
  Python version to match the environment the lock file was generated from.
- **Avoid creating database connections at import time.** Originally `migrate.py` created
  its SQLAlchemy engine as a module-level variable, which meant simply importing the
  `clean()` function for unit testing triggered a live database connection attempt — and
  failed in CI, where no `.env` file exists. Fixed by lazy-loading the engine inside a
  `get_engine()` function, so tests can exercise pure logic without needing live
  infrastructure.