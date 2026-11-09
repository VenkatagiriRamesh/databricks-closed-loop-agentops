"""Score the labelled calibration rows with every panel judge and write judge trust."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

from insurance_automation.common.sql import run_sql
from insurance_automation.contracts import AgentOutput
from insurance_automation.llm.databricks import DatabricksLLM

from agentops.config import load_config
from agentops.delta import upsert_rows
from agentops.judging.calibration import calibrate
from agentops.judging.deepeval_judge import DeepEvalJudge
from agentops.judging.panel import copilot_judge


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default='eval/calibration_to_label.csv')
    args = ap.parse_args()
    cfg = load_config()
    rows = [r for r in csv.DictReader(open(args.csv, encoding='utf-8'))
            if (r.get('human_label') or '').strip()]
    judges = {}
    for m in cfg.judge_models:
        llm = DatabricksLLM(m)
        judges[f'copilot:{m}'] = copilot_judge(llm)
        judges[f'deepeval:{m}'] = DeepEvalJudge(llm).score
    scored = []
    for r in rows:
        item = SimpleNamespace(question=r['question'], reference_answer=r['reference_answer'],
                               claim_id=None, expected_citations=[], must_cite=False)
        out = AgentOutput(answer=r['answer'], route='', evidence=r['evidence'])
        for name, fn in judges.items():
            scored.append({**r, 'metric': r['judge'], 'judge_name': name,
                           'item_id': r['id'], 'judge_score': fn(r['judge'], item, out)})
    trust = calibrate(scored)
    day = dt.date.today().isoformat()
    payload = [asdict(t) for t in trust]
    out_path = Path('reports') / f'judge_trust_{day}.json'
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps({'n_rows': len(rows), 'trust': payload}, indent=2))
    upsert_rows(lambda s: run_sql(s, cfg.warehouse_id), cfg.table('judging', 'trust'), day, payload)
    for t in trust:
        print(f'{t.metric:13s} {t.judge:45s} kappa={t.kappa} n={t.n_labels} -> {t.status}')


if __name__ == '__main__':
    main()
