"""Operator CLI for the runtime circuit breaker: status | trip | clear."""
import argparse

from agentops.config import load_config
from agentops.connect import lakebase_pool
from agentops.runtime.breaker_admin import DEFAULT_AGENT, clear_breaker, read_mode, trip_breaker

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['status', 'trip', 'clear'])
    ap.add_argument('--agent', default=DEFAULT_AGENT)
    ap.add_argument('--by', default='operator')
    ap.add_argument('--reason', default='manual')
    ap.add_argument('--hours', type=float, default=24)
    a = ap.parse_args()
    pool = lakebase_pool(load_config())
    if a.action == 'trip':
        trip_breaker(pool, a.agent, a.reason, a.by, a.hours)
    elif a.action == 'clear':
        clear_breaker(pool, a.agent, a.by)
    print(f'{a.agent}: {read_mode(pool, a.agent)}')
