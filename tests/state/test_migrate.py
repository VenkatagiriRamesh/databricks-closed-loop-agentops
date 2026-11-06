import psycopg
import pytest

from agentops.state.migrate import MIGRATIONS_DIR, migrate


def test_migration_files_are_ordered_and_present():
    names = [p.stem for p in sorted(MIGRATIONS_DIR.glob('*.sql'))]
    assert names == ['001_release', '002_review', '003_runtime']


@pytest.mark.pg
def test_migrate_idempotent(pg_dsn):
    with psycopg.connect(pg_dsn, autocommit=True) as conn:
        for schema in ('release', 'review', 'runtime'):
            conn.execute(f'DROP SCHEMA IF EXISTS {schema} CASCADE')
        conn.execute('DROP TABLE IF EXISTS public.schema_migrations')
        assert migrate(conn) == ['001_release', '002_review', '003_runtime']
        assert migrate(conn) == []


@pytest.mark.pg
def test_flags_mode_check_constraint(pg_dsn):
    with psycopg.connect(pg_dsn, autocommit=True) as conn:
        migrate(conn)
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute("INSERT INTO runtime.flags (agent, mode) VALUES ('a', 'off')")
