import json

import pytest
from insurance_automation.agents.prompts import DEFAULT_PROMPTS
from insurance_automation.evaluation.harness import MetricResult

from agentops.budget import BudgetedLLM
from agentops.improve.attribution import FailureCase
from agentops.improve.optimiser import DevResult, optimise
from agentops.improve.patch import PromptPatch, validate_patch
from agentops.improve.protected import PROTECTED_CLAUSES
from tests.fakes import FakeLedger, ScriptedLLM

BASE = DEFAULT_PROMPTS['writer']
CASES = [FailureCase('c1', 'eval', 'item1', None, 'writer', 'ungrounded', 'e')]


def metrics(v=0.9):
    return {'route_accuracy': MetricResult(v, v - 0.05, v + 0.05, 20)}


def good_patch():
    return json.dumps({'new_text': BASE + ' Cite ids only from the evidence list.',
                       'rationale': 'tighten citations'})


def test_protected_clauses_exist_in_defaults():
    for node, clauses in PROTECTED_CLAUSES.items():
        for c in clauses:
            assert c in DEFAULT_PROMPTS[node], (node, c)


def test_patch_removing_protected_clause_rejected():
    p = PromptPatch('writer', 'v1', BASE.replace('Never invent an id.', ''), 'r')
    assert any('protected clause removed' in x for x in validate_patch(p, BASE))


def test_patch_wrong_node_rejected():
    assert any('not a known prompt' in x for x in
               validate_patch(PromptPatch('nonexistent', 'v1', 'text', 'r'), BASE))


def test_patch_diff_budget():
    big = BASE + ' ' + 'x' * 2000
    assert any('exceeds the budget' in x for x in validate_patch(PromptPatch('writer', 'v1', big, 'r'), BASE))


def make_eval(fixed_after_patch=True, regress=False, splits=None):
    def evaluate(overrides, split):
        if splits is not None:
            splits.append(split)
        assert split == 'dev'
        if not overrides:
            return DevResult(metrics(), {'item1'})
        return DevResult(metrics(0.5 if regress else 0.9),
                         set() if fixed_after_patch else {'item1'})
    return evaluate


def run(llm, evaluate, replay=lambda o: set(), iters=3):
    registered = []
    res = optimise(('writer', 'ungrounded'), CASES, llm=llm, base_text=BASE, evaluate=evaluate,
                   replay=replay, register=lambda n, t, r: registered.append(n) or 'prompts:/w/2',
                   max_iterations=iters)
    return res, registered


def test_optimiser_accepts_when_case_fixed_and_no_regression():
    res, reg = run(ScriptedLLM(default=good_patch()), make_eval())
    assert res.accepted and res.fixed_case_ids == ['item1'] and reg == ['writer']


def test_optimiser_rejects_when_redteam_regresses():
    calls = {'n': 0}

    def replay(o):
        calls['n'] += 1
        return {'a1'} if o else set()
    res, reg = run(ScriptedLLM(default=good_patch()), make_eval(), replay)
    assert not res.accepted and reg == [] and any('red-team' in r for r in res.rejection_reasons)


def test_optimiser_rejects_when_dev_metric_regresses():
    res, _ = run(ScriptedLLM(default=good_patch()), make_eval(regress=True))
    assert not res.accepted and any('regressed' in r for r in res.rejection_reasons)


def test_optimiser_budget_stops_cycle():
    led = FakeLedger()
    led.usd = 5.0
    llm = BudgetedLLM(ScriptedLLM(default=good_patch()), led, max_usd=1.0)
    res, reg = run(llm, make_eval())
    assert res.truncated and not res.accepted and reg == []


def test_optimiser_never_reads_heldout():
    splits = []
    run(ScriptedLLM(default=good_patch()), make_eval(splits=splits))
    assert splits and set(splits) == {'dev'}


def test_optimiser_retries_with_feedback_after_invalid_patch():
    seq = iter([json.dumps({'new_text': 'short', 'rationale': 'x'}), good_patch()])
    llm = ScriptedLLM(default=lambda p: next(seq))
    res, _ = run(llm, make_eval())
    assert res.accepted and res.iterations == 2


@pytest.mark.parametrize('bad', ['not json', '{"new_text": ""}'])
def test_unusable_proposals_do_not_crash(bad):
    res, _ = run(ScriptedLLM(default=bad), make_eval(), iters=2)
    assert not res.accepted and res.iterations == 2
