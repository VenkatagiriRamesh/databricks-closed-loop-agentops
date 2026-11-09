import os

import pytest
from scripts.job_entry import main


def test_job_entry_sets_env_and_runs_module():
    ran = []
    main(['--script', 'run_redteam', '--env', 'prod', '--warehouse-id', 'w1', '--', '--no-lakebase'],
         runner=ran.append)
    assert ran == ['scripts.run_redteam']
    assert os.environ['AGENTOPS_ENV'] == 'prod' and os.environ['DATABRICKS_WAREHOUSE_ID'] == 'w1'


def test_job_entry_rejects_bad_script_name():
    with pytest.raises(SystemExit):
        main(['--script', '../evil'], runner=lambda m: None)
