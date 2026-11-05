"""Run the pre-registered Assignment 4 experiment after Appendix A is uploaded.

Python 3.12+ standard library only. The script refuses to run without a
Moodle upload record and stops if any public dataset revision has changed.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import platform
import re
import statistics
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THRESHOLDS = (0.75, 0.80, 0.85, 0.90)
KAZAKH_LETTERS = set("әғқңөұүһі")


def get_json(url: str, attempts: int = 12) -> dict:
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "KazakhNearDuplicateAssignment4/1.0"})
            with urllib.request.urlopen(req, timeout=90) as response:
                return json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            if attempt == attempts - 1:
                raise
            if isinstance(exc, urllib.error.HTTPError) and exc.code == 429:
                header = exc.headers.get("Retry-After", "")
                delay = max(45, int(header)) if header.isdigit() else 60
            else:
                delay = min(2 ** attempt, 20)
            print(f"Fetch retry {attempt + 1}/{attempts} after {type(exc).__name__}: sleeping {delay}s", flush=True)
            time.sleep(delay)
    raise AssertionError("unreachable")


def current_revision(dataset: str) -> str:
    return get_json("https://huggingface.co/api/datasets/" + dataset)["sha"]


def fetch_rows(source: dict, start: int, cache_dir: Path) -> list[dict]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{source['key']}_{start:08d}.json"
    if path.exists():
        rows = json.loads(path.read_text(encoding="utf-8"))
    else:
        query = urllib.parse.urlencode({
            "dataset": source["dataset"], "config": source["config"],
            "split": "train", "offset": start, "length": 100,
        })
        payload = get_json("https://datasets-server.huggingface.co/rows?" + query)
        rows = [{"row_idx": item["row_idx"], **item["row"]} for item in payload["rows"]]
        path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        time.sleep(1.5)
    if len(rows) != 100 or [r["row_idx"] for r in rows] != list(range(start, start + 100)):
        raise ValueError(f"Invalid cached block: {path}")
    return rows


def exact_text(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value)).strip()


def similarity_text(value: str) -> str:
    value = exact_text(value).casefold()
    return re.sub(r"\s+", " ", "".join(c if c.isalnum() else " " for c in value)).strip()


def kazakh_screen(value: str, rule: dict) -> bool:
    letters = sum(c.isalpha() for c in value)
    marked = sum(c in KAZAKH_LETTERS for c in value.casefold())
    return marked >= rule["engime_kazakh_letter_min"] and marked / max(letters, 1) >= rule["engime_kazakh_letter_share_min"]


def shingles(value: str, kind: str) -> set[str]:
    if kind == "character_7":
        return {value[i:i+7] for i in range(max(0, len(value)-6))}
    words = value.split()
    return {" ".join(words[i:i+5]) for i in range(max(0, len(words)-4))}


def pair_scores(features: list[set[str]], candidate_floor: float = .75) -> tuple[list[tuple[int,int,float]], list[tuple[int,int,float]], dict]:
    order = sorted(range(len(features)), key=lambda i: len(features[i]))
    matched: list[tuple[int,int,float]] = []
    nearest: list[tuple[float,int,int]] = []
    checked = skipped = 0
    for pos, i in enumerate(order):
        a = features[i]
        if not a:
            continue
        for j in order[pos+1:]:
            b = features[j]
            if len(a) / len(b) < candidate_floor:
                skipped += 1
                continue
            checked += 1
            overlap = len(a.intersection(b))
            score = overlap / (len(a) + len(b) - overlap)
            if score >= candidate_floor:
                matched.append((i, j, score))
            if score < .80:
                item = (score, i, j)
                if len(nearest) < 30:
                    heapq.heappush(nearest, item)
                elif item > nearest[0]:
                    heapq.heapreplace(nearest, item)
    return matched, [(i, j, s) for s, i, j in sorted(nearest, reverse=True)], {"pairs_checked": checked, "pairs_skipped_by_size_bound": skipped}


def clusters(records: list[dict], pairs: list[tuple[int,int,float]], threshold: float) -> dict:
    parent = list(range(len(records)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    active = [(i, j, score) for i, j, score in pairs if score >= threshold]
    for i, j, _ in active:
        a, b = find(i), find(j)
        if a != b:
            parent[b] = a
    members: dict[int, list[int]] = {}
    for i in range(len(records)):
        members.setdefault(find(i), []).append(i)
    representatives = {max(ids, key=lambda i: (len(records[i]["text"]), -records[i]["row_idx"])) for ids in members.values()}
    redundant = sorted(set(range(len(records))) - representatives)
    return {
        "pair_count": len(active), "cluster_count": len(members),
        "largest_cluster": max((len(ids) for ids in members.values()), default=0),
        "flagged_records": len(redundant),
        "flag_rate": len(redundant) / len(records) if records else 0,
        "retained_records": len(representatives),
        "retained_characters": sum(len(records[i]["text"]) for i in representatives),
        "flagged_row_indices": [records[i]["row_idx"] for i in redundant],
    }


def describe_pair(records: list[dict], i: int, j: int, score: float, method: str, run_seed: int, source_key: str) -> dict:
    return {
        "source_key": source_key, "run_seed": run_seed, "method": method,
        "row_i": records[i]["row_idx"], "row_j": records[j]["row_idx"],
        "score": round(score, 6), "title_i": records[i]["title"], "title_j": records[j]["title"],
        "url_i": records[i]["url"], "url_j": records[j]["url"],
        "same_nonempty_url": bool(records[i]["url"]) and records[i]["url"] == records[j]["url"],
        "same_sampled_block": records[i]["row_idx"] // 100 == records[j]["row_idx"] // 100,
    }


def analyse(source: dict, run: dict, protocol: dict, cache_dir: Path) -> tuple[dict, list[dict]]:
    started = time.perf_counter()
    raw_rows = []
    for number, start in enumerate(run["block_starts"], 1):
        raw_rows.extend(fetch_rows(source, start, cache_dir))
        if number % 5 == 0:
            print(f"{source['key']} seed={run['seed']}: {number}/{len(run['block_starts'])} blocks", flush=True)
    exclusions = Counter()
    prepared = []
    rule = protocol["eligibility"]
    for row in raw_rows:
        raw = row.get(source["field"])
        if not isinstance(raw, str) or not raw.strip():
            exclusions["missing_field"] += 1
            continue
        clean = exact_text(raw)
        words = len(clean.split())
        if words < rule["min_words"]:
            exclusions["below_min_words"] += 1
            continue
        if words > rule["max_words"]:
            exclusions["above_max_words"] += 1
            continue
        if source["key"] == "engime" and not kazakh_screen(clean, rule):
            exclusions["uncertain_kazakh"] += 1
            continue
        prepared.append({
            "row_idx": row["row_idx"], "text": clean, "words": words,
            "title": str(row.get("title") or "")[:200],
            "url": str(row.get("url") or ""),
            "source_name": str(row.get("source_name") or row.get("source") or source["key"]),
        })
    seen = set()
    unique = []
    for record in prepared:
        digest = hashlib.md5(record["text"].encode("utf-8")).hexdigest()
        if digest in seen:
            exclusions["exact_removed"] += 1
        else:
            seen.add(digest)
            unique.append(record)
    normalized = [similarity_text(r["text"]) for r in unique]
    methods = {}
    audit = []
    for method in ("word_5", "character_7"):
        t0 = time.perf_counter()
        features = [shingles(value, method) for value in normalized]
        pairs, nearest, comparisons = pair_scores(features)
        threshold_results = {str(t): clusters(unique, pairs, t) for t in THRESHOLDS}
        methods[method] = {
            **comparisons, "runtime_seconds": round(time.perf_counter()-t0, 3),
            "threshold_results": threshold_results,
        }
        audit.extend(describe_pair(unique, i, j, s, method, run["seed"], source["key"]) for i, j, s in pairs if s >= .80)
        audit.extend(describe_pair(unique, i, j, s, method + "_nearest_below_0.80", run["seed"], source["key"]) for i, j, s in nearest)
    result = {
        "source_key": source["key"], "source_label": source["label"],
        "dataset": source["dataset"], "config": source["config"], "revision": source["revision"],
        "run_seed": run["seed"], "raw_sample": len(raw_rows), "block_starts": run["block_starts"],
        "excluded": dict(exclusions), "eligible_before_exact": len(prepared), "post_exact": len(unique),
        "total_words_post_exact": sum(r["words"] for r in unique),
        "median_words_post_exact": statistics.median((r["words"] for r in unique)) if unique else 0,
        "post_exact_characters": sum(len(r["text"]) for r in unique),
        "source_name_counts": dict(Counter(r["source_name"] for r in unique)),
        "exact_only": {"flagged_records": 0, "retained_records": len(unique)},
        "methods": methods,
        "total_runtime_seconds": round(time.perf_counter()-started, 3),
    }
    return result, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=ROOT / "config" / "frozen_protocol.json")
    parser.add_argument("--moodle-upload-record", type=Path, help="Timestamp/screenshot record for Appendix A Moodle upload")
    parser.add_argument("--local-freeze-record", type=Path, help="Local pre-run hash record when Moodle upload is deferred; must be disclosed as a deviation")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    if bool(args.moodle_upload_record) == bool(args.local_freeze_record):
        parser.error("Provide exactly one of --moodle-upload-record or --local-freeze-record")
    if args.moodle_upload_record and (not args.moodle_upload_record.is_file() or args.moodle_upload_record.stat().st_size == 0):
        parser.error("Moodle upload record is missing or empty")
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if protocol["status"] != "PREPARED_NOT_UPLOADED_NOT_RUN":
        parser.error("Unexpected protocol status; inspect the freeze file")
    if args.local_freeze_record:
        if not args.local_freeze_record.is_file():
            parser.error("Local freeze record is missing")
        record = json.loads(args.local_freeze_record.read_text(encoding="utf-8"))
        appendix = ROOT / "protocol" / "Assignment4_Appendix_A_Protocol_Freeze.docx"
        if record.get("protocol_sha256") != hashlib.sha256(args.protocol.read_bytes()).hexdigest():
            parser.error("Frozen protocol JSON no longer matches local freeze record")
        if record.get("appendix_sha256") != hashlib.sha256(appendix.read_bytes()).hexdigest():
            parser.error("Appendix A DOCX no longer matches local freeze record")
        if record.get("moodle_uploaded") is not False:
            parser.error("Local freeze record must explicitly state Moodle was not uploaded")
    for source in protocol["corpora"]:
        observed = current_revision(source["dataset"])
        if observed != source["revision"]:
            raise RuntimeError(f"Dataset revision changed for {source['dataset']}: expected {source['revision']}, found {observed}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    result_path = args.out_dir / "final_results.json"
    if result_path.exists():
        parser.error("Final result file exists; do not overwrite a previous run")
    results = []
    audit_rows = []
    for source in protocol["corpora"]:
        for run in source["runs"]:
            checkpoint = args.out_dir / f"run_{source['key']}_{run['seed']}.json"
            audit_checkpoint = args.out_dir / f"audit_{source['key']}_{run['seed']}.json"
            if checkpoint.exists() and audit_checkpoint.exists():
                result = json.loads(checkpoint.read_text(encoding="utf-8"))
                audit = json.loads(audit_checkpoint.read_text(encoding="utf-8"))
                if result["block_starts"] != run["block_starts"] or result["revision"] != source["revision"]:
                    raise RuntimeError(f"Checkpoint does not match frozen protocol: {checkpoint}")
                print("Reused checkpoint", checkpoint.name, flush=True)
            else:
                result, audit = analyse(source, run, protocol, args.cache_dir)
                checkpoint.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                audit_checkpoint.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            results.append(result)
            audit_rows.extend(audit)
            print(source["key"], run["seed"], result["post_exact"], result["methods"]["character_7"]["threshold_results"]["0.8"]["flagged_records"], flush=True)
        if current_revision(source["dataset"]) != source["revision"]:
            raise RuntimeError(f"Dataset revision changed during fetch for {source['dataset']}")
    output = {
        "protocol_selection_sha256": protocol["selection_sha256"],
        "protocol_evidence_file": (args.moodle_upload_record or args.local_freeze_record).name,
        "moodle_uploaded_before_final_runs": bool(args.moodle_upload_record),
        "generated_utc": datetime.utcnow().isoformat() + "Z",
        "python": platform.python_version(), "platform": platform.platform(),
        "results": results,
    }
    result_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out_dir / "audit_candidates.json").write_text(json.dumps(audit_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Wrote", result_path)


if __name__ == "__main__":
    main()
