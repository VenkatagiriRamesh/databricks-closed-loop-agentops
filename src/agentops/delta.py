"""Delta is the analytical record: small JSON-payload tables written through the SQL warehouse."""
from __future__ import annotations

import json
from collections.abc import Callable

Run = Callable[[str], object]


def _lit(text: str) -> str:
    return "'" + text.replace('\\', '\\\\').replace("'", "''") + "'"


def ensure_table(run: Run, table: str) -> None:
    run(f'CREATE TABLE IF NOT EXISTS {table} (key STRING, ts TIMESTAMP, payload STRING)')


def upsert_rows(run: Run, table: str, key: str, rows: list[dict]) -> None:
    """Replace everything under `key` (a run id or a date), so re-running a job is idempotent."""
    ensure_table(run, table)
    run(f'DELETE FROM {table} WHERE key = {_lit(key)}')
    if rows:
        values = ', '.join(f'({_lit(key)}, current_timestamp(), {_lit(json.dumps(r, default=str))})'
                           for r in rows)
        run(f'INSERT INTO {table} VALUES {values}')
