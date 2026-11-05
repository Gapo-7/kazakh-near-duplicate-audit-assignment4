# Kazakh near-duplicate audit  Assignment 4

This repository continues Assignments 2 and 3. It measures residual near-duplicate flags in four public Kazakh text collections after a local exact-deduplication pass. The Assignment 3 run was a development pilot. The final samples are pre-selected in `config/frozen_protocol.json` and exclude all pilot blocks.

## Status

The final 12 runs, figures, tables and a case-by-case AI-assisted draft audit are complete. The course brief requests a Moodle upload of Appendix A before final experiments. The user chose to complete the work first because the course presents only one submission slot. The protocol was fixed locally by hashes before final runs, and this is disclosed as a deviation. The local timestamp is not a Moodle timestamp, and the Assignment 3 pilot numbers are not included as final Assignment 4 results. Student confirmation of the case labels and an independent person's reproduction record are still required before claiming those rubric items.

## Files

- `protocol/Assignment4_Appendix_A_Protocol_Freeze.docx`: the pre-experiment form.
- `config/frozen_protocol.json`: exact source revisions, sample block offsets, seeds, metrics and analysis plan.
- `src/freeze_protocol.py`: deterministic construction of the selection manifest from Assignment 3 pilot metadata.
- `src/run_experiment.py`: downloads public records, checks source revisions, runs all three conditions and writes raw result logs.
- `src/summarize_results.py`: creates the main results table, statistical summary and two SVG figures directly from the raw results.
- `results/`: raw and derived final results, figures and selected audit metadata. The local full-text review HTML is excluded from the shareable package.

Downloaded raw text is cached locally under `data/cache/` and is excluded from the public repository. Dataset licences and publisher rights should be checked before redistributing any text.

## Environment

Python 3.12 or later. The experiment uses only the Python standard library. Install `requirements.txt` for PNG figures and Word document rebuilding. Network access is required for the first data retrieval from Hugging Face Dataset Viewer. Cached reruns can use the same files, but the script still checks the current source revision before running. A revision mismatch stops the run so that changed data cannot be mixed silently.

## Reproduce the final results

1. Preferred course-compliant route: upload Appendix A to Moodle before running any final sample, and save its real upload timestamp as `protocol/moodle_upload_record.txt`. In the current user-directed route, run `src/create_local_freeze.py` before the final experiment and disclose the missing pre-run Moodle upload.
2. Confirm that `config/frozen_protocol.json` has not changed since the freeze.
3. The published package already contains `results/final_results.json`. To rerun from the source datasets without overwriting the published evidence, use separate cache and output folders:

   ```powershell
   py -3.12 -m pip install -r requirements.txt
   py -3.12 src/run_experiment.py --local-freeze-record protocol/local_freeze_record.json --cache-dir reproduction_cache --out-dir reproduction_results
   py -3.12 src/summarize_results.py --input reproduction_results/final_results.json --out-dir reproduction_results
   Compare-Object (Get-Content results/main_results.csv) (Get-Content reproduction_results/main_results.csv)
   ```

4. The comparison should show no differing CSV lines. Inspect `reproduction_results/final_results.json`, `reproduction_results/main_results.csv`, `reproduction_results/summary.json`, and both new SVG figures. `src/validate_results.py` validates the published `results/` folder; it does not target the separate rerun folder.
5. Review all 73 selected cases in the **local-only** `results/audit_review_local.html`. The CSV has AI-assisted draft labels and reasons; a bilingual student must verify and correct them, then update the reviewer field. Rebuild the report with `py -3.12 src/build_report.py`. Do not upload the local HTML or source-text cache.
6. For the independent reproduction test, another team member or classmate runs the same commands on a clean machine. Record their actual machine, commands, outcome and any differences in Appendix C. Never invent this record.

For an additional same-machine integrity check, `py -3.12 src/recheck_from_cache.py` recomputes all twelve deterministic outputs from local cached rows. This check does not replace the independent person required in Appendix C.

For a course-compliant early Moodle upload, use `--moodle-upload-record protocol/moodle_upload_record.txt` instead. The final run refuses to overwrite an existing `final_results.json`. Each completed corpus/run is checkpointed. If a run fails, retain the cache and checkpoints and record the reason before restarting. If an experimental decision changes after the freeze, disclose it in the report's “Deviations from the frozen protocol” section.

## Dataset access

The script retrieves the `train` split for these pinned source revisions:

- `wikimedia/wikipedia`, configuration `20231101.kk`, text field `text`.
- `kurumikz/kaz-news-corpus`, configuration `default`, text field `content`.
- `nyuuzyou/engime`, configuration `default`, text field `text`.
- `shayekh/kazakh-news-summarization-20k-adapted`, configuration `default`, text field `document`.

The exact revision hashes and row offsets are in the frozen protocol JSON. If Hugging Face Dataset Viewer no longer serves the same revision, stop and document the change; do not quietly use the newest version.

## Measurement

For each corpus and seed, exclude missing texts, texts outside 150–5,000 whitespace-separated words, and Engime records failing the prespecified Kazakh-letter screen. Collapse whitespace and normalize Unicode to NFC, then remove exact copies within the sampled corpus by MD5, as in Assignment 3. Compare the remaining texts under two near-duplicate methods: word 5-gram set Jaccard and character 7-gram set Jaccard. The main threshold is 0.80. Pairs at or above the threshold form connected components; all but one longest representative per component count as redundant. Thresholds 0.75, 0.85 and 0.90 are sensitivity checks.

The primary outcome is the character-method redundant-record count divided by the post-exact eligible count, reported separately for each corpus. These are sample-conditional automatic flags. Manual audit is needed before calling every flag a true content duplicate. Block sampling and unavailable neighbours outside each sample limit claims about full-corpus prevalence.

## Integrity and privacy

Every number in the report should be traceable to `results/final_results.json` or `results/summary.json`. Keep raw downloaded text, any local review copies and Moodle evidence out of the public repository. Do not include passwords, tokens or personal data in commits. A `LICENSE` file and a tagged `assignment-4` release are required before final submission.
