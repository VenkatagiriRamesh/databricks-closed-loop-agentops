"""E6: a pending approval survives a process restart (real Lakebase, owner identity).

Scope, stated in the report: two separate Python processes running the copilot's serving agent
with the Lakebase checkpointer. It is NOT the deployed endpoint (that needs a Lakebase role for
the endpoint's service principal, which is the owner's decision).
"""
import argparse
import json
import os
import subprocess
import sys

from experiments.common import ServingAgentTarget, write_report


def build_agent():
    from insurance_automation.agents.approval_log import InMemoryApprovalLog
    from insurance_automation.agents.checkpoint import make_checkpointer
    from insurance_automation.agents.serving import ClaimsResponsesAgent

    from agentops.config import load_config
    from agentops.connect import lakebase_conninfo
    from agentops.live import copilot_ctx_factory
    env = {**os.environ, 'LAKEBASE_CONNINFO': lakebase_conninfo(load_config())}
    return ClaimsResponsesAgent(copilot_ctx_factory(), InMemoryApprovalLog(),
                                checkpointer=make_checkpointer(env))


def phase_start() -> None:
    r = ServingAgentTarget(build_agent()).ask('Decide claim C00009', 'e6')
    run_id = r.answer.split('Run id:')[1].split()[0] if 'Run id:' in r.answer else None
    print(json.dumps({'run_id': run_id, 'pid': os.getpid(), 'pending': r.decision.kind}))


def phase_resume(run_id: str) -> None:
    r = ServingAgentTarget(build_agent()).ask(f'approve {run_id}', 'e6')
    last = [ln for ln in r.answer.splitlines() if ln.startswith('Decision:')]
    print(json.dumps({'pid': os.getpid(), 'resumed_decision_line': last[-1] if last else r.answer[:200]}))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--phase', choices=['start', 'resume', 'all'], default='all')
    ap.add_argument('--run-id')
    a = ap.parse_args()
    if a.phase == 'start':
        phase_start()
    elif a.phase == 'resume':
        phase_resume(a.run_id)
    else:
        def run(*args):
            out = subprocess.run([sys.executable, '-m', 'experiments.e6_durable_approvals', *args],
                                 capture_output=True, text=True, check=True).stdout
            return json.loads(out.strip().splitlines()[-1])
        s = run('--phase', 'start')
        res = run('--phase', 'resume', '--run-id', s['run_id'])
        write_report('e6', {'scope': 'two processes, real Lakebase, not the deployed endpoint',
                            'start': s, 'resume': res,
                            'resumed_decision_line': res['resumed_decision_line'],
                            'different_process': s['pid'] != res['pid']})
        print(res)
