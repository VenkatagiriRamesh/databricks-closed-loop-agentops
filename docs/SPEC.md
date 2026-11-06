# Closed-Loop AgentOps: spec

**Full name:** Closed-Loop AgentOps on Databricks
**Subtitle (README and CV):** red-teaming, trace-driven optimisation and gated releases for multi-agent LLMs
**Repo:** `databricks-closed-loop-agentops` · **Package:** `agentops` · **Date:** 2026-11-06

## 1. Problem

Banks and insurers can build agents. They struggle to ship them, because they cannot show four things:
- the agent resists attack
- the deployed build behaves like the evaluated one
- failures are found, explained and fixed under control
- a bad agent can be stopped at runtime

Closed-Loop AgentOps does all four for any LLM agent. Its first governed system is the claims copilot (`databricks-langgraph-multiagent-llmops`, package `insurance_automation`).

"Runtime assurance" is used in its safety-engineering sense: a monitor watches a complex controller (the agent). When the monitor detects a violation, it switches the system to a verified safe fallback (escalate to a human).

## 2. The closed loop

```
     traces + request logs (MLflow, Delta)
                 │
   ┌─────────────▼─────────────┐     ┌───────────────────────┐
   │ Detect                    │     │ Contain (runtime)     │
   │ red-team crew, monitors,  ├────►│ circuit breaker in    │
   │ parity check              │sev1 │ Lakebase: safe mode   │
   └─────────────┬─────────────┘     └───────────────────────┘
                 │ failure cases
   ┌─────────────▼─────────────┐
   │ Attribute                 │  span-level: which node failed, which failure mode
   └─────────────┬─────────────┘
   ┌─────────────▼─────────────┐
   │ Improve                   │  optimiser agent patches ONLY that node's prompt;
   │                           │  protected safety clauses cannot be removed
   └─────────────┬─────────────┘
   ┌─────────────▼─────────────┐
   │ Verify + gate             │  dev failure set, held-out eval, red-team regression,
   │                           │  calibrated judges, policy-as-code decision
   └─────────────┬─────────────┘
   ┌─────────────▼─────────────┐
   │ Release                   │  Lakebase state machine, promotion lock, four-eyes
   │                           │  approval, prompt-alias promotion with no redeploy, rollback
   └───────────────────────────┘
```

## 3. Goals

| ID | Goal |
|---|---|
| G1 | **Target adapter.** Governs an agent in-process (the evaluated build) or over its serving endpoint (the deployed build). |
| G2 | **Red-team crew.** A LangGraph multi-agent crew (planner, generator, mutator, executor, oracle, judge) runs 6 attack categories with adaptive allocation. It reports the attack success rate (ASR) per category with Wilson 95% intervals. Successful attacks become a permanent regression suite. |
| G3 | **Trace-driven attribution.** Reads MLflow traces (span inputs and outputs per node) and request logs. Assigns each failure to a node and a failure mode with deterministic rules. |
| G4 | **Prompt optimiser.** An LLM agent rewrites only the attributed node's prompt and registers it as a candidate version in the MLflow Prompt Registry. A validator rejects patches that remove protected clauses or exceed a diff budget. At most 3 iterations per cycle. |
| G5 | **Judge panel with calibration.** At least two models per metric, with Cohen's kappa against the owner's labels. A judge's metric blocks a release only if kappa is at least 0.6 on at least 20 labels; otherwise it is advisory. |
| G6 | **Serving parity.** Field-level divergence between the evaluated and the served build. |
| G7 | **Policy-as-code release.** Deterministic YAML policy (quality floors, no regression beyond noise, ASR ceilings, parity, judge trust) → promote or block. An LLM writes the release note; a validator rejects any number not found in the decision. |
| G8 | **Lakebase operational state.** Release state machine, promotion advisory lock, four-eyes approval, review queues, runtime flags, plus durable LangGraph approval checkpoints for the copilot. Delta stays the analytical record. |
| G9 | **Runtime circuit breaker.** On a sev1 incident (PII leak), the copilot switches to safe mode within one flag-cache TTL: claim decisions escalate to a human, and informational answers continue. |
| G10 | **CI/CD and observability.** Asset Bundle (`dev` and `prod`), GitHub Actions, and an AI/BI dashboard. |
| G11 | **Evidence.** Experiments E1–E7. Every CV number comes from their committed reports. |

## 4. Non-goals

- Fine-tuning, GPU serving or provisioned throughput (unavailable on Free Edition).
- Agent Bricks (Knowledge Assistant is unsupported on Free Edition).
- Applying the unmasked-PII grant to the copilot's service principal (the owner's separate decision). Parity reports the divergence.
- Automatic promotion without a human. The optimiser proposes, the gate decides, a person approves.
- Terraform and Kubernetes (owner decision).

## 5. Constraints (Databricks Free Edition, docs checked 2026-11-06)

- **Compute:** serverless only. One 2X-Small SQL warehouse. At most 5 concurrent job tasks per account.
- **Lakebase:**
  - One project per account, with scale-to-zero compute.
  - Closed-Loop AgentOps uses project `portfolio-oltp`, database `agentops`. The future Fraud & AML project gets database `fraud_cases` in the same project.
  - Storage, branch and connection limits are undocumented, so keep the data small.
- **Model Serving:** limited endpoints, no GPU. One version per endpoint (copilot ADR-001), so a challenger is evaluated in-process. Prompt-only changes are promoted by moving the prompt alias (no redeploy). Code changes are promoted with `--replace`.
- **Quota:** exceeding the daily quota stops compute for the day. Every LLM component has a USD budget and stops cleanly.
- **Auth:** CLI OAuth refresh is flaky, so long runs export a fresh token. Lakebase passwords are short-lived OAuth tokens, so pools refresh them.
- **Unconfirmed:** AI Gateway, inference tables, endpoint trace logging, SQL alerts, Lakebase Unity Catalog registration and synced tables. Task 0 checks each one, and the design never depends on them.

## 6. Honesty rules

- Report n and an interval with every rate. A category with n < 20 is labelled "thin sample".
- An improvement claim needs all three of:
  - fixed items on the dev failure set
  - held-out change with an interval
  - zero new red-team successes

  Optimisation happens on dev only. The held-out split is read only by the gate.
- The copilot's fraud and authority ground truth is circular, so this project never claims fraud-detection quality.
- Synthetic data only. Never call this "production". LLM cost is notional.
