"""00_setup: create the agentops_<env> catalog and its schemas via the SQL warehouse.

Usage: python schema_mgt/00_setup.py   (env: AGENTOPS_ENV, DATABRICKS_WAREHOUSE_ID, profile)
Re-runnable: every statement is CREATE ... IF NOT EXISTS.
"""
from insurance_automation.common.sql import run_sql

from agentops.config import load_config
from agentops.uc import SCHEMAS, setup_uc

if __name__ == '__main__':
    cfg = load_config()
    setup_uc(cfg.catalog, lambda stmt: run_sql(stmt, cfg.warehouse_id))
    print(f'ready: {cfg.catalog} with schemas {", ".join(SCHEMAS)}')
