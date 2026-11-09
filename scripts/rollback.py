"""Roll a promoted candidate back to the previous alias."""
import argparse

from agentops.config import load_config
from agentops.connect import lakebase_pool, mlflow_client
from agentops.release.promotion import rollback
from agentops.release.state import ReleaseStore

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidate', required=True)
    ap.add_argument('--actor', required=True)
    a = ap.parse_args()
    rollback(ReleaseStore(lakebase_pool(load_config())), a.candidate, mlflow_client(), a.actor)
    print(f'rolled back {a.candidate}')
