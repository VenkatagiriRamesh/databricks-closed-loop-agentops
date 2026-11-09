"""E4: a dev-only challenger drops the decision line; replay + scoring raises a sev2 incident."""
import dataclasses
import re
import uuid

from insurance_automation.evaluation.golden import load_golden

from agentops.live import GOLDEN, in_process_target
from agentops.monitoring.incidents import detect_signatures
from agentops.monitoring.scoring import score_day
from agentops.monitoring.traffic import TrafficMix, sample_traffic, to_row
from experiments.common import MapTarget, write_report

N = 24


def replay(target, day):
    traffic = sample_traffic(load_golden(GOLDEN), TrafficMix(), N, seed=11)
    rows = [to_row(t, target.ask(t.question, f'e4-{uuid.uuid4()}'), str(uuid.uuid4()), day)
            for t in traffic]
    return score_day(day, rows), rows


if __name__ == '__main__':
    good = in_process_target()
    bad = MapTarget(good, lambda a: re.sub(r'(?m)^Decision:.*$', '', a).strip(),
                    'dropped_decision_line')
    base_q, _ = replay(good, 'baseline')
    bad_q, _ = replay(bad, 'regressed')
    sigs = detect_signatures(bad_q, base_q)
    sev2 = [s for s in sigs if s.severity == 'sev2']
    write_report('e4', {
        'baseline': dataclasses.asdict(base_q), 'regressed': dataclasses.asdict(bad_q),
        'signatures': [dataclasses.asdict(s) for s in sigs],
        'incident_severity': 'sev2' if sev2 else None, 'n_requests': N})
    print([f'{s.severity} {s.code}' for s in sigs])
