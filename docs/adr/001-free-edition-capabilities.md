# ADR-001: Free Edition capabilities

Status: **partial**. Spike run 2026-11-09/10 on workspace `dbc-5545da01-a5ef`. Only what was
actually exercised is listed; everything else is unmeasured.

| Capability | Result | Decision |
|---|---|---|
| Foundation models `llama-3-3-70b`, `gpt-oss-120b` | PASS | target, judge, attacker, optimiser; no fallback needed |
| Catalog creation | Catalogs API FAIL (no storage root); `CREATE CATALOG` via SQL warehouse PASS | create by SQL (`schema_mgt/00_setup.py`) |
| Copilot endpoint | Missing on 2026-11-09; redeployed (model version 6), READY | queryable via `databricks api post` |
| Endpoint traces | Deploy log: "Traces from this deployment will not be logged real-time" | attribution uses in-process traces (plan fallback) |
| Lakebase project | Created `portfolio-oltp`, database `agentops` | in use |
| Lakebase connect | PASS with the workspace OAuth token as password; first connection 4.4 s | `connect_with_retry` covers the cold start |
| Lakebase migrations | applied once, second run `applied: none` | idempotent |
| Serving-to-Lakebase auth, inference tables, AI Gateway, SQL alerts, UC registration, synced tables, workspace service principal | NOT RUN | not depended on; the endpoint needs a Lakebase role for durable approvals / breaker, which is the owner's decision |
