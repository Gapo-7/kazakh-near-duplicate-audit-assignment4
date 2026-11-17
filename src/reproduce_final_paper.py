"""Regenerate the final paper's numerical tables from the released evidence.

This checks recorded labels and their links to audit candidates. It cannot
establish who performed the review or independently validate a human label.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ORDER = ("wikipedia_kk", "kaz_news", "engime", "news_summary")
PAPER_NAMES = {
    "wikipedia_kk": "Kazakh Wikipedia",
    "kaz_news": "Kazakh News Corpus",
    "engime": "Engime educational pages",
    "news_summary": "News Summary documents",
}
EXPECTED_TOTALS = {
    "raw": 25500,
    "missing_or_empty": 1400,
    "too_short": 12355,
    "too_long": 64,
    "non_kazakh": 712,
    "before_exact": 10969,
    "exact_removed": 1309,
    "post_exact": 9660,
    "character_flags": 106,
    "word_flags": 99,
}
EXPECTED_REVIEW = {
    ("flagged_union", "repeated_body"): 27,
    ("flagged_union", "changed_version"): 3,
    ("flagged_union", "partial_overlap"): 2,
    ("flagged_union", "shared_template_only"): 1,
    ("nearest_unflagged", "changed_version"): 7,
    ("nearest_unflagged", "partial_overlap"): 13,
    ("nearest_unflagged", "shared_template_only"): 19,
    ("nearest_unflagged", "unrelated"): 1,
}
ERROR_TYPES = {
    ("flagged_union", "repeated_body"): "true_positive",
    ("flagged_union", "changed_version"): "true_positive",
    ("flagged_union", "partial_overlap"): "false_positive",
    ("flagged_union", "shared_template_only"): "false_positive",
    ("nearest_unflagged", "changed_version"): "candidate_false_negative",
    ("nearest_unflagged", "partial_overlap"): "reviewed_negative",
    ("nearest_unflagged", "shared_template_only"): "reviewed_negative",
    ("nearest_unflagged", "unrelated"): "reviewed_negative",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, columns: list[str], rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)


def pair_key(row: dict) -> tuple[str, int, int, int]:
    a, b = sorted((int(row["row_i"]), int(row["row_j"])))
    return row["source_key"], int(row["run_seed"]), a, b


def audit_review(audit_path: Path, candidates_path: Path) -> tuple[Counter, Counter]:
    with audit_path.open(encoding="utf-8-sig", newline="") as handle:
        cases = list(csv.DictReader(handle))
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    candidate_lookup: dict[tuple, dict[str, float]] = defaultdict(dict)
    for candidate in candidates:
        method = "character_score" if candidate["method"].startswith("character_7") else "word_score"
        candidate_lookup[pair_key(candidate)][method] = float(candidate["score"])

    seen: set[tuple] = set()
    labels: Counter = Counter()
    source_selection: Counter = Counter()
    same_url_news_flags = 0
    character_only_news_substantive = 0
    assert len(cases) == 73, f"Expected 73 recorded review pairs, got {len(cases)}"
    for n, row in enumerate(cases, 1):
        key = pair_key(row)
        assert key not in seen, f"Duplicate review pair at line {n + 1}: {key}"
        seen.add(key)
        assert key in candidate_lookup, f"Review pair missing from audit_candidates.json: {key}"
        assert row["reason"].strip() and row["reviewer"].strip(), f"Empty review field at line {n + 1}"
        scores = []
        for field in ("character_score", "word_score"):
            if row[field].strip():
                score = float(row[field])
                assert 0 <= score <= 1, f"Invalid score at line {n + 1}"
                assert field in candidate_lookup[key], f"Missing candidate score at line {n + 1}"
                assert abs(score - candidate_lookup[key][field]) < 0.0000011, f"Score mismatch at line {n + 1}"
                scores.append(score)
            else:
                assert field not in candidate_lookup[key], f"Missing CSV score at line {n + 1}"
        assert scores, f"No similarity score at line {n + 1}"
        selection = row["selection"]
        assert selection in ("flagged_union", "nearest_unflagged")
        assert (max(scores) >= .8) == (selection == "flagged_union"), f"Threshold mismatch at line {n + 1}"
        label_key = selection, row["manual_label"]
        assert label_key in ERROR_TYPES, f"Unexpected recorded label at line {n + 1}: {label_key}"
        assert row["error_type"] == ERROR_TYPES[label_key], f"Error type mismatch at line {n + 1}"
        labels[label_key] += 1
        source_selection[(row["source_key"], selection)] += 1
        if row["source_key"] == "kaz_news" and selection == "flagged_union":
            same_url_news_flags += int(bool(row["url_i"]) and row["url_i"] == row["url_j"])
            character_only_news_substantive += int(
                float(row["character_score"] or 0) >= .8
                and float(row["word_score"] or 0) < .8
                and row["manual_label"] in ("repeated_body", "changed_version")
            )

    assert dict(labels) == EXPECTED_REVIEW, f"Review counts differ from manuscript: {labels}"
    assert sum(count for (selection, _), count in labels.items() if selection == "flagged_union") == 33
    assert sum(count for (selection, _), count in labels.items() if selection == "nearest_unflagged") == 40
    for source in SOURCE_ORDER:
        assert source_selection[(source, "nearest_unflagged")] == 10
    assert {source: source_selection[(source, "flagged_union")] for source in SOURCE_ORDER} == {
        "wikipedia_kk": 2, "kaz_news": 30, "engime": 1, "news_summary": 0
    }
    assert same_url_news_flags == 27
    assert character_only_news_substantive == 2
    return labels, source_selection


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=ROOT / "results" / "final_results.json")
    parser.add_argument("--audit", type=Path, default=ROOT / "results" / "Appendix_B_Audit_Cases.csv")
    parser.add_argument("--candidates", type=Path, default=ROOT / "results" / "audit_candidates.json")
    parser.add_argument("--summary", type=Path, default=ROOT / "results" / "summary.json")
    parser.add_argument("--protocol", type=Path, default=ROOT / "config" / "frozen_protocol.json")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "final_paper" / "generated")
    args = parser.parse_args()
    data = json.loads(args.results.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    assert data["protocol_selection_sha256"] == protocol["selection_sha256"]
    for source in protocol["corpora"]:
        blocks = [start for run in source["runs"] for start in run["block_starts"]]
        assert len(blocks) == len(set(blocks)), f"Overlapping sample blocks: {source['key']}"
    runs = data["results"]
    assert len(runs) == 12
    by_source: dict[str, list[dict]] = defaultdict(list)
    for run in runs:
        by_source[run["source_key"]].append(run)
    assert set(by_source) == set(SOURCE_ORDER)
    assert all(len(group) == 3 for group in by_source.values())

    totals: Counter = Counter()
    table2: list[list[object]] = []
    table3: list[list[object]] = []
    sensitivity: list[list[object]] = []
    for source in SOURCE_ORDER:
        group = sorted(by_source[source], key=lambda run: run["run_seed"])
        source_counts: Counter = Counter()
        for run in group:
            excluded = run["excluded"]
            counts = {
                "raw": run["raw_sample"],
                "missing_or_empty": excluded.get("missing_field", 0),
                "too_short": excluded.get("below_min_words", 0),
                "too_long": excluded.get("above_max_words", 0),
                "non_kazakh": excluded.get("uncertain_kazakh", 0),
                "before_exact": run["eligible_before_exact"],
                "exact_removed": excluded.get("exact_removed", 0),
                "post_exact": run["post_exact"],
                "character_flags": run["methods"]["character_7"]["threshold_results"]["0.8"]["flagged_records"],
                "word_flags": run["methods"]["word_5"]["threshold_results"]["0.8"]["flagged_records"],
            }
            assert counts["raw"] == sum(counts[key] for key in
                ("missing_or_empty", "too_short", "too_long", "non_kazakh", "before_exact"))
            assert counts["before_exact"] == counts["exact_removed"] + counts["post_exact"]
            source_counts.update(counts)
            totals.update(counts)
            char = run["methods"]["character_7"]["threshold_results"]
            word = run["methods"]["word_5"]["threshold_results"]
            assert set(word["0.8"]["flagged_row_indices"]) <= set(char["0.8"]["flagged_row_indices"])
            table3.append([source, PAPER_NAMES[source], run["run_seed"], counts["post_exact"],
                           counts["character_flags"], counts["word_flags"]])
            for threshold in ("0.75", "0.8", "0.85", "0.9"):
                sensitivity.append([source, run["run_seed"], threshold,
                                    char[threshold]["flagged_records"], char[threshold]["flag_rate"] * 100])
        table2.append([source, PAPER_NAMES[source], source_counts["raw"], source_counts["post_exact"],
                       source_counts["exact_removed"], source_counts["character_flags"],
                       source_counts["word_flags"]])
    assert dict(totals) == EXPECTED_TOTALS, f"Run totals differ from manuscript: {totals}"
    threshold_totals = Counter()
    for source, _seed, threshold, count, _rate in sensitivity:
        threshold_totals[(source, threshold)] += count
    assert {threshold: threshold_totals[("kaz_news", threshold)] for threshold in
            ("0.75", "0.8", "0.85", "0.9")} == {
                "0.75": 104, "0.8": 103, "0.85": 96, "0.9": 76}
    assert {threshold: threshold_totals[("wikipedia_kk", threshold)] for threshold in
            ("0.75", "0.8", "0.85", "0.9")} == {
                "0.75": 2, "0.8": 2, "0.85": 0, "0.9": 0}
    assert {threshold: threshold_totals[("engime", threshold)] for threshold in
            ("0.75", "0.8", "0.85", "0.9")} == {
                "0.75": 1, "0.8": 1, "0.85": 1, "0.9": 0}
    assert {threshold: threshold_totals[("news_summary", threshold)] for threshold in
            ("0.75", "0.8", "0.85", "0.9")} == {
                "0.75": 1, "0.8": 0, "0.85": 0, "0.9": 0}
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    assert summary["input_results_sha256"] == sha256(args.results)
    summary_by_source = {row["source_key"]: row for row in summary["corpora"]}
    assert set(summary_by_source) == set(SOURCE_ORDER)
    assert round(summary_by_source["kaz_news"]["character_mean_rate"] * 100, 3) == 2.630
    assert round(summary_by_source["kaz_news"]["character_sd_rate"] * 100, 3) == 2.325
    assert round(summary_by_source["kaz_news"]["word_mean_rate"] * 100, 3) == 2.502
    assert round(summary_by_source["kaz_news"]["word_sd_rate"] * 100, 3) == 2.261
    assert round(summary_by_source["kaz_news"]["difference_percentage_points"], 3) == 0.129
    assert summary_by_source["kaz_news"]["exact_sign_flip_p"] == .5
    assert all(row["holm_adjusted_p"] == 1 for row in summary_by_source.values())
    table2.append(["TOTAL", "Total", totals["raw"], totals["post_exact"], totals["exact_removed"],
                   totals["character_flags"], totals["word_flags"]])
    labels, source_selection = audit_review(args.audit, args.candidates)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.out_dir / "table_2_record_flow.csv",
              ["source_key", "Collection", "Raw rows", "Post-exact records", "MD5 removals",
               "Character 7-gram flags", "Word 5-gram flags"], table2)
    write_csv(args.out_dir / "table_3_runs.csv",
              ["source_key", "Collection", "Seed", "Post-exact", "Character flags", "Word flags"], table3)
    write_csv(args.out_dir / "threshold_sensitivity.csv",
              ["source_key", "Seed", "Jaccard threshold", "Character flags", "Character flag rate percent"], sensitivity)
    write_csv(args.out_dir / "manual_review_summary.csv",
              ["Selection", "Manual label", "Recorded pairs"],
              [[selection, label, count] for (selection, label), count in sorted(labels.items())])
    evidence = [
        "# Numerical evidence for the final paper", "",
        "Generated from released run JSON, audit candidates and recorded review CSV.",
        "This verifies file consistency, not the truth of human labels or an independent rerun.", "",
        f"- Final run JSON SHA-256: `{sha256(args.results)}`",
        f"- Review CSV SHA-256: `{sha256(args.audit)}`",
        f"- Audit candidates JSON SHA-256: `{sha256(args.candidates)}`", "",
        "## Record flow", "",
        f"- {totals['raw']:,} raw rows; {totals['before_exact']:,} passed eligibility; "
        f"{totals['exact_removed']:,} MD5 removals; {totals['post_exact']:,} post-exact records.",
        f"- Exclusions: {totals['missing_or_empty']:,} missing or empty; {totals['too_short']:,} too short; "
        f"{totals['too_long']:,} too long; {totals['non_kazakh']:,} Kazakh-letter screen.",
        f"- At 0.80: {totals['character_flags']} character flags and {totals['word_flags']} word flags. "
        "Every word-flagged row is also character-flagged within its run.", "",
        "## Targeted review", "",
        "- 73 distinct recorded pairs link to audit candidates and match their recorded scores.",
        "- 33 flagged pairs: 27 repeated bodies, 3 changed versions, 2 partial overlaps, 1 shared template.",
        "- 40 below-threshold pairs: 7 changed versions, 13 partial overlaps, 19 shared templates, 1 unrelated.",
        "- These targeted cases do not yield corpus-wide precision or recall.", "",
        "## Output map", "",
        "- Table 2: `table_2_record_flow.csv`.",
        "- Table 3: `table_3_runs.csv`.",
        "- Threshold counts behind Figure 2: `threshold_sensitivity.csv`.",
        "- Figure 1 means/SD and Figure 2 mean rates: regenerate with `src/summarize_results.py`; "
        "see `summary.json` and the two figure files.",
        "- Manual-review claims: `manual_review_summary.csv`.", "",
        "Source-specific review selection: " + ", ".join(
            f"{PAPER_NAMES[source]} {source_selection[(source, 'flagged_union')]} flagged + "
            f"{source_selection[(source, 'nearest_unflagged')]} below threshold" for source in SOURCE_ORDER) + ".", "",
    ]
    (args.out_dir / "evidence_report.md").write_text("\n".join(evidence), encoding="utf-8")
    print(f"Verified 12 runs and 73 recorded review pairs; wrote {args.out_dir}")


if __name__ == "__main__":
    main()
