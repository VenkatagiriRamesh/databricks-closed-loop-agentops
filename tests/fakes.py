import json

from insurance_automation.llm.base import LLMResult

from agentops.target import TargetResponse, parse_decision_line


class FakeLedger:
    def __init__(self):
        self.usd = 0.0

    def record(self, node, result):
        self.usd += 0.1

    def total_usd(self):
        return self.usd

    def total_tokens(self):
        return (0, 0)


class ScriptedLLM:
    """Returns canned text by node name; callable text allowed."""

    def __init__(self, by_node=None, default='[]'):
        self.by_node, self.default, self.calls = by_node or {}, default, []

    def invoke(self, prompt, *, system='', node=''):
        self.calls.append((node, prompt))
        v = self.by_node.get(node, self.default)
        return LLMResult(v(prompt) if callable(v) else v)


class FakeTarget:
    name = 'fake'

    def __init__(self, fn=None):
        self.fn = fn or (lambda q: 'I cannot help with that.')
        self.asked = []

    def ask(self, question, session_id):
        self.asked.append((question, session_id))
        a = self.fn(question)
        return TargetResponse(a, decision=parse_decision_line(a),
                              route='refuse' if 'cannot help' in a else 'policy')


def prompts_json(n):
    return json.dumps([f'test prompt {i} about C00114' for i in range(n)])
