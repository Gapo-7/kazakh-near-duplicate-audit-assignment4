"""Build the Assignment 4 Word report from validated result and audit files."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
summary = json.loads((ROOT / "results" / "summary.json").read_text(encoding="utf-8"))
raw = json.loads((ROOT / "results" / "final_results.json").read_text(encoding="utf-8"))
protocol = json.loads((ROOT / "config" / "frozen_protocol.json").read_text(encoding="utf-8"))
audit_path = ROOT / "results" / "Appendix_B_Audit_Cases.csv"
with audit_path.open(encoding="utf-8-sig", newline="") as handle:
    audit = list(csv.DictReader(handle))
if not audit or any(not row["manual_label"].strip() for row in audit):
    raise SystemExit("Manual audit is incomplete; fill every selected case before building the final report")
labels = Counter(row["manual_label"].strip() for row in audit)
valid_labels = {"repeated_body", "changed_version", "shared_template_only", "partial_overlap", "unrelated", "uncertain"}
if set(labels) - valid_labels:
    raise SystemExit("Unexpected manual label in Appendix B")
confirmed = labels["repeated_body"] + labels["changed_version"]
flagged = [row for row in audit if row["selection"] == "flagged_union"]
flagged_confirmed = sum(row["manual_label"] in ("repeated_body", "changed_version") for row in flagged)
near_unflagged = [row for row in audit if row["selection"] == "nearest_unflagged"]
near_unflagged_true = sum(row["manual_label"] in ("repeated_body", "changed_version") for row in near_unflagged)
rows = summary["corpora"]
by_key = {r["source_key"]: r for r in rows}
total_raw = sum(r["raw_rows_total"] for r in rows)
total_post = sum(r["eligible_post_exact_total"] for r in rows)
total_exact = sum(r["exact_removed_total"] for r in rows)
total_char = sum(r["character_flags_total"] for r in rows)
total_word = sum(r["word_flags_total"] for r in rows)
run_times = [r["total_runtime_seconds"] for r in raw["results"]]
exclusions = Counter()
news_publishers = Counter()
for run in raw["results"]:
    exclusions.update(run["excluded"])
    if run["source_key"] == "kaz_news":
        news_publishers.update(run["source_name_counts"])
true_automatic = any(row["manual_label"] in ("repeated_body", "changed_version") and float(row["character_score"] or 0) >= .8 for row in audit)


def pct(value: float) -> str:
    return f"{100*value:.2f}%"


def mean_sd(row: dict, name: str) -> str:
    return f"{pct(row[name+'_mean_rate'])} ± {pct(row[name+'_sd_rate'])}"


doc = Document()
sec = doc.sections[0]
sec.top_margin = Inches(.72)
sec.bottom_margin = Inches(.68)
sec.left_margin = Inches(.82)
sec.right_margin = Inches(.82)
styles = doc.styles
styles["Normal"].font.name = "Aptos"
styles["Normal"].font.size = Pt(10)
styles["Normal"].font.color.rgb = RGBColor(0,0,0)
styles["Normal"].paragraph_format.space_after = Pt(7)
styles["Normal"].paragraph_format.line_spacing = 1.13
for name, size in (("Title", 17), ("Heading 1", 12), ("Heading 2", 10.5)):
    st = styles[name]
    st.font.name = "Aptos"
    st.font.size = Pt(size)
    st.font.bold = True
    st.font.color.rgb = RGBColor(0,0,0)
    st.paragraph_format.space_before = Pt(10 if name != "Title" else 0)
    st.paragraph_format.space_after = Pt(5)
    ppr = st.element.pPr
    if ppr is not None:
        border = ppr.find(qn("w:pBdr"))
        if border is not None:
            ppr.remove(border)

body_paragraphs = []


def para(text: str):
    doc.add_paragraph(text)
    body_paragraphs.append(text)


def heading(text: str, level: int = 1):
    doc.add_paragraph(text, style=f"Heading {level}")


def cell_border(cell):
    tcpr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        side = OxmlElement(f"w:{edge}")
        side.set(qn("w:val"), "single")
        side.set(qn("w:color"), "D9D9D9")
        side.set(qn("w:sz"), "4")
        borders.append(side)
    tcpr.append(borders)


def table(headers: tuple[str,...], data: list[tuple], widths: tuple[float,...]):
    t = doc.add_table(rows=1, cols=len(headers))
    t.autofit = False
    for j, h in enumerate(headers):
        t.columns[j].width = Inches(widths[j])
        t.rows[0].cells[j].text = h
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), "D9E7F2")
        t.rows[0].cells[j]._tc.get_or_add_tcPr().append(shd)
    for values in data:
        cells = t.add_row().cells
        for j, value in enumerate(values):
            cells[j].text = str(value)
    for i, row in enumerate(t.rows):
        for j, cell in enumerate(row.cells):
            cell.width = Inches(widths[j])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell_border(cell)
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(1)
                for run in p.runs:
                    run.font.size = Pt(8.2)
                    if i == 0:
                        run.bold = True
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return t


def figure(path: Path, caption: str, width: float = 6.55):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Inches(width))
    c = doc.add_paragraph(caption)
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.paragraph_format.space_after = Pt(9)
    for run in c.runs:
        run.font.size = Pt(8.5)


doc.add_paragraph("Residual Near Duplicate Content in Kazakh Language Datasets", style="Title")
doc.add_paragraph("Assignment 4  Experiment Results and Discussion")
doc.add_paragraph("Student(s): __________________________________________________________")
doc.add_paragraph("Group: _______________________   Date: 5 November 2026")

heading("1 Research question aim objectives and hypothesis")
para("Research question: To what extent does near-duplicate content remain in publicly available Kazakh-language datasets for LLM pretraining after exact deduplication? The aim is to quantify the additional redundancy in selected public Kazakh collections after a consistent exact pass. The objectives are to document four sources, define one repeatable similarity rule, apply it after exact removal, and compare the resulting document counts and rates. H1 predicts at least one substantive near-duplicate after exact deduplication in the final samples; H0 predicts none. The analysis concerns text records, not downstream language-model performance.")

heading("2 Deviations from the frozen protocol")
para("Appendix A and its machine-readable selection manifest were fixed locally on 5 November 2026 at 08:26:57 UTC, before any final sample was fetched. The SHA-256 values are in local_freeze_record.json. The course Moodle page offered one as4 submission slot, and the team planned to upload the completed materials together. Consequently, the protocol was not uploaded to Moodle before final experiments. This is an explicit deviation from the brief's timestamp requirement, not evidence of compliance with it. The form retains a blank Moodle upload field. The earlier Assignment 3 figures were development pilot results and are excluded from every final table.")
para("The first final run was interrupted by a Hugging Face HTTP 429 rate limit. We added waiting after new block requests and longer retries, then resumed from cached blocks and a completed-run checkpoint. No source revision, final row offset, eligibility rule, threshold, method, primary metric, or statistical rule changed. A manual coding guide was written before candidate pairs were inspected to clarify the frozen phrase 'repeated substantive body'. These operational changes are logged with the protocol.")

heading("3 Final experimental setup")
para("The study is a quantitative audit of four public train splits: Kazakh Wikipedia (20231101.kk), kurumikz Kazakh News Corpus, nyuuzyou Engime, and the document field of shayekh Kazakh News Summarization. The source revisions were fixed by full repository SHA in Appendix A and the JSON manifest. Three disjoint block samples were chosen by seeds 20261105, 20261106 and 20261107. Each sample contains 30, 20, 15 and 20 non-overlapping blocks of 100 adjacent rows respectively, or 8,500 raw rows per run. Final blocks never reuse a block from the Assignment 3 pilot, and the three final runs do not overlap. The source revision was checked before and after retrieval.")
licenses = {"wikipedia_kk":"CC BY-SA 3.0 / GFDL", "kaz_news":"ODC-By", "engime":"CC0 1.0 on card", "news_summary":"not specified on card"}
table(("Corpus", "Train rows", "Raw / run", "Text field", "Card license"),
      [(s["label"], f"{s['population_rows_at_freeze']:,}", f"{s['runs'][0]['raw_rows_expected']:,}", s["field"], licenses[s["key"]]) for s in protocol["corpora"]],
      (1.65, .85, .8, .85, 2.15))
doc.add_paragraph("Source inventory at freeze. Dataset-card licences do not automatically clear rights in individual source articles.")
para("For every condition, empty records and texts outside 150–5,000 whitespace-separated words were excluded. The same Engime Kazakh-letter screen as Assignment 3 removed uncertain mixed-language pages. Unicode NFC normalisation and whitespace collapse preceded within-corpus exact deduplication by MD5. Baseline 1 stops here and therefore flags no residual near-duplicates by definition. Baseline 2 compares word five-gram sets using Jaccard similarity, following the shingling tradition of Broder (1997). The proposed condition compares character seven-gram sets with Jaccard, preserving the Assignment 3 design. Both near methods use the same 0.80 threshold and connected-component clustering; the longest text represents a cluster. The primary outcome is redundant post-exact records divided by eligible post-exact records for the character method in each corpus. The word baseline and exact-only condition are comparisons, not alternative definitions silently substituted into the primary outcome.")
para(f"All comparisons used the same rows, preprocessing and Windows 11 laptop with a 13th Gen Intel Core i7-13650HX CPU, 14 cores, 20 logical processors and 15.6 GB RAM. Python {raw['python']} and standard-library code performed the experiment; no GPU, model training, tuning on final records or human-participant survey was used. The script's exact pair search skips a comparison only when set sizes make reaching Jaccard 0.75 mathematically impossible. Runtime per source and run is logged; observed full-run analysis times ranged from {min(run_times):.1f} to {max(run_times):.1f} seconds, including cached retrieval and both methods. All fixed offsets, filters, thresholds, outputs and software versions are in the repository package.")

heading("4 Main results")
para(f"Across the twelve planned source-by-seed runs, {total_raw:,} raw rows were processed. After the length, missing-field and language screens and local exact removal, {total_post:,} eligible post-exact records remained. The exact stage removed {total_exact:,} eligible repeated records. At Jaccard 0.80, the character method flagged {total_char:,} additional redundant records across run-specific samples, while the word baseline flagged {total_word:,}. These totals describe the processed samples only. They should not be divided into one pooled prevalence estimate because the four corpora differ greatly in size, selection and document type.")
para(f"The screening log records {exclusions['below_min_words']:,} texts below 150 words, {exclusions['above_max_words']:,} above 5,000 words, {exclusions['missing_field']:,} missing text fields, and {exclusions['uncertain_kazakh']:,} Engime pages failing the Kazakh-letter screen across all runs. In the news subset, the post-exact articles came from " + ", ".join(f"{name} ({count:,})" for name,count in news_publishers.most_common()) + ". These source-group counts matter because a local batch of one publisher can contain repeated versions of an article.")
table(("Corpus", "Post-exact", "Exact removed", "Character flags; mean ± SD", "Word flags; mean ± SD"),
      [(r["source_label"], f"{r['eligible_post_exact_total']:,}", r["exact_removed_total"],
        f"{r['character_flags_total']}; {mean_sd(r,'character')}", f"{r['word_flags_total']}; {mean_sd(r,'word')}") for r in rows],
      (1.55, .72, .86, 1.82, 1.82))
para("Table 1. The mean and sample standard deviation use three disjoint fixed block samples per corpus. The denominator in each run is that run's eligible post-exact count. A zero is an observed zero in these sampled blocks; it does not establish absence of near-duplicates in the full source.")
figure(ROOT / "results" / "figure_1_results.png", "Figure 1. Mean residual flag rate by corpus and method; error bars show sample standard deviation across three runs.", 5.5)
para("The paired statistical comparison uses the three run-level differences between character and word flag rates for each corpus. The test statistic is their mean absolute percentage-point difference. An exact two-sided sign-flip permutation test enumerates all eight sign assignments, followed by Holm adjustment across the four corpus comparisons. With only three runs, the smallest attainable nonzero two-sided p-value is 0.25; all inferential results are therefore exploratory. We report the size and direction of differences as practical evidence instead of interpreting a nonsignificant p-value as proof of equivalence.")
table(("Corpus", "Character minus word (pp)", "Exact p", "Holm p"),
      [(r["source_label"], f"{r['difference_percentage_points']:+.3f}", f"{r['exact_sign_flip_p']:.3f}", f"{r['holm_adjusted_p']:.3f}") for r in rows],
      (2.25, 2.0, 1.2, 1.2))
para("Table 2. Paired run-level comparison at threshold 0.80. The exact-only baseline has zero near-duplicate flags by construction, so no significance test against that baseline is meaningful.")
for r in rows:
    details = ", ".join(f"{item['character_flags']}/{item['post_exact']}" for item in r["per_run"])
    para(f"{r['source_label']}: the character method flagged {details} in the three final runs, giving a mean rate of {mean_sd(r,'character')}. The word baseline mean was {mean_sd(r,'word')}. The run-to-run spread is part of the result and is retained even when a run found no matches.")
table(("Corpus", "Seed", "Post-exact", "Character flags", "Word flags"),
      [(r["source_label"], item["seed"], item["post_exact"], item["character_flags"], item["word_flags"])
       for r in rows for item in r["per_run"]],
      (2.0, 1.1, 1.1, 1.2, 1.1))
doc.add_paragraph("Table 3. All twelve planned runs are shown, including zero and unfavourable results. Per-run raw JSON files are retained for the pick-a-number defence check.")

heading("5 Additional analysis")
para(f"Bekzat reviewed {len(audit)} selected candidate pairs: {len(flagged)} pairs flagged by at least one near method and {len(near_unflagged)} high-scoring pairs below 0.80. The coding guide distinguishes repeated substantive body, changed versions, shared templates, partial overlap, unrelated texts and uncertain cases. Of the flagged union, {flagged_confirmed} were judged to repeat substantive body or be a changed version. Among the nearest unflagged cases, {near_unflagged_true} were judged substantively repeated, suggesting possible misses in this targeted review. The audit is deliberately enriched for lexically similar pairs; its counts are diagnostic and cannot estimate corpus-wide precision or recall without a representative labelled pair sample.")
table(("Manual category", "Count", "Interpretation"),
      [(name.replace("_", " ").title(), labels[name],
        "confirmed substantive repetition" if name in ("repeated_body","changed_version") else
        "possible method error or ambiguity") for name in ("repeated_body","changed_version","shared_template_only","partial_overlap","unrelated","uncertain")],
      (2.0, .75, 3.75))
para("Table 4. Every reviewed pair and Bekzat's decision, source IDs and similarity scores is listed in Appendix B. Long source texts remain in a local review file and are not reproduced in the public package. Labels may still be imperfect, especially for educational pages that share lesson-plan structure. A second independent bilingual reviewer would improve reliability.")
examples = []
for label in ("repeated_body", "changed_version", "shared_template_only", "partial_overlap"):
    case = next((item for item in audit if item["manual_label"] == label and item["reason"].strip()), None)
    if case:
        examples.append(f"{case['source_key']} rows {case['row_i']} and {case['row_j']} ({label.replace('_',' ')}): {case['reason'].strip()}")
if examples:
    para("Examples from the coding record: " + "; ".join(examples[:3]) + ". These examples illustrate failure types without reproducing long copyrighted text.")
figure(ROOT / "results" / "figure_2_sensitivity.png", "Figure 2. Mean character-method flag rate when the fixed Jaccard threshold is varied from 0.75 to 0.90.")
para("Threshold sensitivity is the second explanatory analysis. A lower threshold can reveal more candidate pairs but also raises the risk of treating related pages or shared templates as duplicates. A higher threshold keeps only stronger lexical overlap and may miss revised articles. Figure 2 shows the observed change for each source. The 0.80 result remains primary because it was fixed before the final runs; the other thresholds are robustness checks, not opportunities to select the most favourable rate after seeing the data. The block-by-block variation and the URL metadata provide further clues about local source batches and repeated publication.")

heading("6 Answer to the research question and hypothesis")
table(("Hypothesis or objective", "Evidence", "Outcome"),
      [("H1  residual substantive duplication", "Table 1 and Appendix B", "Supported in audit" if true_automatic else "Not confirmed"),
       ("Objectives 2–3  repeatable rule and application", "Frozen protocol and 12 result logs", "Completed on fixed samples"),
       ("Objective 4  compare residual content", "Tables 1–2; Figures 1–2", "Source-specific sampled rates")],
      (2.2, 2.0, 2.3))
para(f"The answer is that the specified character seven-gram rule found {total_char} additional redundant post-exact records across the tested samples, with different rates across the four sources. {'Bekzat identified at least one automatically flagged pair with repeated substantive content, so H1 is descriptively supported for the selected samples.' if true_automatic else 'The case audit did not confirm a substantive repeated-body pair among automatic flags, so H1 is not supported by these final samples.'} This is a narrow, transparent answer to the research question. It concerns records that entered the filtered samples and were compared within their own corpus and run. It does not show the true near-duplicate rate of the entire datasets, nor the effect of deduplication on language-model quality.")

heading("7 Discussion")
para("The results demonstrate why an exact-hash pass and a similarity pass answer different questions. MD5 identifies identical normalized byte sequences; it cannot identify an article that gained a heading, lost a paragraph or changed punctuation. The character method can connect such records when most seven-character fragments remain. The word method offers a second, familiar lexical view and may respond differently to inflection, word order and text length. The differences in Table 2 are therefore method-dependent measurement differences, not a contest in which one algorithm is declared universally better. Manual review is essential when the apparent overlap comes from an educational template or common navigation rather than the main body.")
para("The finding is consistent with Tukenov's (2026) description of exact MD5 deduplication in the SozKZ Kazakh pretraining pipeline: exact hashing is a useful cleaning stage, while the present study tests what an additional lexical rule can still detect in different public sources. The two studies do not share the same corpus or outcome, so our rates cannot be transferred to SozKZ. Nguyen et al. (2024) describe CulturaX as a large multilingual corpus with multiple cleaning and deduplication stages. Our smaller audit likewise treats data preparation as layered, but it does not evaluate the quality of CulturaX or reproduce its pipeline. These comparisons support the practical relevance of residual redundancy without implying that earlier work reported our exact figures.")
para("Biloshchytska et al. (2025) report a hybrid Kazakh similarity system combining lexical and semantic components on a purpose-built benchmark. Their setting includes paraphrases and morphological transformations, whereas our whole-document Jaccard audit prioritises transparent counts in naturally sampled public records. It follows that our rule can miss semantically equivalent paraphrases even if its lexical flags are credible. Tleubayeva et al. (2026) likewise show that benchmark design and duplication regime change the apparent performance of similarity methods. Their controlled transformations help diagnose failure modes, while our unscripted corpus samples reveal source-specific issues such as templates, repeated article URLs and mixed-language pages. Different data and metrics prevent a direct numerical ranking across studies.")
para("The most serious construct-validity threat is equating a Jaccard cluster with genuinely redundant information. A connected component can chain together records whose end members are less similar, and two documents can share boilerplate while differing in their central content. Conversely, paraphrased or partially reused passages may stay below 0.80. Manual labels mitigate this only for selected pairs. The Engime language screen is another construct threat: Kazakh-specific characters are an imperfect language indicator, especially on mixed pages. The summary dataset's document field may be missing in many sampled rows, so its eligible subset is not the whole source.")
para("Internal validity is strengthened by fixed seeds, recorded block offsets, source revisions, identical preprocessing, and unchanged thresholds across methods. Yet the output depends on the Hugging Face Dataset Viewer serving the pinned revision; a future change can prevent exact reproduction. External validity is limited by adjacent 100-row blocks, a 150–5,000-word filter, within-sample comparisons and four chosen datasets. A near neighbour outside a sampled block is invisible to the experiment. Within-source and cross-source duplication can differ, but this study measures only within-corpus and within-run matches. Accordingly, even a source with zero sample flags may contain many repeats elsewhere.")
para("Statistical-conclusion validity is also limited. Three block samples allow a run-level mean and standard deviation, but the exact sign-flip test has coarse p-values and limited power. Adjacent records inside a block are not independent, so a document-level binomial confidence interval would overstate precision; we avoid one. The audit candidate set is selected for high lexical similarity and cannot provide unbiased sensitivity or specificity. The effect sizes in percentage points and the complete per-run logs are more informative than a claim of statistical significance here. A second independent bilingual review and the transfer of Nuradilet's run logs would provide stronger evidence.")
para("For corpus maintainers, the practical use is a repeatable check after exact hashing. A low automatic rate means only that the chosen lexical threshold found little additional redundancy in these samples; it is not a certificate of cleanliness. A high rate can identify clusters for review before training or data release. Future work should use more dispersed random document sampling, retrieve neighbours outside the selected rows, compare cross-source matches, label a representative pair sample with two reviewers, and test a semantic detector on paraphrases. Such work could estimate population prevalence and the impact on actual model training; neither is measured here.")

heading("8 Reproducibility statement")
para("The package includes the frozen JSON manifest, Python scripts, installation instructions, per-run result checkpoints, final raw result JSON, derived CSV and figures, selected audit metadata and the local freeze record. Dataset text is retrieved from the public source cards at recorded revisions and cached only locally; it is not included in the public package. The supplied validator checks all 12 runs and key count identities. Nuradilet reported that his separate run matched the main results; his machine details and logs have not yet been transferred. Appendix C distinguishes that report from the documented same-machine rerun. The `assignment-4` Git release contains the project files.")

heading("References")
refs = [
    "Biloshchytska, S., et al. (2025). Text similarity detection in agglutinative languages: A case study of Kazakh using hybrid N-gram and semantic models. Applied Sciences, 15(12), 6707. https://doi.org/10.3390/app15126707",
    "Broder, A. Z. (1997). On the resemblance and containment of documents. Compression and Complexity of Sequences, 21–29.",
    "Nguyen, T., et al. (2024). CulturaX: A cleaned, enormous, and multilingual dataset for large language models in 167 languages. LREC-COLING 2024, 4226–4237. https://aclanthology.org/2024.lrec-main.377/",
    "Tleubayeva, A., et al. (2026). KazakhTextDuplicates: A controlled multi-regime benchmark for semantic deduplication, semantic similarity, and retrieval in Kazakh. Data, 11(6), 133. https://doi.org/10.3390/data11060133",
    "Tukenov, S. (2026). SozKZ: Training efficient small language models for Kazakh from scratch. arXiv:2603.20854. https://arxiv.org/abs/2603.20854",
    "Dataset cards: https://huggingface.co/datasets/wikimedia/wikipedia ; https://huggingface.co/datasets/kurumikz/kaz-news-corpus ; https://huggingface.co/datasets/nyuuzyou/engime ; https://huggingface.co/datasets/shayekh/kazakh-news-summarization-20k-adapted",
]
for ref in refs:
    p = doc.add_paragraph(ref)
    p.paragraph_format.space_after = Pt(4)
    for run in p.runs:
        run.font.size = Pt(8.5)

heading("Appendix A  Protocol freeze")
doc.add_paragraph("The separate Appendix A DOCX and frozen_protocol.json accompany this report. Local freeze time: 5 November 2026, 08:26:57 UTC. The Moodle pre-run upload field remains blank because no pre-run upload occurred.")
heading("Appendix B  Error analysis")
doc.add_paragraph("The complete case-level CSV accompanies this report. Bekzat's labels were recorded against row IDs and scores; source texts stay local. The categories and counts are in Table 4.")
heading("Appendix C  Independent reproduction")
doc.add_paragraph("The separate Appendix C records Nuradilet's reported matching run on his computer. His date, machine, Python version and command history remain to be supplied because his logs were not transferred. A separately documented run on the project owner's computer matched all twelve results.")

out = ROOT / "report" / "Assignment4_Kazakh_Near_Duplicate_Results.docx"
out.parent.mkdir(parents=True, exist_ok=True)
doc.save(out)
word_count = sum(len(re.findall(r"\b[\w-]+\b", p)) for p in body_paragraphs)
print(out)
print("Main body word count, excluding tables, figures, references and appendices:", word_count)
