import pytest

from agentops.budget import BudgetedLLM, BudgetExceeded
from tests.fakes import FakeLedger, ScriptedLLM


def test_budget_stops_after_limit():
    led = FakeLedger()
    llm = BudgetedLLM(ScriptedLLM(default='x'), led, max_usd=0.25)
    for _ in range(3):
        llm.invoke('p', node='n')
    with pytest.raises(BudgetExceeded):
        llm.invoke('p', node='n')


def test_stalled_call_becomes_timeout_and_next_call_works():
    import threading

    from agentops.budget import LLMTimeout
    gate = threading.Event()

    class Stuck:
        calls = 0

        def invoke(self, prompt, *, system='', node=''):
            Stuck.calls += 1
            if Stuck.calls == 1:
                gate.wait(5)
            from insurance_automation.llm.base import LLMResult
            return LLMResult('ok')

    llm = BudgetedLLM(Stuck(), FakeLedger(), max_usd=10, timeout_s=0.2)
    with pytest.raises(LLMTimeout):
        llm.invoke('p')
    assert llm.invoke('p').text == 'ok'
    gate.set()
