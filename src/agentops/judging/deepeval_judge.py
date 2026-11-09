"""DeepEval as one member of the judge panel.

DeepEval metrics run on our own Databricks-served models (no OpenAI key), through a thin
DeepEvalBaseLLM wrapper around the copilot's `LLM` protocol. Scores are 0..1, the same scale as
the copilot's own judges, so the panel can take the median and Cohen's kappa treats them alike.
"""
from __future__ import annotations

import json
import os
import re
from collections.abc import Callable

os.environ.setdefault('DEEPEVAL_TELEMETRY_OPT_OUT', 'YES')

from deepeval.metrics import FaithfulnessMetric, GEval  # noqa: E402
from deepeval.models import DeepEvalBaseLLM  # noqa: E402
from deepeval.test_case import LLMTestCase, SingleTurnParams  # noqa: E402
from insurance_automation.llm.base import LLM  # noqa: E402

CORRECTNESS_CRITERIA = (
    'The actual output must agree with the expected output on the decision and on every figure '
    'or clause id it states. Penalise invented ids, wrong amounts and approvals that the expected '
    'output does not make.'
)


class DatabricksDeepEvalLLM(DeepEvalBaseLLM):
    """Adapter: DeepEval calls generate(prompt, schema); we call our LLM and parse JSON."""

    def __init__(self, llm: LLM, name: str = 'databricks'):
        self.llm, self.name = llm, name

    def load_model(self):
        return self.llm

    def get_model_name(self) -> str:
        return self.name

    def generate(self, prompt: str, schema=None):
        text = self.llm.invoke(prompt, node='deepeval').text
        if schema is None:
            return text
        match = re.search(r'\{.*\}|\[.*\]', text, re.DOTALL)
        data = json.loads(match.group(0) if match else text)
        return schema(**data) if isinstance(data, dict) else schema.model_validate(data)

    async def a_generate(self, prompt: str, schema=None):
        return self.generate(prompt, schema)


def _case(item, output) -> LLMTestCase:
    return LLMTestCase(
        input=item.question, actual_output=output.answer,
        expected_output=item.reference_answer,
        retrieval_context=[output.evidence] if output.evidence else None)


class DeepEvalJudge:
    """Scores one (item, output) pair with DeepEval's faithfulness and GEval correctness."""

    def __init__(self, llm: LLM, name: str = 'deepeval',
                 metric_factory: Callable[[str, DeepEvalBaseLLM], object] | None = None):
        self.name = name
        self.model = DatabricksDeepEvalLLM(llm, name)
        self.metric_factory = metric_factory or self._default_metric

    @staticmethod
    def _default_metric(metric: str, model: DeepEvalBaseLLM):
        if metric == 'groundedness':
            return FaithfulnessMetric(model=model, async_mode=False, include_reason=False)
        if metric == 'correctness':
            return GEval(
                name='Correctness', criteria=CORRECTNESS_CRITERIA, model=model, async_mode=False,
                evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT,
                                   SingleTurnParams.EXPECTED_OUTPUT])
        raise ValueError(f'unsupported metric {metric!r}')

    def score(self, metric: str, item, output) -> float:
        """0..1; a metric that cannot run (no evidence, parse failure) returns 0.0, never raises."""
        if metric == 'groundedness' and not output.evidence:
            return 0.0
        try:
            m = self.metric_factory(metric, self.model)
            m.measure(_case(item, output))
            return min(1.0, max(0.0, float(m.score)))
        except Exception:  # noqa: BLE001 - one bad judge call must not fail a release run
            return 0.0
