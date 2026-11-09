"""Permanent regression suite: every successful attack is kept and replayed on each release."""
from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import asdict
from pathlib import Path

from insurance_automation.evaluation.types import GoldenItem

from agentops.redteam.crew import execute_attack
from agentops.redteam.oracles import ORACLES, OracleVerdict
from agentops.redteam.report import AttackRecord, RedTeamReport, build_report
from agentops.redteam.taxonomy import Attack


def _norm(prompt: str) -> str:
    return re.sub(r'\s+', ' ', prompt.strip().lower())


class RegressionSuite:
    def __init__(self, path: str = 'redteam/regression.jsonl'):
        self.path = Path(path)

    def load(self) -> list[Attack]:
        if not self.path.exists():
            return []
        return [Attack(**json.loads(ln)) for ln in self.path.read_text().splitlines() if ln.strip()]

    def add(self, records: list[AttackRecord]) -> int:
        have = self.load()
        seen = {_norm(a.prompt) for a in have}
        new = []
        for r in records:
            if r.verdict.success is True and _norm(r.attack.prompt) not in seen:
                seen.add(_norm(r.attack.prompt))
                new.append(r.attack)
        if new:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(''.join(json.dumps(asdict(a)) + '\n' for a in have + new))
        return len(new)

    def replay(self, target, fixture: dict | None = None) -> RedTeamReport:
        fixture = fixture or {}
        recs = []
        for a in self.load():
            resp = execute_attack(target, a, f'reg-{a.id}')
            v = (OracleVerdict(None, 'target error') if resp.status != 'ok'
                 else ORACLES[a.category](a, resp, fixture))
            recs.append(AttackRecord(a, resp, v))
        return build_report(target.name, dt.datetime.now(dt.UTC).isoformat(), recs, False, 0.0)


def propose_golden(records: list[AttackRecord]) -> list[GoldenItem]:
    items = []
    for r in records:
        if r.verdict.success is not True:
            continue
        a = r.attack
        route = 'claim_decision' if a.category in ('authority_bypass', 'indirect_injection') \
            else 'refuse'
        items.append(GoldenItem(
            id=f'rt-{a.id}', question=a.prompt, expected_route=route, expected_tools=[],
            reference_answer='', reference_sql=None, reference_rows=None, must_cite=False,
            expected_citations=[], safety_case=True, forbidden_phrases=list(a.forbidden_phrases),
            claim_id=a.claim_id, split='dev'))
    return items
