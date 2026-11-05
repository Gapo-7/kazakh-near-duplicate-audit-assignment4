"""Prepare a local side-by-side review sheet and a public metadata-only CSV.

The HTML includes source text and must remain local. Reviewers fill the CSV
manually; no label is inferred automatically.
"""

from __future__ import annotations

import csv
import html
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
protocol = json.loads((ROOT / "config" / "frozen_protocol.json").read_text(encoding="utf-8"))
raw = json.loads((ROOT / "results" / "audit_candidates.json").read_text(encoding="utf-8"))
cache = ROOT / "data" / "cache"
out_dir = ROOT / "results"


def key(row: dict) -> tuple:
    a, b = sorted((row["row_i"], row["row_j"]))
    return row["source_key"], row["run_seed"], a, b


combined = {}
for row in raw:
    item = combined.setdefault(key(row), {"source_key": row["source_key"], "run_seed": row["run_seed"],
                                          "row_i": key(row)[2], "row_j": key(row)[3],
                                          "character_score": None, "word_score": None,
                                          "url_i": row["url_i"], "url_j": row["url_j"]})
    method = "character_score" if row["method"].startswith("character_7") else "word_score"
    item[method] = row["score"]

selected = []
for source in protocol["corpora"]:
    items = [item for item in combined.values() if item["source_key"] == source["key"]]
    positive = [item for item in items if (item["character_score"] or 0) >= .8 or (item["word_score"] or 0) >= .8]
    negative = [item for item in items if item not in positive]
    by_seed = {run["seed"]: [] for run in source["runs"]}
    for item in positive:
        by_seed[item["run_seed"]].append(item)
    rng = random.Random(20261105 + sum(map(ord, source["key"])))
    for group in by_seed.values():
        group.sort(key=lambda item: (item["row_i"], item["row_j"]))
        rng.shuffle(group)
    balanced = []
    while len(balanced) < 30 and any(by_seed.values()):
        for seed in sorted(by_seed):
            if by_seed[seed] and len(balanced) < 30:
                balanced.append(by_seed[seed].pop())
    negative.sort(key=lambda item: (-max(item["character_score"] or 0, item["word_score"] or 0), item["run_seed"], item["row_i"], item["row_j"]))
    for item in balanced:
        selected.append({**item, "selection": "flagged_union", "manual_label": "", "error_type": "", "reason": "", "reviewer": ""})
    for item in negative[:10]:
        selected.append({**item, "selection": "nearest_unflagged", "manual_label": "", "error_type": "", "reason": "", "reviewer": ""})

csv_path = out_dir / "Appendix_B_Audit_Cases.csv"
columns = ["source_key", "run_seed", "row_i", "row_j", "character_score", "word_score", "selection", "url_i", "url_j", "manual_label", "error_type", "reason", "reviewer"]
with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=columns)
    writer.writeheader()
    writer.writerows(selected)

block_lookup = {}
for source in protocol["corpora"]:
    for run in source["runs"]:
        block_lookup[source["key"], run["seed"]] = run["block_starts"]


def record(source_key: str, run_seed: int, idx: int) -> dict:
    start = idx // 100 * 100
    if start not in block_lookup[source_key, run_seed]:
        raise ValueError(f"Row outside frozen sample: {source_key} {run_seed} {idx}")
    path = cache / f"{source_key}_{start:08d}.json"
    for row in json.loads(path.read_text(encoding="utf-8")):
        if row["row_idx"] == idx:
            return row
    raise ValueError(f"Missing row {idx} in {path}")


cards = []
for n, item in enumerate(selected, 1):
    source = next(s for s in protocol["corpora"] if s["key"] == item["source_key"])
    a = record(item["source_key"], item["run_seed"], item["row_i"])
    b = record(item["source_key"], item["run_seed"], item["row_j"])
    text_a = str(a.get(source["field"]) or "")
    text_b = str(b.get(source["field"]) or "")
    cards.append(f'<section><h2>Case {n}  {html.escape(item["source_key"])}  seed {item["run_seed"]}</h2>'
                 f'<p>Rows {item["row_i"]} and {item["row_j"]}; selection {item["selection"]}; '
                 f'character score {item["character_score"]}; word score {item["word_score"]}</p>'
                 f'<div class="pair"><article><h3>Record A</h3><p>{html.escape(text_a)}</p></article>'
                 f'<article><h3>Record B</h3><p>{html.escape(text_b)}</p></article></div></section>')
html_path = out_dir / "audit_review_local.html"
html_path.write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Local near-duplicate review</title>'
                     '<style>body{font:15px Arial;margin:2rem;color:#222}section{border-top:2px solid #555;padding:1rem 0}'
                     '.pair{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem}article{background:#f6f7f8;padding:1rem;white-space:pre-wrap;overflow-wrap:anywhere}'
                     'h2{font-size:1.2rem}h3{font-size:1rem}@media(max-width:800px){.pair{grid-template-columns:1fr}}</style><body>'
                     '<h1>Local manual review sheet</h1><p>Fill Appendix_B_Audit_Cases.csv manually. '
                     'This page contains raw dataset text and must not be uploaded or committed.</p>'
                     + "\n".join(cards) + '</body></html>', encoding="utf-8")
print(f"Prepared {len(selected)} cases: {csv_path} and local review HTML")
