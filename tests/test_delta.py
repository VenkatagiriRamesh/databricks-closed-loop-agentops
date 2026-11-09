from agentops.delta import upsert_rows


def test_upsert_is_delete_then_insert_and_escapes():
    sql = []
    upsert_rows(sql.append, 'c.s.t', "k'1", [{'a': "it's"}])
    assert sql[0].startswith('CREATE TABLE IF NOT EXISTS c.s.t')
    assert sql[1] == "DELETE FROM c.s.t WHERE key = 'k''1'"
    assert "it''s" in sql[2]


def test_upsert_empty_rows_only_clears():
    sql = []
    upsert_rows(sql.append, 't', 'k', [])
    assert len(sql) == 2
