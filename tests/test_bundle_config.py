import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def jobs():
    out = {}
    for f in (ROOT / 'resources').glob('*.yml'):
        out.update((yaml.safe_load(f.read_text()).get('resources') or {}).get('jobs', {}))
    return out


def test_release_pipeline_dag():
    tasks = {t['task_key']: [d['task_key'] for d in t.get('depends_on', [])]
             for t in jobs()['agentops_release_pipeline']['tasks']}
    assert tasks['setup_uc'] == []
    assert set(tasks['redteam']) == {'eval_challenger', 'parity'}
    assert tasks['decide_release'] == ['redteam']


def _levels(deps: dict[str, set[str]]) -> dict[str, int]:
    depth: dict[str, int] = {}

    def level(k: str) -> int:
        if k not in depth:
            depth[k] = 0 if not deps[k] else 1 + max(level(x) for x in deps[k])
        return depth[k]

    for k in deps:
        level(k)
    return depth


def test_no_more_than_two_parallel_tasks():
    for name, job in jobs().items():
        deps = {t['task_key']: {d['task_key'] for d in t.get('depends_on', [])}
                for t in job['tasks']}
        depth = _levels(deps)
        widths = [list(depth.values()).count(v) for v in set(depth.values())]
        assert max(widths) <= 2, (name, depth)


def test_dashboard_has_six_pages_and_reads_env_catalog_only():
    dash = json.loads((ROOT / 'resources/dashboards/agentops.lvdash.json').read_text())
    assert len(dash['pages']) == 6
    for ds in dash['datasets']:
        sql = ' '.join(ds['queryLines'])
        assert 'agentops_' not in sql  # catalog comes from dataset_catalog = agentops_${var.env}
    res = yaml.safe_load((ROOT / 'resources/dashboard.yml').read_text())
    assert res['resources']['dashboards']['agentops']['dataset_catalog'] == 'agentops_${var.env}'


def test_schedules_paused_in_dev_by_mode():
    assert yaml.safe_load((ROOT / 'databricks.yml').read_text())['targets']['dev']['mode'] == \
        'development'
