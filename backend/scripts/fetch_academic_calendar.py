"""Scrape Bryant's published academic calendar from catalog.bryant.edu.

Bryant publishes its undergraduate academic calendar as HTML tables on the
catalog (Modern Campus / Acalog) site. There is no API, but the markup is
stable enough to scrape twice a year.

The scraper:
  - Tries the next-year URL (e.g. /2026-2027/) first
  - Falls back to the canonical /undergraduate/academiccalendar/ URL
  - Parses every table, normalizes "Tuesday, September 2" → ISO date
  - Tags each event by semester based on context
  - Writes data/bryant_academic_calendar.json

The output is a flat list of events with: date (ISO), label, semester. The UI
filters by date range (next 90 days) and semester.

Usage:
    python -m scripts.fetch_academic_calendar
    python -m scripts.fetch_academic_calendar 2026-2027
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, date
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag

CATALOG_BASE = "https://catalog.bryant.edu/undergraduate/academiccalendar"

# Maps semester header phrasing to a canonical token. The header text appears
# above each table on the calendar page.
SEMESTER_PATTERNS = [
    (re.compile(r"\bFall\s+(\d{4})", re.I), "Fall {year}"),
    (re.compile(r"\bSpring\s+(\d{4})", re.I), "Spring {year}"),
    (re.compile(r"\bWinter(?:\s+Term)?\s+(\d{4})", re.I), "Winter {year}"),
    (re.compile(r"\bSummer\s+(\d{4})", re.I), "Summer {year}"),
]

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def detect_year_for_table(table: Tag, default_year: int) -> int:
    """Walk preceding siblings looking for a year hint."""
    for sib in table.find_all_previous(string=True, limit=20):
        text = str(sib)
        m = re.search(r"\b(20\d{2})", text)
        if m:
            return int(m.group(1))
    return default_year


def parse_date_phrase(text: str, year: int) -> date | None:
    """Extract the first 'Month D' from a string and combine with year."""
    m = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})", text, re.I)
    if not m:
        return None
    month = MONTHS[m.group(1).lower()]
    day = int(m.group(2))
    try:
        return date(year, month, day)
    except ValueError:
        return None


def detect_semester(heading_text: str) -> str | None:
    for pat, fmt in SEMESTER_PATTERNS:
        m = pat.search(heading_text)
        if m:
            return fmt.format(year=m.group(1))
    return None


def find_semester_for_table(table: Tag) -> str | None:
    """Walk preceding headings/strong tags for a semester label."""
    for sib in table.find_all_previous(["h1", "h2", "h3", "h4", "strong", "p"], limit=8):
        sem = detect_semester(sib.get_text(" ", strip=True))
        if sem:
            return sem
    return None


def fetch_html(year_path: str | None = None) -> tuple[str, str]:
    """Try a year-specific path, then fall back. Returns (html, url)."""
    if year_path:
        url = f"{CATALOG_BASE}/{year_path}/"
        r = requests.get(url, timeout=20)
        if r.status_code == 200 and "academic" in r.text.lower():
            return r.text, url
    url = f"{CATALOG_BASE}/"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.text, url


def parse_calendar(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    events: list[dict] = []
    today_year = datetime.now().year

    for table in soup.find_all("table"):
        semester = find_semester_for_table(table)
        # Year hint: pull from the semester string if we have one.
        year_hint = today_year
        if semester:
            ym = re.search(r"(20\d{2})", semester)
            if ym:
                year_hint = int(ym.group(1))

        rows = table.find_all("tr")
        for r in rows:
            cells = [c.get_text(" ", strip=True) for c in r.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            label, when = cells[0], cells[1]
            if not when or label.lower() in {"event", "date"}:
                continue
            d = parse_date_phrase(when, year_hint)
            # Some semester rows span year-end (Dec → Jan). If date is January
            # but the semester says e.g. Fall 2025, push to year+1.
            if d and "January" in when and semester and "Fall" in semester:
                d = d.replace(year=year_hint + 1)
            if d is None:
                continue
            events.append({
                "date": d.isoformat(),
                "label": label.strip().rstrip(":").strip(),
                "raw_when": when.strip(),
                "semester": semester,
            })

    # De-duplicate (date, label) — Bryant repeats rows in some tables.
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for e in events:
        key = (e["date"], e["label"])
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    out.sort(key=lambda x: x["date"])
    return out


def main() -> int:
    year_path = sys.argv[1] if len(sys.argv) > 1 else None
    html, url = fetch_html(year_path)
    events = parse_calendar(html)
    target = Path(__file__).resolve().parents[2] / "data" / "bryant_academic_calendar.json"
    payload = {
        "source_url": url,
        "fetched_at": datetime.now().isoformat(),
        "events": events,
    }
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {len(events)} events to {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
