"""Serving parity: does the deployed build behave like the evaluated one?"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from insurance_automation.evaluation.harness import MetricResult

from agentops.stats import wilson
from agentops.target import AgentTarget, TargetResponse

FIELDS = ('decision.kind', 'decision.authority', 'is_refusal', 'has_decision_line')


@dataclass
class ParityMismatch:
    item_id: str
    field: str
    evaluated: object
    served: object


@dataclass
class ParityReport:
    n_items: int
    n_compared: int
    n_errors: int
    mismatches: list[ParityMismatch] = field(default_factory=list)
    parity_rate: MetricResult = field(default_factory=lambda: wilson(0, 0))

    def to_dict(self) -> dict:
        return asdict(self)


def _view(r: TargetResponse) -> dict:
    return {
        'decision.kind': r.decision.kind,
        'decision.authority': r.decision.authority,
        'is_refusal': r.is_refusal,
        'has_decision_line': r.has_decision_line,
    }


def run_parity(items, evaluated: AgentTarget, served: AgentTarget) -> ParityReport:
    """Compare field by field. An item errors out (not a mismatch) if either side errored."""
    n_compared = n_errors = n_match = 0
    mismatches: list[ParityMismatch] = []
    for item in items:
        a = evaluated.ask(item.question, f'parity-a-{item.id}')
        b = served.ask(item.question, f'parity-b-{item.id}')
        if a.status != 'ok' or b.status != 'ok':
            n_errors += 1
            continue
        n_compared += 1
        va, vb = _view(a), _view(b)
        bad = [f for f in FIELDS if va[f] != vb[f]]
        mismatches.extend(ParityMismatch(item.id, f, va[f], vb[f]) for f in bad)
        n_match += not bad
    return ParityReport(len(items), n_compared, n_errors, mismatches, wilson(n_match, n_compared))
