"""Evaluate a build on one split and write the report the release decision reads."""
import argparse

from agentops.connect import reports_dir
from agentops.live import run_split

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--role', choices=['champion', 'challenger'], default='challenger')
    ap.add_argument('--split', default='heldout')
    ap.add_argument('--prompt', action='append', default=[], metavar='NAME=TEXT')
    a = ap.parse_args()
    report = run_split(dict(p.split('=', 1) for p in a.prompt) or None, a.split)
    out = reports_dir() / f'eval_{a.role}.json'
    out.write_text(report.to_json())
    summary = ', '.join(f'{k}={v.mean:.3f}' for k, v in report.metrics.items())
    print(f'{a.role} {a.split}: {summary}')
