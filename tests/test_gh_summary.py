from scripts.gh_summary import render_summary


def test_summary_block_shows_reasons():
    out = render_summary({'verdict': 'block', 'candidate': 'c1',
                          'reasons': ['ASR:pii_exfiltration: 0.100 exceeds ceiling 0.000 (n=25)'],
                          'warnings': [], 'inputs': {}})
    assert 'BLOCK' in out and 'ASR:pii_exfiltration' in out and 'approve_release' not in out


def test_summary_awaiting_approval_shows_candidate():
    out = render_summary({'verdict': 'promote', 'candidate': 'abc-123', 'reasons': [],
                          'warnings': ['x'], 'inputs': {'asr': {'sql_abuse': {
                              'n': 25, 'successes': 0, 'asr': 0.0, 'ceiling': 0.0}}}})
    assert 'abc-123' in out and 'approve_release' in out and '| sql_abuse | 25 |' in out
