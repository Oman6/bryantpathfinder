"""Bryant Banner Self-Service live section feed.

Hits Bryant's public StudentRegistrationSsb endpoint to pull every section in
a given term with real-time seat counts. Replaces the static sections.json
snapshot with current data — no auth required, no API key.

Endpoint trail (reverse-engineered, all unauthenticated):
  POST /StudentRegistrationSsb/ssb/classSearch/resetDataForm
  POST /StudentRegistrationSsb/ssb/term/search?mode=search   (form: term=<code>)
  GET  /StudentRegistrationSsb/ssb/searchResults/searchResults
       ?txt_term=<code>&pageOffset=<n>&pageMaxSize=500

A Banner session cookie carries state between the term-set and the searchResults
call. The fetcher manages that cookie inside a single requests.Session.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import requests

from .models import Meeting, Section

logger = logging.getLogger(__name__)

BANNER_BASE = "https://reg-prod.bryantec.bryant.edu/StudentRegistrationSsb"
DEFAULT_TERM_CODE = "202710"  # Fall 2026
DEFAULT_TERM_DESC = "Fall 2026"
PAGE_SIZE = 500
TIMEOUT = 30

# Banner's day booleans → Pathfinder's day codes.
_DAY_KEYS = [
    ("monday", "M"),
    ("tuesday", "T"),
    ("wednesday", "W"),
    ("thursday", "R"),
    ("friday", "F"),
]


def _hhmm(t: str | None) -> str | None:
    """Banner returns '1830'; Pathfinder uses '18:30'."""
    if not t or len(t) != 4:
        return None
    return f"{t[:2]}:{t[2:]}"


def _parse_meeting(mt_block: dict[str, Any]) -> Meeting | None:
    mt = mt_block.get("meetingTime") or {}
    days = [code for key, code in _DAY_KEYS if mt.get(key)]
    start = _hhmm(mt.get("beginTime"))
    end = _hhmm(mt.get("endTime"))
    if not days or not start or not end:
        return None
    return Meeting(
        days=days,
        start=start,
        end=end,
        building=mt.get("buildingDescription") or mt.get("building"),
        room=mt.get("room"),
    )


def _instructor_name(faculty: list[dict[str, Any]] | None) -> str | None:
    if not faculty:
        return None
    primary = next((f for f in faculty if f.get("primaryIndicator")), faculty[0])
    return primary.get("displayName")


def _parse_section(row: dict[str, Any]) -> Section | None:
    """Map a Banner JSON row to a Pathfinder Section. Returns None on bad rows."""
    try:
        crn = str(row["courseReferenceNumber"])
        subject = row.get("subject") or ""
        course_number = row.get("courseNumber") or ""
        if not subject or not course_number:
            return None

        meetings_blocks = row.get("meetingsFaculty") or []
        meetings = [m for m in (_parse_meeting(b) for b in meetings_blocks) if m is not None]
        is_async = len(meetings) == 0

        sched_type_desc = row.get("scheduleTypeDescription") or "Lecture"

        # Banner credit hours: sometimes creditHours, sometimes creditHourLow/High.
        credits = row.get("creditHours") or row.get("creditHourLow") or 0
        try:
            credits = float(credits)
        except (TypeError, ValueError):
            credits = 0.0

        seats_total = int(row.get("maximumEnrollment") or 0)
        seats_open = int(row.get("seatsAvailable") or 0)
        wl_total = int(row.get("waitCapacity") or 0)
        wl_open = int(row.get("waitAvailable") or 0)

        return Section(
            crn=crn,
            subject=subject,
            course_number=course_number,
            course_code=f"{subject} {course_number}",
            title=row.get("courseTitle") or "",
            section=row.get("sequenceNumber") or "A",
            credits=credits,
            instructor=_instructor_name(row.get("faculty")),
            meetings=meetings,
            seats_open=seats_open,
            seats_total=seats_total,
            waitlist_open=wl_open,
            waitlist_total=wl_total,
            is_full=seats_open <= 0,
            is_async=is_async,
            schedule_type=sched_type_desc,
            term=row.get("termDesc") or DEFAULT_TERM_DESC,
        )
    except Exception as e:
        logger.warning("banner_live.parse_failed crn=%s err=%s", row.get("courseReferenceNumber"), e)
        return None


def fetch_live_sections(term_code: str = DEFAULT_TERM_CODE) -> list[Section]:
    """Pull every section for the given term from Bryant's Banner SSB.

    Returns a list of Section objects. Raises on network/HTTP errors so the
    caller can fall back to the static snapshot.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "BryantPathfinder/1.0 (research project; oash@bryant.edu)",
    })

    # Step 1: warm a Banner session cookie.
    session.get(f"{BANNER_BASE}/ssb/classSearch/classSearch", timeout=TIMEOUT)

    # Step 2: clear any prior search state.
    session.post(f"{BANNER_BASE}/ssb/classSearch/resetDataForm", timeout=TIMEOUT)

    # Step 3: select the term.
    session.post(
        f"{BANNER_BASE}/ssb/term/search?mode=search",
        data={"term": term_code},
        timeout=TIMEOUT,
    )

    # Step 4: paginate through search results.
    sections: list[Section] = []
    page_offset = 0
    while True:
        resp = session.get(
            f"{BANNER_BASE}/ssb/searchResults/searchResults",
            params={
                "txt_term": term_code,
                "pageOffset": page_offset,
                "pageMaxSize": PAGE_SIZE,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            raise RuntimeError(f"Banner returned success=false at offset {page_offset}")

        rows = body.get("data") or []
        total = body.get("totalCount", 0)
        for row in rows:
            sec = _parse_section(row)
            if sec is not None:
                sections.append(sec)

        page_offset += len(rows)
        if not rows or page_offset >= total:
            break

    logger.info("banner_live.fetched count=%d term=%s", len(sections), term_code)
    return sections


def write_snapshot(sections: list[Section], path: Path) -> None:
    """Persist a Section list as JSON in the same shape as data/sections.json."""
    payload = [s.model_dump() for s in sections]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
