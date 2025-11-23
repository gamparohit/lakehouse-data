# Lakehouse Architecture

## Overview

This lakehouse implements a modern data architecture based on the **Medallion Architecture** pattern, using open-source tools deployed on Kubernetes.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Source Systems                            │
│  (Databases, APIs, Files, Streaming)                            │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ CDC/Batch Ingestion
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Airbyte                                 │
│              (Change Data Capture & Ingestion)                  │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Bronze Layer (MinIO)                        │
│  • Raw, immutable data from sources                             │
│  • Parquet format                                               │
│  • Append-only                                                  │
│  • Data Quality: Schema validation, freshness                   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ dbt + DuckDB
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Silver Layer (MinIO)                        │
│  • Cleansed, standardized data                                  │
│  • Deduplication                                                │
│  • Type conversions                                             │
│  • Data Quality: Completeness, uniqueness, referential integrity│
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ dbt + DuckDB
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Gold Layer (MinIO)                         │
│  • Business-ready aggregates                                    │
│  • Dimensions and facts                                         │
│  • Denormalized for analytics                                   │
│  • Data Quality: KPIs, business metrics                         │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              Analytics & BI Tools                                │
│  (Tableau, Looker, Jupyter, SQL Clients)                        │
└─────────────────────────────────────────────────────────────────┘

     Orchestration: Apache Airflow (KubernetesExecutor)
     Data Quality: Soda Core
     Transformations: dbt
     Compute: DuckDB (embedded in Airflow tasks)
     Metadata: PostgreSQL (shared, schema-isolated)
```

## Component Responsibilities

### Bronze Layer
- **Purpose**: Single source of truth for raw data
- **Operations**: Ingestion via Airbyte
- **Storage**: MinIO `bronze` bucket
- **Format**: Parquet files
- **Data Quality**: Schema validation, freshness checks
- **Retention**: Long-term (archived)

### Silver Layer
- **Purpose**: Cleaned and conformed data
- **Operations**: dbt transformations
- **Storage**: MinIO `silver` bucket
- **Format**: Parquet files (partitioned)
- **Data Quality**: Completeness, uniqueness, referential integrity
- **Key Processes**:
  - Deduplication
  - Standardization (lowercase emails, phone formatting)
  - Type conversions
  - Basic business rules

### Gold Layer
- **Purpose**: Analytics-ready datasets
- **Operations**: dbt aggregations and denormalization
- **Storage**: MinIO `gold` bucket
- **Format**: Parquet files (star schema)
- **Data Quality**: KPI validation, business metrics
- **Key Processes**:
  - Customer segmentation
  - Aggregations and rollups
  - Fact and dimension tables
  - Running totals and window functions

## Data Flow

1. **Ingestion** (Daily 2 AM)
   - Airbyte syncs data from source systems
   - Data lands in Bronze layer as Parquet
   - Soda validates schema and freshness

2. **Transformation** (Daily 4 AM)
   - dbt runs Bronze → Silver transformations
   - dbt tests validate Silver layer
   - Soda runs quality checks on Silver
   - dbt runs Silver → Gold transformations
   - dbt tests validate Gold layer
   - Soda runs KPI checks on Gold

3. **Consumption** (Continuous)
   - BI tools query Gold layer via DuckDB
   - Data scientists access all layers
   - Analysts use pre-built Gold tables

## Scalability

### Compute Scaling
- **Airflow KubernetesExecutor**: Each task runs in its own pod
- **DuckDB**: Embedded in each task pod, scales horizontally
- **Auto-scaling**: Kubernetes HPA based on Airflow queue depth

### Storage Scaling
- **MinIO**: Distributed mode for production
- **Partitioning**: Date-based partitioning for large datasets
- **Format**: Parquet with compression (Snappy/ZSTD)

### Data Growth Strategy
- **Bronze**: Archive old data to cheaper storage after 90 days
- **Silver**: Partition by date, maintain 1 year hot data
- **Gold**: Aggregate to higher granularity for historical data

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Orchestration | Apache Airflow | Workflow scheduling and monitoring |
| Ingestion | Airbyte | CDC and batch data ingestion |
| Transformation | dbt | SQL-based transformations |
| Compute | DuckDB | Analytical query engine |
| Storage | MinIO | S3-compatible object storage |
| Metadata | PostgreSQL | Shared metadata database |
| Data Quality | Soda Core | Data quality validation |
| Container Orchestration | Kubernetes | Infrastructure management |
| Package Management | Helm | Application deployment |

## Security Considerations

1. **Access Control**:
   - MinIO bucket policies
   - Kubernetes RBAC
   - Airflow role-based access

2. **Data Encryption**:
   - In-transit: TLS for all services
   - At-rest: MinIO server-side encryption

3. **Secrets Management**:
   - Kubernetes Secrets for credentials
   - External secrets operator for production

4. **Network Isolation**:
   - Kubernetes NetworkPolicies
   - Service mesh (future consideration)
