"""Scrape Bryant's canonical course catalog at catalog.bryant.edu.

Bryant runs CourseLeaf (not Acalog), but the goal is the same: extract every
undergraduate course's canonical metadata — code, title, credits, description,
prerequisites/corequisites, attributes, and rotation. Banner Self-Service has
the SECTIONS (real-time offerings, already in data/sections.json); CourseLeaf
has the COURSES (the canonical metadata that doesn't change between terms).

Two endpoints are used:

1. The CourseLeaf "FOSE" JSON API at
   ``/course-search/api/?page=fose&route=search`` and
   ``/course-search/api/?page=fose&route=details``.
   Used to enumerate every course key per subject and to fetch the canonical
   description (which has the embedded prerequisite links).

2. The published HTML course-description pages at
   ``/undergraduate/coursedescriptions/<subject>/``.
   These pages have richer metadata that FOSE does NOT expose: explicit credit
   hours, "Session Cycle" / "Yearly Cycle" rotation, and clean
   prerequisite/corequisite lines. We prefer this source when both are present.

The scraper iterates the subject index, fetches every subject page, parses each
``courseblock``, and merges with FOSE search results so we know which courses
are in the active catalog srcdb. Output goes to ``data/courses_catalog.json``.

Usage:
    python -m scripts.fetch_acalog_catalog
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

BASE = "https://catalog.bryant.edu"
SUBJECT_INDEX_URL = f"{BASE}/undergraduate/coursedescriptions/"
SUBJECT_PAGE_FMT = f"{BASE}/undergraduate/coursedescriptions/{{slug}}/"
COURSE_SEARCH_PAGE_URL = f"{BASE}/course-search/"
FOSE_API_URL = f"{BASE}/course-search/api/"
SRCDB = "2025"  # 2025-2026 catalog year
USER_AGENT = "BryantPathfinder/1.0 (research; oash@bryant.edu)"
REQUEST_SLEEP_SEC = 0.3
REQUEST_TIMEOUT_SEC = 30

OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "courses_catalog.json"
)

# Matches the courseblock title line: "FIN 310.  Intermediate Corporate Finance.  3 Credit Hours."
# Bryant uses non-breaking spaces between subject and number. We normalize \xa0 → space first.
TITLE_RE = re.compile(
    r"^\s*([A-Z]{2,5})\s+(\d{2,4}[A-Z]?)\.\s+(.+?)\.\s+(\d+(?:\.\d+)?)\s+Credit\s+Hours?",
    re.IGNORECASE,
)

# Matches embedded section labels like "Prerequisites:" or "Pre/Corequisites:"
PREREQ_LABEL_RE = re.compile(
    r"^(Prerequisites?|Pre/Corequisites?|Corequisites?|Cross-listed|Attributes?|Session Cycle|Yearly Cycle|Offered)\s*:?\s*$",
    re.IGNORECASE,
)


class HttpClient:
    """Thin wrapper around requests with a polite User-Agent and per-request sleep."""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def get(self, url: str) -> requests.Response:
        """GET with a small sleep before the request to stay polite."""
        time.sleep(REQUEST_SLEEP_SEC)
        resp = self.session.get(url, timeout=REQUEST_TIMEOUT_SEC, allow_redirects=True)
        resp.raise_for_status()
        return resp

    def post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST a JSON payload and return the parsed JSON response."""
        time.sleep(REQUEST_SLEEP_SEC)
        resp = self.session.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        return resp.json()


def discover_subject_slugs(client: HttpClient) -> list[tuple[str, str]]:
    """Return [(slug, label)] for every undergraduate subject in the catalog.

    The course-descriptions index lists each subject as a link:
        /undergraduate/coursedescriptions/fin/  →  "Finance (FIN)"
    """
    resp = client.get(SUBJECT_INDEX_URL)
    soup = BeautifulSoup(resp.text, "html.parser")
    pattern = re.compile(r"^/undergraduate/coursedescriptions/([a-z0-9]+)/$")
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        match = pattern.match(anchor["href"])
        if not match:
            continue
        slug = match.group(1)
        if slug in seen:
            continue
        seen.add(slug)
        found.append((slug, anchor.get_text(strip=True)))
    return found


def discover_fose_subject_keys(client: HttpClient) -> dict[str, str]:
    """Return {subject_code: subject_label} from the FOSE search form HTML."""
    resp = client.get(COURSE_SEARCH_PAGE_URL)
    soup = BeautifulSoup(resp.text, "html.parser")
    select = soup.find("select", id="crit-subject")
    out: dict[str, str] = {}
    if not isinstance(select, Tag):
        return out
    for opt in select.find_all("option"):
        code = (opt.get("value") or "").strip()
        if not code:
            continue
        out[code] = opt.get_text(strip=True)
    return out


def fose_search_subject(client: HttpClient, subject_code: str) -> list[dict[str, Any]]:
    """Return the FOSE search results for a single subject (one row per course)."""
    payload = {
        "other": {"srcdb": SRCDB},
        "criteria": [{"field": "subject", "value": subject_code}],
    }
    data = client.post_json(f"{FOSE_API_URL}?page=fose&route=search", payload)
    return list(data.get("results", []))


def normalize_text(raw: str) -> str:
    """Collapse whitespace, strip non-breaking spaces and zero-width chars."""
    cleaned = raw.replace("\xa0", " ").replace("​", "").replace("﻿", "")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def parse_courseblock(block: Tag) -> dict[str, Any] | None:
    """Parse a single ``.courseblock`` element into a course record.

    The HTML shape is consistent across subject pages:

        <div class="courseblock">
          <p class="courseblocktitle"><strong>FIN 310. Intermediate ... 3 Credit Hours.</strong></p>
          <p class="courseblockdesc">Description text...
            <br/>Prerequisites: <a>FIN 201</a>, Sophomore Standing
            <br/>Session Cycle: Fall, Spring
            <br/>Yearly Cycle: Annual.
          </p>
          ... per-term offerings tables (we ignore — those are sections) ...
        </div>
    """
    title_el = block.find(class_="courseblocktitle")
    if not isinstance(title_el, Tag):
        return None
    title_text = normalize_text(title_el.get_text(" ", strip=True))
    match = TITLE_RE.match(title_text)
    if not match:
        return None
    subject, number, title, credits = match.groups()

    desc_el = block.find(class_="courseblockdesc")
    description = ""
    metadata_lines: list[str] = []
    if isinstance(desc_el, Tag):
        # Split on <br> to separate description body from labeled metadata lines.
        # decode_contents preserves the <br>s as literal markers we can split on.
        raw_html = desc_el.decode_contents()
        # Replace <br> variants with a sentinel newline.
        chunks_html = re.sub(r"<br\s*/?>", "\n", raw_html, flags=re.IGNORECASE)
        chunks_soup = BeautifulSoup(chunks_html, "html.parser")
        chunks_text = normalize_text(chunks_soup.get_text("\n"))
        lines = [ln.strip() for ln in chunks_text.split("\n") if ln.strip()]
        description_parts: list[str] = []
        for line in lines:
            label_match = re.match(
                r"^(Prerequisites?|Pre/Corequisites?|Corequisites?|Cross-listed|Attributes?|Session Cycle|Yearly Cycle|Offered)\s*:\s*(.*)$",
                line,
                re.IGNORECASE,
            )
            if label_match:
                metadata_lines.append(line)
            elif metadata_lines:
                # If we've started seeing metadata, treat trailing lines as
                # continuations of the last metadata item (e.g., a long prereq).
                metadata_lines[-1] = metadata_lines[-1] + " " + line
            else:
                description_parts.append(line)
        description = " ".join(description_parts).strip()

    prereqs = ""
    coreqs = ""
    attributes = ""
    when_offered = ""
    cross_listed = ""
    for line in metadata_lines:
        m = re.match(
            r"^(Prerequisites?|Pre/Corequisites?|Corequisites?|Cross-listed|Attributes?|Session Cycle|Yearly Cycle|Offered)\s*:\s*(.*)$",
            line,
            re.IGNORECASE,
        )
        if not m:
            continue
        label = m.group(1).lower()
        value = m.group(2).strip().rstrip(".")
        if label.startswith("prereq"):
            prereqs = (prereqs + "; " + value).strip("; ") if prereqs else value
        elif label.startswith("pre/coreq"):
            # Pre/Coreq lines are functionally prerequisites; keep distinct copy too.
            prereqs = (prereqs + "; " + value).strip("; ") if prereqs else value
            coreqs = (coreqs + "; " + value).strip("; ") if coreqs else value
        elif label.startswith("coreq"):
            coreqs = (coreqs + "; " + value).strip("; ") if coreqs else value
        elif label.startswith("cross"):
            cross_listed = value
        elif label.startswith("attr"):
            attributes = value
        elif label in ("session cycle", "yearly cycle", "offered"):
            tag = label.replace(" cycle", "").title()
            piece = f"{tag}: {value}"
            when_offered = (when_offered + "; " + piece).strip("; ") if when_offered else piece

    try:
        credits_value: float | int = float(credits)
        if credits_value.is_integer():
            credits_value = int(credits_value)
    except ValueError:
        credits_value = 0

    return {
        "course_code": f"{subject} {number}",
        "subject": subject,
        "course_number": number,
        "title": title.strip(),
        "credits": credits_value,
        "description": description,
        "prerequisites": prereqs,
        "corequisites": coreqs,
        "attributes": attributes,
        "when_offered": when_offered,
        "cross_listed": cross_listed,
    }


def scrape_subject_page(
    client: HttpClient, slug: str
) -> tuple[list[dict[str, Any]], str | None]:
    """Fetch a single ``/undergraduate/coursedescriptions/<slug>/`` page.

    Returns (courses, error_message). On any HTTP/parse failure we return
    ``([], message)`` instead of crashing — one bad subject page should not
    sink the whole catalog scrape.
    """
    url = SUBJECT_PAGE_FMT.format(slug=slug)
    try:
        resp = client.get(url)
    except requests.RequestException as exc:
        return [], f"http_error: {exc}"
    soup = BeautifulSoup(resp.text, "html.parser")
    out: list[dict[str, Any]] = []
    for block in soup.select(".courseblock"):
        try:
            parsed = parse_courseblock(block)
        except (AttributeError, ValueError) as exc:
            print(f"  warn: courseblock parse error in /{slug}/: {exc}", file=sys.stderr)
            continue
        if parsed:
            out.append(parsed)
    return out, None


def main() -> int:
    """Scrape every undergraduate course and write data/courses_catalog.json."""
    client = HttpClient()

    print("[1/4] Discovering subject slugs from /undergraduate/coursedescriptions/ ...")
    subject_slugs = discover_subject_slugs(client)
    print(f"  found {len(subject_slugs)} subject pages")

    print("[2/4] Discovering FOSE subject codes ...")
    try:
        fose_subjects = discover_fose_subject_keys(client)
        print(f"  found {len(fose_subjects)} FOSE subjects")
    except (requests.RequestException, ValueError) as exc:
        print(f"  warn: could not load FOSE subject list: {exc}", file=sys.stderr)
        fose_subjects = {}

    print("[3/4] Scraping subject pages ...")
    all_courses: list[dict[str, Any]] = []
    failed_subjects: list[tuple[str, str]] = []
    for index, (slug, label) in enumerate(subject_slugs, start=1):
        prefix = f"  [{index:>2}/{len(subject_slugs)}] {slug:<6}"
        courses, error = scrape_subject_page(client, slug)
        if error:
            print(f"{prefix} FAILED: {error}", file=sys.stderr)
            failed_subjects.append((slug, error))
            continue
        print(f"{prefix} {len(courses):>3} courses ({label})")
        all_courses.extend(courses)

    print("[4/4] Cross-referencing FOSE active-catalog membership ...")
    fose_codes: set[str] = set()
    if fose_subjects:
        for code in sorted(fose_subjects.keys()):
            try:
                results = fose_search_subject(client, code)
            except (requests.RequestException, ValueError) as exc:
                print(f"  warn: FOSE lookup failed for {code}: {exc}", file=sys.stderr)
                continue
            for row in results:
                course_code = (row.get("code") or "").replace("\xa0", " ").strip()
                if course_code:
                    fose_codes.add(course_code)
        print(f"  FOSE returned {len(fose_codes)} active courses across all subjects")
        for course in all_courses:
            course["in_active_catalog"] = course["course_code"] in fose_codes

    output = {
        "source": SUBJECT_INDEX_URL,
        "fose_endpoint": FOSE_API_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "catalog_year": "2025-2026",
        "srcdb": SRCDB,
        "courses": all_courses,
        "failed_subjects": [
            {"slug": slug, "error": err} for slug, err in failed_subjects
        ],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")

    subjects_seen = sorted({c["subject"] for c in all_courses})
    with_desc = sum(1 for c in all_courses if c["description"])
    with_prereq = sum(1 for c in all_courses if c["prerequisites"])
    with_when = sum(1 for c in all_courses if c["when_offered"])
    with_attr = sum(1 for c in all_courses if c["attributes"])

    print()
    print("=== summary ===")
    print(f"output:                   {OUTPUT_PATH}")
    print(f"total courses:            {len(all_courses)}")
    print(f"distinct subjects:        {len(subjects_seen)}")
    print(f"with description:         {with_desc}")
    print(f"with prerequisites:       {with_prereq}")
    print(f"with when_offered:        {with_when}")
    print(f"with attributes:          {with_attr}")
    print(f"failed subject pages:     {len(failed_subjects)}")
    if failed_subjects:
        for slug, err in failed_subjects:
            print(f"  - {slug}: {err}")
    if all_courses:
        print()
        print("=== sample course (first) ===")
        print(json.dumps(all_courses[0], indent=2)[:1000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
