from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from insurance_automation.evaluation.harness import MetricResult

from agentops.redteam.oracles import OracleVerdict
from agentops.redteam.taxonomy import CATEGORIES, Attack
from agentops.stats import is_thin, wilson
from agentops.target import TargetResponse


@dataclass
class AttackRecord:
    attack: Attack
    response: TargetResponse
    verdict: OracleVerdict
    judged: bool = False


@dataclass
class CategoryResult:
    attempts: int
    successes: int
    undetermined: int
    asr: MetricResult
    thin_sample: bool


@dataclass
class RedTeamReport:
    target: str
    started_at: str
    categories: dict[str, CategoryResult]
    overall_asr: MetricResult
    truncated: bool
    cost_usd: float
    successful_attack_ids: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, text: str) -> RedTeamReport:
        d = json.loads(text)
        cats = {k: CategoryResult(**{**v, 'asr': MetricResult(**v['asr'])})
                for k, v in d['categories'].items()}
        return cls(d['target'], d['started_at'], cats, MetricResult(**d['overall_asr']),
                   d['truncated'], d['cost_usd'], d['successful_attack_ids'])


def build_report(target: str, started_at: str, records: list[AttackRecord], truncated: bool,
                 cost_usd: float) -> RedTeamReport:
    cats: dict[str, CategoryResult] = {}
    tot_s = tot_n = 0
    for c in CATEGORIES:
        rs = [r for r in records if r.attack.category == c]
        undetermined = sum(r.verdict.success is None for r in rs)
        determined = len(rs) - undetermined
        succ = sum(r.verdict.success is True for r in rs)
        cats[c] = CategoryResult(len(rs), succ, undetermined, wilson(succ, determined),
                                 is_thin(determined))
        tot_s, tot_n = tot_s + succ, tot_n + determined
    return RedTeamReport(target, started_at, cats, wilson(tot_s, tot_n), truncated, cost_usd,
                         [r.attack.id for r in records if r.verdict.success is True])
