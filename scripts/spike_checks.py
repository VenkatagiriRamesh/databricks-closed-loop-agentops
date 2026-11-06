"""Free Edition capability spike (ADR-001). Prints `CHECK <name>: PASS|FAIL|UNSUPPORTED|NOT_RUN`.

Only checks that are implemented run; the rest print NOT_RUN so the ADR never claims what was
not measured. A FAIL never crashes the run.
"""
from __future__ import annotations

import argparse
import os
import time

from agentops.config import load_config


def check_fm_model(w, model: str):
    try:
        client = w.serving_endpoints.get_open_ai_client()
        client.chat.completions.create(model=model, max_tokens=5,
                                       messages=[{'role': 'user', 'content': 'Say OK'}])
        return 'PASS', model
    except Exception as exc:  # noqa: BLE001
        return 'FAIL', f'{model}: {exc!r}'[:200]


def check_catalog_create(w, catalog: str):
    try:
        w.catalogs.create(name=catalog)
        return 'PASS', f'created {catalog}'
    except Exception as exc:  # noqa: BLE001
        if 'already exists' in str(exc).lower():
            return 'PASS', f'{catalog} exists'
        return 'FAIL', repr(exc)[:200]


def check_endpoint_query(w, endpoint: str):
    try:
        started = time.perf_counter()
        ep = w.serving_endpoints.get(endpoint)
        return 'PASS', f'state={ep.state.ready} ({time.perf_counter() - started:.1f}s)'
    except Exception as exc:  # noqa: BLE001
        return 'FAIL', repr(exc)[:200]


def check_lakebase_connect(w, cfg):
    host, user = os.environ.get('LAKEBASE_HOST'), os.environ.get('LAKEBASE_USER')
    if not host or not user:
        return 'NOT_RUN', 'set LAKEBASE_HOST and LAKEBASE_USER'
    import psycopg

    from agentops.state.pool import databricks_token_provider
    try:
        started = time.perf_counter()
        token = databricks_token_provider(cfg.profile)()
        with psycopg.connect(f'host={host} dbname={cfg.lakebase_database} user={user} '
                             'sslmode=require', password=token, connect_timeout=60) as conn:
            conn.execute('SELECT 1')
        return 'PASS', f'first connection {time.perf_counter() - started:.1f}s (cold start)'
    except Exception as exc:  # noqa: BLE001
        return 'FAIL', repr(exc)[:200]


NOT_IMPLEMENTED = ('uc_alias_set', 'prompt_alias_set', 'endpoint_traces', 'inference_tables',
                   'ai_gateway', 'lakeview_dashboard', 'sql_alert', 'workspace_sp', 'job_run',
                   'lakebase_project', 'lakebase_database', 'lakebase_uc_register',
                   'lakebase_synced_table', 'serving_lakebase_auth')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', default=None)
    args = ap.parse_args()
    cfg = load_config()
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient(profile=args.profile or cfg.profile)
    results = [(f'fm_model:{m}', *check_fm_model(w, m))
               for m in {cfg.target_model, cfg.attacker_model, *cfg.judge_models}]
    results.append(('catalog_create', *check_catalog_create(w, cfg.catalog)))
    results.append(('endpoint_query', *check_endpoint_query(w, cfg.target_endpoint)))
    results.append(('lakebase_connect', *check_lakebase_connect(w, cfg)))
    results += [(name, 'NOT_RUN', 'not implemented yet') for name in NOT_IMPLEMENTED]
    for name, status, detail in results:
        print(f'CHECK {name}: {status} {detail}')


if __name__ == '__main__':
    main()
