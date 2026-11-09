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


def make_eval_report(**means):
    from insurance_automation.evaluation.harness import EvalReport, MetricResult
    base = {'route_accuracy': 0.95, 'groundedness': 0.9, 'safety_pass': 1.0,
            'authority_match': 0.95, 'correctness': 0.9}
    base.update(means)
    metrics = {k: MetricResult(v, max(0.0, v - 0.05), min(1.0, v + 0.05), 20)
               for k, v in base.items()}
    return EvalReport(metrics=metrics, failures=[], by_failure_mode={}, cost_usd_median=0.005,
                      latency_p95_s=5.0, stp_rate=0.3, escalation_rate=0.1, fraud_precision=None,
                      fraud_recall=None, n_items=20, n_runs=1, graph_hash='t')


def make_redteam(**succ):
    """succ: category -> (successes, determined_n)."""
    from agentops.redteam.report import CategoryResult, RedTeamReport
    from agentops.redteam.taxonomy import CATEGORIES
    from agentops.stats import is_thin, wilson
    cats = {}
    for c in CATEGORIES:
        s, n = succ.get(c, (0, 25))
        cats[c] = CategoryResult(n, s, 0, wilson(s, n), is_thin(n))
    return RedTeamReport('t', 'now', cats, wilson(sum(v.successes for v in cats.values()), 100),
                         False, 0.0)
