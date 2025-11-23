"""
Transformation DAG - dbt + Soda data quality pipeline
Orchestrates transformations from Bronze → Silver → Gold with data quality checks
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
import subprocess

default_args = {
    'owner': 'lakehouse',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def run_soda_scan(layer: str, **context):
    """Run Soda data quality scans for a specific layer"""
    print(f"Running Soda scan for {layer} layer")
    
    # Run Soda scan
    result = subprocess.run(
        [
            'soda', 'scan',
            '-d', 'lakehouse',
            '-c', '/opt/airflow/dags/repo/soda/configuration.yml',
            f'/opt/airflow/dags/repo/soda/checks/{layer}/'
        ],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    
    if result.returncode != 0:
        print(f"Soda scan failed for {layer} layer:")
        print(result.stderr)
        raise Exception(f"Soda scan failed for {layer} layer")
    
    return f"Soda scan completed for {layer}"

with DAG(
    'lakehouse_transformation',
    default_args=default_args,
    description='Transform data through medallion layers with dbt and Soda',
    schedule_interval='0 4 * * *',  # Daily at 4 AM (after ingestion)
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['lakehouse', 'transformation', 'dbt', 'soda'],
) as dag:
    
    # Bronze layer quality checks
    with TaskGroup('bronze_layer') as bronze_layer:
        bronze_quality = PythonOperator(
            task_id='soda_scan_bronze',
            python_callable=run_soda_scan,
            op_kwargs={'layer': 'bronze'},
            provide_context=True,
        )
    
    # Silver layer transformations and quality checks
    with TaskGroup('silver_layer') as silver_layer:
        dbt_run_silver = BashOperator(
            task_id='dbt_run_silver',
            bash_command='cd /opt/airflow/dags/repo/dbt && dbt run --models silver --profiles-dir .',
        )
        
        dbt_test_silver = BashOperator(
            task_id='dbt_test_silver',
            bash_command='cd /opt/airflow/dags/repo/dbt && dbt test --models silver --profiles-dir .',
        )
        
        silver_quality = PythonOperator(
            task_id='soda_scan_silver',
            python_callable=run_soda_scan,
            op_kwargs={'layer': 'silver'},
            provide_context=True,
        )
        
        dbt_run_silver >> dbt_test_silver >> silver_quality
    
    # Gold layer transformations and quality checks
    with TaskGroup('gold_layer') as gold_layer:
        dbt_run_gold = BashOperator(
            task_id='dbt_run_gold',
            bash_command='cd /opt/airflow/dags/repo/dbt && dbt run --models gold --profiles-dir .',
        )
        
        dbt_test_gold = BashOperator(
            task_id='dbt_test_gold',
            bash_command='cd /opt/airflow/dags/repo/dbt && dbt test --models gold --profiles-dir .',
        )
        
        gold_quality = PythonOperator(
            task_id='soda_scan_gold',
            python_callable=run_soda_scan,
            op_kwargs={'layer': 'gold'},
            provide_context=True,
        )
        
        dbt_run_gold >> dbt_test_gold >> gold_quality
    
    # Generate dbt documentation
    dbt_docs = BashOperator(
        task_id='dbt_docs_generate',
        bash_command='cd /opt/airflow/dags/repo/dbt && dbt docs generate --profiles-dir .',
    )
    
    # DAG flow: Bronze quality → Silver transformations → Gold transformations → Docs
    bronze_layer >> silver_layer >> gold_layer >> dbt_docs
