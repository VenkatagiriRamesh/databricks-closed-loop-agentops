"""Compare today's quality with the baseline day, open incidents, trip the breaker on sev1."""
import argparse
import dataclasses
import datetime as dt
import json

from insurance_automation.llm.databricks import DatabricksLLM

from agentops.config import load_config
from agentops.connect import lakebase_pool, sql_runner
from agentops.delta import upsert_rows
from agentops.monitoring.incidents import detect_signatures, handle
from agentops.monitoring.scoring import DailyQuality
from agentops.review.queue import ReviewQueue


def _quality(run, cfg, day):
    got = run(f"SELECT payload FROM {cfg.table('monitoring', 'daily_quality')} WHERE key = '{day}'")
    return DailyQuality(**json.loads(got[0]['payload'])) if got else None


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=dt.date.today().isoformat())
    ap.add_argument('--baseline-date', required=True)
    a = ap.parse_args()
    cfg = load_config()
    run = sql_runner(cfg)
    today, base = _quality(run, cfg, a.date), _quality(run, cfg, a.baseline_date)
    if today is None or base is None:
        raise SystemExit('need daily_quality rows for both dates (run score_daily first)')
    raw = run(f"SELECT payload FROM {cfg.table('monitoring', 'requests')} WHERE key = '{a.date}'")
    rows = [json.loads(r['payload']) for r in raw]
    pool = lakebase_pool(cfg)
    incidents = handle(DatabricksLLM(cfg.target_model), pool, ReviewQueue(pool),
                       detect_signatures(today, base), rows, a.date)
    upsert_rows(run, cfg.table('monitoring', 'incidents'), a.date,
                [dataclasses.asdict(i) for i in incidents])
    for i in incidents:
        print(f'{i.signature.severity} {i.signature.code}: {i.signature.detail} '
              f'breaker_tripped={i.breaker_tripped}')
    print(f'{len(incidents)} incidents')
