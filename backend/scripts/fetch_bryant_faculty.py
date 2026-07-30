"""Scrape Bryant University's faculty directory.

Two-stage strategy:

1. PRIMARY: Parse the catalog page
   https://catalog.bryant.edu/undergraduate/universityadministrationfacultystaff/
   It serves a single static page listing every faculty member with name, rank,
   department, and education in a consistent ``<div><p><b>Name</b>, Title,
   Department, Education</p></div>`` pattern under three section headers
   (Emeritus, Tenure & Tenure Track, Term).

2. ENRICHMENT: For each faculty, try the marketing site profile at
   ``https://www.bryant.edu/academics/faculty/<last>-<first>`` to pull email,
   profile_url, expertise/research interests, and college affiliation. Many
   profiles 404 (especially Emeritus / Term lecturers); we skip cleanly.

The Drupal directory at /undergraduate/academics/faculty is AJAX-paginated and
its /views/ajax endpoint rejects unauthenticated cross-site POSTs, so the
catalog page is the only practical full-roster source. Documented as a
limitation below.

After writing data/bryant_faculty.json, the script prints how many of the
catalog names match keys in data/professor_ratings.json.

Usage:
    python -m scripts.fetch_bryant_faculty
"""

from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

CATALOG_URL = (
    "https://catalog.bryant.edu/undergraduate/"
    "universityadministrationfacultystaff/"
)
PROFILE_BASE = "https://www.bryant.edu/academics/faculty/"

UA = "BryantPathfinder/1.0 (+student project; owen.ash777@gmail.com)"
HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}
SLEEP = 0.3
TIMEOUT = 20

# Headings under which we expect faculty entries on the catalog page.
SECTION_HEADERS = {
    "Dean Emeritus": "emeritus",
    "Emeritus Faculty": "emeritus",
    "Tenure and Tenure Track Faculty": "tenure_track",
    "Term Faculty": "term",
}

# Bryant department names that appear in the catalog as the segment after
# the academic title. We use this whitelist to decide where the title ends
# and the department begins (titles can themselves contain commas, e.g.
# "Associate Professor of Practice"). Multi-word departments listed first.
KNOWN_DEPARTMENTS = [
    # Multi-word with internal commas first (regex anchors on these).
    "History, Literature and the Arts",
    "History, Literature, and the Arts",
    "Politics, Law and Society",
    "Politics, Law, and Society",
    # Multi-word without internal commas
    "Communication and Language Studies",
    "Biological and Biomedical Sciences",
    "Biological Biomedical Sciences",
    "English and Cultural Studies",
    "History and Social Sciences",
    "Information Systems and Analytics",
    "Computer Information Systems",
    "Exercise and Movement Science",
    "Physician Assistant Studies",
    "Mathematics and Economics",
    "Mathematics Economics",
    "Information Systems Analytics",
    "History, Literature, and Cultural Studies",
    "Exercise Science",
    "Literary and Cultural Studies",
    "Modern Languages",
    "Health Sciences",
    "Public Health",
    "Science and Technology",
    "Marketing/Management",
    "Management/Marketing",
    "Communications",
    "Communication",
    # Single word
    "Accounting",
    "Finance",
    "Marketing",
    "Management",
    "Psychology",
    "Biology",
    "Mathematics",
    "Economics",
    "Philosophy",
    "Sociology",
]

# Known department -> college mapping for Bryant. Used as an enrichment when
# the profile page does not state the college explicitly.
DEPT_TO_COLLEGE = {
    # College of Business
    "Accounting": "College of Business",
    "Finance": "College of Business",
    "Marketing": "College of Business",
    "Management": "College of Business",
    "Marketing/Management": "College of Business",
    "Management/Marketing": "College of Business",
    "Information Systems and Analytics": "College of Business",
    "Computer Information Systems": "College of Business",
    # School of Health and Behavioral Sciences
    "Psychology": "School of Health and Behavioral Sciences",
    "Biology": "School of Health and Behavioral Sciences",
    "Biological and Biomedical Sciences":
        "School of Health and Behavioral Sciences",
    "Biological Biomedical Sciences":
        "School of Health and Behavioral Sciences",
    "Health Sciences": "School of Health and Behavioral Sciences",
    "Public Health": "School of Health and Behavioral Sciences",
    "Exercise and Movement Science":
        "School of Health and Behavioral Sciences",
    "Physician Assistant Studies":
        "School of Health and Behavioral Sciences",
    # College of Arts and Sciences
    "English and Cultural Studies": "College of Arts and Sciences",
    "Communication": "College of Arts and Sciences",
    "Communications": "College of Arts and Sciences",
    "Communication and Language Studies": "College of Arts and Sciences",
    "History and Social Sciences": "College of Arts and Sciences",
    "History, Literature and the Arts": "College of Arts and Sciences",
    "History, Literature, and the Arts": "College of Arts and Sciences",
    "Politics, Law and Society": "College of Arts and Sciences",
    "Politics, Law, and Society": "College of Arts and Sciences",
    "Modern Languages": "College of Arts and Sciences",
    "Mathematics": "College of Arts and Sciences",
    "Mathematics and Economics": "College of Arts and Sciences",
    "Mathematics Economics": "College of Arts and Sciences",
    "History, Literature, and Cultural Studies": "College of Arts and Sciences",
    "Information Systems Analytics": "College of Business",
    "Exercise Science": "School of Health and Behavioral Sciences",
    "Economics": "College of Arts and Sciences",
    "Science and Technology": "College of Arts and Sciences",
    "Literary and Cultural Studies": "College of Arts and Sciences",
    "Philosophy": "College of Arts and Sciences",
    "Sociology": "College of Arts and Sciences",
}


def _collapse_ws(text: str) -> str:
    """Collapse runs of whitespace and strip."""
    return re.sub(r"\s+", " ", text).strip()


def _slugify(name_part: str) -> str:
    """Lowercase + ASCII fold + non-alnum -> dash. Matches Bryant URL slugs."""
    norm = unicodedata.normalize("NFKD", name_part)
    norm = "".join(c for c in norm if not unicodedata.combining(c))
    norm = norm.lower()
    norm = re.sub(r"[^a-z0-9]+", "-", norm).strip("-")
    return norm


def split_name(full: str) -> tuple[str, str]:
    """Best-effort split of 'First [M.] Last' into (first, last).

    The catalog uses 'First [Middle] Last'. Common edge cases:
    - Two-word last names (Van Houtte, De La Rosa) → take last token only.
    - Initials in middle (Kwadwo N. Asare) → drop initials.
    """
    parts = [p for p in full.replace(",", " ").split() if p]
    if len(parts) == 1:
        return parts[0], parts[0]
    last = parts[-1]
    first = parts[0]
    return first, last


def parse_catalog(html: str) -> list[dict]:
    """Extract faculty from the catalog page.

    Returns a list of dicts: name (Last, First), display_name, title,
    department, education, status (emeritus|tenure_track|term).
    """
    soup = BeautifulSoup(html, "html.parser")
    out: list[dict] = []

    for h3 in soup.find_all(["h2", "h3"]):
        head_txt = h3.get_text(" ", strip=True)
        status = SECTION_HEADERS.get(head_txt)
        if not status:
            continue

        # The catalog wraps each faculty in a <div><p><b>Name</b>...</p></div>.
        # Walk forward until we hit another section header.
        for sib in h3.find_next_siblings():
            if sib.name in {"h2", "h3"}:
                break
            for p in sib.find_all("p"):
                bold = p.find("b") or p.find("strong")
                if not bold:
                    continue
                display_name = _collapse_ws(bold.get_text(" "))
                if not display_name:
                    continue

                # Full <p> text, normalized. Pattern:
                #   "<Name>, <Title>, <Department>, <Education...>"
                # Title may itself contain commas (e.g. "Associate Professor
                # of Practice, Department of"). We anchor on a known
                # department name to find the boundary deterministically.
                full = _collapse_ws(p.get_text(" "))

                # Strip name prefix.
                if full.startswith(display_name + ","):
                    rest = full[len(display_name) + 1:].strip()
                elif full.startswith(display_name):
                    rest = full[len(display_name):].lstrip(", ").strip()
                else:
                    rest = full

                # Find department by scanning for a known department name.
                department = ""
                title = ""
                education = ""
                dept_idx = -1
                for dept in KNOWN_DEPARTMENTS:
                    pat = re.compile(rf",\s*{re.escape(dept)}\s*,", re.I)
                    m = pat.search(rest)
                    if m:
                        dept_idx = m.start()
                        department = dept
                        title = rest[:dept_idx].strip().rstrip(",").strip()
                        education = rest[m.end():].strip()
                        break

                if dept_idx == -1:
                    # Fallback: degree-anchored split for entries whose
                    # department isn't in our whitelist (rare).
                    segments = [s.strip() for s in rest.split(",")]
                    degree_re = re.compile(
                        r"^(B\.?[A-Z]\.?|M\.?[A-Z]\.?|Ph\.?D\.?|J\.?D\.?|"
                        r"LL\.?[MB]\.?|M\.?B\.?A\.?|M\.?D\.?|Ed\.?D\.?|"
                        r"D\.?[A-Z]\.?|Bachelor|Master|Doctor|Doctorate)",
                        re.I,
                    )
                    edu_start = None
                    for i, seg in enumerate(segments):
                        if degree_re.match(seg):
                            edu_start = i
                            break
                    if edu_start is not None and edu_start >= 2:
                        title = segments[0]
                        department = ", ".join(segments[1:edu_start])
                        education = ", ".join(segments[edu_start:])
                    elif edu_start is not None and edu_start == 1:
                        title = segments[0]
                        education = ", ".join(segments[1:])
                    elif segments:
                        title = segments[0]
                        if len(segments) >= 2:
                            department = segments[1]
                        if len(segments) >= 3:
                            education = ", ".join(segments[2:])

                first, last = split_name(display_name)
                name_lf = f"{last}, {first}"

                out.append({
                    "name": name_lf,
                    "display_name": display_name,
                    "title": title,
                    "department": department,
                    "college": DEPT_TO_COLLEGE.get(department, ""),
                    "education": education,
                    "status": status,
                    "email": None,
                    "phone": None,
                    "office": None,
                    "profile_url": None,
                    "expertise": [],
                })

    return out


def enrich_from_profile(rec: dict, session: requests.Session) -> bool:
    """Try the marketing-site profile page; fill email/profile_url/expertise.

    Returns True if a profile was found, False otherwise. Faculty without a
    profile page (most Emeritus, many Term lecturers) silently get skipped.
    """
    first, last = split_name(rec["display_name"])
    slug = f"{_slugify(last)}-{_slugify(first)}"
    url = f"{PROFILE_BASE}{slug}"

    try:
        resp = session.get(url, headers=HEADERS, timeout=TIMEOUT,
                           allow_redirects=True)
    except requests.RequestException:
        return False

    if resp.status_code != 200 or "page-not-found" in resp.url:
        return False

    soup = BeautifulSoup(resp.text, "html.parser")

    # Heuristic: real faculty profiles have <title>Last, First | Bryant
    # University</title> and an <a href="mailto:...@bryant.edu">.
    title_tag = soup.title.get_text(strip=True) if soup.title else ""
    if "Bryant University" not in title_tag:
        return False

    rec["profile_url"] = url

    # Email
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("mailto:") and "@bryant.edu" in href:
            email = href[len("mailto:"):].strip()
            if "graduateprograms" in email or "admission" in email:
                continue
            rec["email"] = email
            break

    # Pull main content text and look for label-driven sections.
    main = soup.find("main") or soup
    text = main.get_text("\n", strip=True)
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Expertise heuristic: collect lines under Research/Teaching Interests
    # until we hit the next section header.
    expertise: list[str] = []
    section_headers = {
        "Research Interests", "Teaching Interests", "Areas of Expertise",
        "Expertise", "Specializations",
    }
    stop_headers = {
        "Publications", "Presentations", "Education", "Awards", "Grants",
        "Professional Affiliations", "Professional Memberships", "Service",
        "Courses Taught", "Recent Publications", "Selected Publications",
        "Editorial Boards", "Industry Experience", "Find Your Path",
    }
    in_section = False
    for line in lines:
        if line in section_headers:
            in_section = True
            continue
        if in_section:
            if line in stop_headers or len(line) > 200:
                in_section = False
                continue
            # Skip duplicates and very short noise
            if line and line not in expertise and len(line) < 120:
                expertise.append(line)
            if len(expertise) >= 8:
                break
    if expertise:
        rec["expertise"] = expertise

    # Phone heuristic: 401-xxx-xxxx
    m = re.search(r"\b(401[-.\s]?\d{3}[-.\s]?\d{4})\b", text)
    if m:
        rec["phone"] = m.group(1)

    # Office heuristic: lines like "Suite XXX" or "Hall XXX"
    for line in lines:
        if re.search(r"\b(Hall|Suite|Building|Room|Center)\b\s*\d+",
                     line) and len(line) < 80:
            rec["office"] = line
            break

    # College: the profile page nav lists all three schools, so a substring
    # match is unreliable. Trust DEPT_TO_COLLEGE that was set during catalog
    # parse. As a tiebreaker, look for breadcrumb-style links scoping the
    # profile to a specific college URL.
    for href_col, name in (
        ("/college-business", "College of Business"),
        ("/college-arts-and-sciences", "College of Arts and Sciences"),
        ("/school-health-and-behavioral-sciences",
         "School of Health and Behavioral Sciences"),
    ):
        # Only count it if the href appears in the breadcrumb area, not the
        # global nav. Heuristic: breadcrumb appears after the <main> open.
        m = re.search(
            rf'<nav[^>]*breadcrumb[^>]*>.*?{re.escape(href_col)}',
            text + resp.text, re.S | re.I,
        )
        if m:
            rec["college"] = name
            break

    return True


def fetch_text(url: str, session: requests.Session) -> str:
    resp = session.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text


def main() -> int:
    out_path = DATA_DIR / "bryant_faculty.json"
    raw_catalog = RAW_DIR / "catalog_faculty.html"

    session = requests.Session()

    # 1. Catalog page (cache to raw/ for reproducibility)
    print(f"[1/3] GET {CATALOG_URL}")
    try:
        html = fetch_text(CATALOG_URL, session)
        raw_catalog.write_text(html, encoding="utf-8")
    except requests.RequestException as exc:
        if raw_catalog.exists():
            print(f"  network failed ({exc}); using cached {raw_catalog.name}")
            html = raw_catalog.read_text(encoding="utf-8")
        else:
            print(f"  fatal: cannot reach catalog and no cache: {exc}")
            return 1

    faculty = parse_catalog(html)
    print(f"  parsed {len(faculty)} faculty from catalog")

    # 2. Enrich from marketing-site profile pages.
    print(f"[2/3] enriching from {PROFILE_BASE}<slug> "
          f"({len(faculty)} attempts, {SLEEP}s sleep)")
    enriched = 0
    for i, rec in enumerate(faculty, 1):
        # Skip emeritus — the marketing site rarely keeps profiles for them.
        if rec["status"] == "emeritus":
            continue
        try:
            if enrich_from_profile(rec, session):
                enriched += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  warn: {rec['name']}: {exc}")
        time.sleep(SLEEP)
        if i % 25 == 0:
            print(f"    progress {i}/{len(faculty)}, "
                  f"profiles found: {enriched}")
    print(f"  enriched {enriched}/{len(faculty)} with profile data")

    # 3. Cross-reference with professor_ratings.json
    print("[3/3] cross-referencing with data/professor_ratings.json")
    rmp_path = DATA_DIR / "professor_ratings.json"
    matched = 0
    matched_names: list[str] = []
    if rmp_path.exists():
        rmp = json.loads(rmp_path.read_text(encoding="utf-8"))
        rmp_keys = set(rmp.keys()) if isinstance(rmp, dict) else set()
        # Match strategy: exact "Last, First" first; then case-insensitive;
        # then last-name + first-initial fallback.
        rmp_lower = {k.lower(): k for k in rmp_keys}
        rmp_lastinit = {}
        for k in rmp_keys:
            if "," in k:
                last_part, first_part = [s.strip() for s in k.split(",", 1)]
                if first_part:
                    rmp_lastinit.setdefault(
                        f"{last_part.lower()},{first_part[0].lower()}", k
                    )

        for rec in faculty:
            key = rec["name"]
            if key in rmp_keys:
                rec["rmp_key"] = key
                matched += 1
                matched_names.append(key)
                continue
            kl = key.lower()
            if kl in rmp_lower:
                rec["rmp_key"] = rmp_lower[kl]
                matched += 1
                matched_names.append(rmp_lower[kl])
                continue
            if "," in key:
                last_part, first_part = [s.strip()
                                         for s in key.split(",", 1)]
                if first_part:
                    li = f"{last_part.lower()},{first_part[0].lower()}"
                    if li in rmp_lastinit:
                        rec["rmp_key"] = rmp_lastinit[li]
                        matched += 1
                        matched_names.append(rmp_lastinit[li])
        print(f"  RMP keys: {len(rmp_keys)}; matched to faculty: {matched}")
    else:
        print("  professor_ratings.json missing, skipping cross-reference")
        rmp_keys = set()

    payload = {
        "source": CATALOG_URL,
        "secondary_source": PROFILE_BASE,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "faculty_count": len(faculty),
        "enriched_count": enriched,
        "rmp_match_count": matched,
        "rmp_total_keys": len(rmp_keys),
        "limitation": (
            "Bryant's /undergraduate/academics/faculty Drupal view paginates "
            "via AJAX; the views/ajax endpoint rejects unauthenticated POSTs. "
            "Catalog page used as the canonical roster instead — it is "
            "comprehensive but lacks photos, emails, expertise. Marketing-"
            "site profile pages enrich a subset where slug guesses succeed."
        ),
        "faculty": faculty,
    }
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Summary report
    by_status: dict[str, int] = {}
    by_college: dict[str, int] = {}
    by_dept: dict[str, int] = {}
    for r in faculty:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        col = r["college"] or "(unknown)"
        by_college[col] = by_college.get(col, 0) + 1
        d = r["department"] or "(unknown)"
        by_dept[d] = by_dept.get(d, 0) + 1

    print()
    print(f"  wrote {out_path.relative_to(ROOT)}")
    print(f"  total faculty: {len(faculty)}")
    print(f"  by status: {by_status}")
    print(f"  by college:")
    for col, n in sorted(by_college.items(), key=lambda x: -x[1]):
        print(f"    {n:3d}  {col}")
    print(f"  enriched with email/profile: {enriched}")
    print(f"  matched to RMP: {matched}/{len(rmp_keys)} RMP keys")
    if faculty:
        sample = next(
            (r for r in faculty if r.get("email")),
            faculty[0],
        )
        print()
        print("  sample record:")
        print(json.dumps(sample, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
