"""Render a release decision JSON as a GitHub step summary."""
from __future__ import annotations

import json
import sys


def render_summary(decision: dict) -> str:
    verdict = decision.get('verdict', 'unknown')
    lines = [f'## Release decision: **{verdict.upper()}**', '',
             f'Candidate: `{decision.get("candidate")}`', '']
    if decision.get('reasons'):
        lines += ['### Blocking reasons'] + [f'- {r}' for r in decision['reasons']] + ['']
    if decision.get('warnings'):
        lines += ['### Warnings'] + [f'- {w}' for w in decision['warnings']] + ['']
    asr = (decision.get('inputs') or {}).get('asr') or {}
    if asr:
        lines += ['### Attack success rate', '', '| category | n | successes | ASR | ceiling |',
                  '|---|---|---|---|---|']
        lines += [f'| {c} | {v["n"]} | {v["successes"]} | {v["asr"]} | {v["ceiling"]} |'
                  for c, v in asr.items()]
        lines.append('')
    if verdict == 'promote':
        lines.append(f'Awaiting a human: `python -m scripts.approve_release --candidate '
                     f'{decision.get("candidate")} --approver <name>`')
    return '\n'.join(lines)


if __name__ == '__main__':
    print(render_summary(json.load(open(sys.argv[1]))))
