"""End-to-end smoke: runs the milestone exit checks in order, stops at the first failure.

Without --live it checks committed artefacts and local files only. With --live it also reads the
real workspace (Lakebase migration state, Delta tables).
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from collections.abc import Callable
from pathlib import Path

MILESTONES = ('M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7')


def _reports(pattern: str) -> list[str]:
    return sorted(glob.glob(f'reports/{pattern}'))


def _need(pattern: str) -> str:
    found = _reports(pattern)
    if not found:
        raise AssertionError(f'no reports/{pattern}')
    return found[-1]


def adr001_complete():
    text = Path('docs/adr/001-free-edition-capabilities.md').read_text()
    assert 'Status: **open**' not in text, 'ADR-001 is still open'


def parity_report():
    d = json.loads(Path(_need('parity_*.json')).read_text())
    assert d['n_compared'] > 0, 'parity report compared nothing'


def migrations_idempotent_live():
    from agentops.config import load_config
    from agentops.connect import lakebase_conninfo
    from agentops.state.migrate import migrate
    from agentops.state.pool import connect_with_retry, databricks_token_provider
    cfg = load_config()
    with connect_with_retry(lakebase_conninfo(cfg), databricks_token_provider(cfg.profile),
                            autocommit=True) as conn:
        assert migrate(conn) == [], 'migrations were not already applied'


def redteam_six_categories():
    d = json.loads(Path(_need('redteam_2*.json')).read_text())
    assert len(d['categories']) == 6, 'expected 6 categories'
    assert d['overall_asr']['n_items'] > 0


def regression_suite_present():
    assert Path('redteam/regression.jsonl').exists(), 'regression suite missing'


def copilot_has_upgrades():
    from insurance_automation.agents import breaker, checkpoint  # noqa: F401


def e6_durable_approvals():
    d = json.loads(Path(_need('e6/*.json')).read_text())
    assert d.get('resumed_decision_line', '').startswith('Decision: APPROVED'), d


def release_report():
    d = json.loads(Path(_need('release_2*.json')).read_text())
    assert d['verdict'] in ('promote', 'block') and d.get('candidate')


def e1_blocked():
    d = json.loads(Path(_need('e1/*.json')).read_text())
    assert d['unsafe_verdict'] == 'block' and any(r.startswith('ASR:') for r in d['reasons']), d


def e5_cycle_recorded():
    d = json.loads(Path(_need('e5/*.json')).read_text())
    assert 'accepted' in d and 'heldout_gate' in d, d


def e4_incident():
    d = json.loads(Path(_need('e4/*.json')).read_text())
    assert d['incident_severity'] == 'sev2', d


def e7_containment():
    d = json.loads(Path(_need('e7/*.json')).read_text())
    assert d['first_escalated_after_s'] is not None and d['restored_after_clear'] is True, d


def evaluation_numbers_traceable():
    """Every decimal in README/EVALUATION must appear in some committed report."""
    import re
    corpus = ' '.join(Path(p).read_text() for p in glob.glob('reports/**/*.json', recursive=True))
    missing = []
    for doc in ('README.md', 'docs/EVALUATION.md'):
        text = Path(doc).read_text()
        for num in set(re.findall(r'(?<![\w.])0\.\d{2,3}\b', text)):
            if num not in corpus and num.rstrip('0') not in corpus:
                missing.append(f'{doc}:{num}')
    assert not missing, f'numbers not found in reports/: {sorted(missing)[:8]}'


# (milestone, check id, function, needs --live)
CHECKS: list[tuple[str, str, Callable[[], None], bool]] = [
    ('M1', 'adr001_complete', adr001_complete, False),
    ('M1', 'migrations_idempotent_live', migrations_idempotent_live, True),
    ('M1', 'parity_report', parity_report, False),
    ('M2', 'redteam_six_categories', redteam_six_categories, False),
    ('M2', 'regression_suite_present', regression_suite_present, False),
    ('M3', 'copilot_has_upgrades', copilot_has_upgrades, False),
    ('M3', 'e6_durable_approvals', e6_durable_approvals, False),
    ('M4', 'release_report', release_report, False),
    ('M4', 'e1_blocked', e1_blocked, False),
    ('M5', 'e5_cycle_recorded', e5_cycle_recorded, False),
    ('M6', 'e4_incident', e4_incident, False),
    ('M6', 'e7_containment', e7_containment, False),
    ('M7', 'evaluation_numbers_traceable', evaluation_numbers_traceable, False),
]


def run(upto: str, live: bool, checks=None) -> int:
    for milestone, cid, fn, needs_live in (checks or CHECKS):
        if MILESTONES.index(milestone) > MILESTONES.index(upto):
            break
        if needs_live and not live:
            print(f'SKIP {milestone}/{cid} (needs --live)')
            continue
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            print(f'FAIL {milestone}/{cid}: {exc}')
            return 1
        print(f'PASS {milestone}/{cid}')
    return 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--upto', choices=MILESTONES, default='M7')
    ap.add_argument('--live', action='store_true')
    a = ap.parse_args()
    sys.exit(run(a.upto, a.live))
