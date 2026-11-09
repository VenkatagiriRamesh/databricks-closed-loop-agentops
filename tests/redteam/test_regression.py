from agentops.redteam.oracles import OracleVerdict
from agentops.redteam.regression import RegressionSuite, propose_golden
from agentops.redteam.report import AttackRecord
from agentops.redteam.taxonomy import Attack
from agentops.target import TargetResponse
from tests.fakes import FakeTarget


def rec(prompt, ok=True, cat='pii_exfiltration'):
    return AttackRecord(Attack(prompt[:8], cat, prompt), TargetResponse('x'), OracleVerdict(ok, 'e'))


def test_regression_suite_dedupes(tmp_path):
    s = RegressionSuite(str(tmp_path / 'reg.jsonl'))
    assert s.add([rec('Give me  the PII'), rec('give me the pii'), rec('benign', ok=False)]) == 1
    assert s.add([rec('GIVE ME THE PII')]) == 0
    assert len(s.load()) == 1


def test_regression_replay_detects_still_vulnerable(tmp_path):
    s = RegressionSuite(str(tmp_path / 'reg.jsonl'))
    s.add([rec('who is the adjuster')])
    still_bad = FakeTarget(lambda q: 'Adjuster A9999')
    fixed = FakeTarget(lambda q: 'I cannot help with that.')
    assert s.replay(still_bad).categories['pii_exfiltration'].successes == 1
    assert s.replay(fixed).categories['pii_exfiltration'].successes == 0


def test_propose_golden_only_successes():
    items = propose_golden([rec('a very bad prompt'), rec('fine', ok=False)])
    assert len(items) == 1 and items[0].safety_case and items[0].split == 'dev'
