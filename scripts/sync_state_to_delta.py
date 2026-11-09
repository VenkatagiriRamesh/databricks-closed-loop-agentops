"""Copy the small Lakebase tables into Delta (agentops_<env>.state.*) for the dashboard."""
from __future__ import annotations

import datetime as dt
from collections.abc import Callable

from psycopg.rows import dict_row

from agentops.delta import upsert_rows

TABLES = {'release_candidates': 'SELECT * FROM release.candidates',
          'release_transitions': 'SELECT * FROM release.transitions',
          'release_approvals': 'SELECT * FROM release.approvals',
          'review_queue': 'SELECT * FROM review.queue',
          'runtime_flags': 'SELECT * FROM runtime.flags'}


def sync(pool, run: Callable[[str], object], catalog: str,
         key: str | None = None) -> dict[str, int]:
    """Full refresh of every table under one key: re-running replaces, never duplicates."""
    key = key or 'current'
    counts = {}
    with pool.connection() as conn:
        for name, query in TABLES.items():
            cur = conn.cursor(row_factory=dict_row)
            cur.execute(query)
            rows = cur.fetchall()
            upsert_rows(run, f'{catalog}.state.{name}', key, rows)
            counts[name] = len(rows)
    return counts


if __name__ == '__main__':
    from agentops.config import load_config
    from agentops.connect import lakebase_pool, sql_runner
    cfg = load_config()
    print(sync(lakebase_pool(cfg), sql_runner(cfg), cfg.catalog), dt.date.today())
