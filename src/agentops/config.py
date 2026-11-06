"""One config loader. No other module reads environment variables directly."""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_TARGET_MODEL = 'databricks-meta-llama-3-3-70b-instruct'
DEFAULT_ATTACKER_MODEL = 'databricks-gpt-oss-120b'


@dataclass(frozen=True)
class AgentOpsConfig:
    env: str
    warehouse_id: str
    target_endpoint: str
    target_model: str
    attacker_model: str
    judge_models: tuple[str, ...]
    lakebase_project: str
    lakebase_database: str
    max_attacks: int = 60
    max_llm_usd: float = 0.50
    profile: str | None = None

    @property
    def catalog(self) -> str:
        return f'agentops_{self.env}'

    def table(self, schema: str, name: str) -> str:
        return f'{self.catalog}.{schema}.{name}'


def load_config(env: Mapping[str, str] | None = None) -> AgentOpsConfig:
    e = os.environ if env is None else env
    judges = e.get('JUDGE_MODELS') or f'{DEFAULT_TARGET_MODEL},{DEFAULT_ATTACKER_MODEL}'
    return AgentOpsConfig(
        env=e.get('AGENTOPS_ENV', 'dev'),
        warehouse_id=e.get('DATABRICKS_WAREHOUSE_ID', ''),
        target_endpoint=e.get('TARGET_ENDPOINT', ''),
        target_model=e.get('TARGET_MODEL', DEFAULT_TARGET_MODEL),
        attacker_model=e.get('ATTACKER_MODEL', DEFAULT_ATTACKER_MODEL),
        judge_models=tuple(m.strip() for m in judges.split(',') if m.strip()),
        lakebase_project=e.get('LAKEBASE_PROJECT', 'portfolio-oltp'),
        lakebase_database=e.get('LAKEBASE_DATABASE', 'agentops'),
        max_attacks=int(e.get('MAX_ATTACKS', '60')),
        max_llm_usd=float(e.get('MAX_LLM_USD', '0.50')),
        profile=e.get('DATABRICKS_CONFIG_PROFILE') or None,
    )
