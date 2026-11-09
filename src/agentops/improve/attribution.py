"""Deterministic failure attribution: which node failed, and how."""
from __future__ import annotations

from dataclasses import dataclass

from insurance_automation.agents.graph import MAX_RETRIES

from agentops.improve.traces import SpanView

GROUNDED_MIN = 0.75


@dataclass
class FailureCase:
    case_id: str
    source: str  # 'eval' | 'redteam' | 'monitoring'
    item_id: str
    trace_id: str | None
    node: str
    mode: str
    evidence: str
    prompt_version: str | None = None


def _span(spans: list[SpanView], node: str) -> SpanView | None:
    return next((s for s in spans if s.node == node), None)


def attribute(item, output, spans: list[SpanView], failed_metrics: list[str], *,
              source: str = 'eval', item_id: str | None = None,
              trace_id: str | None = None) -> list[FailureCase]:
    fm = set(failed_metrics)
    iid = item_id or getattr(item, 'id', 'unknown')
    cases: list[FailureCase] = []
    suffix = '' if spans else ' [no_spans]'

    def add(node: str, mode: str, evidence: str) -> None:
        sp = _span(spans, node)
        cases.append(FailureCase(f'{source}:{iid}:{node}:{mode}', source, iid, trace_id, node,
                                 mode, evidence + suffix, sp.prompt_version if sp else None))

    route = getattr(output, 'route', None)
    if 'route_accuracy' in fm:
        expected = getattr(item, 'expected_route', None)
        if expected == 'refuse':
            add('supervisor', 'missed_refusal', f'expected refuse, routed {route}')
        elif route == 'refuse':
            add('supervisor', 'false_refusal', f'refused; expected {expected}')
        else:
            add('supervisor', 'misroute', f'routed {route}; expected {expected}')
    if 'sql_exec_match' in fm:
        err = (_span(spans, 'sql_analyst') or SpanView('sql_analyst')).outputs.get('sql_error')
        if err:
            add('sql_analyst', 'sql_error', str(err)[:300])
        else:
            add('sql_analyst', 'sql_wrong_result', f'sql={getattr(output, "sql", None)}')
    if 'citation_valid' in fm or 'groundedness' in fm:
        expected = set(getattr(item, 'expected_citations', []) or [])
        hits = set(getattr(output, 'hit_ids', []) or [])
        if expected <= hits:
            add('writer', 'ungrounded', 'retrieval had the evidence; the answer is not grounded')
        else:
            add('policy_rag', 'retrieval_miss', f'missing from hits: {sorted(expected - hits)}')
    critic = _span(spans, 'critic')
    if critic and int(critic.outputs.get('retries', 0) or 0) >= MAX_RETRIES:
        add('writer', 'critic_loop', f'critic rejected {MAX_RETRIES} drafts')
    if 'safety_pass' in fm or 'redteam_success' in fm:
        add('critic', 'critic_miss', 'unsafe output passed the critic')
    if 'redteam_leak' in fm:
        add('writer', 'instruction_followed', 'writer produced the leaking text')
    if 'cost' in fm:
        top = max(spans, key=lambda s: s.tokens_in + s.tokens_out, default=None)
        cases.append(FailureCase(f'{source}:{iid}:{top.node if top else "unknown"}:cost_hotspot',
                                 source, iid, trace_id, top.node if top else 'unknown',
                                 'cost_hotspot', f'tokens={top.tokens_in + top.tokens_out}'
                                 if top else 'no_spans'))
    if 'latency_p95' in fm:
        top = max(spans, key=lambda s: s.duration_ms, default=None)
        cases.append(FailureCase(f'{source}:{iid}:{top.node if top else "unknown"}:latency_hotspot',
                                 source, iid, trace_id, top.node if top else 'unknown',
                                 'latency_hotspot', f'{top.duration_ms:.0f} ms' if top
                                 else 'no_spans'))
    return cases


def group_cases(cases: list[FailureCase]) -> dict[tuple[str, str], list[FailureCase]]:
    groups: dict[tuple[str, str], list[FailureCase]] = {}
    for c in cases:
        groups.setdefault((c.node, c.mode), []).append(c)
    return dict(sorted(groups.items(), key=lambda kv: -len(kv[1])))
