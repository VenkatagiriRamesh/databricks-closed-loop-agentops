"""Entry point for bundle job tasks: `--script name -- <args>` runs scripts.<name> as __main__."""
import argparse
import os
import re
import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root, for `scripts.*`


def main(argv=None, runner=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--script', required=True)
    ap.add_argument('--env', default='dev')
    ap.add_argument('--warehouse-id', default='')
    ap.add_argument('--target-endpoint', default='')
    ap.add_argument('--lakebase-project', default='portfolio-oltp')
    ap.add_argument('--lakebase-database', default='agentops')
    args, rest = ap.parse_known_args(argv)
    if not re.fullmatch(r'[a-z_0-9]+', args.script):
        ap.error(f'invalid script name: {args.script}')
    os.environ.update({'AGENTOPS_ENV': args.env, 'DATABRICKS_WAREHOUSE_ID': args.warehouse_id,
                       'TARGET_ENDPOINT': args.target_endpoint,
                       'LAKEBASE_PROJECT': args.lakebase_project,
                       'LAKEBASE_DATABASE': args.lakebase_database})
    os.environ.setdefault('REPORTS_DIR', f'/Volumes/agentops_{args.env}/state/reports')
    sys.argv = [args.script, *[a for a in rest if a != '--']]
    (runner or (lambda m: runpy.run_module(m, run_name='__main__')))(f'scripts.{args.script}')


if __name__ == '__main__':
    main()
