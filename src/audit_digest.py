"""Print compact, local-only evidence for manual review cases."""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("source_key", choices=("wikipedia_kk", "kaz_news", "engime", "news_summary"))
parser.add_argument("--selection", choices=("flagged_union", "nearest_unflagged"))
parser.add_argument("--compact", action="store_true")
args = parser.parse_args()
sys.stdout.reconfigure(encoding="utf-8")
protocol = json.loads((ROOT / "config" / "frozen_protocol.json").read_text(encoding="utf-8"))
source = next(item for item in protocol["corpora"] if item["key"] == args.source_key)
with (ROOT / "results" / "Appendix_B_Audit_Cases.csv").open(encoding="utf-8-sig", newline="") as handle:
    cases = [row for row in csv.DictReader(handle) if row["source_key"] == args.source_key and (not args.selection or row["selection"] == args.selection)]


def get_row(idx: int) -> dict:
    start = idx // 100 * 100
    path = ROOT / "data" / "cache" / f"{source['key']}_{start:08d}.json"
    return next(row for row in json.loads(path.read_text(encoding="utf-8")) if row["row_idx"] == idx)


for number, case in enumerate(cases, 1):
    a, b = get_row(int(case["row_i"])), get_row(int(case["row_j"]))
    at, bt = str(a.get(source["field"]) or ""), str(b.get(source["field"]) or "")
    aw, bw = at.split(), bt.split()
    matcher = difflib.SequenceMatcher(None, aw, bw, autojunk=True)
    shared_words = sum(block.size for block in matcher.get_matching_blocks())
    digest = {
        "case": number, "seed": case["run_seed"], "rows": [case["row_i"], case["row_j"]],
        "selection": case["selection"], "scores": [case["character_score"], case["word_score"]],
        "same_url": bool(case["url_i"]) and case["url_i"] == case["url_j"],
        "titles": [str(a.get("title") or "")[:130], str(b.get("title") or "")[:130]],
        "word_counts": [len(aw), len(bw)],
        "shared_exact_word_fraction_of_shorter": round(shared_words / max(1, min(len(aw), len(bw))), 3),
        "heads": [re.sub(r"\s+", " ", at)[:260], re.sub(r"\s+", " ", bt)[:260]],
        "tails": [re.sub(r"\s+", " ", at)[-160:], re.sub(r"\s+", " ", bt)[-160:]],
    }
    if args.compact:
        digest.pop("heads")
        digest.pop("tails")
    print(json.dumps(digest, ensure_ascii=False))
