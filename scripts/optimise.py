"""One optimiser cycle for the top failure groups; accepted patches become release candidates."""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json

from insurance_automation.agents.prompts import DEFAULT_PROMPTS
from insurance_automation.llm.cost import CostLedger
from insurance_automation.llm.databricks import DatabricksLLM

from agentops.budget import BudgetedLLM
from agentops.config import load_config
from agentops.connect import lakebase_pool, mlflow_client, reports_dir, sql_runner
from agentops.delta import upsert_rows
from agentops.improve.attribution import FailureCase
from agentops.improve.optimiser import optimise
from agentops.live import dev_evaluator, in_process_target, load_fixture
from agentops.redteam.regression import RegressionSuite
from agentops.release.state import ReleaseStore

MAX_OPT_USD = 1.00


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--top', type=int, default=2)
    ap.add_argument('--no-lakebase', action='store_true')
    args = ap.parse_args()
    cfg = load_config()
    groups = json.loads((reports_dir() / 'failure_groups.json').read_text())
    ledger = CostLedger(cfg.attacker_model)
    llm = BudgetedLLM(DatabricksLLM(cfg.attacker_model), ledger, MAX_OPT_USD)
    suite, fixture = RegressionSuite('redteam/regression.jsonl'), load_fixture()
    prompt_schema = 'insurance_automation.eval'
    results = []

    def replay(overrides):
        rep = suite.replay(in_process_target(overrides or None), fixture)
        return set(rep.successful_attack_ids)

    def register(node, text, rationale):
        import mlflow.genai
        mlflow_client()
        name = f'{prompt_schema}.{node}'
        v = mlflow.genai.register_prompt(name=name, template=text, commit_message=rationale[:200])
        mlflow.genai.set_prompt_alias(name, alias='candidate', version=v.version)
        if not args.no_lakebase:
            ReleaseStore(lakebase_pool(cfg)).propose(
                name, 'prompt', {'version': v.version, 'rationale': rationale}, None, 'optimiser')
        return f'prompts:/{name}/{v.version}'

    for key, raw in list(groups.items())[:args.top]:
        node, mode = key.split(':')
        if node not in DEFAULT_PROMPTS:
            results.append({'node': node, 'mode': mode, 'skipped': 'node has no editable prompt'})
            continue
        cases = [FailureCase(**c) for c in raw]
        res = optimise((node, mode), cases, llm=llm, base_text=DEFAULT_PROMPTS[node],
                       evaluate=dev_evaluator(), replay=replay, register=register)
        results.append(dataclasses.asdict(res))
        print(f'{node}:{mode} accepted={res.accepted} iterations={res.iterations} '
              f'truncated={res.truncated}')
    day = dt.date.today().isoformat()
    (reports_dir() / f'optimise_{day}.json').write_text(json.dumps(results, indent=1, default=str))
    upsert_rows(sql_runner(cfg), cfg.table('improve', 'cycles'), day, results)


if __name__ == '__main__':
    main()
