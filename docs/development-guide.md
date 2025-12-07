# Development Guide

Guide for developing and testing lakehouse data pipelines locally.

## Prerequisites

- Python 3.11+
- DuckDB CLI
- Docker Desktop (for local Kubernetes)
- kubectl
- Helm
- kind or minikube (for local K8s cluster)

## Local Development Setup

### 1. Install Python Dependencies

```bash
pip install \
  dbt-core==1.7.4 \
  dbt-duckdb==1.7.1 \
  soda-core==3.3.0 \
  soda-core-duckdb==3.3.0 \
  apache-airflow==2.8.0 \
  duckdb==0.9.2
```

### 2. Set Up Local Infrastructure

#### Option A: Full Local Kubernetes

```bash
# Create local cluster with kind
kind create cluster --name lakehouse

# Deploy infrastructure
cd lakehouse-infrastructure
./scripts/deploy-all.sh

# Port-forward services
kubectl port-forward svc/lakehouse-minio 9000:9000 -n lakehouse &
kubectl port-forward svc/lakehouse-postgres-postgresql 5432:5432 -n lakehouse &
kubectl port-forward svc/lakehouse-airflow-webserver 8080:8080 -n lakehouse &
```

#### Option B: Local DuckDB Only (for dbt development)

```bash
# Use local DuckDB with sample data
cd lakehouse-data/dbt

# Create sample local database
duckdb lakehouse_dev.duckdb
```

### 3. Configure dbt Profile

Edit `~/.dbt/profiles.yml` or use `dbt/profiles.yml`:

```yaml
lakehouse:
  target: local
  outputs:
    local:
      type: duckdb
      path: ./lakehouse_dev.duckdb
      extensions:
        - httpfs
        - parquet
      threads: 4
```

## Development Workflow

### dbt Development

#### 1. Make Changes to Models

```bash
cd lakehouse-data/dbt
```

Edit SQL files in `models/` directory.

#### 2. Run Specific Models

```bash
# Run a specific model
dbt run --models silver_customers

# Run models with dependencies
dbt run --models +silver_customers

# Run models and downstream
dbt run --models silver_customers+
```

#### 3. Test Models

```bash
# Test specific model
dbt test --models silver_customers

# Test all models in a directory
dbt test --models silver
```

#### 4. Generate Documentation

```bash
dbt docs generate
dbt docs serve
```

Open http://localhost:8080 to view documentation.

### Soda Development

#### 1. Edit Soda Checks

Edit YAML files in `soda/checks/` directory.

#### 2. Run Soda Scans

```bash
cd lakehouse-data/soda

# Scan specific layer
soda scan -d lakehouse -c configuration.yml checks/bronze/

# Scan all layers
soda scan -d lakehouse -c configuration.yml checks/
```

#### 3. View Results

Soda will output results to console. For production, integrate with Soda Cloud for dashboards.

### Airflow DAG Development

#### 1. Validate DAG Syntax

```bash
cd lakehouse-data

# Parse DAG file
python airflow/dags/transformation_dag.py

# List all DAGs
airflow dags list

# Test specific task
airflow tasks test lakehouse_transformation bronze_layer.soda_scan_bronze 2024-01-01
```

#### 2. Run DAG Locally

```bash
# Trigger DAG
airflow dags trigger lakehouse_transformation

# Check DAG status
airflow dags list-runs -d lakehouse_transformation
```

## Testing Best Practices

### Unit Testing dbt Models

Create custom tests in `dbt/tests/`:

```sql
-- tests/assert_positive_revenue.sql
SELECT *
FROM {{ ref('dim_customers') }}
WHERE lifetime_revenue < 0
```

### Integration Testing

1. **Create Sample Data**:
   ```sql
   -- dbt/seeds/sample_customers.csv
   customer_id,email,first_name,last_name
   1,john@example.com,John,Doe
   2,jane@example.com,Jane,Smith
   ```

2. **Run Pipeline**:
   ```bash
   dbt seed
   dbt run
   dbt test
   ```

### End-to-End Testing

1. Deploy to local Kubernetes
2. Ingest sample data to Bronze layer
3. Trigger transformation DAG
4. Verify data in Silver and Gold layers

## Debugging

### dbt Debugging

```bash
# Compile model without running
dbt compile --models silver_customers

# View compiled SQL
cat target/compiled/lakehouse/models/silver/silver_customers.sql

# Run in interactive mode
dbt run --models silver_customers --debug
```

### Soda Debugging

```bash
# Verbose output
soda scan -d lakehouse -c configuration.yml checks/bronze/ -V
```

### Airflow Debugging

```bash
# View task logs
airflow tasks logs lakehouse_transformation bronze_layer.soda_scan_bronze 2024-01-01

# Test task with verbose logging
airflow tasks test lakehouse_transformation bronze_layer.soda_scan_bronze 2024-01-01 -v
```

## Performance Optimization

### DuckDB Optimization

```sql
-- Use COPY for bulk loads
COPY bronze.customers FROM 's3://bronze/customers/*.parquet';

-- Create indexes (if using persistent database)
CREATE INDEX idx_customer_id ON silver_customers(customer_id);

-- Partition data
CREATE TABLE silver_orders_partitioned 
PARTITION BY (order_year, order_month)
AS SELECT * FROM silver_orders;
```

### dbt Optimization

```yaml
# Use incremental models for large tables
{{ config(materialized='incremental') }}

# Partition external tables
{{ config(
  materialized='external',
  location='s3://silver/orders',
  partition_by=['year', 'month']
) }}
```

## Common Issues

### Issue: dbt can't connect to S3/MinIO

**Solution**: Check S3 credentials and endpoint in `profiles.yml`:
```yaml
settings:
  s3_endpoint: 'localhost:9000'
  s3_access_key_id: 'lakehouse'
  s3_secret_access_key: 'lakehouse123'
```

### Issue: Soda scan fails with connection error

**Solution**: Verify DuckDB extensions are loaded:
```sql
INSTALL httpfs;
LOAD httpfs;
```

### Issue: Airflow DAG not showing up

**Solution**:
1. Check DAG syntax: `python airflow/dags/your_dag.py`
2. Verify DAG directory is correctly mounted
3. Check Airflow logs for import errors

## CI/CD Integration

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/mirrors-sqlfluff
    rev: v2.3.5
    hooks:
      - id: sqlfluff-lint
        files: \.sql$
        args: [--dialect, duckdb]
```

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Test dbt models
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dbt
        run: pip install dbt-duckdb
      - name: Run dbt tests
        run: |
          cd dbt
          dbt deps
          dbt seed
          dbt run
          dbt test
```
