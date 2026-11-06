"""Apply Lakebase migrations. Re-runnable: a second run prints `applied: none`."""
from __future__ import annotations

import argparse
import os

from agentops.config import load_config
from agentops.state.migrate import migrate
from agentops.state.pool import connect_with_retry, databricks_token_provider


def lakebase_conninfo(host: str, database: str, user: str) -> str:
    return f'host={host} dbname={database} user={user} sslmode=require'


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', default=None)
    args = ap.parse_args()
    cfg = load_config()
    profile = args.profile or cfg.profile
    host = os.environ['LAKEBASE_HOST']
    user = os.environ['LAKEBASE_USER']
    conn = connect_with_retry(lakebase_conninfo(host, cfg.lakebase_database, user),
                              databricks_token_provider(profile), autocommit=True)
    with conn:
        applied = migrate(conn)
    print('applied:', ', '.join(applied) if applied else 'none')


if __name__ == '__main__':
    main()
