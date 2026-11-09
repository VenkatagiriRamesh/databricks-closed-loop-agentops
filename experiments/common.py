"""Shared helpers for experiments. Every experiment writes reports/<exp>/<date>.json."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from agentops.target import TargetResponse, parse_decision_line


def write_report(exp: str, payload: dict) -> Path:
    out = Path('reports') / exp / f'{dt.date.today().isoformat()}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, default=str))
    return out


class MapTarget:
    """Wraps a target and rewrites its answers (to plant a regression or a leak in a dev build)."""

    def __init__(self, inner, fn, name: str):
        self.inner, self.fn, self.name = inner, fn, name

    def ask(self, question: str, session_id: str) -> TargetResponse:
        r = self.inner.ask(question, session_id)
        if r.status == 'ok':
            r.answer = self.fn(r.answer)
            r.decision = parse_decision_line(r.answer)
        return r


class ServingAgentTarget:
    """The copilot's ClaimsResponsesAgent in this process (checkpointer + breaker optional)."""

    def __init__(self, agent, name='serving_in_process'):
        self.agent, self.name = agent, name

    def ask(self, question: str, session_id: str) -> TargetResponse:
        import time

        from mlflow.types.responses import ResponsesAgentRequest
        t = time.perf_counter()
        try:
            resp = self.agent.predict(ResponsesAgentRequest(
                input=[{'role': 'user', 'content': question}]))
            text = resp.output[0].content[0]['text']
        except Exception as exc:  # noqa: BLE001
            return TargetResponse('', 'error', time.perf_counter() - t, error=repr(exc))
        return TargetResponse(text, latency_s=time.perf_counter() - t,
                              decision=parse_decision_line(text))
