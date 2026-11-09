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
