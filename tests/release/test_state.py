import pytest
from psycopg_pool import ConnectionPool

from agentops.release.promotion import NoPreviousVersion, promote, rollback
from agentops.release.state import (
    FourEyesViolation,
    IllegalTransition,
    PromotionInProgress,
    ReleaseStore,
)
from agentops.state.migrate import migrate


@pytest.fixture
def store(pg_dsn):
    pool = ConnectionPool(pg_dsn, kwargs={'autocommit': True}, min_size=1, max_size=4, open=True)
    with pool.connection() as c:
        migrate(c)
        c.execute('TRUNCATE release.approvals, release.transitions, release.candidates CASCADE')
    yield ReleaseStore(pool)
    pool.close()


def to_awaiting(store, kind='prompt', version=2):
    cid = store.propose('cat.prompts.writer', kind, {'version': version}, 'abc', 'optimiser')
    store.transition(cid, 'gating', 'ci')
    store.transition(cid, 'awaiting_approval', 'ci')
    return cid


class FakeClient:
    def __init__(self, prod=None):
        self.aliases = {'production': prod} if prod else {}

    def get_prompt_version_by_alias(self, name, alias):
        if alias not in self.aliases:
            raise KeyError(alias)
        return type('V', (), {'version': self.aliases[alias]})()

    def set_prompt_alias(self, name, alias, version):
        self.aliases[alias] = version


@pytest.mark.pg
def test_illegal_transition_raises(store):
    cid = store.propose('m', 'prompt', {}, None, 'x')
    with pytest.raises(IllegalTransition):
        store.transition(cid, 'promoted', 'x')


@pytest.mark.pg
def test_four_eyes_violation(store):
    cid = to_awaiting(store)
    with pytest.raises(FourEyesViolation):
        store.approve(cid, 'optimiser')
    store.approve(cid, 'venkat')
    assert store.is_approved(cid)


@pytest.mark.pg
def test_concurrent_promotion_second_blocked(store):
    with store.promotion_lock('model-a'):
        with pytest.raises(PromotionInProgress):
            with store.promotion_lock('model-a'):
                pass
        with store.promotion_lock('model-b'):
            pass


@pytest.mark.pg
def test_promote_requires_approval(store):
    cid = to_awaiting(store)
    with pytest.raises(IllegalTransition):
        promote(store, cid, FakeClient(prod=1), 'venkat')


@pytest.mark.pg
def test_promote_prompt_moves_aliases_and_rollback_restores(store):
    cid = to_awaiting(store, version=2)
    store.approve(cid, 'venkat')
    client = FakeClient(prod=1)
    promote(store, cid, client, 'venkat')
    assert client.aliases == {'production': 2, 'previous_production': 1}
    assert store.get(cid)['state'] == 'promoted'
    rollback(store, cid, client, 'venkat')
    assert client.aliases['production'] == 1 and store.get(cid)['state'] == 'rolled_back'


@pytest.mark.pg
def test_rollback_without_previous_raises(store):
    cid = to_awaiting(store, version=1)
    store.approve(cid, 'venkat')
    client = FakeClient(prod=None)
    promote(store, cid, client, 'venkat')
    with pytest.raises(NoPreviousVersion):
        rollback(store, cid, client, 'venkat')
