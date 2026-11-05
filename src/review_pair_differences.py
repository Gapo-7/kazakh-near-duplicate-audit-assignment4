"""Show different token spans for one local audit pair; do not publish output."""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument("source_key")
p.add_argument("row_i", type=int)
p.add_argument("row_j", type=int)
a = p.parse_args()
sys.stdout.reconfigure(encoding="utf-8")
source = next(item for item in json.loads((ROOT / "config" / "frozen_protocol.json").read_text(encoding="utf-8"))["corpora"] if item["key"] == a.source_key)


def row(idx):
    path = ROOT / "data" / "cache" / f"{a.source_key}_{idx // 100 * 100:08d}.json"
    return next(value for value in json.loads(path.read_text(encoding="utf-8")) if value["row_idx"] == idx)


r1, r2 = row(a.row_i), row(a.row_j)
w1, w2 = str(r1.get(source["field"]) or "").split(), str(r2.get(source["field"]) or "").split()
print("TITLE A:", r1.get("title"), "URL:", r1.get("url"))
print("TITLE B:", r2.get("title"), "URL:", r2.get("url"))
print("WORDS:", len(w1), len(w2))
m = difflib.SequenceMatcher(None, w1, w2)
for tag, i1, i2, j1, j2 in m.get_opcodes():
    if tag == "equal":
        continue
    print("\n", tag, f"A[{i1}:{i2}] B[{j1}:{j2}]")
    print("A:", " ".join(w1[i1:i2])[:700])
    print("B:", " ".join(w2[j1:j2])[:700])
