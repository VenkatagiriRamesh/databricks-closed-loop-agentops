# ADR-001: Free Edition capabilities

Status: **partial**. Spike run 2026-11-09 against workspace `dbc-5545da01-a5ef`
(`python -m scripts.spike_checks`). Only the checks below were run; everything else is unmeasured.

| Capability | Result | Decision |
|---|---|---|
| `fm_model:databricks-meta-llama-3-3-70b-instruct` | PASS | target and judge model |
| `fm_model:databricks-gpt-oss-120b` | PASS | attacker, optimiser and second judge; no fallback needed |
| `catalog_create` (`agentops_dev` via API) | FAIL: metastore has no storage root; Default Storage catalogs must be created in the UI | owner creates `agentops_dev` (and `agentops_prod`) in the UI, or we use schemas inside an existing catalog |
| `endpoint_query` (`agents_insurance_automation-models-claims_copilot_agent`) | FAIL: endpoint does not exist in the workspace today | redeploy the copilot endpoint before parity, red-team against the endpoint and E2/E3 |
| `lakebase_project` | `postgres list-projects` returns none | create `portfolio-oltp` (needs owner confirmation) |
| `lakebase_connect` | NOT RUN: no project, no host | blocked on the project |
| All other plan checks | NOT RUN | implement as they become needed |

If `lakebase_connect` fails once a project exists, stop and use the Delta fallback (plan, Task 0 Step 4).
