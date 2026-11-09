"""00_setup: create the agentops_<env> catalog and its schemas via the SQL warehouse.

Usage: python schema_mgt/00_setup.py (same as `python -m scripts.setup_uc`). Re-runnable.
"""
import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
runpy.run_module('scripts.setup_uc', run_name='__main__')
