CREATE SCHEMA IF NOT EXISTS release;

CREATE TABLE IF NOT EXISTS release.candidates (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name text NOT NULL,
    change_kind text NOT NULL CHECK (change_kind IN ('prompt', 'model')),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    git_sha text,
    proposed_by text NOT NULL,
    state text NOT NULL DEFAULT 'proposed',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS release.transitions (
    id bigserial PRIMARY KEY,
    candidate_id uuid NOT NULL REFERENCES release.candidates (id),
    from_state text,
    to_state text NOT NULL,
    actor text NOT NULL,
    reason text,
    at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS release.approvals (
    candidate_id uuid PRIMARY KEY REFERENCES release.candidates (id),
    approver text NOT NULL,
    approved_at timestamptz NOT NULL DEFAULT now()
);
