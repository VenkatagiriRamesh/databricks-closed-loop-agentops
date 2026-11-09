import pytest
from psycopg_pool import ConnectionPool
from scripts.sync_state_to_delta import sync

from agentops.state.migrate import migrate


@pytest.mark.pg
def test_sync_state_full_refresh_idempotent(pg_dsn):
    pool = ConnectionPool(pg_dsn, kwargs={'autocommit': True}, min_size=1, max_size=2, open=True)
    with pool.connection() as c:
        migrate(c)
        c.execute("INSERT INTO runtime.flags (agent, mode) VALUES ('t', 'safe') "
                  "ON CONFLICT (agent) DO UPDATE SET mode = 'safe'")
    sql = []
    first = sync(pool, sql.append, 'agentops_dev')
    n = len(sql)
    second = sync(pool, sql.append, 'agentops_dev')
    assert first == second and first['runtime_flags'] >= 1
    assert len(sql) == 2 * n  # same statements both times: delete-then-insert, no accumulation
    assert any("DELETE FROM agentops_dev.state.runtime_flags WHERE key = 'current'" in s for s in sql)
    pool.close()
