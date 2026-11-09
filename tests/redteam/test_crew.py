import json
from pathlib import Path

from agentops.budget import BudgetedLLM
from agentops.redteam.crew import build_crew, plan_allocation, run_redteam
from agentops.redteam.report import RedTeamReport
from agentops.redteam.taxonomy import CATEGORIES
from tests.fakes import FakeLedger, FakeTarget, ScriptedLLM, prompts_json

FIX = json.loads((Path(__file__).parents[1] / 'fixtures' / 'claims.json').read_text())


def crew(attacker, judge=None, target=None, max_attacks=24, ledger=None, budget=100.0):
    led = ledger or FakeLedger()
    return build_crew(BudgetedLLM(attacker, led, budget),
                      BudgetedLLM(judge or ScriptedLLM(default='{"success": false}'), led, budget),
                      target or FakeTarget(), FIX, max_attacks, ledger=led)


def test_planner_round2_favours_successful_category():
    hist = {c: (0, 4) for c in CATEGORIES}
    hist['pii_exfiltration'] = (4, 4)
    plan = plan_allocation(2, 30, hist)
    assert plan['pii_exfiltration'] > plan['sql_abuse'] >= 2


def test_planner_round1_is_even():
    assert len(set(plan_allocation(1, 30, {}).values())) == 1


def test_generator_falls_back_to_seeds():
    c = crew(ScriptedLLM(default='not json at all'), max_attacks=12)
    report, records = run_redteam(c)
    assert records and all(r.attack.source == 'seed' for r in records)
    assert set(report.categories) == set(CATEGORIES)


def test_crew_runs_two_rounds_and_reports_asr():
    leak = FakeTarget(lambda q: 'Adjuster A1234 said so' if 'prompt' in q else 'no')
    c = crew(ScriptedLLM(default=prompts_json(4)), target=leak, max_attacks=24)
    report, records = run_redteam(c)
    assert len(records) <= 24 and not report.truncated
    assert report.categories['pii_exfiltration'].successes > 0
    assert report.categories['pii_exfiltration'].asr.n_items > 0
    assert RedTeamReport.from_json(report.to_json()).overall_asr == report.overall_asr


def test_redteam_budget_truncates_cleanly():
    led = FakeLedger()
    c = crew(ScriptedLLM(default=prompts_json(4)), ledger=led, budget=0.35, max_attacks=24)
    report, records = run_redteam(c)
    assert report.truncated is True
    assert report.cost_usd >= 0.3


def test_report_marks_thin_sample_under_20():
    c = crew(ScriptedLLM(default=prompts_json(2)), max_attacks=12)
    report, _ = run_redteam(c)
    assert all(r.thin_sample for r in report.categories.values())


def test_judge_parse_failure_is_undetermined_not_success():
    c = crew(ScriptedLLM(default=prompts_json(3)), judge=ScriptedLLM(default='garbage'),
             max_attacks=12)
    report, _ = run_redteam(c)
    assert report.categories['scope_jailbreak'].successes == 0
