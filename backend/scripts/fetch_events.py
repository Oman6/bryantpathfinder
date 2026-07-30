"""Fetch upcoming Bryant campus events from the Localist public API.

events.bryant.edu runs Localist (Concept3D), which exposes a documented
unauthenticated read API at /api/2/events. We pull the next 60 days, ranked.

Usage:
    python -m scripts.fetch_events
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import requests

EVENTS_URL = "https://events.bryant.edu/api/2/events"
PAGE_SIZE = 100
DAYS_AHEAD = 60


def fetch_all() -> list[dict]:
    out: list[dict] = []
    page = 1
    while True:
        resp = requests.get(
            EVENTS_URL,
            params={"days": DAYS_AHEAD, "pp": PAGE_SIZE, "page": page},
            headers={"User-Agent": "BryantPathfinder/1.0 (oash@bryant.edu)"},
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        events = body.get("events") or []
        if not events:
            break
        out.extend(events)
        # Localist returns the same length each page until exhausted.
        if len(events) < PAGE_SIZE:
            break
        page += 1
        if page > 10:  # safety stop
            break
    return out


def shape(events: list[dict]) -> list[dict]:
    shaped: list[dict] = []
    for wrapper in events:
        e = wrapper.get("event") or {}
        instances = e.get("event_instances") or []
        first = (instances[0] or {}).get("event_instance") or {}
        shaped.append({
            "id": e.get("id"),
            "title": e.get("title"),
            "url": e.get("url"),
            "location": e.get("location_name") or e.get("location"),
            "experience": e.get("experience"),
            "start": first.get("start"),
            "end": first.get("end"),
            "all_day": first.get("all_day"),
            "ranking": first.get("ranking", 0),
            "tags": e.get("tags") or [],
            "free": e.get("free"),
        })
    shaped.sort(key=lambda x: x["start"] or "")
    return shaped


def main() -> int:
    raw = fetch_all()
    events = shape(raw)
    out = {
        "source": EVENTS_URL,
        "fetched_at": datetime.now().isoformat(),
        "events": events,
    }
    target = Path(__file__).resolve().parents[2] / "data" / "bryant_events.json"
    target.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {len(events)} events to {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
