# Architecture

```
copilot endpoint / in-process graph  <--- AgentTarget adapter --- every check
        |  traces (in-process), request log (replay)
        v
 Detect:    redteam crew (planner > generator > mutator > executor > oracle > judge > recorder)
            monitors (replay > score > signatures), parity (evaluated vs served)
 Contain:   Lakebase runtime.flags  --> copilot RuntimeBreaker (30 s cache, fail safe)
 Attribute: span-level rules (improve/attribution.py)
 Improve:   optimiser agent patches ONE node prompt; protected clauses; dev split only
 Verify:    dev failure set + held-out gate + regression suite + judge trust + parity
 Release:   policies/release.yaml -> decide(); Lakebase state machine, four-eyes, alias promotion
```

Python decides; LLMs propose (attacks, patches, judgments of undetermined cases, prose) and every
LLM output is validated. State: Lakebase `release`, `review`, `runtime` schemas; Delta
`agentops_<env>.{redteam,judging,release,monitoring,improve,state}`.

Module map: `target.py` adapters; `redteam/` taxonomy, oracles, crew, regression;
`improve/` traces, attribution, patch, optimiser; `judging/` panel, calibration, DeepEval;
`release/` policy, notes, state, promotion; `monitoring/` traffic, scoring, drift, incidents;
`runtime/breaker_admin.py`; `state/` pool and migrations.
