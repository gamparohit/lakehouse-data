# Lakehouse Data Pipelines

Data pipeline repository containing SQL transformations, data quality checks, and DAG definitions for the lakehouse.

## Overview

This repository contains the "T" in ELT:
- **Airbyte configurations**: Source/destination connections for CDC and data ingestion
- **dbt models**: SQL transformations implementing medallion architecture (Bronze → Silver → Gold)
- **Soda checks**: Data quality validation at each layer
- **Airflow DAGs**: Orchestration workflows that tie everything together

## Medallion Architecture

### Bronze Layer (Raw Data)
- Raw, immutable data ingested from sources via Airbyte
- Stored as Parquet files in MinIO `bronze` bucket
- Minimal transformations, append-only
- dbt sources defined here

### Silver Layer (Cleansed Data)
- Cleaned, standardized, and deduplicated data
- Data type conversions and basic transformations
- Stored in MinIO `silver` bucket
- dbt models with basic tests (unique, not_null, relationships)
- Soda checks for data quality

### Gold Layer (Business-Ready Data)
- Aggregated, denormalized data ready for analytics
- Dimension and fact tables
- Stored in MinIO `gold` bucket
- dbt models with business logic
- Soda checks for KPIs and business metrics

## Directory Structure

```
lakehouse-data/
├── README.md
├── airbyte/                      # Airbyte connection configs
│   ├── connections/
│   └── README.md
├── dbt/                          # dbt project
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/
│   │   ├── bronze/              # Raw data models
│   │   ├── silver/              # Cleansed data models
│   │   └── gold/                # Business-ready models
│   └── tests/                   # Custom dbt tests
├── soda/                        # Soda Core data quality
│   ├── configuration.yml
│   └── checks/
│       ├── bronze/
│       ├── silver/
│       └── gold/
├── airflow/                     # Airflow DAGs
│   └── dags/
│       ├── ingestion_dag.py
│       ├── transformation_dag.py
│       └── utils/
└── docs/                        # Documentation
    ├── architecture.md
    └── development-guide.md
```

## Development Setup

### Prerequisites
- Python 3.11+
- DuckDB CLI
- dbt CLI
- Soda Core

### Install Dependencies

```bash
pip install dbt-core dbt-duckdb soda-core soda-core-duckdb
```

### Configure dbt Profile

Edit `dbt/profiles.yml` to point to your local or remote DuckDB instance:

```yaml
lakehouse:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: /path/to/local/lakehouse.duckdb
```

### Run dbt Models

```bash
cd dbt
dbt deps
dbt run
dbt test
```

### Run Soda Checks

```bash
cd soda
soda scan -d duckdb -c configuration.yml checks/bronze/
```

## Deploying to Airflow

Airflow is configured with git-sync to automatically pull DAGs from this repository.

1. Push changes to the `main` branch
2. Airflow will sync DAGs within 60 seconds
3. Trigger DAGs from the Airflow UI

## Data Pipeline Flow

```
Source System
    ↓
Airbyte (CDC/Ingestion)
    ↓
Bronze Layer (MinIO)
    ↓
dbt + Soda (Clean + Validate)
    ↓
Silver Layer (MinIO)
    ↓
dbt + Soda (Transform + Validate)
    ↓
Gold Layer (MinIO)
    ↓
Analytics/BI Tools
```

## Testing Locally

See [docs/development-guide.md](docs/development-guide.md) for detailed instructions on:
- Setting up a local DuckDB database
- Running dbt models locally
- Testing Soda checks
- Validating Airflow DAGs before deployment
