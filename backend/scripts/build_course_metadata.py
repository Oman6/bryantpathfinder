"""Build a compact course_metadata.json keyed by course_code.

Pulls descriptions / prerequisites / when_offered / cross_listed from the
CourseLeaf catalog scrape AND historical-offering counts from the master
catalog. The backend joins this into each Section before serving;
the frontend uses the same file for the course-detail popover.

Inputs:
  - data/courses_catalog.json
  - data/bryant_master_catalog.json (for historical offering counts)

Output:
  - data/course_metadata.json
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _normalize_prereq(text: str) -> str:
    if not text:
        return ""
    # Collapse whitespace, strip stray semicolons / artifacts
    return re.sub(r"\s+", " ", text).strip().rstrip(",").rstrip(";")


def main() -> int:
    catalog = json.loads((DATA_DIR / "courses_catalog.json").read_text(encoding="utf-8"))
    try:
        master = json.loads((DATA_DIR / "bryant_master_catalog.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        master = {"courses": []}

    # Map master records by course_code for the offering-count fields
    master_by_code: dict[str, dict] = {c["course_code"]: c for c in master.get("courses", [])}

    out: dict[str, dict] = {}
    for c in catalog.get("courses", []):
        code = c.get("course_code")
        if not code:
            continue
        m = master_by_code.get(code, {})
        out[code] = {
            "title": c.get("title") or "",
            "credits": c.get("credits"),
            "description": (c.get("description") or "").strip(),
            "prerequisites": _normalize_prereq(c.get("prerequisites") or ""),
            "corequisites": _normalize_prereq(c.get("corequisites") or ""),
            "when_offered": (c.get("when_offered") or "").strip(),
            "cross_listed": (c.get("cross_listed") or "").strip(),
            "in_active_catalog": c.get("in_active_catalog", True),
            "total_sections": m.get("total_sections", 0),
            "terms_offered": m.get("terms_offered", 0),
            "unique_instructors": m.get("unique_instructors", []),
            "programs_requiring_it": m.get("programs_requiring_it", []),
        }

    payload = {
        "_metadata": {
            "version": "1",
            "generated_at": datetime.now().isoformat(),
            "source": "courses_catalog.json + bryant_master_catalog.json",
        },
        "courses": out,
    }
    target = DATA_DIR / "course_metadata.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {len(out)} course records to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
