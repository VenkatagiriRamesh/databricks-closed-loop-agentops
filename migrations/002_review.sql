CREATE SCHEMA IF NOT EXISTS review;

CREATE TABLE IF NOT EXISTS review.queue (
    id bigserial PRIMARY KEY,
    kind text NOT NULL CHECK (kind IN ('incident', 'golden_proposal', 'calibration')),
    dedupe_key text NOT NULL UNIQUE,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    status text NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'claimed', 'accepted', 'rejected')),
    claimed_by text,
    decided_by text,
    note text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
