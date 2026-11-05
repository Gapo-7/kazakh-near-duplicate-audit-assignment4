"""Recompute all deterministic metrics from local cached rows for technical QA.

This is not the required independent classmate reproduction in Appendix C.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import run_experiment as experiment


ROOT = Path(__file__).resolve().parents[1]
protocol = json.loads((ROOT / "config" / "frozen_protocol.json").read_text(encoding="utf-8"))
result_path = ROOT / "results" / "final_results.json"
saved = json.loads(result_path.read_text(encoding="utf-8"))
lookup = {(r["source_key"], r["run_seed"]): r for r in saved["results"]}
checked = []
for source in protocol["corpora"]:
    for run in source["runs"]:
        expected = lookup[source["key"], run["seed"]]
        current, _ = experiment.analyse(source, run, protocol, ROOT / "data" / "cache")
        for key in ("raw_sample", "excluded", "eligible_before_exact", "post_exact", "total_words_post_exact", "source_name_counts", "exact_only"):
            if current[key] != expected[key]:
                raise AssertionError((source["key"], run["seed"], key))
        for method in ("word_5", "character_7"):
            for key in ("pairs_checked", "pairs_skipped_by_size_bound", "threshold_results"):
                if current["methods"][method][key] != expected["methods"][method][key]:
                    raise AssertionError((source["key"], run["seed"], method, key))
        checked.append({"source_key": source["key"], "seed": run["seed"], "matched": True})
record = {"checked_utc": datetime.now(timezone.utc).isoformat(),
          "final_results_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(),
          "checked_runs": checked,
          "note": "Same-machine cache recomputation by project scripts; not an independent student reproduction."}
out = ROOT / "results" / "technical_recheck.json"
out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print("Recomputed", len(checked), "runs from cache with exact metric agreement")
