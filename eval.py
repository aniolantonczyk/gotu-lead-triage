#!/usr/bin/env python3
"""Score a decision log against the hand-labeled synthetic leads.

Usage: python3 eval.py runs/rules_<timestamp>.jsonl [runs/claude_<timestamp>.jsonl ...]
Prints a report and writes eval_report.md next to this file.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def load_truth():
    truth = {}
    for name in ("synthetic_leads.csv", "hard_leads.csv"):
        with open(ROOT / "data" / name, newline="", encoding="utf-8") as f:
            truth.update({r["id"]: r for r in csv.DictReader(f)})
    return truth


def score(path, truth):
    rows = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
    n = len(rows)
    aud_ok = stage_ok = review = parse_fail = 0
    conf_right, conf_wrong, misses = [], [], []
    for r in rows:
        t = truth[r["lead_id"]]
        d = r["decision"]
        a = d["audience"] == t["true_audience"]
        s = d["recommended_stage"] == t["true_stage"]
        aud_ok += a
        stage_ok += s
        review += r["needs_review"]
        parse_fail += r["status"] != "ok"
        (conf_right if (a and s) else conf_wrong).append(d["confidence"])
        if not (a and s):
            misses.append(
                f"lead {r['lead_id']}: predicted {d['audience']}/{d['recommended_stage']} "
                f"(conf {d['confidence']:.2f}), expected {t['true_audience']}/{t['true_stage']}. "
                f"Text: \"{t['form_text'][:70]}\""
            )
    avg = lambda xs: sum(xs) / len(xs) if xs else float("nan")
    return {
        "file": Path(path).name,
        "n": n,
        "audience_acc": aud_ok / n,
        "stage_acc": stage_ok / n,
        "review_rate": review / n,
        "parse_failures": parse_fail,
        "conf_right": avg(conf_right),
        "conf_wrong": avg(conf_wrong),
        "misses": misses,
    }


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    truth = load_truth()
    lines = ["# Triage eval report", "", "Synthetic leads, hand-labeled. Small sample: treat as a smoke test, not a benchmark.", ""]
    lines += ["| Run | Leads | Audience acc. | Stage acc. | Flagged for review | Parse failures | Avg conf. (right) | Avg conf. (wrong) |", "|---|---|---|---|---|---|---|---|"]
    results = [score(p, truth) for p in sys.argv[1:]]
    for r in results:
        lines.append(
            f"| {r['file']} | {r['n']} | {r['audience_acc']:.0%} | {r['stage_acc']:.0%} | {r['review_rate']:.0%} | "
            f"{r['parse_failures']} | {r['conf_right']:.2f} | {r['conf_wrong']:.2f} |"
        )
    for r in results:
        lines += ["", f"## Misses: {r['file']}", ""]
        lines += [f"- {m}" for m in r["misses"]] or ["- none"]
    report = "\n".join(lines)
    print(report)
    (ROOT / "eval_report.md").write_text(report + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
