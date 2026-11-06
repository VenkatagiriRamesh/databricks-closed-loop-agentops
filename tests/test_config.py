from agentops.config import load_config


def test_defaults_and_catalog():
    cfg = load_config({})
    assert cfg.catalog == 'agentops_dev'
    assert cfg.table('release', 'decisions') == 'agentops_dev.release.decisions'
    assert cfg.lakebase_database == 'agentops' and cfg.max_attacks == 60


def test_env_overrides():
    cfg = load_config({'AGENTOPS_ENV': 'prod', 'JUDGE_MODELS': 'a, b', 'MAX_ATTACKS': '10'})
    assert cfg.catalog == 'agentops_prod'
    assert cfg.judge_models == ('a', 'b') and cfg.max_attacks == 10
