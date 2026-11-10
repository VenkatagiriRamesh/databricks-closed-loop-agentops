"""Every LLM path goes through BudgetedLLM: a budget stop is a clean truncation, not a crash."""
from __future__ import annotations

import concurrent.futures as cf

from insurance_automation.llm.base import LLM, LLMResult

DEFAULT_TIMEOUT_S = 90.0


class BudgetExceeded(RuntimeError):
    pass


class LLMTimeout(RuntimeError):
    pass


class BudgetedLLM:
    """Budget cap plus a hard per-call timeout (a stalled HTTP call becomes an LLMTimeout)."""

    def __init__(self, inner: LLM, ledger, max_usd: float, timeout_s: float = DEFAULT_TIMEOUT_S):
        self.inner, self.ledger, self.max_usd, self.timeout_s = inner, ledger, max_usd, timeout_s
        self._pool = cf.ThreadPoolExecutor(max_workers=1, thread_name_prefix='llm')

    def invoke(self, prompt: str, *, system: str = '', node: str = '') -> LLMResult:
        if self.ledger.total_usd() >= self.max_usd:
            raise BudgetExceeded(f'LLM budget {self.max_usd} USD reached')
        future = self._pool.submit(self.inner.invoke, prompt, system=system, node=node)
        try:
            result = future.result(timeout=self.timeout_s)
        except cf.TimeoutError as exc:
            # The stuck thread cannot be killed; abandon it and use a fresh worker next call.
            self._pool.shutdown(wait=False, cancel_futures=True)
            self._pool = cf.ThreadPoolExecutor(max_workers=1, thread_name_prefix='llm')
            raise LLMTimeout(f'LLM call exceeded {self.timeout_s}s') from exc
        self.ledger.record(node or 'llm', result)
        return result
