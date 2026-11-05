"""Timestamp and hash the prepared protocol before any final data are read."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
protocol = ROOT / "config" / "frozen_protocol.json"
appendix = ROOT / "protocol" / "Assignment4_Appendix_A_Protocol_Freeze.docx"
out = ROOT / "protocol" / "local_freeze_record.json"
if out.exists():
    raise SystemExit("Local freeze record already exists; do not overwrite it")
record = {
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
    "appendix_sha256": hashlib.sha256(appendix.read_bytes()).hexdigest(),
    "moodle_uploaded": False,
    "deviation": "The user found no separate protocol submission in Moodle and requested completing the project before uploading. Appendix A was fixed locally before the final run and will be submitted with the report; this does not satisfy the brief's pre-run Moodle timestamp rule.",
}
out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(out)
print(record["created_utc"])
