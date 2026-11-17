# Numerical evidence for the final paper

Generated from released run JSON, audit candidates and recorded review CSV.
This verifies file consistency, not the truth of human labels or an independent rerun.

- Final run JSON SHA-256: `61b6baa3d8e50844a616c874a2a23a542fa354b7c4963a322852ac84ae026ec8`
- Review CSV SHA-256: `0d35466707db8026f7f44ea15ca15f842a15a5925274bdc9f8bb1d06d4409eeb`
- Audit candidates JSON SHA-256: `c805a165ec05e30d3c0205aa0471f687e927bfefdaaf10910ed32cf8f83b7ede`

## Record flow

- 25,500 raw rows; 10,969 passed eligibility; 1,309 MD5 removals; 9,660 post-exact records.
- Exclusions: 1,400 missing or empty; 12,355 too short; 64 too long; 712 Kazakh-letter screen.
- At 0.80: 106 character flags and 99 word flags. Every word-flagged row is also character-flagged within its run.

## Targeted review

- 73 distinct recorded pairs link to audit candidates and match their recorded scores.
- 33 flagged pairs: 27 repeated bodies, 3 changed versions, 2 partial overlaps, 1 shared template.
- 40 below-threshold pairs: 7 changed versions, 13 partial overlaps, 19 shared templates, 1 unrelated.
- These targeted cases do not yield corpus-wide precision or recall.

## Output map

- Table 2: `table_2_record_flow.csv`.
- Table 3: `table_3_runs.csv`.
- Threshold counts behind Figure 2: `threshold_sensitivity.csv`.
- Figure 1 means/SD and Figure 2 mean rates: regenerate with `src/summarize_results.py`; see `summary.json` and the two figure files.
- Manual-review claims: `manual_review_summary.csv`.

Source-specific review selection: Kazakh Wikipedia 2 flagged + 10 below threshold, Kazakh News Corpus 30 flagged + 10 below threshold, Engime educational pages 1 flagged + 10 below threshold, News Summary documents 0 flagged + 10 below threshold.
