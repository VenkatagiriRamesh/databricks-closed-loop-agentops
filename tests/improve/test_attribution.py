from types import SimpleNamespace as NS

from agentops.improve.attribution import attribute, group_cases
from agentops.improve.traces import SpanView


def item(**kw):
    base = dict(id='i1', expected_route='policy', expected_citations=['COV-01'])
    return NS(**{**base, **kw})


def out(**kw):
    base = dict(route='policy', sql=None, hit_ids=['COV-01'], citations=[], answer='a')
    return NS(**{**base, **kw})


def one(item_, out_, spans, failed):
    cases = attribute(item_, out_, spans, failed)
    assert len(cases) == 1, cases
    return cases[0]


SP = [SpanView('supervisor')]


def test_attr_missed_refusal():
    c = one(item(expected_route='refuse'), out(route='policy'), SP, ['route_accuracy'])
    assert (c.node, c.mode) == ('supervisor', 'missed_refusal')


def test_attr_false_refusal():
    c = one(item(), out(route='refuse'), SP, ['route_accuracy'])
    assert (c.node, c.mode) == ('supervisor', 'false_refusal')


def test_attr_misroute():
    c = one(item(), out(route='analytics'), SP, ['route_accuracy'])
    assert c.mode == 'misroute'


def test_attr_sql_error():
    spans = [SpanView('sql_analyst', outputs={'sql_error': 'PARSE_SYNTAX_ERROR'})]
    c = one(item(), out(), spans, ['sql_exec_match'])
    assert (c.node, c.mode) == ('sql_analyst', 'sql_error')


def test_attr_sql_wrong_result():
    c = one(item(), out(sql='SELECT 1'), [SpanView('sql_analyst')], ['sql_exec_match'])
    assert c.mode == 'sql_wrong_result'


def test_attr_ungrounded():
    c = one(item(), out(hit_ids=['COV-01']), SP, ['groundedness'])
    assert (c.node, c.mode) == ('writer', 'ungrounded')


def test_attr_retrieval_miss():
    c = one(item(), out(hit_ids=[]), SP, ['citation_valid'])
    assert (c.node, c.mode) == ('policy_rag', 'retrieval_miss')


def test_attr_critic_loop():
    spans = [SpanView('critic', outputs={'retries': 9})]
    assert one(item(), out(), spans, []).mode == 'critic_loop'


def test_attr_critic_miss_and_instruction_followed():
    modes = {c.mode for c in attribute(item(), out(), SP, ['safety_pass', 'redteam_leak'])}
    assert modes == {'critic_miss', 'instruction_followed'}


def test_attr_cost_and_latency_hotspots():
    spans = [SpanView('writer', tokens_in=900, duration_ms=10),
             SpanView('policy_rag', tokens_in=10, duration_ms=5000)]
    cases = {c.mode: c.node for c in attribute(item(), out(), spans, ['cost', 'latency_p95'])}
    assert cases == {'cost_hotspot': 'writer', 'latency_hotspot': 'policy_rag'}


def test_attr_multiple_rules_emit_multiple_cases():
    cases = attribute(item(), out(route='analytics', hit_ids=[]), SP,
                      ['route_accuracy', 'groundedness'])
    assert {c.mode for c in cases} == {'misroute', 'retrieval_miss'}


def test_attr_missing_spans_falls_back_to_output_only():
    c = one(item(expected_route='refuse'), out(), [], ['route_accuracy'])
    assert c.node == 'supervisor' and 'no_spans' in c.evidence


def test_group_cases_orders_by_count():
    cs = attribute(item(), out(route='analytics'), SP, ['route_accuracy'])
    cs += attribute(item(id='i2'), out(route='analytics'), SP, ['route_accuracy'])
    cs += attribute(item(id='i3'), out(sql='x'), SP, ['sql_exec_match'])
    g = group_cases(cs)
    assert list(g)[0] == ('supervisor', 'misroute') and len(g[('supervisor', 'misroute')]) == 2
