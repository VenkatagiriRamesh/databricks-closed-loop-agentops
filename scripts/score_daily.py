"""Score one day of replayed requests and store DailyQuality."""
import argparse
import dataclasses
import datetime as dt
import json

from agentops.config import load_config
from agentops.connect import sql_runner
from agentops.delta import upsert_rows
from agentops.monitoring.scoring import score_day

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=dt.date.today().isoformat())
    a = ap.parse_args()
    cfg = load_config()
    run = sql_runner(cfg)
    raw = run(f"SELECT payload FROM {cfg.table('monitoring', 'requests')} WHERE key = '{a.date}'")
    rows = [json.loads(r['payload']) for r in raw]
    q = score_day(a.date, rows)
    upsert_rows(run, cfg.table('monitoring', 'daily_quality'), a.date, [dataclasses.asdict(q)])
    print(json.dumps(dataclasses.asdict(q), indent=1))
