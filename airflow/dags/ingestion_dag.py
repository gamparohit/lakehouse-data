"""
Ingestion DAG - Trigger Airbyte sync jobs
Runs daily to sync data from source systems to Bronze layer
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.airbyte.operators.airbyte import AirbyteTriggerSyncOperator
from airflow.providers.airbyte.sensors.airbyte import AirbyteJobSensor
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'lakehouse',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

def log_ingestion_start(**context):
    """Log the start of ingestion process"""
    print(f"Starting ingestion for execution date: {context['ds']}")
    return "Ingestion started"

def log_ingestion_complete(**context):
    """Log the completion of ingestion"""
    print(f"Ingestion completed successfully for {context['ds']}")
    return "Ingestion complete"

with DAG(
    'lakehouse_ingestion',
    default_args=default_args,
    description='Ingest data from sources via Airbyte to Bronze layer',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['lakehouse', 'ingestion', 'bronze'],
) as dag:
    
    start_task = PythonOperator(
        task_id='log_start',
        python_callable=log_ingestion_start,
        provide_context=True,
    )
    
    # Trigger Airbyte sync for customers
    # Note: Replace connection_id with actual Airbyte connection ID
    sync_customers = AirbyteTriggerSyncOperator(
        task_id='sync_customers',
        airbyte_conn_id='airbyte_default',
        connection_id='{{ var.value.airbyte_customers_connection_id }}',
        asynchronous=False,
        timeout=3600,
        wait_seconds=10,
    )
    
    # Trigger Airbyte sync for orders
    sync_orders = AirbyteTriggerSyncOperator(
        task_id='sync_orders',
        airbyte_conn_id='airbyte_default',
        connection_id='{{ var.value.airbyte_orders_connection_id }}',
        asynchronous=False,
        timeout=3600,
        wait_seconds=10,
    )
    
    # Trigger Airbyte sync for products
    sync_products = AirbyteTriggerSyncOperator(
        task_id='sync_products',
        airbyte_conn_id='airbyte_default',
        connection_id='{{ var.value.airbyte_products_connection_id }}',
        asynchronous=False,
        timeout=3600,
        wait_seconds=10,
    )
    
    end_task = PythonOperator(
        task_id='log_complete',
        python_callable=log_ingestion_complete,
        provide_context=True,
    )
    
    # DAG flow
    start_task >> [sync_customers, sync_orders, sync_products] >> end_task
