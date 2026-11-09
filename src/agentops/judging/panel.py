"""Judge panel: several models per metric, median score, agreement on JUDGE_PASS."""
from __future__ import annotations

import statistics
from collections.abc import Callable
from dataclasses import dataclass

from insurance_automation.evaluation.harness import JUDGE_PASS

JudgeFn = Callable[[str, object, object], float]  # (metric, item, output) -> 0..1


@dataclass
class PanelScore:
    metric: str
    per_judge: dict[str, float]
    panel: float
    agreement: float


class JudgePanel:
    def __init__(self, judges: dict[str, JudgeFn]):
        if not judges:
            raise ValueError('a panel needs at least one judge')
        self.judges = judges

    def score(self, metric: str, item, output) -> PanelScore:
        per = {name: float(fn(metric, item, output)) for name, fn in self.judges.items()}
        passes = {v >= JUDGE_PASS for v in per.values()}
        return PanelScore(metric, per, statistics.median(per.values()),
                          1.0 if len(passes) == 1 else 0.0)


def copilot_judge(llm) -> JudgeFn:
    """Wrap the copilot's own LLM judges as a panel member."""
    from insurance_automation.evaluation.judges import judge_correctness, judge_groundedness
    fns = {'groundedness': judge_groundedness, 'correctness': judge_correctness}

    def judge(metric: str, item, output) -> float:
        return fns[metric](llm, item, output).score

    return judge
