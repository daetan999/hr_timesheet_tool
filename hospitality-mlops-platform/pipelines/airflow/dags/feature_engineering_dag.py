"""Daily feature-engineering DAG (illustrative blueprint).

Rebuilds the three engineered feature families and materializes them into the
Feast online store. Connection IDs, warehouses, and schedules are placeholders —
no production configuration is represented.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

DEFAULT_ARGS = {
    "owner": "ml-platform",
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
    "sla": timedelta(hours=2),  # ingestion success SLO: >99.9% daily runs
}


def build_demand_lag_features(**ctx):
    """F_Demand_Lag — rolling ADR/occupancy at t-1/7/14/30 + OTB booking velocity.

    Runs as Spark SQL window functions over 90-day partitioned reservation
    tables in the offline store, then writes back a point-in-time-correct
    feature table for Feast materialization.
    """
    raise NotImplementedError("Blueprint stub — proprietary transformation omitted")


def build_climate_index_features(**ctx):
    """F_Climate_Index — CDD/HDD vs 18C base from localized weather APIs."""
    raise NotImplementedError("Blueprint stub — proprietary transformation omitted")


def materialize_to_online_store(**ctx):
    """feast materialize-incremental: offline (Snowflake) -> online (Redis).

    Freshness SLO: PMS state change visible in Redis within 5 minutes.
    """
    raise NotImplementedError("Blueprint stub — proprietary configuration omitted")


with DAG(
    dag_id="daily_feature_engineering",
    default_args=DEFAULT_ARGS,
    schedule_interval="0 2 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["features", "feast"],
) as dag:
    demand_lag = PythonOperator(
        task_id="build_demand_lag_features",
        python_callable=build_demand_lag_features,
    )
    climate_index = PythonOperator(
        task_id="build_climate_index_features",
        python_callable=build_climate_index_features,
    )
    materialize = PythonOperator(
        task_id="materialize_to_online_store",
        python_callable=materialize_to_online_store,
    )

    [demand_lag, climate_index] >> materialize
