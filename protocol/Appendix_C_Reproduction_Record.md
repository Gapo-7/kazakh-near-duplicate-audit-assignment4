# Appendix C Reproduction Test Record

- **Person who reproduced the results:** Nuradilet, on his own computer, as reported by the project team.
- **Date and time of Nuradilet's run:** To be supplied by Nuradilet.
- **Machine and operating system:** Nuradilet's computer; model and operating system to be supplied.
- **Python version:** To be supplied by Nuradilet.
- **Commit or release tag:** Project release tag `assignment-4`; Nuradilet's exact checkout reference is to be confirmed.
- **Commands Nuradilet executed:** To be supplied from his command history or notes. The project commands are in `README.md`.
- **Did the main results table reproduce?** Yes, according to Nuradilet's report to the project team. His output files and console logs could not be transferred to this computer, so a line-by-line comparison of his files is not available.
- **Differences observed:** None reported by Nuradilet; detailed comparison record pending.
- **Problems in the README fixed after the test:** The published package contains `results/final_results.json`, so a fresh run must use a separate `--out-dir`. The README on `main` now gives those commands.

## Additional local verification

A second run was completed in a separate folder on the project owner's Windows 11 computer on 5 November 2026 at 14:28:55 Asia/Qyzylorda, using Python 3.12.14 and a new download cache. This is distinct from Nuradilet's reported run. All twelve deterministic result records matched the published ones; `main_results.csv` had zero differing lines and SHA-256 `21123f9aa93e7fdc1f0e8a29fbbd1c3a5975789b971abe09f24a43aca6a6bd53` in both copies. Hugging Face HTTP 429 retries and a resume from two valid checkpoints occurred during this local check. Runtime and generation timestamps were not expected to match.
