"""Build the Assignment 4 Word report from validated result and audit files."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
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
properties = doc.core_properties
properties.title = "Residual Near Duplicate Content in Kazakh Language Datasets"
properties.subject = "Assignment 4 experiment and results"
properties.author = "Gapar Galym; Bekzat Rashiduly; Nuradilet Mustafa"
properties.last_modified_by = "Gapar Galym"
properties.comments = "Research report for group SE-2418"
properties.created = datetime.now(timezone.utc)
properties.modified = properties.created
sec = doc.sections[0]
sec.top_margin = Inches(.72)
sec.bottom_margin = Inches(.68)
sec.left_margin = Inches(.82)
sec.right_margin = Inches(.82)
styles = doc.styles
styles["Normal"].font.name = "Times New Roman"
styles["Normal"].font.size = Pt(12)
styles["Normal"].font.color.rgb = RGBColor(0,0,0)
styles["Normal"].paragraph_format.space_after = Pt(7)
styles["Normal"].paragraph_format.line_spacing = 1.13
for name, size in (("Title", 16), ("Heading 1", 13), ("Heading 2", 12)):
    st = styles[name]
    st.font.name = "Times New Roman"
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
                    run.font.size = Pt(9.5)
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
        run.font.size = Pt(10)


doc.add_paragraph("Residual Near Duplicate Content in Kazakh Language Datasets", style="Title")
doc.add_paragraph("Assignment 4  Experiment Results and Discussion")
doc.add_paragraph("Student(s): Gapar Galym; Bekzat Rashiduly; Nuradilet Mustafa")
doc.add_paragraph("Group: SE-2418   Date: 5 November 2026")
doc.add_paragraph("Roles: Gapar Galym — project owner; Bekzat Rashiduly — 73-pair manual audit; Nuradilet Mustafa — independent reproduction and result comparison.")

heading("1 Research question aim objectives and hypothesis")
para("How much near-duplicate text remains in public Kazakh datasets after exact deduplication? We examined four collections that could be used for language-model pretraining. We documented their source versions, applied the same exact-removal step, and compared a fixed character-shingle rule with a word-shingle baseline. H1 predicts that at least one substantive repeated pair survives exact removal in our final samples; H0 predicts none. We measured repeated records, not language-model performance.")

heading("2 Deviations from the frozen protocol")
para("We fixed Appendix A and the selection manifest locally on 5 November 2026 at 08:26:57 UTC, before fetching the final samples. Their SHA-256 hashes are in local_freeze_record.json. We then submitted Appendix A with the finished work at 16:22 local time. This missed the brief's requirement for a Moodle upload before the experiments; the local hash is evidence of what was fixed, but it is not a Moodle timestamp. Assignment 3 figures were pilot results and are absent from the final tables.")
para("Hugging Face returned HTTP 429 during the first final run. We slowed new block requests, lengthened retries, and resumed from the cached blocks and a completed checkpoint. The source revisions, row offsets, eligibility rules, threshold, methods, primary metric, and statistical plan stayed the same. Before inspecting candidate pairs, we also wrote a coding guide for the protocol's phrase 'repeated substantive body'. The deviations log records both changes.")

heading("3 Final experimental setup")
para("The study is a quantitative audit of four public train splits: Kazakh Wikipedia (20231101.kk), kurumikz Kazakh News Corpus, nyuuzyou Engime, and the document field of shayekh Kazakh News Summarization. The source revisions were fixed by full repository SHA in Appendix A and the JSON manifest. Three disjoint block samples were chosen by seeds 20261105, 20261106 and 20261107. Each sample contains 30, 20, 15 and 20 non-overlapping blocks of 100 adjacent rows respectively, or 8,500 raw rows per run. Final blocks never reuse a block from the Assignment 3 pilot, and the three final runs do not overlap. The source revision was checked before and after retrieval.")
licenses = {"wikipedia_kk":"CC BY-SA 3.0 / GFDL", "kaz_news":"ODC-By", "engime":"CC0 1.0 on card", "news_summary":"not specified on card"}
table(("Corpus", "Train rows", "Raw / run", "Text field", "Card license"),
      [(s["label"], f"{s['population_rows_at_freeze']:,}", f"{s['runs'][0]['raw_rows_expected']:,}", s["field"], licenses[s["key"]]) for s in protocol["corpora"]],
      (1.65, .85, .8, .85, 2.15))
doc.add_paragraph("Source inventory at freeze. Dataset-card licences do not automatically clear rights in individual source articles.")
para("All three conditions used the same eligible records. We excluded empty texts, records outside 150–5,000 whitespace-separated words, and Engime pages that failed the Kazakh-letter screen used in Assignment 3. After NFC normalisation and whitespace collapse, MD5 removed exact copies within each corpus. That exact-only stage is the simple baseline. The second baseline uses Jaccard similarity on word five-gram sets, following Broder's shingling approach (1997). Our main method uses character seven-gram sets. Both near-duplicate methods apply the fixed 0.80 threshold, group linked pairs into connected components, and retain the longest record in each component. The primary metric is the character-method redundant-record count divided by the eligible post-exact count for each corpus.")
para(f"The methods ran on the same Windows 11 laptop: Intel Core i7-13650HX (14 cores, 20 logical processors), 15.6 GB RAM, and Python {raw['python']}. The experiment code uses the standard library and no GPU. We did not train a model or tune on final records. To avoid unnecessary pair calculations, the search skips pairs whose set sizes make Jaccard 0.75 mathematically unreachable. Per-run analysis took {min(run_times):.1f}–{max(run_times):.1f} seconds, including cached retrieval and both near-duplicate methods. The repository records the offsets, filters, thresholds, and outputs.")

heading("4 Main results")
para(f"The twelve planned runs processed {total_raw:,} raw rows. Screening and within-run exact removal left {total_post:,} eligible records; MD5 removed {total_exact:,} exact repeats. At the fixed 0.80 threshold, character seven-grams flagged {total_char:,} additional redundant records, compared with {total_word:,} for word five-grams. These are counts from our sampled blocks. We report rates by corpus rather than a pooled rate because the sources have different sizes and document types.")
para(f"Across all runs, the filters excluded {exclusions['below_min_words']:,} texts under 150 words, {exclusions['above_max_words']:,} over 5,000 words, {exclusions['missing_field']:,} missing text fields, and {exclusions['uncertain_kazakh']:,} Engime pages that failed the Kazakh-letter screen. Eligible news articles came from " + ", ".join(f"{name} ({count:,})" for name,count in news_publishers.most_common()) + ". Consecutive records from one publisher can include revised versions of the same article, which helps explain the news results.")
table(("Corpus", "Post-exact", "Exact removed", "Character flags; mean ± SD", "Word flags; mean ± SD"),
      [(r["source_label"], f"{r['eligible_post_exact_total']:,}", r["exact_removed_total"],
        f"{r['character_flags_total']}; {mean_sd(r,'character')}", f"{r['word_flags_total']}; {mean_sd(r,'word')}") for r in rows],
      (1.55, .72, .86, 1.82, 1.82))
para("Table 1. The mean and sample standard deviation use three disjoint fixed block samples per corpus. The denominator in each run is that run's eligible post-exact count. A zero is an observed zero in these sampled blocks; it does not establish absence of near-duplicates in the full source.")
figure(ROOT / "results" / "figure_1_results.png", "Figure 1. Mean residual flag rate by corpus and method; error bars show sample standard deviation across three runs.", 5.5)
para("For each corpus, we compared the character and word rates within the same three runs. We tested the mean difference in percentage points with an exact two-sided sign-flip test over all eight sign assignments, then applied Holm adjustment across the four corpora. Three runs give a minimum nonzero two-sided p-value of 0.25. The p-values are too coarse to establish that the methods agree or differ reliably, so Table 2 also gives the size and direction of each difference.")
table(("Corpus", "Character minus word (pp)", "Exact p", "Holm p"),
      [(r["source_label"], f"{r['difference_percentage_points']:+.3f}", f"{r['exact_sign_flip_p']:.3f}", f"{r['holm_adjusted_p']:.3f}") for r in rows],
      (2.25, 2.0, 1.2, 1.2))
para("Table 2. Paired run-level comparison at threshold 0.80. The exact-only baseline has zero near-duplicate flags by construction, so no significance test against that baseline is meaningful.")
news_row = next(r for r in rows if r["source_key"] == "kaz_news")
news_details = ", ".join(f"{item['character_flags']}/{item['post_exact']}" for item in news_row["per_run"])
para(f"Kazakh News accounts for most character-method flags: {news_details} across the three runs. The other sources had few matches, and some runs had none. Table 3 keeps those zero results alongside the news counts. The large change between news runs also shows why one block sample would give an unstable impression of that source.")
table(("Corpus", "Seed", "Post-exact", "Character flags", "Word flags"),
      [(r["source_label"], item["seed"], item["post_exact"], item["character_flags"], item["word_flags"])
       for r in rows for item in r["per_run"]],
      (2.0, 1.1, 1.1, 1.2, 1.1))
doc.add_paragraph("Table 3. All twelve planned runs are shown, including zero and unfavourable results. Per-run raw JSON files are retained for the pick-a-number defence check.")

heading("5 Additional analysis")
para(f"Bekzat Rashiduly examined {len(audit)} pairs: {len(flagged)} flagged by at least one near-duplicate method and {len(near_unflagged)} similar pairs that fell below 0.80. Using the coding guide, he marked {flagged_confirmed} flagged pairs as repeated body or changed versions. He also found {near_unflagged_true} substantive repeats among the unflagged cases, showing that the threshold can miss relevant pairs. We selected these cases for high similarity, so the proportions in this review are not estimates of precision or recall for the full datasets.")
table(("Manual category", "Count", "Interpretation"),
      [(name.replace("_", " ").title(), labels[name],
        "confirmed substantive repetition" if name in ("repeated_body","changed_version") else
        "possible method error or ambiguity") for name in ("repeated_body","changed_version","shared_template_only","partial_overlap","unrelated","uncertain")],
      (2.0, .75, 3.75))
para("Table 4. Every reviewed pair and Bekzat Rashiduly's decision, source IDs and similarity scores is listed in Appendix B. Long source texts remain in a local review file and are not reproduced in the public package. Labels may still be imperfect, especially for educational pages that share lesson-plan structure. A second independent bilingual reviewer would improve reliability.")
examples = []
for label in ("repeated_body", "changed_version", "shared_template_only", "partial_overlap"):
    case = next((item for item in audit if item["manual_label"] == label and item["reason"].strip()), None)
    if case:
        examples.append(f"{case['source_key']} rows {case['row_i']} and {case['row_j']} ({label.replace('_',' ')}): {case['reason'].strip()}")
if examples:
    para("Examples from the coding record: " + "; ".join(examples[:3]) + ". These examples illustrate failure types without reproducing long copyrighted text.")
figure(ROOT / "results" / "figure_2_sensitivity.png", "Figure 2. Mean character-method flag rate when the fixed Jaccard threshold is varied from 0.75 to 0.90.")
para("Figure 2 shows what happens when the character threshold changes. Lowering it to 0.75 adds pairs, including some with shared templates; raising it to 0.90 removes pairs that may be revised articles. Kazakh News changes most, while the other three sources remain close to zero in these samples. We keep 0.80 as the main result because it was set before the final runs. Publisher and URL fields help us inspect the news clusters, but they do not turn this sensitivity check into a population estimate.")

heading("6 Answer to the research question and hypothesis")
table(("Hypothesis or objective", "Evidence", "Outcome"),
      [("H1  residual substantive duplication", "Table 1 and Appendix B", "Supported in audit" if true_automatic else "Not confirmed"),
       ("Objectives 2–3  repeatable rule and application", "Frozen protocol and 12 result logs", "Completed on fixed samples"),
       ("Objective 4  compare residual content", "Tables 1–2; Figures 1–2", "Source-specific sampled rates")],
      (2.2, 2.0, 2.3))
para(f"The character seven-gram rule found {total_char} additional redundant records after exact removal in our samples. {'Bekzat Rashiduly confirmed substantive repetition in at least one automatically flagged pair, supporting H1 for the sampled records.' if true_automatic else 'The manual audit did not confirm substantive repetition in any automatically flagged pair, so these samples do not support H1.'} The rates differ by source. They describe only eligible records compared within the same corpus and run; we did not measure whole-dataset prevalence or effects on a language model.")

heading("7 Discussion")
para("Exact hashing removed many copies but missed articles that had been edited. A new heading, deleted paragraph, or punctuation change breaks an MD5 match. Character shingles can still match much of the revised text. Word shingles respond differently to word order and inflection, which helps explain the gaps between methods in Table 2. A high score still needs inspection: two educational pages may share a template while teaching different material.")
para("Tukenov (2026) used exact MD5 deduplication in the SozKZ Kazakh pretraining pipeline. Our additional similarity pass asks what that kind of exact step can leave behind, though our sources differ from SozKZ. CulturaX combines several cleaning and deduplication stages at multilingual scale (Nguyen et al., 2024). We examined a smaller, Kazakh-focused set of public sources and did not reproduce either pipeline. The comparison is about the cleaning choices, not a direct comparison of their reported rates with ours.")
para("Biloshchytska et al. (2025) combine lexical and semantic methods for Kazakh text similarity and include paraphrases and morphological changes in their benchmark. Our whole-document Jaccard rule will miss some meaning-preserving rewrites because it relies on shared text fragments. Tleubayeva et al. (2026) test several duplication regimes with controlled transformations. Those benchmarks make particular failure types easier to measure; our sampled records instead expose messy source features such as article revisions, repeated URLs, and mixed-language pages. The tasks and metrics differ, so their scores cannot be ranked against our flag rates.")
para("Our flag is an operational measure of repeated text, not a judgment that two records contain the same information. Connected-component clustering can link A to B and B to C even when A and C are less alike. Shared boilerplate can lift a score, while a paraphrase or reused passage can stay below 0.80. The 73 reviewed pairs help identify both problems but cover only selected cases. The Engime screen also uses Kazakh-specific letters as a rough language signal; mixed pages can pass or fail incorrectly. Many rows in the summary source lack a usable document field, so its filtered subset is especially narrow.")
para("Fixed seeds, offsets, source revisions, and one preprocessing path make the runs checkable. Reproduction still depends on the Dataset Viewer serving the pinned Hugging Face revisions. The adjacent 100-row blocks, word-length filter, and four selected sources limit generalisation. We compared records only within each corpus and run. A duplicate outside the sampled rows, or in another corpus, is invisible here. A zero in one run therefore says little about the rest of its source.")
para("With three block samples, the mean and standard deviation show variation but support only a coarse sign-flip test. Adjacent records in a block are related, so treating each document as an independent trial would overstate precision. The manual audit also favours high-scoring pairs and cannot yield unbiased sensitivity or specificity. We therefore report every run and the percentage-point differences. A second bilingual reviewer and Nuradilet Mustafa's original run logs would make the checks stronger.")
para("The script provides a repeatable check for corpus maintainers after exact removal. High-scoring clusters are worth reviewing before release or training; low rates only describe what this threshold found in these blocks. A larger study could sample documents more widely, search for neighbours beyond the selected rows, compare across sources, and label a representative pair sample with two reviewers. A semantic method would also help test paraphrases. We would need those steps, and an actual training experiment, to estimate broader prevalence or model impact.")

heading("8 Reproducibility statement")
para("The package includes the frozen JSON manifest, Python scripts, installation instructions, per-run result checkpoints, final raw result JSON, derived CSV and figures, selected audit metadata and the local freeze record. Dataset text is retrieved from the public source cards at recorded revisions and cached only locally; it is not included in the public package. The supplied validator checks all 12 runs and key count identities. Nuradilet Mustafa reported that his separate run matched the main results; his machine details and logs have not yet been transferred. Appendix C distinguishes that report from the documented same-machine rerun. The `assignment-4` Git release contains the project files.")
para("Repository release: https://github.com/Gapo-7/kazakh-near-duplicate-audit-assignment4/releases/tag/assignment-4")

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
        run.font.size = Pt(10)

heading("Appendix A  Protocol freeze")
doc.add_paragraph("The original Appendix A DOCX and frozen_protocol.json accompany this report. Local freeze time: 5 November 2026, 08:26:57 UTC. The Moodle pre-run upload field remains blank because no pre-run upload occurred. A separate submission copy adds the student names without changing the frozen experimental decisions.")
heading("Appendix B  Error analysis")
doc.add_paragraph("The complete case-level CSV accompanies this report. Bekzat Rashiduly's labels were recorded against row IDs and scores; source texts stay local. The categories and counts are in Table 4.")
heading("Appendix C  Independent reproduction")
doc.add_paragraph("The separate Appendix C records Nuradilet Mustafa's reported matching run on his computer. His date, machine, Python version and command history were not provided, so they are marked unavailable rather than inferred from another run. A separately documented run on Gapar Galym's computer matched all twelve results.")

out = ROOT / "report" / "Assignment4_Kazakh_Near_Duplicate_Results.docx"
out.parent.mkdir(parents=True, exist_ok=True)
for paragraph in doc.paragraphs:
    for run in paragraph.runs:
        run.font.name = "Times New Roman"
for word_table in doc.tables:
    for row in word_table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.name = "Times New Roman"
doc.save(out)
word_count = sum(len(re.findall(r"\b[\w-]+\b", p)) for p in body_paragraphs)
print(out)
print("Main body word count, excluding tables, figures, references and appendices:", word_count)
