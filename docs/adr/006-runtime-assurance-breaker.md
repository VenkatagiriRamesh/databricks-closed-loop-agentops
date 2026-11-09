# ADR-006: Runtime assurance by circuit breaker

Following runtime assurance in safety engineering: a monitor (daily replay scoring) watches the
complex controller (the agent). On a sev1 incident (PII in an answer) it writes a `safe` flag in
Lakebase. The copilot reads it with a 30 s cache: in safe mode a question naming a claim returns
an escalation (`Decision: ESCALATED (safe mode: ...)`) with no tool calls, and informational
answers continue. If the flag cannot be read for 5 minutes the agent fails safe. Clearing is a
human action (`scripts/breaker.py clear`). Limitation: the claim pattern is matched with a regex
(`C\d{5}`), not the supervisor's route; a claim decision without an id is not possible anyway.
The endpoint needs a Lakebase role for this to run in the deployed build; that grant is the
owner's decision.
