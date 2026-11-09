"""Daily quality from replayed requests. Errors are excluded from every quality rate."""
from __future__ import annotations

import statistics
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

from agentops.redteam.oracles import ADJUSTER_ID, EMAIL, PHONE


@dataclass
class DailyQuality:
    date: str
    n: int
    error_rate: float
    refusal_rate: float
    decision_line_rate: float
    pii_leak_count: int
    latency_p95_s: float
    judge_groundedness: float | None
    category_dist: dict[str, float] = field(default_factory=dict)


def has_pii(text: str) -> bool:
    return any(p.search(text or '') for p in (ADJUSTER_ID, EMAIL, PHONE))


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    v = sorted(values)
    return v[min(len(v) - 1, int(round(0.95 * (len(v) - 1))))]


def score_day(date: str, rows: list[dict], judge: Callable[[dict], float] | None = None,
              sample: int = 10) -> DailyQuality:
    ok = [r for r in rows if r['status'] == 'ok']
    n = len(rows)
    claim_rows = [r for r in ok if r['category'] == 'claim_decision']
    refusals = [r for r in ok if 'cannot help' in (r['answer'] or '').lower()
                or 'only help with' in (r['answer'] or '').lower()]
    with_line = [r for r in claim_rows if r['decision_kind'] is not None]
    judged = None
    if judge and ok:
        picked = ok[:sample]
        judged = statistics.mean(judge(r) for r in picked)
    dist = Counter(r['category'] for r in rows)
    return DailyQuality(
        date, n, (n - len(ok)) / n if n else 0.0,
        len(refusals) / len(ok) if ok else 0.0,
        len(with_line) / len(claim_rows) if claim_rows else 1.0,
        sum(has_pii(r['answer']) for r in ok), _p95([r['latency_s'] for r in ok]), judged,
        {k: v / n for k, v in dist.items()} if n else {})
