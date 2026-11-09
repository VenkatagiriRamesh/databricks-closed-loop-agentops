"""Lakebase review queue: incidents, golden proposals and calibration labels."""
from __future__ import annotations

import json

from psycopg.rows import dict_row


class ReviewQueue:
    def __init__(self, pool):
        self.pool = pool

    def enqueue(self, kind: str, payload: dict, dedupe_key: str) -> int | None:
        with self.pool.connection() as conn:
            row = conn.execute(
                'INSERT INTO review.queue (kind, dedupe_key, payload) VALUES (%s, %s, %s) '
                'ON CONFLICT (dedupe_key) DO NOTHING RETURNING id',
                (kind, dedupe_key, json.dumps(payload))).fetchone()
        return row[0] if row else None

    def claim_next(self, kind: str, reviewer: str) -> dict | None:
        with self.pool.connection() as conn, conn.transaction():
            cur = conn.cursor(row_factory=dict_row)
            cur.execute(
                "SELECT id FROM review.queue WHERE kind = %s AND status = 'open' "
                'ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1', (kind,))
            row = cur.fetchone()
            if row is None:
                return None
            cur.execute(
                "UPDATE review.queue SET status = 'claimed', claimed_by = %s, updated_at = now() "
                'WHERE id = %s RETURNING *', (reviewer, row['id']))
            return cur.fetchone()

    def resolve(self, item_id: int, decision: str, decided_by: str, note: str = '') -> None:
        if decision not in ('accepted', 'rejected'):
            raise ValueError(decision)
        with self.pool.connection() as conn:
            conn.execute(
                'UPDATE review.queue SET status = %s, decided_by = %s, note = %s, '
                'updated_at = now() WHERE id = %s', (decision, decided_by, note, item_id))

    def list_open(self, kind: str) -> list[dict]:
        with self.pool.connection() as conn:
            cur = conn.cursor(row_factory=dict_row)
            cur.execute("SELECT * FROM review.queue WHERE kind = %s AND status = 'open' "
                        'ORDER BY id', (kind,))
            return cur.fetchall()
