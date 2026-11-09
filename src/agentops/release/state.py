"""Lakebase release state machine: transitions, four-eyes approval, promotion lock."""
from __future__ import annotations

import json
from contextlib import contextmanager

from psycopg.rows import dict_row

ALLOWED = {
    'proposed': ['gating'],
    'gating': ['awaiting_approval', 'blocked'],
    'awaiting_approval': ['promoted', 'blocked'],
    'promoted': ['rolled_back'],
}


class IllegalTransition(RuntimeError):
    pass


class FourEyesViolation(RuntimeError):
    pass


class PromotionInProgress(RuntimeError):
    pass


class ReleaseStore:
    def __init__(self, pool):
        self.pool = pool

    def propose(self, model_name: str, change_kind: str, payload: dict, git_sha: str | None,
                proposed_by: str) -> str:
        with self.pool.connection() as conn, conn.transaction():
            cid = conn.execute(
                'INSERT INTO release.candidates (model_name, change_kind, payload, git_sha, '
                'proposed_by) VALUES (%s, %s, %s, %s, %s) RETURNING id',
                (model_name, change_kind, json.dumps(payload), git_sha, proposed_by)).fetchone()[0]
            conn.execute('INSERT INTO release.transitions (candidate_id, from_state, to_state, '
                         "actor, reason) VALUES (%s, NULL, 'proposed', %s, 'proposed')",
                         (cid, proposed_by))
        return str(cid)

    def get(self, cid: str) -> dict:
        with self.pool.connection() as conn:
            cur = conn.cursor(row_factory=dict_row)
            cur.execute('SELECT * FROM release.candidates WHERE id = %s', (cid,))
            return cur.fetchone()

    def transition(self, cid: str, to_state: str, actor: str, reason: str = '') -> None:
        with self.pool.connection() as conn, conn.transaction():
            row = conn.execute('SELECT state FROM release.candidates WHERE id = %s FOR UPDATE',
                               (cid,)).fetchone()
            if row is None:
                raise KeyError(cid)
            if to_state not in ALLOWED.get(row[0], []):
                raise IllegalTransition(f'{row[0]} -> {to_state}')
            conn.execute('UPDATE release.candidates SET state = %s, updated_at = now() '
                         'WHERE id = %s', (to_state, cid))
            conn.execute('INSERT INTO release.transitions (candidate_id, from_state, to_state, '
                         'actor, reason) VALUES (%s, %s, %s, %s, %s)',
                         (cid, row[0], to_state, actor, reason))

    def update_payload(self, cid: str, **fields) -> None:
        with self.pool.connection() as conn:
            conn.execute('UPDATE release.candidates SET payload = payload || %s::jsonb '
                         'WHERE id = %s', (json.dumps(fields), cid))

    def approve(self, cid: str, approver: str) -> None:
        with self.pool.connection() as conn, conn.transaction():
            row = conn.execute('SELECT proposed_by, state FROM release.candidates WHERE id = %s '
                               'FOR UPDATE', (cid,)).fetchone()
            if row is None:
                raise KeyError(cid)
            if approver == row[0]:
                raise FourEyesViolation(f'{approver} proposed this candidate and cannot approve it')
            if row[1] != 'awaiting_approval':
                raise IllegalTransition(f'cannot approve a candidate in state {row[1]}')
            conn.execute('INSERT INTO release.approvals (candidate_id, approver) VALUES (%s, %s) '
                         'ON CONFLICT (candidate_id) DO NOTHING', (cid, approver))

    def is_approved(self, cid: str) -> bool:
        with self.pool.connection() as conn:
            return conn.execute('SELECT 1 FROM release.approvals WHERE candidate_id = %s',
                                (cid,)).fetchone() is not None

    @contextmanager
    def promotion_lock(self, model_name: str):
        with self.pool.connection() as conn, conn.transaction():
            got = conn.execute('SELECT pg_try_advisory_xact_lock(hashtext(%s))',
                               (model_name,)).fetchone()[0]
            if not got:
                raise PromotionInProgress(model_name)
            yield
