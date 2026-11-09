"""Attribute dev-split eval failures to nodes using in-process traces."""
from __future__ import annotations

import dataclasses
import datetime as dt

from insurance_automation.evaluation.golden import load_golden

from agentops.config import load_config
from agentops.connect import reports_dir, sql_runner
from agentops.delta import upsert_rows
from agentops.improve.attribution import attribute, group_cases
from agentops.improve.traces import load_trace
from agentops.live import GOLDEN, in_process_target, run_split


def main() -> None:
    import json

    import mlflow
    cfg = load_config()
    report = run_split(None, 'dev')
    items = {i.id: i for i in load_golden(GOLDEN, split='dev')}
    failed: dict[str, list[str]] = {}
    for f in report.failures:
        failed.setdefault(f['id'], []).append(f['metric'])
    target = in_process_target()
    client = mlflow.MlflowClient()
    cases = []
    for iid, metrics in failed.items():
        item = items[iid]
        resp = target.ask(item.question, f'attr-{iid}')
        spans = load_trace(client, resp.trace_id) if resp.trace_id else []
        cases += attribute(item, resp, spans, metrics, trace_id=resp.trace_id)
    groups = group_cases(cases)
    day = dt.date.today().isoformat()
    upsert_rows(sql_runner(cfg), cfg.table('improve', 'failure_cases'), day,
                [dataclasses.asdict(c) for c in cases])
    (reports_dir() / 'failure_groups.json').write_text(json.dumps(
        {f'{n}:{m}': [dataclasses.asdict(c) for c in cs] for (n, m), cs in groups.items()},
        indent=1))
    for (n, m), cs in groups.items():
        print(f'{n:14s} {m:20s} {len(cs)}')


if __name__ == '__main__':
    main()
