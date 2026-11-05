"""Create a shareable Assignment 4 package without downloaded source texts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT.parent / "outputs" / "Assignment4_Kazakh_Near_Duplicate_Project.zip"
INCLUDE = [
    ROOT / "README.md", ROOT / "requirements.txt", ROOT / "LICENSE", ROOT / ".gitignore",
    *sorted((ROOT / "src").glob("*.py")),
    ROOT / "config" / "frozen_protocol.json",
    ROOT / "protocol" / "Assignment4_Appendix_A_Protocol_Freeze.docx",
    ROOT / "protocol" / "local_freeze_record.json",
    ROOT / "protocol" / "deviations_log.md",
    ROOT / "protocol" / "manual_audit_codebook.md",
    ROOT / "protocol" / "Appendix_C_Reproduction_Test_Template.md",
    ROOT / "protocol" / "Appendix_C_Reproduction_Record.md",
    ROOT / "report" / "Assignment4_Kazakh_Near_Duplicate_Results.docx",
    ROOT / "report" / "Assignment4_Individual_Defence_Notes.md",
    *sorted((ROOT / "results").glob("*.json")),
    *sorted((ROOT / "results").glob("*.csv")),
    *sorted((ROOT / "results").glob("*.svg")),
    *sorted((ROOT / "results").glob("*.png")),
]
INCLUDE = [path for path in INCLUDE if path.is_file() and path.name not in ("audit_review_local.html", "release_file_hashes.json")]
DEST.parent.mkdir(parents=True, exist_ok=True)
manifest = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in INCLUDE}
manifest_path = ROOT / "results" / "release_file_hashes.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
with ZipFile(DEST, "w", ZIP_DEFLATED) as archive:
    for path in INCLUDE + [manifest_path]:
        archive.write(path, path.relative_to(ROOT))
print(DEST)
print("Packaged", len(INCLUDE) + 1, "files; bytes", DEST.stat().st_size)
