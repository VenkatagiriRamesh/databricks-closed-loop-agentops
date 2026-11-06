CREATE SCHEMA IF NOT EXISTS runtime;

CREATE TABLE IF NOT EXISTS runtime.flags (
    agent text PRIMARY KEY,
    mode text NOT NULL CHECK (mode IN ('normal', 'safe')),
    reason text,
    set_by text,
    set_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz
);
