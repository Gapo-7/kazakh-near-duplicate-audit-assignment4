"""Audit the generated result files against the frozen protocol."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
protocol_path = ROOT / "config" / "frozen_protocol.json"
freeze_path = ROOT / "protocol" / "local_freeze_record.json"
result_path = ROOT / "results" / "final_results.json"
protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
results = json.loads(result_path.read_text(encoding="utf-8"))

assert hashlib.sha256(protocol_path.read_bytes()).hexdigest() == freeze["protocol_sha256"]
assert hashlib.sha256((ROOT / "protocol" / "Assignment4_Appendix_A_Protocol_Freeze.docx").read_bytes()).hexdigest() == freeze["appendix_sha256"]
assert results["protocol_selection_sha256"] == protocol["selection_sha256"]
assert results["moodle_uploaded_before_final_runs"] is False
assert len(results["results"]) == 12

expected = {(source["key"], run["seed"]): (source, run)
            for source in protocol["corpora"] for run in source["runs"]}
seen = set()
for result in results["results"]:
    key = result["source_key"], result["run_seed"]
    assert key in expected and key not in seen, key
    seen.add(key)
    source, run = expected[key]
    assert result["block_starts"] == run["block_starts"]
    assert result["revision"] == source["revision"]
    assert result["raw_sample"] == run["raw_rows_expected"]
    assert result["raw_sample"] == result["eligible_before_exact"] + sum(v for k, v in result["excluded"].items() if k != "exact_removed")
    assert result["eligible_before_exact"] == result["post_exact"] + result["excluded"].get("exact_removed", 0)
    assert result["exact_only"]["retained_records"] == result["post_exact"]
    assert result["exact_only"]["flagged_records"] == 0
    for method in ("word_5", "character_7"):
        values = result["methods"][method]["threshold_results"]
        flagged = []
        for threshold in ("0.75", "0.8", "0.85", "0.9"):
            measure = values[threshold]
            assert measure["flagged_records"] + measure["retained_records"] == result["post_exact"]
            assert measure["retained_records"] == measure["cluster_count"]
            assert len(measure["flagged_row_indices"]) == measure["flagged_records"]
            assert abs(measure["flag_rate"] - measure["flagged_records"] / result["post_exact"]) < 1e-12 if result["post_exact"] else measure["flag_rate"] == 0
            flagged.append(measure["flagged_records"])
        assert flagged == sorted(flagged, reverse=True), (key, method, flagged)
assert seen == set(expected)
print("Validated all 12 planned runs, frozen sample offsets, counts and threshold monotonicity")
