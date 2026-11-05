"""Add administrative names to a copy of the frozen Appendix A."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from docx import Document


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "protocol" / "Assignment4_Appendix_A_Protocol_Freeze.docx"
OUTPUT = ROOT / "protocol" / "Assignment4_Appendix_A_Submission_Copy.docx"
RECORD = ROOT / "protocol" / "local_freeze_record.json"
AUTHORS = "Gapar Galym; Bekzat Rashiduly; Nuradilet Mustafa"
GROUP = "SE-2418"

record = json.loads(RECORD.read_text(encoding="utf-8"))
actual = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
if actual != record["appendix_sha256"]:
    raise SystemExit("The original Appendix A no longer matches the local freeze record")

doc = Document(SOURCE)
for style_name in ("Normal", "Title", "Subtitle", "Heading 1"):
    doc.styles[style_name].font.name = "Times New Roman"
for paragraph in doc.paragraphs:
    if paragraph.text.startswith("Student(s):"):
        paragraph.text = f"Student(s): {AUTHORS}"
    elif paragraph.text.startswith("Group:"):
        paragraph.text = (
            f"Group: {GROUP}   Moodle upload date and time: "
            "Not uploaded before final experiments"
        )

for paragraph in doc.paragraphs:
    for run in paragraph.runs:
        run.font.name = "Times New Roman"
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.name = "Times New Roman"

doc.save(OUTPUT)
print(OUTPUT)
print("Original frozen Appendix A SHA-256:", actual)
