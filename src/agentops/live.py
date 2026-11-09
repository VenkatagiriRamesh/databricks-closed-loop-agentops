"""Live wiring against the real workspace: copilot context, targets, eval runs, fixture."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from agentops.config import AgentOpsConfig
from agentops.improve.optimiser import DevResult
from agentops.target import EndpointTarget, InProcessClaimsTarget

GOLDEN = os.environ.get('GOLDEN_PATH', 'eval/golden_set.jsonl')


def cli_post(profile: str | None):
    def post(endpoint: str, body: dict) -> dict:
        cmd = ['databricks', 'api', 'post', f'/serving-endpoints/{endpoint}/invocations',
               '--json', json.dumps(body)]
        if profile:
            cmd += ['--profile', profile]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(out.stdout)

    return post


def copilot_ctx_factory(overrides: dict[str, str] | None = None):
    from insurance_automation.agents.prompts import OverlayPromptStore, RegistryPromptStore
    from insurance_automation.common.config import load_config
    from insurance_automation.runtime import build_live_context

    cfg = load_config(require_warehouse=True)

    def factory():
        prompts = RegistryPromptStore(cfg.schema('eval'))
        if overrides:
            prompts = OverlayPromptStore(prompts, overrides)
        return build_live_context(cfg, prompts=prompts)

    return factory


def in_process_target(overrides: dict[str, str] | None = None) -> InProcessClaimsTarget:
    return InProcessClaimsTarget(copilot_ctx_factory(overrides), overrides)


def endpoint_target(cfg: AgentOpsConfig) -> EndpointTarget:
    return EndpointTarget(cfg.target_endpoint, cli_post(cfg.profile))


def run_split(overrides: dict[str, str] | None, split: str,
              results_dir: str = 'eval/results_agentops'):
    """Run the copilot's evaluation on one split; returns the EvalReport."""
    from insurance_automation.agents.graph import build_graph, invoke, resume
    from insurance_automation.agents.prompts import DEFAULT_PROMPTS
    from insurance_automation.evaluation.golden import load_golden
    from insurance_automation.evaluation.harness import compute_graph_hash, make_runner, run_eval
    from insurance_automation.evaluation.judges import judge_correctness, judge_groundedness

    ctx = copilot_ctx_factory(overrides)()
    graph = build_graph(ctx)
    items = load_golden(GOLDEN, split=split)

    def judge(item, output):
        return {'groundedness': judge_groundedness(ctx.llm, item, output).score,
                'correctness': judge_correctness(ctx.llm, item, output).score}

    import insurance_automation
    src = Path(insurance_automation.__file__).parent
    paths = [p for sub in ('agents', 'tools', 'llm') for p in sorted((src / sub).glob('*.py'))]
    graph_hash = compute_graph_hash(
        paths, {n: ctx.prompts.get(n) for n in sorted(DEFAULT_PROMPTS)},
        os.environ.get('FM_API_MODEL', 'default'), Path(GOLDEN).read_text(encoding='utf-8'))
    Path(results_dir).mkdir(parents=True, exist_ok=True)
    return run_eval(make_runner(graph, invoke, resume), items, n_runs=1, judge=judge,
                    results_path=f'{results_dir}/results_{split}.jsonl', graph_hash=graph_hash)


def dev_evaluator():
    """evaluate(overrides, split) for the optimiser. Raises on any split but 'dev'."""
    def evaluate(overrides: dict[str, str], split: str) -> DevResult:
        if split != 'dev':
            raise PermissionError('the optimiser may only read the dev split')
        report = run_split(overrides or None, 'dev')
        return DevResult(report.metrics, {f['id'] for f in report.failures})

    return evaluate


def load_fixture(path: str = 'redteam/fixture.json') -> dict:
    return json.loads(Path(path).read_text())
