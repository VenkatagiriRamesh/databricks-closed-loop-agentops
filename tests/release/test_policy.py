from pathlib import Path

from agentops.parity import ParityReport
from agentops.release.notes import template_note, validate_note, write_release_note
from agentops.release.policy import decide, load_policy
from agentops.stats import wilson
from tests.fakes import ScriptedLLM, make_eval_report, make_redteam

POLICY = load_policy(Path(__file__).parents[2] / 'policies' / 'release.yaml')
BLOCKING = {'groundedness': 'blocking', 'correctness': 'blocking'}


def run(challenger=None, rt=None, reg=None, parity=None, trust=BLOCKING, champion=None):
    return decide(POLICY, champion, challenger or make_eval_report(), rt or make_redteam(),
                  reg or make_redteam(), parity, trust)


def test_clean_candidate_promotes():
    d = run()
    assert d.verdict == 'promote' and not d.reasons


def test_block_on_pii_asr_above_zero():
    d = run(rt=make_redteam(pii_exfiltration=(1, 25)))
    assert d.verdict == 'block' and any(r.startswith('ASR:pii_exfiltration') for r in d.reasons)


def test_thin_sample_point_estimate_warns():
    d = run(rt=make_redteam(direct_injection=(1, 10)))  # 0.10 > 0.05 ceiling
    assert any(r.startswith('ASR:direct_injection') for r in d.reasons)
    assert any('thin sample' in w for w in d.warnings)


def test_zero_successes_promote_but_warn_about_upper_bound():
    d = run()
    assert d.verdict == 'promote'
    assert any('upper bound' in w for w in d.warnings)


def test_regression_suite_success_blocks():
    d = run(reg=make_redteam(sql_abuse=(1, 25)))
    assert any(r.startswith('REGRESSION') for r in d.reasons)


def test_advisory_judge_regression_is_warning():
    d = run(challenger=make_eval_report(groundedness=0.5), trust={})
    assert d.verdict == 'promote'
    assert any(w.startswith('JUDGE_ADVISORY:groundedness') for w in d.warnings)


def test_blocking_judge_regression_blocks():
    d = run(challenger=make_eval_report(groundedness=0.5), trust=BLOCKING)
    assert d.verdict == 'block' and any(r.startswith('GATE: groundedness') for r in d.reasons)


def test_parity_below_minimum_warns_unless_required():
    bad = ParityReport(10, 10, 0, [], wilson(5, 10))
    assert run(parity=bad).verdict == 'promote'
    strict = POLICY.__class__(POLICY.thresholds, POLICY.max_asr, 0, 0.95, True)
    d = decide(strict, None, make_eval_report(), make_redteam(), make_redteam(), bad, BLOCKING)
    assert d.verdict == 'block' and any(r.startswith('PARITY') for r in d.reasons)


def test_release_note_rejects_unknown_number():
    d = run(rt=make_redteam(pii_exfiltration=(1, 25)))
    good = template_note(d)
    assert validate_note(good, d) == []
    assert validate_note(good + '\nSuccess rate was 42.7 percent.', d)


def test_release_note_requires_reason_codes():
    d = run(rt=make_redteam(pii_exfiltration=(1, 25)))
    assert any('ASR:pii_exfiltration' in p for p in validate_note('All fine.', d))


def test_note_falls_back_to_template_on_bad_llm():
    d = run(rt=make_redteam(pii_exfiltration=(1, 25)))
    note, src = write_release_note(ScriptedLLM(default='invented 99.9 figure'), d)
    assert src == 'template' and 'ASR:pii_exfiltration' in note
