"""E3: evaluated-vs-served parity on the held-out split."""
import json
import subprocess
import sys
from pathlib import Path

from experiments.common import write_report

if __name__ == '__main__':
    subprocess.run([sys.executable, '-m', 'scripts.run_parity', '--golden', 'eval/golden_set.jsonl',
                    '--split', 'heldout'], check=True)
    latest = sorted(Path('reports').glob('parity_2*.json'))[-1]
    d = json.loads(latest.read_text())
    Path('reports/parity_latest.json').write_text(latest.read_text())
    write_report('e3', d)
