"""Read MLflow traces into per-node SpanViews."""
from __future__ import annotations

from dataclasses import dataclass, field

NODES = ('supervisor', 'refuse', 'sql_analyst', 'policy_rag', 'coverage_checker', 'fraud_screener',
         'risk_scorer', 'writer', 'critic', 'escalate', 'approval_gate')


@dataclass
class SpanView:
    node: str
    inputs: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    tokens_in: int = 0
    tokens_out: int = 0
    duration_ms: float = 0.0
    prompt_version: str | None = None


def _dict(v) -> dict:
    return v if isinstance(v, dict) else {}


def span_view(span) -> SpanView | None:
    attrs = _dict(getattr(span, 'attributes', {}))
    node = attrs.get('node') or getattr(span, 'name', '')
    if node not in NODES:
        return None
    start, end = getattr(span, 'start_time_ns', 0) or 0, getattr(span, 'end_time_ns', 0) or 0
    return SpanView(node, _dict(getattr(span, 'inputs', {})), _dict(getattr(span, 'outputs', {})),
                    int(attrs.get('tokens_in') or 0), int(attrs.get('tokens_out') or 0),
                    (end - start) / 1e6, attrs.get('prompt_version'))


def load_trace(client, trace_id: str) -> list[SpanView]:
    trace = client.get_trace(trace_id)
    views = [v for s in trace.data.spans if (v := span_view(s))]
    return sorted(views, key=lambda v: 0)  # stable; order is the span order in the trace
