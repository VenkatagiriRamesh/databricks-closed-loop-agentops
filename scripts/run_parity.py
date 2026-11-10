"""Parity of the evaluated (in-process) build vs the served endpoint on the golden set."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path

from insurance_automation.evaluation.golden import load_golden

from agentops.config import load_config
from agentops.parity import run_parity
from agentops.target import EndpointTarget


def cli_post(profile: str | None):
    def post(endpoint: str, body: dict) -> dict:
        cmd = ['databricks', 'api', 'post', f'/serving-endpoints/{endpoint}/invocations',
               '--json', json.dumps(body)]
        if profile:
            cmd += ['--profile', profile]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=180)
        return json.loads(out.stdout)

    return post


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--golden', required=True, help='path to golden_set.jsonl')
    ap.add_argument('--split', default='heldout')
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()
    cfg = load_config()
    items = load_golden(args.golden, args.split)
    if args.limit:
        items = items[:args.limit]
    # The evaluated build is the copilot's in-process graph, built the way its own eval builds it.
    from insurance_automation.common.config import load_config as load_copilot  # noqa: PLC0415
    from insurance_automation.runtime import build_live_context  # noqa: PLC0415

    from agentops.target import InProcessClaimsTarget  # noqa: PLC0415

    copilot_cfg = load_copilot()
    evaluated = InProcessClaimsTarget(lambda: build_live_context(copilot_cfg))
    served = EndpointTarget(cfg.target_endpoint, cli_post(cfg.profile))
    report = run_parity(items, evaluated, served)
    out = Path('reports') / f'parity_{dt.date.today().isoformat()}.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({'split': args.split, **report.to_dict()}, indent=2, default=str))
    print(f'parity {report.parity_rate.mean:.3f} (n={report.n_compared}, errors={report.n_errors})'
          f' -> {out}')


if __name__ == '__main__':
    main()
