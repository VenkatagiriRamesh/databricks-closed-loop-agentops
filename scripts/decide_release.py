"""Decide a release: gate -> policy -> note. Stops at awaiting_approval or blocked."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from dataclasses import asdict
from pathlib import Path

from insurance_automation.evaluation.harness import EvalReport

from agentops.config import load_config
from agentops.connect import lakebase_pool, reports_dir, sql_runner
from agentops.delta import upsert_rows
from agentops.parity import ParityReport
from agentops.redteam.report import RedTeamReport
from agentops.release.notes import write_release_note
from agentops.release.policy import decide, load_policy
from agentops.release.state import ReleaseStore


def _load(path: Path, loader):
    return loader(path.read_text()) if path.exists() else None


def _parity(path: Path):
    if not path.exists():
        return None
    from insurance_automation.evaluation.harness import MetricResult
    d = json.loads(path.read_text())
    rate = MetricResult(**d['parity_rate'])
    return ParityReport(d['n_items'], d['n_compared'], d['n_errors'], [], rate)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidate', help='existing candidate id; otherwise one is proposed')
    ap.add_argument('--model-name', default='insurance_automation.models.claims_copilot_agent')
    ap.add_argument('--change-kind', default='model')
    ap.add_argument('--version', default='latest')
    ap.add_argument('--proposer', default='github-actions')
    args = ap.parse_args()
    cfg = load_config()
    rd = reports_dir()
    policy = load_policy('policies/release.yaml')
    challenger = _load(rd / 'eval_challenger.json', EvalReport.from_json)
    if challenger is None:
        print('missing reports/eval_challenger.json', file=sys.stderr)
        return 2
    champion = _load(rd / 'eval_champion.json', EvalReport.from_json)
    redteam = _load(rd / 'redteam_latest.json', RedTeamReport.from_json)
    regression = _load(rd / 'regression_latest.json', RedTeamReport.from_json)
    trust_raw = json.loads((rd / 'trust_map.json').read_text()) if (rd / 'trust_map.json').exists() \
        else {}
    decision = decide(policy, champion, challenger, redteam, regression,
                      _parity(rd / 'parity_latest.json'), trust_raw)

    from insurance_automation.llm.databricks import DatabricksLLM
    note, note_src = write_release_note(DatabricksLLM(cfg.target_model), decision)

    day = dt.date.today().isoformat()
    row = {'candidate': args.candidate, 'verdict': decision.verdict, 'reasons': decision.reasons,
           'warnings': decision.warnings, 'inputs': decision.inputs, 'note_source': note_src}
    state_ok = True
    try:
        store = ReleaseStore(lakebase_pool(cfg))
        cid = args.candidate or store.propose(
            args.model_name, args.change_kind, {'version': args.version}, None, args.proposer)
        row['candidate'] = cid
        if store.get(cid)['state'] == 'proposed':
            store.transition(cid, 'gating', args.proposer, 'release pipeline started')
        store.transition(cid, 'awaiting_approval' if decision.verdict == 'promote' else 'blocked',
                         args.proposer, '; '.join(decision.reasons)[:500] or 'all checks passed')
    except Exception as exc:  # noqa: BLE001
        state_ok = False
        row['reasons'] = row['reasons'] + [f'state_store_unavailable: {exc!r}'[:300]]
    upsert_rows(sql_runner(cfg), cfg.table('release', 'decisions'), f'{day}:{row["candidate"]}',
                [row])
    (rd / f'release_{day}.json').write_text(json.dumps(
        {**asdict(decision), 'candidate': row['candidate'], 'note': note}, indent=2))
    (rd / f'release_{day}.md').write_text(note)
    print(f'{decision.verdict} candidate={row["candidate"]} reasons={len(decision.reasons)}')
    return 0 if state_ok else 3


if __name__ == '__main__':
    sys.exit(main())
