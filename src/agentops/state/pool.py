"""Connection pool whose every new connection gets a fresh OAuth token as its password."""
from __future__ import annotations

import time
from collections.abc import Callable

import psycopg
from psycopg_pool import ConnectionPool

TokenProvider = Callable[[], str]
BACKOFF_S = (2, 4, 8, 16)  # covers the scale-to-zero cold start


def databricks_token_provider(profile: str | None = None) -> TokenProvider:
    from databricks.sdk import WorkspaceClient

    def provide() -> str:
        w = WorkspaceClient(profile=profile) if profile else WorkspaceClient()
        return w.config.authenticate()['Authorization'].removeprefix('Bearer ')

    return provide


def connect_with_retry(conninfo: str, token_provider: TokenProvider, *,
                       connect=psycopg.connect, sleep: Callable[[float], None] = time.sleep,
                       backoff: tuple[float, ...] = BACKOFF_S, **kwargs):
    """Connect with a freshly fetched password; retry OperationalError (cold start, expiry)."""
    last: Exception | None = None
    for attempt in range(len(backoff) + 1):
        try:
            return connect(conninfo, password=token_provider(), **kwargs)
        except psycopg.OperationalError as exc:
            last = exc
            if attempt < len(backoff):
                sleep(backoff[attempt])
    raise last  # type: ignore[misc]


def make_pool(conninfo: str, token_provider: TokenProvider, min_size: int = 0,
              max_size: int = 4) -> ConnectionPool:
    """Pool where each new physical connection fetches a fresh password (tokens expire)."""

    class TokenConnection(psycopg.Connection):
        @classmethod
        def connect(cls, conninfo: str = '', **kwargs):  # type: ignore[override]
            return connect_with_retry(
                conninfo, token_provider,
                connect=lambda ci, **kw: psycopg.Connection.connect.__func__(cls, ci, **kw),
                **kwargs)

    return ConnectionPool(conninfo, connection_class=TokenConnection, min_size=min_size,
                          max_size=max_size, kwargs={'autocommit': True}, open=True)
