# Closed-Loop AgentOps on Databricks

*Red-teaming, trace-driven optimisation and gated releases for multi-agent LLMs.*

Banks and insurers can build agents. They struggle to ship them, because they cannot show that
the agent resists attack, that the deployed build behaves like the evaluated one, that failures
are found and fixed under control, and that a bad agent can be stopped at runtime.
Closed-Loop AgentOps does all four. Its first governed system is the
[claims copilot](https://github.com/VenkatagiriRamesh/databricks-langgraph-multiagent-llmops).

```
Detect (red-team crew, monitors, parity) -> Contain (Lakebase circuit breaker)
   -> Attribute (span-level) -> Improve (prompt optimiser, protected clauses)
   -> Verify + gate (policy-as-code) -> Release (four-eyes, alias promotion, rollback)
```

Runs on **Databricks Free Edition** (serverless only). Synthetic data only; this is not a
production system and makes no fraud-detection-quality claims.

## Status

Work in progress. Design: [docs/SPEC.md](docs/SPEC.md). Plan:
[docs/superpowers/plans/2026-11-06-closed-loop-agentops.md](docs/superpowers/plans/2026-11-06-closed-loop-agentops.md).
**No evaluation results exist yet**; numbers will appear here only once they are generated into
`reports/` by the experiments (E1-E7).

| Milestone | State |
|---|---|
| M1 Foundations: config, target adapters, Lakebase pool and migrations, parity | code and unit tests done; live checks (ADR-001, parity report on the real endpoint) wait on workspace login |
| M2 Detect: red-team crew | not started |
| M3 Copilot upgrades | not started |
| M4 Gate and release | not started |
| M5 Improve | not started |
| M6 Runtime | not started |
| M7 Evidence and docs | not started |

## DeepEval

[DeepEval](https://github.com/confident-ai/deepeval) is a member of the judge panel
(`src/agentops/judging/deepeval_judge.py`). Its `FaithfulnessMetric` (groundedness) and a `GEval`
correctness metric run on the Databricks-served models through a small `DeepEvalBaseLLM` wrapper,
so no OpenAI key is needed and telemetry is off. Scores are 0..1 like the copilot's own judges, and
like them each DeepEval metric blocks a release only once its Cohen's kappa against your labels is
at least 0.6 on 20 or more labels. A call that errors scores 0.0 rather than raising.

## Develop

```bash
python -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/ruff check . && .venv/bin/pytest -q
# Postgres-backed tests (skipped when unset):
PG_TEST_DSN=postgresql://postgres@localhost:5432/postgres .venv/bin/pytest -q
```

## License

MIT, see [LICENSE](LICENSE).
