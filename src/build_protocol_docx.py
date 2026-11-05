"""Render the prepared Assignment 4 Appendix A as a Word form."""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


ROOT = Path(__file__).resolve().parents[1]
protocol = json.loads((ROOT / "config" / "frozen_protocol.json").read_text(encoding="utf-8"))
out = ROOT / "protocol" / "Assignment4_Appendix_A_Protocol_Freeze.docx"


def shade(cell, color="EAF0F5"):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), color)
    tc_pr.append(shd)


def borders(cell):
    tc_pr = cell._tc.get_or_add_tcPr()
    b = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:color"), "D9D9D9")
        e.set(qn("w:sz"), "4")
        b.append(e)
    tc_pr.append(b)


doc = Document()
section = doc.sections[0]
section.top_margin = Inches(.72)
section.bottom_margin = Inches(.66)
section.left_margin = Inches(.8)
section.right_margin = Inches(.8)

styles = doc.styles
styles["Normal"].font.name = "Aptos"
styles["Normal"].font.size = Pt(9)
styles["Normal"].font.color.rgb = RGBColor(0, 0, 0)
styles["Normal"].paragraph_format.space_after = Pt(4)
styles["Normal"].paragraph_format.line_spacing = 1.08
for name, size in (("Title", 16), ("Heading 1", 11)):
    st = styles[name]
    st.font.name = "Aptos"
    st.font.size = Pt(size)
    st.font.bold = True
    st.font.color.rgb = RGBColor(0, 0, 0)
    st.paragraph_format.space_after = Pt(7)
    ppr = st.element.pPr
    if ppr is not None:
        border = ppr.find(qn("w:pBdr"))
        if border is not None:
            ppr.remove(border)
styles["Subtitle"].font.name = "Aptos"
styles["Subtitle"].font.size = Pt(10)
styles["Subtitle"].font.italic = False
styles["Subtitle"].font.color.rgb = RGBColor(0, 0, 0)

doc.add_paragraph("Assignment 4 Experiment Protocol Freeze", style="Title")
doc.add_paragraph("Appendix A  Decisions fixed before final experiments", style="Subtitle")
doc.add_paragraph("Student(s): __________________________________________________________")
doc.add_paragraph("Group: _______________________   Moodle upload date and time: _______________________")
doc.add_paragraph(
    "This form fixes the final sample and analysis choices for the Kazakh near-duplicate study. "
    "The Assignment 3 results were development pilot evidence. The three samples below are new and have not been analysed at the time of local freeze."
)

rows = [
    ("Primary research question", protocol["research_question"]),
    ("Hypothesis / expected comparison", protocol["hypothesis"]),
    ("Primary outcome and justification", protocol["primary_metric"] + ". This measure directly quantifies the additional records flagged after exact removal and keeps a clear denominator."),
    ("Secondary metrics", "; ".join(protocol["secondary_metrics"])),
    ("Baseline 1  simple", protocol["conditions"]["baseline_1"]),
    ("Baseline 2  literature method", protocol["conditions"]["baseline_2"] + ". Word shingling and Jaccard resemblance are established near-duplicate methods (Broder, 1997)."),
    ("Proposed method", protocol["conditions"]["proposed"] + ". The same text eligibility and exact stage apply to all conditions."),
    ("Dataset versions and test set", "Four Hugging Face train splits at the source revisions listed below. Three fixed, mutually disjoint samples of 8,500 raw rows each, in 100-row blocks. All final blocks exclude the Assignment 3 pilot. Selection SHA-256: " + " ".join(protocol["selection_sha256"][i:i+16] for i in range(0, 64, 16))),
    ("Runs, seeds and preprocessing", "Three runs with seeds 20261105, 20261106, 20261107. Texts must have 150–5,000 words after NFC and whitespace collapse. Engime uses the same explicit Kazakh-letter screen as Assignment 3. Exact copies are removed within each corpus and run by MD5."),
    ("Statistical analysis", protocol["statistical_plan"]),
    ("Result supporting H1", "At least one post-exact pair reaches the fixed 0.80 character threshold in final data, with manual confirmation that the substantive body is repeated."),
    ("Result not supporting H1", "No confirmed near-duplicate pair is found in any final sample. Automatic flags that are only boilerplate do not support H1."),
    ("Additional analyses", "Manual error analysis using the attached coding scheme; threshold sensitivity at 0.75, 0.80, 0.85 and 0.90; per-corpus and per-run results; runtime comparison."),
]

table = doc.add_table(rows=1, cols=2)
table.autofit = False
table.columns[0].width = Inches(1.65)
table.columns[1].width = Inches(5.15)
table.rows[0].cells[0].text = "Item"
table.rows[0].cells[1].text = "Frozen decision"
for cell in table.rows[0].cells:
    shade(cell, "D9E7F2")
    for p in cell.paragraphs:
        for run in p.runs:
            run.bold = True
for label, value in rows:
    cells = table.add_row().cells
    cells[0].text = label
    cells[1].text = value
for row in table.rows:
    for idx, cell in enumerate(row.cells):
        cell.width = Inches(1.65 if idx == 0 else 5.15)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        borders(cell)
        for p in cell.paragraphs:
            p.paragraph_format.space_after = Pt(1)
            for run in p.runs:
                run.font.size = Pt(8.3)

doc.add_paragraph("Fixed source revisions and sample sizes", style="Heading 1")
small = doc.add_table(rows=1, cols=4)
small.autofit = False
for cell, text in zip(small.rows[0].cells, ("Source", "Revision SHA prefix", "Rows per run", "Three runs")):
    cell.text = text
    shade(cell, "D9E7F2")
for source in protocol["corpora"]:
    cells = small.add_row().cells
    for cell, text in zip(cells, (source["label"], source["revision"][:12], str(source["runs"][0]["raw_rows_expected"]), str(sum(r["raw_rows_expected"] for r in source["runs"])))):
        cell.text = text
for row in small.rows:
    for cell in row.cells:
        borders(cell)
        for p in cell.paragraphs:
            p.paragraph_format.space_after = Pt(0)
            for run in p.runs:
                run.font.size = Pt(8)

doc.add_paragraph(
    "The exact block offsets and full source SHAs are in the accompanying frozen_protocol.json. "
    "Any change after this local freeze must be listed with a reason in Deviations from the frozen protocol. "
    "A source revision mismatch stops the run until the deviation is documented."
)
for source in protocol["corpora"]:
    p = doc.add_paragraph(f"{source['key']} revision: " + " ".join(source["revision"][i:i+10] for i in range(0, 40, 10)))
    p.paragraph_format.space_after = Pt(0)
    for run in p.runs:
        run.font.size = Pt(7.5)
doc.add_paragraph("Reference: Broder, A. Z. (1997). On the resemblance and containment of documents. Compression and Complexity of Sequences, 21–29.")
out.parent.mkdir(parents=True, exist_ok=True)
doc.save(out)
print(out)
