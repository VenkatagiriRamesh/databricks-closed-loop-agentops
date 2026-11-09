"""A prompt patch and its validator. The LLM proposes; this module decides if it is allowed."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from insurance_automation.agents.prompts import DEFAULT_PROMPTS

from agentops.improve.protected import PROTECTED_CLAUSES

MAX_DIFF_FRACTION = 0.40
MAX_DIFF_CHARS = 1200

PATCH_SYSTEM = (
    'You improve one prompt of an insurance claims assistant. Change as little as possible, keep '
    'every safety sentence exactly as written, and fix only the failures shown. Reply with only '
    'JSON: {"new_text": "...", "rationale": "..."}.')


@dataclass
class PromptPatch:
    node: str
    base_version: str
    new_text: str
    rationale: str
    cases: list[str] = field(default_factory=list)


def _char_diff(a: str, b: str) -> int:
    from difflib import SequenceMatcher
    sm = SequenceMatcher(None, a, b, autojunk=False)
    return sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != 'equal')


def validate_patch(patch: PromptPatch, base_text: str) -> list[str]:
    problems: list[str] = []
    if patch.node not in DEFAULT_PROMPTS:
        problems.append(f'node {patch.node!r} is not a known prompt')
    if not patch.new_text.strip():
        problems.append('new text is empty')
        return problems
    for clause in PROTECTED_CLAUSES.get(patch.node, []):
        if clause not in patch.new_text:
            problems.append(f'protected clause removed: {clause!r}')
    diff = _char_diff(base_text, patch.new_text)
    if diff > MAX_DIFF_CHARS or diff > MAX_DIFF_FRACTION * max(1, len(base_text)):
        problems.append(f'diff of {diff} characters exceeds the budget')
    return problems


def propose_patch(llm, node: str, base_text: str, cases, examples: list[str],
                  base_version: str = 'base', feedback: list[str] | None = None) -> PromptPatch:
    prompt = (f'Prompt name: {node}\nCurrent prompt:\n{base_text}\n\nFailures:\n'
              + '\n'.join(f'- {c.mode}: {c.evidence}' for c in cases[:6])
              + ('\n\nPassing examples:\n' + '\n'.join(examples[:3]) if examples else '')
              + ('\n\nYour last attempt was rejected: ' + '; '.join(feedback) if feedback else ''))
    text = llm.invoke(prompt, system=PATCH_SYSTEM, node='optimiser').text
    m = re.search(r'\{.*\}', text, re.DOTALL)
    data = json.loads(m.group(0)) if m else {}
    return PromptPatch(node, base_version, str(data.get('new_text', '')),
                       str(data.get('rationale', '')), [c.case_id for c in cases])
