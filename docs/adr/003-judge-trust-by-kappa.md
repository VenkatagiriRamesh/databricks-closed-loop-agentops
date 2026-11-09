# ADR-003: A judge blocks a release only when its agreement with the owner is measured

LLM judges (the copilot's two, and DeepEval's faithfulness and GEval) are not ground truth. A
judge metric blocks a release only if Cohen's kappa against the owner's labels is >= 0.6 on >= 20
labels (the `panel` pseudo-judge, the per-item median, is what counts). Until then the metric is
**advisory**: gate reasons on it become `JUDGE_ADVISORY:` warnings. With no labels, every judge
metric is advisory, and the README says so. Labels come from `scripts/label_calibration.py`.
