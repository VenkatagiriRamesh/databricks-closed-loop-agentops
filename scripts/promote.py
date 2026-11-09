"""Promote an approved candidate by moving the prompt or model alias."""
import argparse
import subprocess

from agentops.config import load_config
from agentops.connect import lakebase_pool, mlflow_client
from agentops.release.promotion import promote
from agentops.release.state import ReleaseStore


def deploy(model_name: str) -> None:  # code changes only; prompt changes need no redeploy
    subprocess.run(['python', '-m', 'scripts.deploy_agent_endpoint', '--deploy', '--replace'],
                   check=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidate', required=True)
    ap.add_argument('--actor', required=True)
    a = ap.parse_args()
    promote(ReleaseStore(lakebase_pool(load_config())), a.candidate, mlflow_client(), a.actor,
            deploy)
    print(f'promoted {a.candidate}')
