from scripts.smoke_e2e import CHECKS, MILESTONES, run


def test_smoke_checks_cover_every_milestone():
    assert {m for m, *_ in CHECKS} == set(MILESTONES) - set()  # M1..M7 each have a check


def test_smoke_stops_at_first_failure(capsys):
    calls = []

    def ok():
        calls.append('ok')

    def bad():
        raise AssertionError('boom')

    def never():
        calls.append('never')

    checks = [('M1', 'a', ok, False), ('M1', 'b', bad, False), ('M2', 'c', never, False)]
    assert run('M7', False, checks) == 1
    assert calls == ['ok']
    assert 'FAIL M1/b: boom' in capsys.readouterr().out


def test_smoke_respects_upto_and_live_skip(capsys):
    checks = [('M1', 'a', lambda: None, True), ('M2', 'b', lambda: 1 / 0, False)]
    assert run('M1', False, checks) == 0
    assert 'SKIP M1/a' in capsys.readouterr().out
