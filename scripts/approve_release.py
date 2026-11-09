"""The human step: approve a candidate that is awaiting approval (four-eyes enforced)."""
import argparse

from agentops.config import load_config
from agentops.connect import lakebase_pool
from agentops.release.state import ReleaseStore

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidate', required=True)
    ap.add_argument('--approver', required=True)
    a = ap.parse_args()
    ReleaseStore(lakebase_pool(load_config())).approve(a.candidate, a.approver)
    print(f'approved {a.candidate} by {a.approver}')
