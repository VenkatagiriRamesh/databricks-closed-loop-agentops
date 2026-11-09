"""Wiring helpers: SQL runner, Lakebase pool, reports directory. The only env readers."""
from __future__ import annotations

import os
from pathlib import Path

from agentops.config import AgentOpsConfig


def reports_dir() -> Path:
    p = Path(os.environ.get('REPORTS_DIR', 'reports'))
    p.mkdir(parents=True, exist_ok=True)
    return p


def sql_runner(cfg: AgentOpsConfig):
    from insurance_automation.common.sql import run_sql
    return lambda stmt: run_sql(stmt, cfg.warehouse_id)


def lakebase_conninfo(cfg: AgentOpsConfig) -> str:
    host, user = os.environ['LAKEBASE_HOST'], os.environ['LAKEBASE_USER']
    return f'host={host} dbname={cfg.lakebase_database} user={user} sslmode=require'


def lakebase_pool(cfg: AgentOpsConfig):
    from agentops.state.pool import databricks_token_provider, make_pool
    return make_pool(lakebase_conninfo(cfg), databricks_token_provider(cfg.profile))


def mlflow_client():
    import mlflow
    mlflow.set_registry_uri('databricks-uc')
    return mlflow.MlflowClient()
