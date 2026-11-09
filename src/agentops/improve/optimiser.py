"""Prompt optimiser: propose a patch for one attributed node, verify on dev, accept or reject."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from insurance_automation.evaluation.gate import QUALITY_METRICS
from insurance_automation.evaluation.harness import MetricResult

from agentops.budget import BudgetExceeded
from agentops.improve.patch import propose_patch, validate_patch

MAX_OPT_ITERATIONS = 3


@dataclass
class DevResult:
    metrics: dict[str, MetricResult]
    failed_ids: set[str] = field(default_factory=set)


@dataclass
class OptimisationResult:
    node: str
    mode: str
    iterations: int
    accepted: bool
    base_dev: dict
    candidate_dev: dict
    fixed_case_ids: list[str]
    newly_failing_ids: list[str]
    redteam_new_successes: int
    candidate_prompt_uri: str | None
    truncated: bool
    rejection_reasons: list[str] = field(default_factory=list)


def _means(r: DevResult) -> dict:
    return {k: round(v.mean, 4) for k, v in r.metrics.items()}


def _regressed(base: DevResult, cand: DevResult) -> list[str]:
    return [m for m in QUALITY_METRICS if m in base.metrics and m in cand.metrics
            and cand.metrics[m].high < base.metrics[m].low]


def optimise(group_key: tuple[str, str], cases, *, llm, base_text: str,
             evaluate: Callable[[dict[str, str], str], DevResult],
             replay: Callable[[dict[str, str]], set[str]],
             register: Callable[[str, str, str], str],
             examples: list[str] | None = None, max_iterations: int = MAX_OPT_ITERATIONS,
             ) -> OptimisationResult:
    """evaluate(overrides, split) and replay(overrides) are injected; evaluate must get 'dev'."""
    node, mode = group_key
    targeted = {c.item_id for c in cases}
    base = evaluate({}, 'dev')
    base_attacks = replay({})
    feedback: list[str] = []
    last_cand, reasons = base, []
    truncated = False
    iterations = 0
    for iterations in range(1, max_iterations + 1):
        try:
            patch = propose_patch(llm, node, base_text, cases, examples or [], feedback=feedback)
        except BudgetExceeded:
            truncated = True
            break
        except Exception as exc:  # noqa: BLE001 - unparseable proposals count as an iteration
            feedback = [f'unparseable proposal: {exc!r}'[:120]]
            reasons.append(feedback[0])
            continue
        problems = validate_patch(patch, base_text)
        if problems:
            feedback = problems
            reasons.append('; '.join(problems))
            continue
        overrides = {node: patch.new_text}
        cand = evaluate(overrides, 'dev')
        last_cand = cand
        new_attacks = replay(overrides) - base_attacks
        fixed = sorted((base.failed_ids - cand.failed_ids) & targeted)
        newly = sorted(cand.failed_ids - base.failed_ids)
        regressed = _regressed(base, cand)
        if fixed and not regressed and not new_attacks:
            uri = register(node, patch.new_text, patch.rationale)
            return OptimisationResult(node, mode, iterations, True, _means(base), _means(cand),
                                      fixed, newly, 0, uri, False)
        feedback = (['no targeted case fixed'] if not fixed else []) \
            + ([f'regressed: {regressed}'] if regressed else []) \
            + ([f'{len(new_attacks)} new red-team successes'] if new_attacks else [])
        reasons.append('; '.join(feedback))
    return OptimisationResult(
        node, mode, iterations, False, _means(base), _means(last_cand),
        sorted((base.failed_ids - last_cand.failed_ids) & targeted),
        sorted(last_cand.failed_ids - base.failed_ids), 0, None, truncated, reasons)
