"""Run the adaptive red-team crew against the endpoint (default) or the in-process build."""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json

from insurance_automation.llm.cost import CostLedger
from insurance_automation.llm.databricks import DatabricksLLM

from agentops.budget import BudgetedLLM
from agentops.config import load_config
from agentops.connect import lakebase_pool, reports_dir, sql_runner
from agentops.delta import upsert_rows
from agentops.live import endpoint_target, in_process_target, load_fixture
from agentops.redteam.crew import build_crew, run_redteam
from agentops.redteam.regression import RegressionSuite, propose_golden
from agentops.review.queue import ReviewQueue


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', choices=['endpoint', 'in_process'], default='endpoint')
    ap.add_argument('--replay-only', action='store_true', help='replay the regression suite only')
    ap.add_argument('--no-lakebase', action='store_true')
    args = ap.parse_args()
    cfg = load_config()
    rd, day = reports_dir(), dt.date.today().isoformat()
    target = endpoint_target(cfg) if args.target == 'endpoint' else in_process_target()
    fixture = load_fixture()
    suite = RegressionSuite('redteam/regression.jsonl')
    if args.replay_only:
        rep = suite.replay(target, fixture)
        (rd / 'regression_latest.json').write_text(rep.to_json())
        print(f'regression replay: {rep.overall_asr.mean:.3f} (n={rep.overall_asr.n_items})')
        return
    ledger = CostLedger(cfg.attacker_model)
    attacker = BudgetedLLM(DatabricksLLM(cfg.attacker_model), ledger, cfg.max_llm_usd)
    judge = BudgetedLLM(DatabricksLLM(cfg.judge_models[0]), ledger, cfg.max_llm_usd)
    crew = build_crew(attacker, judge, target, fixture, cfg.max_attacks, ledger=ledger)
    report, records = run_redteam(crew)
    added = suite.add(records)
    (rd / f'redteam_{day}.json').write_text(report.to_json())
    (rd / 'redteam_latest.json').write_text(report.to_json())
    (rd / 'regression_latest.json').write_text(suite.replay(target, fixture).to_json())
    run = sql_runner(cfg)
    upsert_rows(run, cfg.table('redteam', 'runs'), day, [json.loads(report.to_json())])
    upsert_rows(run, cfg.table('redteam', 'attacks'), day, [
        {'id': r.attack.id, 'category': r.attack.category, 'mutation': r.attack.mutation,
         'success': r.verdict.success, 'evidence': r.verdict.evidence,
         'judged': r.judged, 'answer': r.response.answer[:500]} for r in records])
    if not args.no_lakebase:
        q = ReviewQueue(lakebase_pool(cfg))
        for g in propose_golden(records):
            q.enqueue('golden_proposal', dataclasses.asdict(g), f'golden:{g.id}')
    print(f'{len(records)} attacks, ASR {report.overall_asr.mean:.3f} '
          f'[{report.overall_asr.low:.3f}, {report.overall_asr.high:.3f}] '
          f'truncated={report.truncated} +{added} regression cases')


if __name__ == '__main__':
    main()
