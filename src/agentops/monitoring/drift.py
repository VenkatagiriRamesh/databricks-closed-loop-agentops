from __future__ import annotations

import math


def psi(expected: dict[str, float], actual: dict[str, float], eps: float = 1e-4) -> float:
    """Population stability index over category distributions (each normalised to sum to 1)."""
    keys = set(expected) | set(actual)
    te, ta = sum(expected.values()) or 1.0, sum(actual.values()) or 1.0
    total = 0.0
    for k in keys:
        e = max(expected.get(k, 0.0) / te, eps)
        a = max(actual.get(k, 0.0) / ta, eps)
        total += (a - e) * math.log(a / e)
    return total


def psi_band(value: float) -> str:
    return 'none' if value < 0.1 else 'moderate' if value <= 0.25 else 'major'
