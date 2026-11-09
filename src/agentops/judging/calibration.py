"""Judge trust by Cohen's kappa against the owner's labels."""
from __future__ import annotations

from dataclasses import dataclass

from insurance_automation.evaluation.calibration import cohens_kappa
from insurance_automation.evaluation.harness import JUDGE_PASS

MIN_KAPPA = 0.6
MIN_LABELS = 20


@dataclass
class JudgeTrust:
    metric: str
    judge: str
    kappa: float | None
    n_labels: int
    status: str  # 'blocking' | 'advisory'


def trust_status(kappa: float | None, n: int) -> str:
    return 'blocking' if kappa is not None and kappa >= MIN_KAPPA and n >= MIN_LABELS \
        else 'advisory'


def calibrate(labels: list[dict]) -> list[JudgeTrust]:
    """labels: rows with human_label and judge_score.

    Row keys: `metric` (falls back to the copilot CSV's `judge` column, which holds the metric),
    `judge_name` (default 'copilot'), `item_id` (falls back to `id`). The 'panel' pseudo-judge is
    the median score over the judges that scored the same item.
    """
    by: dict[tuple[str, str], tuple[list[str], list[str]]] = {}
    per_item: dict[tuple[str, str], list[tuple[float, str]]] = {}
    for row in labels:
        human = (row.get('human_label') or '').strip().lower()
        if human not in ('pass', 'fail'):
            continue
        metric = row.get('metric') or row['judge']
        judge = row.get('judge_name') or 'copilot'
        item_id = row.get('item_id') or row['id']
        score = float(row['judge_score'])
        j, h = by.setdefault((metric, judge), ([], []))
        j.append('pass' if score >= JUDGE_PASS else 'fail')
        h.append(human)
        per_item.setdefault((metric, item_id), []).append((score, human))
    out = []
    for (metric, judge), (j, h) in by.items():
        k = cohens_kappa(j, h)
        out.append(JudgeTrust(metric, judge, k, len(j), trust_status(k, len(j))))
    for metric in {m for m, _ in per_item}:
        rows = [(sorted(s for s, _ in v)[len(v) // 2], v[0][1])
                for (m, _), v in per_item.items() if m == metric]
        j = ['pass' if s >= JUDGE_PASS else 'fail' for s, _ in rows]
        h = [x for _, x in rows]
        k = cohens_kappa(j, h)
        out.append(JudgeTrust(metric, 'panel', k, len(rows), trust_status(k, len(rows))))
    return out


def trust_map(trust: list[JudgeTrust]) -> dict[str, str]:
    """Per metric: blocking iff the panel pseudo-judge is blocking; unknown metrics advisory."""
    return {t.metric: t.status for t in trust if t.judge == 'panel'}
