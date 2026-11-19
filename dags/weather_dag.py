from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from src.etl import run_etl

with DAG(
    dag_id="weather_daily",
    start_date=datetime(2026, 11, 16),
    schedule="@daily",
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
) as dag:
    PythonOperator(task_id="run_etl", python_callable=run_etl)

