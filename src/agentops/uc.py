"""Create the Unity Catalog catalog and schemas. Idempotent."""
from __future__ import annotations

from collections.abc import Callable

SCHEMAS = ('redteam', 'judging', 'release', 'monitoring', 'improve', 'state', 'prompts')


def setup_statements(catalog: str) -> list[str]:
    return [f'CREATE CATALOG IF NOT EXISTS {catalog}'] + [
        f'CREATE SCHEMA IF NOT EXISTS {catalog}.{s}' for s in SCHEMAS]


def setup_uc(catalog: str, run: Callable[[str], object]) -> list[str]:
    stmts = setup_statements(catalog)
    for s in stmts:
        run(s)
    return stmts
