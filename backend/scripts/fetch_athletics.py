"""Fetch Bryant Bulldogs athletic schedule from the SIDEARM RSS feed.

bryantbulldogs.com runs SIDEARM Sports, which exposes an unauthenticated RSS
feed of every team's schedule at /calendar.ashx?path=all&type=rss. The RSS
includes per-event start/end times, sport, opponent, location, and links.

We normalize this to data/bryant_athletics.json which the UI consumes.

Usage:
    python -m scripts.fetch_athletics
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import requests

RSS_URL = "https://bryantbulldogs.com/calendar.ashx?path=all&type=rss"

NS = {
    "ev": "http://purl.org/rss/1.0/modules/event/",
    "s": "http://sidearmsports.com/schemas/cal_rss/1.0/",
}


def _text(el: ET.Element | None) -> str | None:
    if el is None:
        return None
    return (el.text or "").strip() or None


def _parse_iso(value: str | None) -> str | None:
    if not value:
        return None
    # SIDEARM uses non-standard 7-digit fractional seconds; strip them.
    cleaned = re.sub(r"\.\d+", "", value).rstrip("Z")
    try:
        dt = datetime.fromisoformat(cleaned)
        return dt.isoformat()
    except ValueError:
        return None


def parse_events(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    events: list[dict] = []
    for item in root.findall(".//item"):
        title = _text(item.find("title")) or ""
        # Parse out sport name from title pattern: "3/27 8:00 AM [N] Bryant University <Sport> vs <Opp>"
        sport = ""
        m = re.search(r"\bBryant University\s+(.+?)\s+(?:vs|at)\s+", title)
        if m:
            sport = m.group(1).strip()

        location = _text(item.find("ev:location", NS)) or ""
        is_home = "Smithfield" in location

        local_start = _text(item.find("s:localstartdate", NS))
        local_end = _text(item.find("s:localenddate", NS))
        opponent = _text(item.find("s:opponent", NS)) or ""

        events.append({
            "title": title,
            "sport": sport,
            "opponent": opponent,
            "location": location,
            "is_home": is_home,
            "start_local": _parse_iso(local_start),
            "end_local": _parse_iso(local_end),
            "link": _text(item.find("link")),
        })
    events.sort(key=lambda e: e["start_local"] or "")
    return events


def main() -> int:
    resp = requests.get(
        RSS_URL,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0 (BryantPathfinder; oash@bryant.edu)",
            "Accept": "application/rss+xml, text/xml, */*",
        },
    )
    resp.raise_for_status()
    events = parse_events(resp.text)

    out = {
        "source": RSS_URL,
        "fetched_at": datetime.now().isoformat(),
        "events": events,
    }
    target = Path(__file__).resolve().parents[2] / "data" / "bryant_athletics.json"
    target.write_text(json.dumps(out, indent=2), encoding="utf-8")
    home_count = sum(1 for e in events if e["is_home"])
    print(f"wrote {len(events)} events ({home_count} home) to {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
