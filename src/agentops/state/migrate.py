"""Idempotent SQL migrations, recorded in public.schema_migrations."""
from __future__ import annotations

from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / 'migrations'

_BOOKKEEPING = (
    'CREATE TABLE IF NOT EXISTS public.schema_migrations ('
    'version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())'
)


def migrate(conn, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply pending migrations in order, each in its own transaction. Returns new versions."""
    with conn.transaction():
        conn.execute(_BOOKKEEPING)
    done = {r[0] for r in conn.execute('SELECT version FROM public.schema_migrations').fetchall()}
    applied: list[str] = []
    for path in sorted(directory.glob('*.sql')):
        if path.stem in done:
            continue
        with conn.transaction():
            conn.execute(path.read_text())
            conn.execute('INSERT INTO public.schema_migrations (version) VALUES (%s)', (path.stem,))
        applied.append(path.stem)
    return applied
