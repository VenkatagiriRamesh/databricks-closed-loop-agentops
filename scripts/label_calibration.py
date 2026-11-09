"""Interactive, resumable labeller for eval/calibration_to_label.csv. The OWNER runs this.

Writes human_label (pass/fail) back to the CSV after every answer, so quitting and re-running
resumes where you stopped. Keys: p = pass, f = fail, s = skip, q = quit.
"""
from __future__ import annotations

import argparse
import csv


def label(path: str) -> int:
    with open(path, newline='', encoding='utf-8') as fh:
        rows = list(csv.DictReader(fh))
        fields = list(rows[0].keys()) if rows else []
    if 'human_label' not in fields:
        fields.append('human_label')
    done = 0
    for row in rows:
        if (row.get('human_label') or '').strip():
            continue
        print('\n' + '=' * 70)
        for k, v in row.items():
            if k != 'human_label':
                print(f'{k}: {v}')
        ans = input('\n[p]ass / [f]ail / [s]kip / [q]uit > ').strip().lower()
        if ans == 'q':
            break
        if ans in ('p', 'f'):
            row['human_label'] = 'pass' if ans == 'p' else 'fail'
            done += 1
            with open(path, 'w', newline='', encoding='utf-8') as fh:
                w = csv.DictWriter(fh, fieldnames=fields)
                w.writeheader()
                w.writerows(rows)
    return done


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default='eval/calibration_to_label.csv')
    print(f'labelled {label(ap.parse_args().csv)} rows this session')
