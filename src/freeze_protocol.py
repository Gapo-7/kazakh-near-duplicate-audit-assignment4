"""Create the pre-registered final-sample manifest from the Assignment 3 pilot.

Run this once, inspect the output, and upload Appendix A before running
run_experiment.py. The final samples exclude every pilot 100-row block.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path


SEEDS = (20261105, 20261106, 20261107)
BLOCK_SIZE = 100


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def build(pilot: dict) -> dict:
    corpora = []
    for old in pilot["manifests"]:
        spec = old["spec"]
        used = set(old["block_starts"])
        available = [i for i in range(0, old["population_rows"] - BLOCK_SIZE + 1, BLOCK_SIZE) if i not in used]
        count = spec["blocks"]
        runs = []
        for seed in SEEDS:
            rng = random.Random(seed + sum(map(ord, spec["key"])))
            chosen = sorted(rng.sample(available, count))
            available = [i for i in available if i not in set(chosen)]
            runs.append({"seed": seed, "block_starts": chosen, "raw_rows_expected": count * BLOCK_SIZE})
        corpora.append({
            "key": spec["key"], "label": spec["label"], "dataset": spec["dataset"],
            "config": spec["config"], "field": spec["field"],
            "revision": old["revision"], "population_rows_at_freeze": old["population_rows"],
            "pilot_block_starts": old["block_starts"], "runs": runs,
        })
    protocol = {
        "status": "PREPARED_NOT_UPLOADED_NOT_RUN",
        "research_question": "To what extent does near-duplicate content remain in publicly available Kazakh-language datasets for LLM pretraining after exact deduplication?",
        "design": "Three pre-selected, non-overlapping 100-row block samples per corpus; no pilot block reused",
        "block_size": BLOCK_SIZE, "seeds": list(SEEDS),
        "eligibility": {"min_words": 150, "max_words": 5000, "engime_kazakh_letter_min": 3, "engime_kazakh_letter_share_min": 0.01},
        "exact_normalization": "NFC and collapsed whitespace; MD5 of UTF-8 normalized text, as in Assignment 3",
        "similarity_normalization": "NFC, collapsed whitespace, casefold, punctuation replaced by spaces",
        "conditions": {
            "baseline_1": "Exact-only deduplication (MD5); residual near-duplicate flags set to zero by design",
            "baseline_2": "Word 5-gram set Jaccard at 0.80; connected-component clusters",
            "proposed": "Character 7-gram set Jaccard at 0.80; connected-component clusters",
        },
        "primary_metric": "Within each corpus, redundant post-exact records / eligible post-exact records at character 7-gram Jaccard >= 0.80",
        "secondary_metrics": ["exact duplicates removed", "word 5-gram flagged rate", "retained record count", "pair count", "runtime", "manual precision on flagged candidate pairs"],
        "planned_sensitivity": [0.75, 0.80, 0.85, 0.90],
        "statistical_plan": "Across three independent block samples, report per-run rates and mean +/- sample SD by corpus. For paired proposed-versus-word-baseline differences, report per-run differences and an exact sign-flip permutation p-value; apply Holm correction across four corpora. Treat n=3 inference as exploratory, and report absolute percentage-point differences.",
        "manual_audit_plan": "Review all union-of-method flagged pairs up to 30 per corpus; if fewer than 30 failures exist, review all. Also review up to 30 nearest unflagged pairs per corpus. Code false positives, false negatives when found, boilerplate overlap, true repeated body, changed version, and uncertain. Keep annotation decisions in a separate audit file.",
        "hypothesis": "H1: after exact deduplication, character 7-gram Jaccard detects additional residual near-duplicate records in at least one of the four selected corpora. H0: it detects none in any selected corpus.",
        "support_rule": "H1 is supported descriptively if at least one post-exact pair reaches 0.80 in the final samples and manual inspection confirms repeated substantive body content; otherwise H1 is not supported. Do not interpret the three-run comparison as a population prevalence estimate.",
        "corpora": corpora,
    }
    protocol["selection_sha256"] = hashlib.sha256(canonical_bytes(corpora)).hexdigest()
    return protocol


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pilot_json", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    pilot = json.loads(args.pilot_json.read_text(encoding="utf-8"))
    protocol = build(pilot)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(protocol, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Selection SHA-256:", protocol["selection_sha256"])
    for source in protocol["corpora"]:
        print(source["key"], [len(run["block_starts"]) for run in source["runs"]])


if __name__ == "__main__":
    main()
