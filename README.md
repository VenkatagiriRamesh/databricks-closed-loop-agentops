# Closed-Loop AgentOps on Databricks

*Red-teaming, trace-driven optimisation and gated releases for multi-agent LLMs.*

Banks and insurers can build agents. They struggle to ship them, because they cannot show that
the agent resists attack, that the deployed build behaves like the evaluated one, that failures
are found and fixed under control, and that a bad agent can be stopped at runtime. This repo
does all four for the [claims copilot](https://github.com/VenkatagiriRamesh/databricks-langgraph-multiagent-llmops).
Runs on **Databricks Free Edition**. Synthetic data only; not a production system.

```
Detect (red-team crew, monitors, parity) -> Contain (Lakebase circuit breaker)
  -> Attribute (span-level) -> Improve (prompt optimiser, protected clauses)
  -> Verify + gate (policy-as-code) -> Release (four-eyes, alias promotion, rollback)
```

## Status (honest)

**Built and unit-tested (121 tests, ruff clean, Postgres tests run against a real Postgres):**
config/target adapters, Lakebase pool + migrations, parity, red-team taxonomy/oracles/crew/
regression suite, review queue, failure attribution, prompt optimiser with protected clauses,
judge panel with kappa trust (including DeepEval), policy-as-code release decision, release state
machine with four-eyes and alias promotion/rollback, monitoring/incidents/breaker admin, asset
bundle (validates), dashboard definition, CI workflows, smoke test. The copilot gained span I/O,
a prompt TTL, Lakebase checkpoints and a fail-safe circuit breaker (its 362 tests pass).

**Measured on the real workspace so far:** only E3 (serving parity), see
[docs/EVALUATION.md](docs/EVALUATION.md). Lakebase migrations ran twice (second: `applied: none`).

**Not yet run live (no results, so no claims):** E1 unsafe challenger, E2 baseline red team,
E4 injected regression, E5 optimiser cycle, E6 durable approvals, E7 containment, judge
calibration (needs your labels), the bundle deploy and the release job. Long live runs were
interrupted when the laptop slept; run them with the Mac awake (see the runbook).

### What the first real result says
Parity of the in-process build vs the served endpoint on the held-out split was 0.882
(n=34, 2 errors). All 4 mismatching claims are ones the evaluated build refers to SIU but the
served build does not; two of them are auto-settled by the served build. This is the known
masked-data divergence of the endpoint's service principal. The unmasking grant has **not** been
applied; it is your decision.

### Findings from building it
- A 95% upper-bound ASR gate blocks everything at 60 attacks, so ceilings compare the observed
  rate and report the interval as a warning ([ADR-002](docs/adr/002-asr-ceiling-uses-observed-rate.md)).
- An LLM judge marked plain refusals as successful attacks, and a phone regex matched run-id
  digits. Both were fixed: refusals are cleared deterministically, judge verdicts are reported
  separately and never enter the ASR, and the PII oracle ignores UUIDs and amounts.

## Develop

```bash
make setup && cp .env.example .env     # fill LAKEBASE_HOST / LAKEBASE_USER
make test                              # PG_TEST_DSN=postgresql://... to include Postgres tests
```
See [docs/RUNBOOK.md](docs/RUNBOOK.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/SPEC.md](docs/SPEC.md).

## DeepEval

DeepEval's `FaithfulnessMetric` and a `GEval` correctness metric are panel judges
(`src/agentops/judging/deepeval_judge.py`) running on Databricks-served models, no OpenAI key.
Like every judge they block a release only after kappa >= 0.6 on >= 20 of your labels.

## License
MIT, see [LICENSE](LICENSE).
