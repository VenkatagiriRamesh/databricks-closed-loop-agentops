"""Replay dev-split traffic against the endpoint and store the request log."""
from __future__ import annotations

import argparse
import datetime as dt
import time
import uuid

from insurance_automation.evaluation.golden import load_golden

from agentops.config import load_config
from agentops.connect import sql_runner
from agentops.delta import upsert_rows
from agentops.live import GOLDEN, endpoint_target
from agentops.monitoring.traffic import TrafficMix, sample_traffic, to_row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=40)
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--pause', type=float, default=1.0)
    ap.add_argument('--target-endpoint', default=None)
    a = ap.parse_args()
    cfg = load_config()
    day = dt.date.today().isoformat()
    seed = a.seed if a.seed is not None else int(day.replace('-', ''))
    target = endpoint_target(cfg)
    rows = []
    for t in sample_traffic(load_golden(GOLDEN), TrafficMix(), a.n, seed):
        resp = target.ask(t.question, f'replay-{uuid.uuid4()}')
        rows.append(to_row(t, resp, str(uuid.uuid4()), dt.datetime.now(dt.UTC).isoformat()))
        time.sleep(a.pause)
    upsert_rows(sql_runner(cfg), cfg.table('monitoring', 'requests'), day, rows)
    print(f'replayed {len(rows)} requests, {sum(r["status"] != "ok" for r in rows)} errors')


if __name__ == '__main__':
    main()
