# Appendix C — same-machine reproduction record

**Status:** Actual repeat run completed. This is an automated check by Codex on the original laptop, **not** the independent student/classmate reproduction requested in the assignment.

- **Person who reproduced the results:** Codex AI assistant, operating on the project owner's computer. No other student participated.
- **Date and time:** 5 November 2026, completed at 14:28:55 Asia/Qyzylorda (09:28:55 UTC).
- **Machine and operating system:** Original laptop, Windows 11 (reported as `Windows-11-10.0.26200-SP0`). The release archive was extracted into a separate `assignment4_reproduction_check` folder. Downloaded text was fetched into a new `reproduction_cache` folder.
- **Python version:** 3.12.14 from the Codex bundled runtime.
- **Commit and release tag:** `7e67fb5ee7e77e358cd883230bf6d0b691b29e35`, tag `assignment-4`.
- **Commands executed:**

  ```powershell
  python src/run_experiment.py --local-freeze-record protocol/local_freeze_record.json --cache-dir reproduction_cache --out-dir reproduction_results
  python src/summarize_results.py --input reproduction_results/final_results.json --out-dir reproduction_results
  Compare-Object (Get-Content results/main_results.csv) (Get-Content reproduction_results/main_results.csv)
  ```

- **Did the main results table reproduce?** Yes, on the same machine. `Compare-Object` returned zero differing CSV lines. Both CSV files have SHA-256 `21123f9aa93e7fdc1f0e8a29fbbd1c3a5975789b971abe09f24a43aca6a6bd53`.
- **Additional check:** All twelve runs matched on sample offsets, exclusion counts, post-exact counts, source group counts, pair-comparison counts, and all recorded character and word threshold results. Runtime and generation timestamps were not compared.
- **Differences observed:** None in the deterministic result fields. The new `final_results.json` has a different generation timestamp and runtime measurements, as expected.
- **Operational problems:** Hugging Face rate limiting caused automatic HTTP 429 retries. The first attempt was interrupted after two complete Wikipedia runs; the next invocation reused those valid checkpoints and completed the other ten runs. The script emitted a Python `datetime.utcnow()` deprecation warning after writing the result; it did not affect counts.
- **README issue found and fixed afterward:** The release archive already includes `results/final_results.json`. Running the original README's bare `run_experiment.py` command in that extracted folder stops to protect the published results. This check used a separate `--out-dir reproduction_results`. The README on the repository's `main` branch now gives the separate-output commands; the earlier `assignment-4` tag retains the original instructions.
- **Independent-person requirement:** Not fulfilled. A real team member or classmate must run the project on their own computer and enter their own name, machine, commands, and observations before this record can be presented as independent reproduction.
