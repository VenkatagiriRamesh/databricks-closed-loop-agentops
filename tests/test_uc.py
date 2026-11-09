from agentops.uc import SCHEMAS, setup_uc


def test_setup_is_idempotent_sql_and_creates_all_schemas():
    ran = []
    setup_uc('agentops_dev', ran.append)
    assert ran[0] == 'CREATE CATALOG IF NOT EXISTS agentops_dev'
    assert all('IF NOT EXISTS' in s for s in ran) and len(ran) == 2 + len(SCHEMAS)
