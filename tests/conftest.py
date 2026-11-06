import os

import pytest


def pytest_collection_modifyitems(config, items):
    if os.environ.get('PG_TEST_DSN'):
        return
    skip = pytest.mark.skip(reason='PG_TEST_DSN not set')
    for item in items:
        if 'pg' in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def pg_dsn():
    return os.environ['PG_TEST_DSN']
