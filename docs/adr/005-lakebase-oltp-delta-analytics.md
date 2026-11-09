# ADR-005: Lakebase for operational state, Delta for the analytical record

Release transitions, the promotion lock, four-eyes approval, review-queue claims and the runtime
flag need transactions, `FOR UPDATE`, `SKIP LOCKED` and advisory locks; Delta gives optimistic
concurrency at best. Lakebase (Postgres) holds that state; Delta holds reports and history, and
`sync_state_to_delta` copies the small Lakebase tables across for the dashboard. If Lakebase is
unreachable a decision is still written to Delta with `state_store_unavailable` and the job fails
loudly. Measured on Free Edition: first connection 4.4 s (scale-to-zero cold start), workspace
OAuth token accepted as the password.
