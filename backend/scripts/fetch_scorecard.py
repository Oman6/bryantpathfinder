"""Fetch Bryant University earnings outcomes by major from College Scorecard.

College Scorecard is the U.S. Department of Education's free public dataset of
post-graduation earnings, debt, and demographics by school and major.

Bryant's UNITID is 217165. Bachelor's degrees are credential.level == 3.

DEMO_KEY works for low-volume requests. For sustained use, get a free key at
https://api.data.gov/signup/ and set SCORECARD_API_KEY in .env.

Usage:
    python -m scripts.fetch_scorecard
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

SCORECARD_URL = "https://api.data.gov/ed/collegescorecard/v1/schools"
BRYANT_UNITID = 217165


def fetch() -> list[dict]:
    api_key = os.environ.get("SCORECARD_API_KEY", "DEMO_KEY")
    params = {
        "id": BRYANT_UNITID,
        "fields": "latest.programs.cip_4_digit",
        "api_key": api_key,
    }
    resp = requests.get(SCORECARD_URL, params=params, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    school = (body.get("results") or [{}])[0]
    return school.get("latest.programs.cip_4_digit") or []


def shape(programs: list[dict]) -> list[dict]:
    """Filter to Bachelor's-level programs and flatten earnings."""
    out: list[dict] = []
    for p in programs:
        cred = (p.get("credential") or {}).get("level")
        if cred != 3:
            continue
        earnings = p.get("earnings") or {}
        e1 = (earnings.get("1_yr") or {}).get("overall_median_earnings")
        e4 = (earnings.get("4_yr") or {}).get("overall_median_earnings")
        e5 = (earnings.get("5_yr") or {}).get("overall_median_earnings")
        e4_natl = (earnings.get("4_yr") or {}).get("overall_median_earnings_national")
        out.append({
            "cip_code": p.get("code"),
            "title": (p.get("title") or "").strip().rstrip(".").strip(),
            "credential": (p.get("credential") or {}).get("title"),
            "ipeds_awards": (p.get("counts") or {}).get("ipeds_awards1"),
            "earnings_1yr": e1,
            "earnings_4yr": e4,
            "earnings_5yr": e5,
            "earnings_4yr_national": e4_natl,
        })
    out.sort(key=lambda x: (x["earnings_4yr"] or 0), reverse=True)
    return out


def main() -> int:
    programs = fetch()
    bachelors = shape(programs)
    out = {
        "source": "U.S. Dept. of Education College Scorecard (api.data.gov)",
        "school_name": "Bryant University",
        "unitid": BRYANT_UNITID,
        "programs": bachelors,
    }
    target = Path(__file__).resolve().parents[2] / "data" / "scorecard_bryant.json"
    target.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {len(bachelors)} bachelor's programs to {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
