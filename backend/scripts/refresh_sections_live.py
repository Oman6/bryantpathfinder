"""Pull live section data from Bryant Banner SSB and overwrite data/sections.json.

Run this anytime to refresh seat counts and pick up newly-added sections.
No auth required; the endpoint is public.

Usage:
    python -m scripts.refresh_sections_live
    python -m scripts.refresh_sections_live 202710
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Allow running as a top-level script or as a module.
if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.banner_live import DEFAULT_TERM_CODE, fetch_live_sections, write_snapshot


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    term = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TERM_CODE
    sections = fetch_live_sections(term)

    out = Path(__file__).resolve().parents[2] / "data" / "sections.json"
    write_snapshot(sections, out)

    print(f"wrote {len(sections)} sections to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
