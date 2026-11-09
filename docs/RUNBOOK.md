# Runbook

## First-time setup
1. `make setup`; copy `.env.example` to `.env` and fill it (`LAKEBASE_HOST`, `LAKEBASE_USER`).
2. `databricks auth login --profile candiate-analysis`
3. `python schema_mgt/00_setup.py` (catalog, schemas, reports volume), `python -m scripts.migrate_lakebase`
4. Copilot endpoint must exist (`python -m scripts.deploy_agent_endpoint --deploy --replace` in the copilot repo).
5. `python -m scripts.export_fixture`

## Daily operation
- Release pipeline (`make release-dev`): eval challenger, parity, red team, decision.
- Runtime monitor (daily): replay, score, open incidents, sync Lakebase to Delta.
- Improvement cycle (weekly): attribute failures, optimiser (top 2 groups).

## Approve, promote, roll back
`python -m scripts.approve_release --candidate <id> --approver <you>` (a person other than the proposer),
then `python -m scripts.promote --candidate <id> --actor <you>`. Prompt candidates go live inside
the copilot's 300 s prompt TTL; model candidates redeploy. `python -m scripts.rollback ...` restores
the previous alias (fails if there was none).

## Circuit breaker
`python -m scripts.breaker status|trip|clear`. sev1 trips it automatically; clearing is manual.

## Severity
sev1 PII in an answer (breaker trips) / sev2 error rate > 0.1 or decision-line drop > 0.15 /
sev3 p95 latency > 2x baseline or major traffic drift (PSI > 0.25).

## Quota days
Free Edition stops compute when the daily quota is hit. Budgets truncate runs cleanly
(`truncated: true`); re-run the next day. LLM answers are cached, so a re-run is cheap.
Export a fresh token before long runs: `export DATABRICKS_TOKEN=$(databricks auth token -p candiate-analysis -o json | jq -r .access_token)`.
