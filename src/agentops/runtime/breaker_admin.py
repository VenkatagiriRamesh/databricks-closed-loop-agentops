"""Operator side of the runtime circuit breaker (the copilot reads it, see Task 7)."""
from __future__ import annotations

DEFAULT_AGENT = 'claims_copilot'


def trip_breaker(pool, agent: str, reason: str, set_by: str = 'incident-agent',
                 hours: float = 24) -> None:
    with pool.connection() as conn:
        conn.execute(
            "INSERT INTO runtime.flags (agent, mode, reason, set_by, set_at, expires_at) "
            "VALUES (%s, 'safe', %s, %s, now(), now() + make_interval(hours => %s)) "
            "ON CONFLICT (agent) DO UPDATE SET mode = 'safe', reason = EXCLUDED.reason, "
            'set_by = EXCLUDED.set_by, set_at = now(), expires_at = EXCLUDED.expires_at',
            (agent, reason, set_by, hours))


def clear_breaker(pool, agent: str, cleared_by: str) -> None:
    with pool.connection() as conn:
        conn.execute(
            "INSERT INTO runtime.flags (agent, mode, reason, set_by) VALUES (%s, 'normal', "
            "'cleared', %s) ON CONFLICT (agent) DO UPDATE SET mode = 'normal', reason = 'cleared', "
            'set_by = EXCLUDED.set_by, set_at = now(), expires_at = NULL', (agent, cleared_by))


def read_mode(pool, agent: str) -> str:
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT mode FROM runtime.flags WHERE agent = %s AND (expires_at IS NULL "
            'OR expires_at > now())', (agent,)).fetchone()
    return row[0] if row else 'normal'
