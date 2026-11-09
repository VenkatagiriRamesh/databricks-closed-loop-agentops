"""Signatures -> incidents. Detection is deterministic; the LLM only writes the summary."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from agentops.monitoring.drift import psi, psi_band
from agentops.monitoring.scoring import DailyQuality
from agentops.runtime.breaker_admin import DEFAULT_AGENT, trip_breaker


@dataclass
class Signature:
    code: str
    severity: str  # sev1 | sev2 | sev3
    detail: str


@dataclass
class Incident:
    signature: Signature
    summary: str
    hypothesis: str
    source: str  # 'llm' | 'template'
    evidence_request_ids: list[str] = field(default_factory=list)
    breaker_tripped: bool = False


def detect_signatures(q: DailyQuality, baseline: DailyQuality) -> list[Signature]:
    sigs = []
    if q.pii_leak_count > 0:
        sigs.append(Signature('pii_leak', 'sev1', f'{q.pii_leak_count} answers contain PII'))
    if q.error_rate > 0.1:
        sigs.append(Signature('error_rate', 'sev2', f'error rate {q.error_rate:.2f}'))
    if baseline.decision_line_rate - q.decision_line_rate > 0.15:
        sigs.append(Signature('decision_line_drop', 'sev2',
                              f'{baseline.decision_line_rate:.2f} -> {q.decision_line_rate:.2f}'))
    if baseline.latency_p95_s > 0 and q.latency_p95_s > 2 * baseline.latency_p95_s:
        sigs.append(Signature('latency_p95', 'sev3',
                              f'{baseline.latency_p95_s:.1f}s -> {q.latency_p95_s:.1f}s'))
    value = psi(baseline.category_dist, q.category_dist)
    if psi_band(value) == 'major':
        sigs.append(Signature('traffic_drift', 'sev3', f'PSI {value:.2f}'))
    return sigs


def open_incident(llm, sig: Signature, rows: list[dict]) -> Incident:
    ids = [r['request_id'] for r in rows][:10]
    template = Incident(sig, f'{sig.code}: {sig.detail}',
                        'See the attributed failure cases for the failing node.', 'template', ids)
    try:
        text = llm.invoke(
            f'Incident {sig.code} ({sig.severity}): {sig.detail}. Sample questions: '
            + json.dumps([r['question'][:100] for r in rows[:5]])
            + '\nReply with only JSON {"summary": "...", "hypothesis": "..."}.',
            system='You write concise incident summaries for an AI operations team.',
            node='incident').text
        d = json.loads(re.search(r'\{.*\}', text, re.DOTALL).group(0))
        return Incident(sig, str(d['summary']), str(d['hypothesis']), 'llm', ids)
    except Exception:  # noqa: BLE001
        return template


def handle(llm, pool, queue, sigs: list[Signature], rows: list[dict], day: str,
           agent: str = DEFAULT_AGENT) -> list[Incident]:
    """Open an incident per signature; only sev1 trips the breaker."""
    out = []
    for sig in sigs:
        inc = open_incident(llm, sig, rows)
        queue.enqueue('incident', {'signature': sig.code, 'severity': sig.severity,
                                   'summary': inc.summary, 'hypothesis': inc.hypothesis,
                                   'requests': inc.evidence_request_ids},
                      f'{day}:{sig.code}')
        if sig.severity == 'sev1':
            trip_breaker(pool, agent, f'{sig.code}: {sig.detail}')
            inc.breaker_tripped = True
        out.append(inc)
    return out
