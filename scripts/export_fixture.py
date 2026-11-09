"""Export the claims facts the red-team oracles need from the curated tables (read-only)."""
import json
from pathlib import Path

from insurance_automation.data.generate import INJECTION_NOTE
from insurance_automation.tools.authority import required_authority

from agentops.config import load_config
from agentops.connect import sql_runner

if __name__ == '__main__':
    cfg = load_config()
    run = sql_runner(cfg)
    rows = run('SELECT claim_id, amount, adjuster_notes FROM insurance_automation.curated.claims')
    claims, notes = {}, []
    for r in rows:
        note = r.get('adjuster_notes') or ''
        claims[r['claim_id']] = {
            'amount': float(r['amount']), 'has_injection': INJECTION_NOTE in note,
            'expected_authority': required_authority(float(r['amount']), False)}
        if len(note) >= 20 and INJECTION_NOTE not in note:
            notes.append(note)
    out = Path('redteam/fixture.json')
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({'claims': claims, 'notes': sorted(set(notes))}, indent=1))
    masked = sum(1 for r in rows if not r.get('adjuster_notes'))
    print(f'{len(claims)} claims, {sum(c["has_injection"] for c in claims.values())} injected, '
          f'{masked} with empty/masked notes -> {out}')
