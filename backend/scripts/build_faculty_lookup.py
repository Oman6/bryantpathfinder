"""Build a compact faculty lookup keyed by 'Last, First' name.

Frontend consumes this for the schedule-card instructor enrichment.

Input:  data/bryant_faculty.json
Output: data/faculty_lookup.json (mirrored to frontend/public/)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def main() -> int:
    src = json.loads((DATA_DIR / "bryant_faculty.json").read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for f in src.get("faculty", []) or []:
        name = f.get("name") or f.get("display_name")
        if not name:
            continue
        out[name] = {
            "title": (f.get("title") or "").strip(),
            "department": (f.get("department") or "").strip(),
            "college": (f.get("college") or "").strip(),
            "email": (f.get("email") or "").strip(),
            "profile_url": f.get("profile_url"),
            "expertise": f.get("expertise"),
            "education": f.get("education"),
        }
    payload = {
        "_metadata": {
            "version": "1",
            "generated_at": datetime.now().isoformat(),
            "source": "data/bryant_faculty.json",
        },
        "faculty": out,
    }
    target = DATA_DIR / "faculty_lookup.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {len(out)} faculty records to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
