"""LLM-written release note, checked by a validator: reason codes present, no invented numbers."""
from __future__ import annotations

import json
import re

from agentops.release.policy import ReleaseDecision

NUM = re.compile(r'(?<![\w.])\d+(?:\.\d+)?')
CODE = re.compile(r'^(GATE|ASR:[a-z_]+|REGRESSION|PARITY)')


def _numbers(text: str) -> set[float]:
    return {float(m) for m in NUM.findall(text)}


def _codes(decision: ReleaseDecision) -> list[str]:
    return [m.group(0) for r in decision.reasons if (m := CODE.match(r))]


def template_note(decision: ReleaseDecision) -> str:
    lines = [f'# Release decision: {decision.verdict.upper()}', '']
    lines += [f'- {r}' for r in decision.reasons] or ['- No blocking reasons.']
    if decision.warnings:
        lines += ['', 'Warnings:'] + [f'- {w}' for w in decision.warnings]
    return '\n'.join(lines)


def validate_note(note: str, decision: ReleaseDecision) -> list[str]:
    problems = [f'missing reason code {c}' for c in _codes(decision) if c not in note]
    allowed = _numbers(json.dumps(decision.inputs) + ' '.join(decision.reasons + decision.warnings))
    body = re.sub(r'(?m)^\s*(\d+[.)]|[-*#]+)\s*', '', note)
    for n in _numbers(body):
        if not any(abs(n - a) <= 0.0006 + 0.0005 * abs(a) for a in allowed):
            problems.append(f'number {n} not found in the decision')
    return problems


def write_release_note(llm, decision: ReleaseDecision) -> tuple[str, str]:
    prompt = ('Write a short release note (under 150 words, markdown) for this decision. Use only '
              'numbers that appear in the data and mention every reason code verbatim.\n'
              + json.dumps({'verdict': decision.verdict, 'reasons': decision.reasons,
                            'warnings': decision.warnings, 'inputs': decision.inputs}))
    try:
        note = llm.invoke(prompt, system='You write precise release notes.',
                          node='release_note').text
        if not validate_note(note, decision):
            return note, 'llm'
    except Exception:  # noqa: BLE001 - any LLM failure falls back to the template
        pass
    return template_note(decision), 'template'
