"""Interval statistics. Every reported rate carries n and a 95% interval."""
from __future__ import annotations

import math

from insurance_automation.evaluation.harness import MetricResult

Z95 = 1.959963984540054
THIN_SAMPLE_N = 20


def wilson(successes: int, n: int) -> MetricResult:
    """Wilson 95% interval for a proportion. n == 0 gives the uninformative [0, 1]."""
    if n == 0:
        return MetricResult(mean=0.0, low=0.0, high=1.0, n_items=0)
    p = successes / n
    z2 = Z95 ** 2
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = Z95 * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    return MetricResult(p, max(0.0, centre - half), min(1.0, centre + half), n)


def is_thin(n: int) -> bool:
    return n < THIN_SAMPLE_N
