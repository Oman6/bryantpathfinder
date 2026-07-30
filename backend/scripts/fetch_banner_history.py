"""Pull every section across the last ~10 regular Bryant terms from Banner SSB.

Expands on `backend/app/banner_live.py` (which fetches one term) by sweeping
the most recent regular undergraduate Fall / Spring / Summer terms. Output is
written to `data/sections_history.json` so the solver / requirement expander
can answer "was FIN 470 offered last year?" type questions.

Usage:
    python -m backend.scripts.fetch_banner_history

Filtering rules — keep only:
    - Fall YYYY
    - Spring YYYY
    - Undergraduate Summer YYYY

Skip:
    - "(View Only)" suffix (still kept — most recent past terms are view-only)
    - "PA " prefixed terms (Physician Assistant program)
    - "Online Program(s) ..." terms
    - "Graduate ..." / "GR Prerequisite ..." terms
    - "Winter Session ..." terms
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests

# Make `app` importable when running this file directly. The backend uses
# `app.*` imports (no top-level `backend` package), so we put `backend/` on
# sys.path and pull from `app.banner_live`.
HERE = Path(__file__).resolve()
BACKEND_DIR = HERE.parents[1]
REPO_ROOT = HERE.parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.banner_live import _parse_section  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fetch_banner_history")

BANNER_BASE = "https://reg-prod.bryantec.bryant.edu/StudentRegistrationSsb"
USER_AGENT = "BryantPathfinder/1.0 (research; oash@bryant.edu)"
PAGE_SIZE = 500
TIMEOUT = 60
TERM_PAUSE_SECONDS = 1.0
MAX_TERMS = 10

# A "regular" undergraduate term description, ignoring any "(View Only)" suffix.
# Examples that match: "Fall 2026", "Spring 2024", "Undergraduate Summer 2025".
_REGULAR_RE = re.compile(
    r"^(Fall|Spring|Undergraduate Summer)\s+\d{4}(\s*\(View Only\))?\s*$"
)

OUTPUT_PATH = REPO_ROOT / "data" / "sections_history.json"


def fetch_term_list() -> list[dict[str, Any]]:
    """Return Banner's full term list (no auth required)."""
    resp = requests.get(
        f"{BANNER_BASE}/ssb/classSearch/getTerms",
        params={"searchTerm": "", "offset": 1, "max": 200},
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def filter_regular_terms(
    terms: list[dict[str, Any]], limit: int = MAX_TERMS
) -> list[dict[str, Any]]:
    """Pick the `limit` most recent regular undergraduate terms.

    Banner returns terms sorted newest-first, so we iterate in order and stop
    once we've collected `limit` matches.
    """
    kept: list[dict[str, Any]] = []
    for t in terms:
        desc = (t.get("description") or "").strip()
        if not _REGULAR_RE.match(desc):
            continue
        kept.append(t)
        if len(kept) >= limit:
            break
    return kept


def fetch_term_sections(term_code: str, term_desc: str) -> list[dict[str, Any]]:
    """Run the 3-step Banner flow for one term and return parsed sections.

    Each call gets a fresh `requests.Session` — Banner's term-state cookie
    must be issued AFTER the term-set POST, and a stale cookie from the
    previous term causes the searchResults endpoint to return the wrong data.

    Returns a list of `Section.model_dump()` dicts. Empty list on any failure.
    """
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    try:
        # Step 1: warm a Banner session cookie. Banner sometimes 302s here.
        session.get(
            f"{BANNER_BASE}/ssb/classSearch/classSearch",
            timeout=TIMEOUT,
            allow_redirects=True,
        )
        # Step 2: clear any prior search state.
        session.post(
            f"{BANNER_BASE}/ssb/classSearch/resetDataForm", timeout=TIMEOUT
        )
        # Step 3: select the term.
        session.post(
            f"{BANNER_BASE}/ssb/term/search?mode=search",
            data={"term": term_code},
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        logger.warning(
            "term_setup.failed term=%s desc=%s err=%s", term_code, term_desc, e
        )
        return []

    sections: list[dict[str, Any]] = []
    page_offset = 0
    while True:
        try:
            resp = session.get(
                f"{BANNER_BASE}/ssb/searchResults/searchResults",
                params={
                    "txt_term": term_code,
                    "pageOffset": page_offset,
                    "pageMaxSize": PAGE_SIZE,
                },
                timeout=TIMEOUT,
            )
        except requests.RequestException as e:
            logger.warning(
                "searchResults.network_error term=%s offset=%s err=%s",
                term_code,
                page_offset,
                e,
            )
            return sections  # return what we have so far

        if resp.status_code == 404:
            logger.info("term.not_found term=%s desc=%s", term_code, term_desc)
            return []
        if resp.status_code != 200:
            logger.warning(
                "searchResults.bad_status term=%s offset=%s status=%s",
                term_code,
                page_offset,
                resp.status_code,
            )
            return sections

        try:
            body = resp.json()
        except ValueError:
            logger.warning(
                "searchResults.bad_json term=%s offset=%s", term_code, page_offset
            )
            return sections

        if not body.get("success"):
            logger.warning(
                "searchResults.success_false term=%s offset=%s",
                term_code,
                page_offset,
            )
            return sections

        rows = body.get("data") or []
        total = int(body.get("totalCount", 0))

        for row in rows:
            sec = _parse_section(row)
            if sec is None:
                continue
            payload = sec.model_dump()
            # The shared parser stamps a default term_desc; overwrite with this
            # term's true description so history rows are unambiguous.
            payload["term"] = term_desc
            sections.append(payload)

        page_offset += len(rows)
        if not rows or page_offset >= total:
            break

    return sections


def main() -> int:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    logger.info("fetching term list")
    all_terms = fetch_term_list()
    logger.info("term_list.size=%d", len(all_terms))

    targets = filter_regular_terms(all_terms, limit=MAX_TERMS)
    logger.info(
        "selected %d regular terms: %s",
        len(targets),
        ", ".join(f"{t['code']} {t['description']}" for t in targets),
    )

    output: dict[str, Any] = {"terms": []}
    summary_rows: list[tuple[str, str, int]] = []
    failures: list[tuple[str, str, str]] = []

    for i, term in enumerate(targets):
        code = str(term["code"])
        desc = str(term["description"])
        logger.info("term.start [%d/%d] %s %s", i + 1, len(targets), code, desc)

        try:
            sections = fetch_term_sections(code, desc)
        except Exception as e:
            logger.exception("term.exception term=%s err=%s", code, e)
            failures.append((code, desc, str(e)))
            sections = []

        logger.info("term.done %s sections=%d", code, len(sections))

        output["terms"].append(
            {
                "code": code,
                "description": desc,
                "section_count": len(sections),
                "sections": sections,
            }
        )
        summary_rows.append((code, desc, len(sections)))

        if i < len(targets) - 1:
            time.sleep(TERM_PAUSE_SECONDS)

    OUTPUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")

    total_sections = sum(c for _, _, c in summary_rows)
    unique_courses: set[str] = set()
    for term_block in output["terms"]:
        for s in term_block["sections"]:
            unique_courses.add(s["course_code"])

    print()
    print("=" * 64)
    print(f"{'TERM CODE':<12}{'DESCRIPTION':<36}{'SECTIONS':>10}")
    print("-" * 64)
    for code, desc, count in summary_rows:
        print(f"{code:<12}{desc:<36}{count:>10}")
    print("-" * 64)
    print(f"{'TOTAL':<48}{total_sections:>10}")
    print(f"unique course codes: {len(unique_courses)}")
    print(f"output: {OUTPUT_PATH}")
    if failures:
        print()
        print(f"failures ({len(failures)}):")
        for code, desc, err in failures:
            print(f"  {code} {desc}: {err}")
    print("=" * 64)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
