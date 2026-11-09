import pytest
from psycopg_pool import ConnectionPool

from agentops.monitoring.drift import psi, psi_band
from agentops.monitoring.incidents import Signature, detect_signatures, handle, open_incident
from agentops.monitoring.scoring import DailyQuality, score_day
from agentops.monitoring.traffic import TrafficMix, sample_traffic
from agentops.review.queue import ReviewQueue
from agentops.runtime.breaker_admin import clear_breaker, read_mode
from agentops.state.migrate import migrate
from tests.fakes import ScriptedLLM


class It:
    def __init__(self, i, route, split):
        self.id, self.question, self.expected_route, self.split = i, f'q{i}', route, split


ITEMS = [It(i, r, 'dev' if i % 3 else 'heldout')
         for i, r in enumerate(['policy', 'analytics', 'claim_decision', 'risk', 'refuse'] * 6)]


def row(i, answer='ok', status='ok', cat='claim_decision', kind='auto_settled', lat=1.0):
    return {'request_id': f'r{i}', 'question': 'q', 'category': cat, 'answer': answer,
            'status': status, 'latency_s': lat, 'decision_kind': kind}


def test_sample_traffic_never_uses_heldout():
    held = {i.id for i in ITEMS if i.split == 'heldout'}
    got = sample_traffic(ITEMS, TrafficMix(), 200, seed=1)
    assert not ({t.item_id for t in got} & held)


def test_sample_reproducible():
    a = sample_traffic(ITEMS, TrafficMix(), 30, seed=7)
    assert a == sample_traffic(ITEMS, TrafficMix(), 30, seed=7)
    assert a != sample_traffic(ITEMS, TrafficMix(), 30, seed=8)


def test_psi_zero_identical_and_major_shift():
    d = {'a': 0.5, 'b': 0.5}
    assert psi(d, d) == pytest.approx(0.0, abs=1e-9)
    assert psi_band(psi(d, {'a': 0.95, 'b': 0.05})) == 'major'


def test_score_day_counts_pii_leak():
    q = score_day('2026-11-09', [row(1, 'Adjuster A1234'), row(2), row(3, 'mail a@b.com')])
    assert q.pii_leak_count == 2


def test_errors_excluded_from_rates():
    q = score_day('d', [row(1), row(2, answer='', status='error', kind=None)])
    assert q.error_rate == 0.5 and q.decision_line_rate == 1.0


def test_decision_line_rate_drops():
    q = score_day('d', [row(1), row(2, kind=None)])
    assert q.decision_line_rate == 0.5


BASE = DailyQuality('b', 40, 0.0, 0.05, 0.95, 0, 5.0, None, {'a': 0.5, 'b': 0.5})


def q(**kw):
    d = dict(date='d', n=40, error_rate=0.0, refusal_rate=0.05, decision_line_rate=0.95,
             pii_leak_count=0, latency_p95_s=5.0, judge_groundedness=None,
             category_dist={'a': 0.5, 'b': 0.5})
    return DailyQuality(**{**d, **kw})


def test_detect_signatures_severities():
    codes = {s.code: s.severity for s in detect_signatures(
        q(pii_leak_count=1, error_rate=0.2, decision_line_rate=0.5, latency_p95_s=11.0,
          category_dist={'a': 0.99, 'b': 0.01}), BASE)}
    assert codes == {'pii_leak': 'sev1', 'error_rate': 'sev2', 'decision_line_drop': 'sev2',
                     'latency_p95': 'sev3', 'traffic_drift': 'sev3'}
    assert detect_signatures(q(), BASE) == []


def test_incident_llm_parse_failure_uses_template():
    inc = open_incident(ScriptedLLM(default='nonsense'), Signature('pii_leak', 'sev1', 'x'),
                        [row(1)])
    assert inc.source == 'template' and 'pii_leak' in inc.summary


@pytest.fixture
def pool(pg_dsn):
    p = ConnectionPool(pg_dsn, kwargs={'autocommit': True}, min_size=1, max_size=4, open=True)
    with p.connection() as c:
        migrate(c)
        c.execute('TRUNCATE review.queue, runtime.flags')
    yield p
    p.close()


@pytest.mark.pg
def test_sev1_trips_breaker_and_clear_restores(pool):
    queue = ReviewQueue(pool)
    handle(ScriptedLLM(default='x'), pool, queue, [Signature('pii_leak', 'sev1', 'd')],
           [row(1)], '2026-11-09')
    assert read_mode(pool, 'claims_copilot') == 'safe'
    clear_breaker(pool, 'claims_copilot', 'venkat')
    assert read_mode(pool, 'claims_copilot') == 'normal'


@pytest.mark.pg
def test_sev2_does_not_trip_breaker(pool):
    handle(ScriptedLLM(default='x'), pool, ReviewQueue(pool),
           [Signature('error_rate', 'sev2', 'd')], [row(1)], '2026-11-09')
    assert read_mode(pool, 'claims_copilot') == 'normal'
    assert len(ReviewQueue(pool).list_open('incident')) == 1
