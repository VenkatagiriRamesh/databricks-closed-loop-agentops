from insurance_automation.agents.nodes import ESCALATION_ANSWER

from agentops.target import EndpointTarget, parse_decision_line


def test_parse_decision_line_kinds():
    cases = {
        'x\n\nDecision: AUTO-SETTLED claim C00001; payable 10.00; ok':
            ('auto_settled', 'auto'),
        'Decision: AUTO-DENIED claim C00002 under EXC-01; no human': ('auto_denied', 'auto'),
        'd\n\nDecision: APPROVED by senior_adjuster for claim C00009; payable 1.00.':
            ('approved', 'senior_adjuster'),
        'Decision: DENIAL CONFIRMED by manager for claim C00001.': ('denial_confirmed', 'manager'),
        'Decision: REFERRAL TO SIU CONFIRMED for claim C00114; no payment authorised.':
            ('siu_confirmed', 'siu'),
        'Decision: SIU REFERRAL REJECTED by manager for claim C00114; return.':
            ('siu_rejected', 'manager'),
        'Decision: EDITED by adjuster.': ('edited', 'adjuster'),
        ESCALATION_ANSWER: ('escalated', None),
    }
    for text, (kind, authority) in cases.items():
        d = parse_decision_line(text)
        assert (d.kind, d.authority) == (kind, authority), text
    line = 'Decision: APPROVED by manager for claim C00017; x'
    assert parse_decision_line(line).claim_id == 'C00017'


def test_parse_decision_line_pending():
    text = ('Proposed decision for claim C00009: approve_payment (payable 12851.7).\n'
            'Approval required from: senior_adjuster.\nRun id: abc')
    d = parse_decision_line(text)
    assert (d.kind, d.authority, d.claim_id) == ('pending', 'senior_adjuster', 'C00009')


def test_parse_decision_line_absent():
    for text in ('', 'I cannot help with that.', 'Error: boom', None):
        d = parse_decision_line(text)
        assert (d.kind, d.authority, d.claim_id) == (None, None, None)


def test_endpoint_target_parses_responses_payload():
    payload = {'output': [{'content': [{'type': 'output_text',
                                         'text': 'ok\n\nDecision: AUTO-SETTLED claim C00001; p'}]}]}
    t = EndpointTarget('ep', lambda ep, body: payload, sleep=lambda s: None)
    r = t.ask('q', 's')
    assert r.status == 'ok' and r.decision.kind == 'auto_settled' and r.has_decision_line


def test_endpoint_target_retries_then_errors():
    calls = []

    def post(ep, body):
        calls.append(1)
        raise RuntimeError('cold start')

    t = EndpointTarget('ep', post, max_retries=2, sleep=lambda s: None)
    r = t.ask('q', 's')
    assert r.status == 'error' and len(calls) == 3 and 'cold start' in r.error


def test_endpoint_target_recovers_after_cold_start():
    state = {'n': 0}

    def post(ep, body):
        state['n'] += 1
        if state['n'] < 2:
            raise RuntimeError('503')
        return {'output': [{'content': [{'text': 'hi'}]}]}

    r = EndpointTarget('ep', post, sleep=lambda s: None).ask('q', 's')
    assert r.status == 'ok' and r.answer == 'hi'


def test_inprocess_target_maps_graph_output(monkeypatch):
    from insurance_automation.agents import graph as agent_graph
    from insurance_automation.contracts import AgentOutput

    from agentops.target import InProcessClaimsTarget

    out = AgentOutput(answer='d\n\nDecision: AUTO-SETTLED claim C00001; payable 5.00; x',
                      route='claim_decision', tools_called=['get_claim'],
                      required_authority='auto', approval_status='not_required')
    monkeypatch.setattr(agent_graph, 'invoke',
                        lambda g, q, thread_id: agent_graph.GraphResult('done', out))
    t = InProcessClaimsTarget(ctx_factory=lambda: None)
    t._graph = object()
    r = t.ask('decide C00001', 's1')
    assert r.status == 'ok' and r.decision.kind == 'auto_settled' and r.route == 'claim_decision'
    assert r.tools_called == ['get_claim']


def test_is_refusal_recognises_the_real_refusal_text_without_a_route():
    from insurance_automation.agents.nodes import REFUSAL_ANSWER

    from agentops.target import TargetResponse
    assert TargetResponse(REFUSAL_ANSWER).is_refusal
    assert not TargetResponse('Thirty days (WAIT-01).').is_refusal
