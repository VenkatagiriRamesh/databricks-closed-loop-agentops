import psycopg
import pytest

from agentops.state.pool import connect_with_retry


def test_pool_refreshes_expired_password():
    tokens = iter(['expired', 'fresh'])
    seen = []

    def fake_connect(conninfo, password=None, **kw):
        seen.append(password)
        if password == 'expired':
            raise psycopg.OperationalError('password authentication failed')
        return 'conn'

    conn = connect_with_retry('dbname=x', lambda: next(tokens), connect=fake_connect,
                              sleep=lambda s: None)
    assert conn == 'conn' and seen == ['expired', 'fresh']


def test_pool_retries_cold_start():
    attempts = []
    sleeps = []

    def fake_connect(conninfo, password=None, **kw):
        attempts.append(1)
        if len(attempts) < 3:
            raise psycopg.OperationalError('connection refused')
        return 'conn'

    assert connect_with_retry('x', lambda: 't', connect=fake_connect,
                              sleep=sleeps.append) == 'conn'
    assert sleeps == [2, 4]


def test_pool_gives_up_after_backoff_exhausted():
    def always_fail(conninfo, password=None, **kw):
        raise psycopg.OperationalError('down')

    with pytest.raises(psycopg.OperationalError):
        connect_with_retry('x', lambda: 't', connect=always_fail, sleep=lambda s: None)
