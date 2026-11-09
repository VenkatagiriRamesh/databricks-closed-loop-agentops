from pydantic import BaseModel

from agentops.judging.deepeval_judge import DatabricksDeepEvalLLM, DeepEvalJudge


class FakeLLM:
    def __init__(self, text):
        self.text, self.prompts = text, []

    def invoke(self, prompt, *, system='', node=''):
        from insurance_automation.llm.base import LLMResult
        self.prompts.append(prompt)
        return LLMResult(self.text)


class Verdict(BaseModel):
    verdict: str
    n: int = 0


class Item:
    question = 'q'
    reference_answer = 'ref'


class Out:
    answer = 'ans'
    evidence = 'ev'


class FakeMetric:
    def __init__(self, score=None, boom=False):
        self.score, self.boom, self.case = score, boom, None

    def measure(self, case):
        if self.boom:
            raise RuntimeError('bad json')
        self.case = case


def test_wrapper_returns_text_without_schema():
    assert DatabricksDeepEvalLLM(FakeLLM('hello')).generate('p') == 'hello'


def test_wrapper_parses_json_into_schema_even_with_prose():
    llm = FakeLLM('Sure! {"verdict": "yes", "n": 3} done')
    out = DatabricksDeepEvalLLM(llm).generate('p', Verdict)
    assert out == Verdict(verdict='yes', n=3)


def test_judge_builds_test_case_and_clamps_score():
    metric = FakeMetric(score=1.7)
    j = DeepEvalJudge(FakeLLM(''), metric_factory=lambda name, model: metric)
    assert j.score('correctness', Item, Out) == 1.0
    assert metric.case.input == 'q' and metric.case.expected_output == 'ref'
    assert metric.case.retrieval_context == ['ev']


def test_judge_failure_scores_zero_not_raise():
    j = DeepEvalJudge(FakeLLM(''), metric_factory=lambda n, m: FakeMetric(boom=True))
    assert j.score('groundedness', Item, Out) == 0.0


def test_groundedness_without_evidence_is_zero():
    class NoEv(Out):
        evidence = ''
    j = DeepEvalJudge(FakeLLM(''), metric_factory=lambda n, m: FakeMetric(score=1.0))
    assert j.score('groundedness', Item, NoEv) == 0.0


def test_default_metrics_construct():
    j = DeepEvalJudge(FakeLLM(''))
    assert j._default_metric('groundedness', j.model) is not None
    assert j._default_metric('correctness', j.model) is not None
