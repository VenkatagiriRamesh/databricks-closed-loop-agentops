"""Every LLM path goes through BudgetedLLM: a budget stop is a clean truncation, not a crash."""
from __future__ import annotations

from insurance_automation.llm.base import LLM, LLMResult


class BudgetExceeded(RuntimeError):
    pass


class BudgetedLLM:
    def __init__(self, inner: LLM, ledger, max_usd: float):
        self.inner, self.ledger, self.max_usd = inner, ledger, max_usd

    def invoke(self, prompt: str, *, system: str = '', node: str = '') -> LLMResult:
        if self.ledger.total_usd() >= self.max_usd:
            raise BudgetExceeded(f'LLM budget {self.max_usd} USD reached')
        result = self.inner.invoke(prompt, system=system, node=node)
        self.ledger.record(node or 'llm', result)
        return result
