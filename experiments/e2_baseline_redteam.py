"""E2: baseline red-team of the deployed endpoint (the report is the run_redteam output)."""
import shutil
import subprocess
import sys

from experiments.common import write_report

if __name__ == '__main__':
    subprocess.run([sys.executable, '-m', 'scripts.run_redteam', '--target', 'endpoint'],
                   check=True)
    import json
    from pathlib import Path
    src = json.loads(Path('reports/redteam_latest.json').read_text())
    write_report('e2', src)
    shutil.copy('reports/redteam_latest.json', 'reports/redteam_baseline.json')
