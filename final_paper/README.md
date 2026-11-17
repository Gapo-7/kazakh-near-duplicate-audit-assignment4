# Reproduce the final paper's numerical results

Run these commands from the repository root with Python 3.12 or later. The
released run logs and review metadata are sufficient to rebuild the paper's
tables and figures without downloading source texts. Install `requirements.txt`
for the figure generator.

```powershell
python -m pip install -r requirements.txt
python src/validate_results.py
python src/summarize_results.py --input results/final_results.json --out-dir final_paper/rebuilt
python src/reproduce_final_paper.py --out-dir final_paper/rebuilt
```

The first command may be skipped if the listed packages are already installed.
`validate_results.py` checks the 12 runs, frozen offsets and internal counts.
The other two commands write:

| Paper item | Rebuilt file | Source evidence |
| --- | --- | --- |
| Table 2, record flow by collection | `final_paper/rebuilt/table_2_record_flow.csv` | `results/final_results.json` |
| Table 3, each run | `final_paper/rebuilt/table_3_runs.csv` | `results/final_results.json` |
| Figure 1, mean and SD of flag rates | `final_paper/rebuilt/figure_1_results.svg` and `.png` | `results/final_results.json`; values also in `summary.json` |
| Figure 2, threshold sensitivity | `final_paper/rebuilt/figure_2_sensitivity.svg` and `.png` | `results/final_results.json`; counts in `threshold_sensitivity.csv` |
| Review counts in Results section 4.4 | `final_paper/rebuilt/manual_review_summary.csv` | `results/Appendix_B_Audit_Cases.csv` and `results/audit_candidates.json` |
| Summary statistics and exploratory tests | `final_paper/rebuilt/main_results.csv` and `summary.json` | `results/final_results.json` |

`final_paper/rebuilt/evidence_report.md` gives the input hashes and reconciled
totals. To check the figure and summary files against the released outputs in
PowerShell, run:

```powershell
Compare-Object (Get-Content results/main_results.csv) (Get-Content final_paper/rebuilt/main_results.csv)
Get-FileHash results/figure_1_results.svg, final_paper/rebuilt/figure_1_results.svg -Algorithm SHA256
Get-FileHash results/figure_2_sensitivity.svg, final_paper/rebuilt/figure_2_sensitivity.svg -Algorithm SHA256
```

`Compare-Object` should print nothing; each pair of hashes should match.
The numerical check also requires the manually recorded pair labels and scores
to match the selected audit candidates. This demonstrates consistency of the
files, not whether the human judgment was correct. The 73 pairs were targeted
for error analysis, so they cannot estimate full-corpus precision or recall.

To repeat the experiment from the public datasets, follow the repository's
main README. That route needs network access and the pinned source revisions;
use separate cache and output folders. Do not overwrite the released logs.
