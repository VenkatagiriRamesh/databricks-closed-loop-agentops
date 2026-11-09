import pytest
from psycopg_pool import ConnectionPool

from agentops.review.queue import ReviewQueue
from agentops.state.migrate import migrate


@pytest.fixture
def queue(pg_dsn):
    pool = ConnectionPool(pg_dsn, kwargs={'autocommit': True}, min_size=1, max_size=4, open=True)
    with pool.connection() as c:
        migrate(c)
        c.execute('TRUNCATE review.queue')
    yield ReviewQueue(pool)
    pool.close()


@pytest.mark.pg
def test_queue_enqueue_dedupes(queue):
    assert queue.enqueue('incident', {'a': 1}, 'k1') is not None
    assert queue.enqueue('incident', {'a': 2}, 'k1') is None


@pytest.mark.pg
def test_queue_skip_locked_two_reviewers(queue):
    queue.enqueue('incident', {}, 'a')
    queue.enqueue('incident', {}, 'b')
    first = queue.claim_next('incident', 'r1')
    second = queue.claim_next('incident', 'r2')
    assert first['id'] != second['id'] and queue.claim_next('incident', 'r3') is None
    queue.resolve(first['id'], 'accepted', 'r1', 'ok')
