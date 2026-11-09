import pytest

from agentops.judging.calibration import calibrate, trust_map, trust_status
from agentops.judging.panel import JudgePanel


def test_panel_median_and_agreement():
    p = JudgePanel({'a': lambda m, i, o: 0.9, 'b': lambda m, i, o: 0.8, 'c': lambda m, i, o: 0.2})
    s = p.score('groundedness', None, None)
    assert s.panel == 0.8 and s.agreement == 0.0
    agree = JudgePanel({'a': lambda m, i, o: 0.9, 'b': lambda m, i, o: 0.8}).score('x', 1, 2)
    assert agree.agreement == 1.0


def test_panel_needs_a_judge():
    with pytest.raises(ValueError):
        JudgePanel({})


def test_trust_blocking_requires_kappa_and_n():
    assert trust_status(0.7, 19) == 'advisory'
    assert trust_status(0.7, 20) == 'blocking'
    assert trust_status(0.5, 30) == 'advisory'
    assert trust_status(None, 30) == 'advisory'


def _rows(n, agree=True):
    rows = []
    for i in range(n):
        human = 'pass' if i % 2 == 0 else 'fail'
        score = (0.9 if human == 'pass' else 0.1) if agree else (0.1 if human == 'pass' else 0.9)
        rows.append({'judge': 'groundedness', 'id': f'i{i}', 'judge_score': score,
                     'human_label': human, 'judge_name': 'j1'})
    return rows


def test_calibrate_good_judge_with_enough_labels_blocks():
    trust = calibrate(_rows(24))
    assert {t.judge: t.status for t in trust} == {'j1': 'blocking', 'panel': 'blocking'}
    assert trust_map(trust) == {'groundedness': 'blocking'}


def test_trust_unlabelled_all_advisory():
    rows = [{**r, 'human_label': ''} for r in _rows(24)]
    assert calibrate(rows) == []
    assert trust_map([]) == {}


def test_calibrate_disagreeing_judge_is_advisory():
    assert all(t.status == 'advisory' for t in calibrate(_rows(24, agree=False)))
