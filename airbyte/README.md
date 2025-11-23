# Airbyte Connections Configuration

This directory contains configuration for Airbyte connections, sources, and destinations.

## Setup with Octavia CLI

Airbyte provides [Octavia CLI](https://docs.airbyte.com/using-airbyte/octavia), an Infrastructure-as-Code tool for managing Airbyte configurations.

### Install Octavia

```bash
pip install octavia-cli
```

### Initialize Octavia

```bash
octavia init
```

### Example: Create a Source

```bash
# List available source connectors
octavia list connectors sources

# Create a PostgreSQL source
octavia generate source postgres my-postgres-source \
  --host localhost \
  --port 5432 \
  --database mydb \
  --username postgres \
  --password secret
```

### Example: Create a Destination

```bash
# Create an S3 destination (MinIO)
octavia generate destination s3 bronze-layer \
  --s3_bucket_name bronze \
  --s3_bucket_path / \
  --s3_endpoint http://lakehouse-minio:9000 \
  --access_key_id lakehouse \
  --secret_access_key lakehouse123
```

### Example: Create a Connection

```bash
octavia generate connection my-postgres-to-bronze \
  --source my-postgres-source \
  --destination bronze-layer \
  --sync-mode full_refresh_append
```

### Apply Configurations

```bash
octavia apply
```

## Manual Configuration

Alternatively, you can configure connections via the Airbyte UI:

1. Access Airbyte UI: `kubectl port-forward svc/lakehouse-airbyte-webapp-svc 8000:80 -n lakehouse`
2. Navigate to http://localhost:8000
3. Create sources, destinations, and connections
4. Export connection IDs and add them as Airflow variables:
   ```bash
   airflow variables set airbyte_customers_connection_id <connection-id>
   ```

## Connection Patterns

### CDC with PostgreSQL

For Change Data Capture with PostgreSQL:
- Use Airbyte's PostgreSQL CDC connector
- Configure replication slot
- Sync mode: Incremental - Deduped History
- Destination: MinIO Bronze bucket as Parquet

### Full Refresh Sources

For sources without CDC:
- Sync mode: Full Refresh - Overwrite
- Schedule: Daily or as needed
- Destination: MinIO Bronze bucket as Parquet

## Best Practices

1. **Naming Convention**: Use descriptive names like `source-system_table-name`
2. **Normalization**: Disable Airbyte normalization (we handle this in dbt)
3. **Output Format**: Use Parquet for optimal DuckDB performance
4. **Partitioning**: Consider partitioning by date for large datasets
5. **Sync Frequency**: Align with business requirements (hourly, daily, etc.)
