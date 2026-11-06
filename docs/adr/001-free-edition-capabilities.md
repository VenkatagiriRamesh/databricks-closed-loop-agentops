# ADR-001: Free Edition capabilities

Status: **open**. `python -m scripts.spike_checks` needs a fresh `databricks auth login`;
no live check has been run yet, so every result below is unknown, not assumed.

| Capability | Result | Decision |
|---|---|---|
| fm models, catalog create, endpoint query, Lakebase connect | not run | run the spike |
| other checks listed in the plan (Task 0) | script reports `NOT_RUN` (not implemented) | implement as needed |

Fixed fallbacks from the plan apply when a check fails (see the plan, Task 0 Step 4). If
`lakebase_connect` fails, stop and report to the owner; the Delta state-store fallback is then used.
