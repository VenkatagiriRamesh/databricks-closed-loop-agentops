from dataclasses import dataclass

from agentops.parity import run_parity
from agentops.target import TargetResponse, parse_decision_line

SETTLED = 'ok\n\nDecision: AUTO-SETTLED claim C00001; payable 1.00; x'
SIU = 'ok\n\nDecision: REFERRAL TO SIU CONFIRMED for claim C00001; none.'


@dataclass
class Item:
    id: str
    question: str


class Fake:
    def __init__(self, name, answers, status='ok'):
        self.name, self.answers, self.status = name, answers, status

    def ask(self, question, session_id):
        a = self.answers[question]
        return TargetResponse(a, self.status, decision=parse_decision_line(a))


ITEMS = [Item('i1', 'q1'), Item('i2', 'q2')]


def test_parity_identical_targets_rate_one():
    t = Fake('a', {'q1': SETTLED, 'q2': SIU})
    r = run_parity(ITEMS, t, Fake('b', {'q1': SETTLED, 'q2': SIU}))
    assert r.parity_rate.mean == 1.0 and r.n_compared == 2 and not r.mismatches


def test_parity_flags_lost_siu_routing():
    r = run_parity(ITEMS, Fake('a', {'q1': SETTLED, 'q2': SIU}),
                   Fake('b', {'q1': SETTLED, 'q2': SETTLED}))
    assert r.parity_rate.mean == 0.5
    assert {m.item_id for m in r.mismatches} == {'i2'}
    assert 'decision.kind' in {m.field for m in r.mismatches}


def test_endpoint_cold_start_is_error_not_mismatch():
    r = run_parity(ITEMS, Fake('a', {'q1': SETTLED, 'q2': SIU}),
                   Fake('b', {'q1': '', 'q2': ''}, status='error'))
    assert r.n_errors == 2 and r.n_compared == 0 and not r.mismatches
