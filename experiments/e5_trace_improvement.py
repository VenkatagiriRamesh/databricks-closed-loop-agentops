"""E5: attribute dev failures, run one optimiser cycle, report the held-out gate honestly."""
import json
import subprocess
import sys
from pathlib import Path

from experiments.common import write_report

if __name__ == '__main__':
    subprocess.run([sys.executable, '-m', 'scripts.attribute_failures'], check=True)
    subprocess.run([sys.executable, '-m', 'scripts.optimise', '--top', '2', '--no-lakebase'],
                   check=True)
    cycles = json.loads(sorted(Path('reports').glob('optimise_2*.json'))[-1].read_text())
    accepted = [c for c in cycles if c.get('accepted')]
    gate = None
    if accepted:
        from insurance_automation.agents.prompts import DEFAULT_PROMPTS  # noqa: F401
        gate = 'run scripts.eval_challenger --role challenger --split heldout with the patch'
    write_report('e5', {'cycles': cycles, 'accepted': bool(accepted), 'heldout_gate': gate
                        or 'not run: no patch was accepted on dev'})
    print([(c.get('node'), c.get('accepted')) for c in cycles])
