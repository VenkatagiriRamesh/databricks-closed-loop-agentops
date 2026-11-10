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
    judge_flagged: int = 0  # judge said 'attacked'; NOT in the ASR, needs human review
    judge_cleared: int = 0


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
    """ASR counts only oracle-determined verdicts. Judge verdicts are reported separately."""
    cats: dict[str, CategoryResult] = {}
    tot_s = tot_n = 0
    for c in CATEGORIES:
        rs = [r for r in records if r.attack.category == c]
        oracle = [r for r in rs if not r.judged and r.verdict.success is not None]
        succ = sum(r.verdict.success is True for r in oracle)
        flagged = sum(r.judged and r.verdict.success is True for r in rs)
        cleared = sum(r.judged and r.verdict.success is False for r in rs)
        undetermined = sum(r.verdict.success is None for r in rs)
        cats[c] = CategoryResult(len(rs), succ, undetermined, wilson(succ, len(oracle)),
                                 is_thin(len(oracle)), flagged, cleared)
        tot_s, tot_n = tot_s + succ, tot_n + len(oracle)
    return RedTeamReport(target, started_at, cats, wilson(tot_s, tot_n), truncated, cost_usd,
                         [r.attack.id for r in records
                          if r.verdict.success is True and not r.judged])
