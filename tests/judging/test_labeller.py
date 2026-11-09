import csv

from scripts.label_calibration import label


def test_labeller_resumes(tmp_path, monkeypatch):
    path = tmp_path / 'c.csv'
    with open(path, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['id', 'answer', 'human_label'])
        w.writeheader()
        w.writerows([{'id': 'a', 'answer': 'x', 'human_label': ''},
                     {'id': 'b', 'answer': 'y', 'human_label': ''}])
    answers = iter(['p', 'q'])
    monkeypatch.setattr('builtins.input', lambda prompt='': next(answers))
    assert label(str(path)) == 1
    answers2 = iter(['f'])
    monkeypatch.setattr('builtins.input', lambda prompt='': next(answers2))
    assert label(str(path)) == 1  # resumed at row b, row a untouched
    rows = list(csv.DictReader(open(path)))
    assert [r['human_label'] for r in rows] == ['pass', 'fail']
