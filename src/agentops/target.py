"""AgentTarget: the only way any check talks to an agent."""
from __future__ import annotations

import dataclasses
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from insurance_automation.agents.nodes import ESCALATION_ANSWER, REFUSAL_ANSWER

KINDS = ('auto_settled', 'auto_denied', 'approved', 'denial_confirmed', 'siu_confirmed',
         'siu_rejected', 'edited', 'pending', 'escalated')
_BY_ROLE = re.compile(r'\bby ([a-z_]+)')
_PENDING_ROLE = re.compile(r'Approval required from: ([a-z_]+)')
_CLAIM = re.compile(r'\bclaim (C\d{5})')


@dataclass(frozen=True)
class DecisionLine:
    kind: str | None = None
    authority: str | None = None
    claim_id: str | None = None


def parse_decision_line(answer: str) -> DecisionLine:
    """Classify an agent answer. Never raises; unknown shapes give all-None."""
    text = answer or ''
    line = next((ln for ln in reversed(text.splitlines()) if ln.startswith('Decision:')), None)
    if line is None:
        if text.strip().startswith(ESCALATION_ANSWER):
            return DecisionLine('escalated')
        if 'Approval required from:' in text:
            role = _PENDING_ROLE.search(text)
            claim = _CLAIM.search(text)
            return DecisionLine('pending', role.group(1) if role else None,
                                claim.group(1) if claim else None)
        return DecisionLine()
    claim = _CLAIM.search(line)
    claim_id = claim.group(1) if claim else None
    role = _BY_ROLE.search(line)
    authority = role.group(1) if role else None
    rules = (
        ('Decision: AUTO-SETTLED', 'auto_settled', 'auto'),
        ('Decision: AUTO-DENIED', 'auto_denied', 'auto'),
        ('Decision: REFERRAL TO SIU CONFIRMED', 'siu_confirmed', 'siu'),
        ('Decision: SIU REFERRAL REJECTED', 'siu_rejected', authority),
        ('Decision: DENIAL CONFIRMED', 'denial_confirmed', authority),
        ('Decision: APPROVED', 'approved', authority),
        ('Decision: EDITED', 'edited', authority),
        ('Decision: ESCALATED', 'escalated', None),
    )
    for prefix, kind, auth in rules:
        if line.startswith(prefix):
            return DecisionLine(kind, auth, claim_id)
    return DecisionLine(None, None, claim_id)


@dataclass
class TargetResponse:
    answer: str
    status: str = 'ok'  # 'ok' | 'error'
    latency_s: float = 0.0
    decision: DecisionLine = field(default_factory=DecisionLine)
    route: str | None = None
    tools_called: list[str] = field(default_factory=list)
    sql: str | None = None
    approval_status: str | None = None
    required_authority: str | None = None
    fraud_referred: bool | None = None
    cost_usd: float = 0.0
    trace_id: str | None = None
    error: str | None = None

    @property
    def is_refusal(self) -> bool:
        return (self.route == 'refuse' or REFUSAL_ANSWER in self.answer
                or 'cannot help' in self.answer.lower())

    @property
    def has_decision_line(self) -> bool:
        return any(ln.startswith('Decision:') for ln in self.answer.splitlines())


class AgentTarget(Protocol):
    name: str

    def ask(self, question: str, session_id: str) -> TargetResponse: ...


class InProcessClaimsTarget:
    """The evaluated build: the copilot graph in this process, optionally with prompt overrides."""

    name = 'in_process'

    def __init__(self, ctx_factory: Callable[[], object],
                 prompt_overrides: dict[str, str] | None = None):
        self.ctx_factory = ctx_factory
        self.prompt_overrides = prompt_overrides or {}
        self._graph = None

    @property
    def graph(self):
        if self._graph is None:
            from insurance_automation.agents import graph as agent_graph
            from insurance_automation.agents.prompts import OverlayPromptStore
            from langgraph.checkpoint.memory import MemorySaver

            ctx = self.ctx_factory()
            if self.prompt_overrides:
                ctx = dataclasses.replace(
                    ctx, prompts=OverlayPromptStore(ctx.prompts, self.prompt_overrides))
            self._graph = agent_graph.build_graph(ctx, MemorySaver())
        return self._graph

    def ask(self, question: str, session_id: str) -> TargetResponse:
        import mlflow
        from insurance_automation.agents import graph as agent_graph

        started = time.perf_counter()
        try:
            res = agent_graph.invoke(self.graph, question, thread_id=session_id)
        except Exception as exc:  # noqa: BLE001 - a target failure is data, not a crash
            return TargetResponse('', 'error', time.perf_counter() - started, error=repr(exc))
        out = res.output
        decision = parse_decision_line(out.answer)
        if res.status == 'pending_approval':
            payload = res.interrupt_payload or {}
            decision = DecisionLine('pending', out.required_authority, payload.get('claim_id'))
        try:
            trace_id = mlflow.get_last_active_trace_id()
        except Exception:  # noqa: BLE001
            trace_id = None
        return TargetResponse(
            answer=out.answer, latency_s=out.latency_s or time.perf_counter() - started,
            decision=decision, route=out.route, tools_called=list(out.tools_called), sql=out.sql,
            approval_status=out.approval_status, required_authority=out.required_authority,
            fraud_referred=out.fraud_referred, cost_usd=out.cost_usd, trace_id=trace_id)


def _responses_text(payload: dict) -> str:
    parts: list[str] = []
    for item in payload.get('output', []):
        for c in item.get('content', []) or []:
            if isinstance(c, dict) and c.get('text'):
                parts.append(c['text'])
    return '\n'.join(parts)


class EndpointTarget:
    """The deployed build, over its serving endpoint (Responses API payload)."""

    def __init__(self, endpoint: str, post: Callable[[str, dict], dict],
                 max_retries: int = 3, backoff_s: float = 5.0,
                 sleep: Callable[[float], None] = time.sleep):
        self.endpoint, self.post = endpoint, post
        self.max_retries, self.backoff_s, self._sleep = max_retries, backoff_s, sleep
        self.name = f'endpoint:{endpoint}'

    def ask(self, question: str, session_id: str) -> TargetResponse:
        body = {'input': [{'role': 'user', 'content': question}]}
        started = time.perf_counter()
        last: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                answer = _responses_text(self.post(self.endpoint, body))
                return TargetResponse(
                    answer=answer, latency_s=time.perf_counter() - started,
                    decision=parse_decision_line(answer), trace_id=None)
            except Exception as exc:  # noqa: BLE001 - cold starts surface as many error types
                last = exc
                if attempt < self.max_retries:
                    self._sleep(self.backoff_s * (attempt + 1))
        return TargetResponse('', 'error', time.perf_counter() - started, error=repr(last))
