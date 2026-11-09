"""Replayed production-like traffic. Only the DEV split is ever sampled."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from agentops.redteam.crew import load_seeds


@dataclass
class TrafficMix:
    weights: dict[str, float] = field(default_factory=lambda: {
        'policy': 0.35, 'analytics': 0.20, 'claim_decision': 0.25, 'risk': 0.10, 'refuse': 0.05,
        'redteam_seed': 0.05})


@dataclass
class TrafficItem:
    question: str
    category: str
    item_id: str


def sample_traffic(items, mix: TrafficMix, n: int, seed: int) -> list[TrafficItem]:
    rng = random.Random(seed)
    dev = [i for i in items if i.split == 'dev']
    pools: dict[str, list[TrafficItem]] = {}
    for it in dev:
        pools.setdefault(it.expected_route, []).append(
            TrafficItem(it.question, it.expected_route, it.id))
    pools['redteam_seed'] = [TrafficItem(a.prompt, 'redteam_seed', a.id) for a in load_seeds()]
    cats = [c for c in mix.weights if pools.get(c)]
    out = []
    for _ in range(n):
        cat = rng.choices(cats, weights=[mix.weights[c] for c in cats])[0]
        out.append(rng.choice(pools[cat]))
    return out


def to_row(item: TrafficItem, resp, request_id: str, ts: str) -> dict:
    return {'request_id': request_id, 'ts': ts, 'question': item.question,
            'category': item.category, 'answer': resp.answer, 'status': resp.status,
            'latency_s': resp.latency_s, 'decision_kind': resp.decision.kind,
            'trace_id': resp.trace_id, 'prompt_versions': None}
