"""Fetch Bryant University academic programs (majors, minors, concentrations).

Bryant publishes its undergraduate catalog on a CourseLeaf-powered site at
``catalog.bryant.edu``. Each program lives at a clean URL such as
``/undergraduate/collegeofbusiness/financedepartment/financeconcentration/``
and follows a predictable structure:

* ``<h1 class="page-title">`` -> program label
* ``<div id="textcontainer">`` -> program body
  * One or more ``<p>`` tags -> narrative description
  * ``<table class="sc_courselist">`` rows ->
    * ``tr.areaheader`` -> section header ("Finance Concentration")
    * ``tr.orclass``    -> alternative course ("or FIN 371 ...")
    * ``tr`` with ``td.codecol`` -> required course
    * ``span.courselistcomment`` -> free-text rule ("Two Additional Finance Electives")
  * ``dl.sc_footnotes`` -> footnote constraints

We capture every requirement line verbatim. We do NOT translate them into the
Pathfinder requirement DSL here -- that's a downstream job. The shape is:

    {
      "id": "finance_concentration",
      "label": "Finance Concentration",
      "degree_type": "Concentration",
      "college": "College of Business",
      "department": "Finance Department",
      "total_credits": 120,
      "description": "...",
      "requirements": [
        "[HEADER] Finance Concentration",
        "FIN 310 - Intermediate Corporate Finance (3 credits)",
        ...
      ],
      "concentrations": [],
      "source_url": "https://catalog.bryant.edu/.../financeconcentration/"
    }

Usage:
    python -m scripts.fetch_bryant_programs
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag

USER_AGENT = "BryantPathfinder/1.0 (research; oash@bryant.edu)"
BASE = "https://catalog.bryant.edu"
SLEEP_SECONDS = 0.3
TIMEOUT_SECONDS = 30

logger = logging.getLogger("fetch_bryant_programs")

# Hardcoded seed list of program URLs, derived from a manual exploration of the
# 2025-2026 undergraduate catalog. Re-running discovery on every fetch is
# unnecessary churn -- the catalog rev's once a year. Add or remove URLs here
# when the catalog changes.
#
# Format: (path, kind) where kind is one of: "major", "minor", "concentration"
# Concentrations under a parent BSBA are tagged "concentration" so the writer
# can group them.
PROGRAMS: list[tuple[str, str]] = [
    # ---- College of Business: BSBA concentrations ----
    ("/undergraduate/collegeofbusiness/accountingdepartment/accountingconcentration/", "concentration"),
    ("/undergraduate/collegeofbusiness/accountingdepartment/managerialaccountingandfinanceconcentration/", "concentration"),
    ("/undergraduate/collegeofbusiness/financedepartment/financeconcentration/", "concentration"),
    ("/undergraduate/collegeofbusiness/financedepartment/financialservicesconcentration/", "concentration"),
    ("/undergraduate/collegeofbusiness/globalsupplychainmanagementprogram/globalsupplychainmanagementconcentration/", "concentration"),
    ("/undergraduate/collegeofbusiness/managementdepartment/healthcaremanagementandstrategy/", "concentration"),
    ("/undergraduate/collegeofbusiness/managementdepartment/humanresourcemanagementconcentration/", "concentration"),
    ("/undergraduate/collegeofbusiness/managementdepartment/leadershipandinnovationconcentration/", "concentration"),
    ("/undergraduate/collegeofbusiness/managementdepartment/teamandprojectmanagementconcentration/", "concentration"),
    ("/undergraduate/collegeofbusiness/informationsystemsandanalyticsdepartment/infosysandanalyticsconcentration/", "concentration"),
    ("/undergraduate/collegeofbusiness/marketingdepartment/marketingconcentration/", "concentration"),
    # ---- College of Business: standalone majors ----
    ("/undergraduate/collegeofbusiness/datascienceprogram/", "major"),
    ("/undergraduate/collegeofbusiness/entrepreneurshipprogram/entrepreneurshipdegree/", "major"),
    # ---- College of Business: International Business concentrations ----
    ("/undergraduate/collegeofbusiness/internationalbusinessprogram/internationalbusinessaccountingconcentration/", "concentration"),
    ("/undergraduate/collegeofbusiness/internationalbusinessprogram/internationalbusinessdigitalmarketingconcentration/", "concentration"),
    ("/undergraduate/collegeofbusiness/internationalbusinessprogram/internationalbusinessfinanceconcentration/", "concentration"),
    ("/undergraduate/collegeofbusiness/internationalbusinessprogram/internationalbusinessglobalsupplychainmanagementconcentration/", "concentration"),
    ("/undergraduate/collegeofbusiness/internationalbusinessprogram/internationalbusinesshumanresourcemanagementconcentration/", "concentration"),
    ("/undergraduate/collegeofbusiness/internationalbusinessprogram/internationalbusinessinformationsystemsconcentration/", "concentration"),
    ("/undergraduate/collegeofbusiness/internationalbusinessprogram/internationalbusinessleadershipandinnovationconcentration/", "concentration"),
    ("/undergraduate/collegeofbusiness/internationalbusinessprogram/internationalbusinessmarketingconcentration/", "concentration"),
    ("/undergraduate/collegeofbusiness/internationalbusinessprogram/internationalbusinessteamandprojectmanagementconcentration/", "concentration"),
    # ---- College of Business: minors ----
    ("/undergraduate/collegeofbusiness/entrepreneurshipprogram/entrepreneurshipminor/", "minor"),
    ("/undergraduate/collegeofbusiness/financedepartment/financeminor/", "minor"),
    ("/undergraduate/collegeofbusiness/globalsupplychainmanagementprogram/globalsupplychainmanagementminor/", "minor"),
    ("/undergraduate/collegeofbusiness/internationalbusinessprogram/internationalbusinessminor/", "minor"),
    ("/undergraduate/collegeofbusiness/managementdepartment/healthcaremanagementandstrategyminorhealthcaremanagementandstrategy/", "minor"),
    ("/undergraduate/collegeofbusiness/managementdepartment/humanresourcemanagementminor/", "minor"),
    ("/undergraduate/collegeofbusiness/managementdepartment/managementminor/", "minor"),
    ("/undergraduate/collegeofbusiness/managementdepartment/teamandprojectmanagementminor/", "minor"),
    ("/undergraduate/collegeofbusiness/marketingdepartment/marketinganalyticsminor/", "minor"),
    ("/undergraduate/collegeofbusiness/marketingdepartment/marketingminor/", "minor"),
    ("/undergraduate/collegeofbusiness/marketingdepartment/salesminor/", "minor"),
    # ---- College of Arts and Sciences: majors ----
    ("/undergraduate/collegeofartsandsciences/departmentofcommunicationandlanguagestudies/communicationprograms/", "major"),
    ("/undergraduate/collegeofartsandsciences/departmentofcommunicationandlanguagestudies/digitalcommunicationprogram/", "major"),
    ("/undergraduate/collegeofartsandsciences/departmentofcommunicationandlanguagestudies/sportsindustriescommunicationandpromotion/", "major"),
    ("/undergraduate/collegeofartsandsciences/departmentofcommunicationandlanguagestudies/languagestudiesprograms/", "major"),
    ("/undergraduate/collegeofartsandsciences/historyliteratureandtheartsdepartment/artsandcreativeindustries/", "major"),
    ("/undergraduate/collegeofartsandsciences/historyliteratureandtheartsdepartment/historyprograms/", "major"),
    ("/undergraduate/collegeofartsandsciences/historyliteratureandtheartsdepartment/literaryandculturalstudiesprograms/", "major"),
    ("/undergraduate/collegeofartsandsciences/departmentofmathematicsandeconomics/economicsprograms/", "major"),
    ("/undergraduate/collegeofartsandsciences/departmentofmathematicsandeconomics/mathematicsprograms/", "major"),
    ("/undergraduate/collegeofartsandsciences/departmentofpoliticslawandsociety/politicsandlawprograms/", "major"),
    ("/undergraduate/collegeofartsandsciences/departmentofpoliticslawandsociety/sociology/", "major"),
    # ---- College of Arts and Sciences: minors ----
    ("/undergraduate/collegeofartsandsciences/departmentofmathematicsandeconomics/appliedstatisticsminor/", "minor"),
    ("/undergraduate/collegeofartsandsciences/departmentofcommunicationandlanguagestudies/languagestudiesminor/", "minor"),
    ("/undergraduate/collegeofartsandsciences/departmentofcommunicationandlanguagestudies/spanishforhealthsciencesminor/", "minor"),
    ("/undergraduate/collegeofartsandsciences/departmentofmathematicsandeconomics/mathematicsminor/", "minor"),
    ("/undergraduate/collegeofartsandsciences/departmentofpoliticslawandsociety/politicsandlawprograms/legalstudiesminor/", "minor"),
    ("/undergraduate/collegeofartsandsciences/departmentofpoliticslawandsociety/politicsandlawprograms/politicalscienceminor/", "minor"),
    ("/undergraduate/collegeofartsandsciences/departmentofpoliticslawandsociety/globalstudiesminor/", "minor"),
    ("/undergraduate/collegeofartsandsciences/historyliteratureandtheartsdepartment/literaryandculturalstudiesminor/", "minor"),
    ("/undergraduate/collegeofartsandsciences/historyliteratureandtheartsdepartment/literatureminor/", "minor"),
    ("/undergraduate/collegeofartsandsciences/historyliteratureandtheartsdepartment/mediaandculturalstudiesminor/", "minor"),
    # ---- School of Health and Behavioral Sciences: majors ----
    ("/undergraduate/schoolofhealthandbehavioralsciences/departmentofbiologicalandbiomedicalsciences/bsbiology/", "major"),
    ("/undergraduate/schoolofhealthandbehavioralsciences/departmentofbiologicalandbiomedicalsciences/bsexerciseandmovementscience/", "major"),
    ("/undergraduate/schoolofhealthandbehavioralsciences/healthsciencesprogram/healthscience_major/", "major"),
    ("/undergraduate/schoolofhealthandbehavioralsciences/healthcareinformaticsmajor/", "major"),
    ("/undergraduate/schoolofhealthandbehavioralsciences/departmentofpsychology/bspsychology/", "major"),
    # ---- School of Health and Behavioral Sciences: concentrations ----
    ("/undergraduate/schoolofhealthandbehavioralsciences/departmentofbiologicalandbiomedicalsciences/biologyconcentration/", "concentration"),
    ("/undergraduate/schoolofhealthandbehavioralsciences/departmentofbiologicalandbiomedicalsciences/envsciconcentration/", "concentration"),
    ("/undergraduate/schoolofhealthandbehavioralsciences/departmentofbiologicalandbiomedicalsciences/healthandwellnessconcentration/", "concentration"),
    ("/undergraduate/schoolofhealthandbehavioralsciences/departmentofbiologicalandbiomedicalsciences/strenghtandconditioningconcentration/", "concentration"),
    ("/undergraduate/schoolofhealthandbehavioralsciences/departmentofbiologicalandbiomedicalsciences/sustainabilityandclimateactionconcentration/", "concentration"),
    ("/undergraduate/schoolofhealthandbehavioralsciences/departmentofpsychology/psychology_concentration/", "concentration"),
    # ---- School of Health and Behavioral Sciences: minors ----
    ("/undergraduate/schoolofhealthandbehavioralsciences/departmentofbiologicalandbiomedicalsciences/biologyminor/", "minor"),
    ("/undergraduate/schoolofhealthandbehavioralsciences/departmentofbiologicalandbiomedicalsciences/biotechnologyminor/", "minor"),
    ("/undergraduate/schoolofhealthandbehavioralsciences/departmentofbiologicalandbiomedicalsciences/chemistryminor/", "minor"),
    ("/undergraduate/schoolofhealthandbehavioralsciences/departmentofbiologicalandbiomedicalsciences/environmentalscienceminor/", "minor"),
    ("/undergraduate/schoolofhealthandbehavioralsciences/departmentofbiologicalandbiomedicalsciences/forensicscienceminor/", "minor"),
    ("/undergraduate/schoolofhealthandbehavioralsciences/departmentofbiologicalandbiomedicalsciences/healthandwellnessminor/", "minor"),
    ("/undergraduate/schoolofhealthandbehavioralsciences/departmentofbiologicalandbiomedicalsciences/nutritionminor/", "minor"),
    ("/undergraduate/schoolofhealthandbehavioralsciences/departmentofbiologicalandbiomedicalsciences/strengthandconditioningminor/", "minor"),
    ("/undergraduate/schoolofhealthandbehavioralsciences/departmentofbiologicalandbiomedicalsciences/sustainabilityandclimateactionminor/", "minor"),
    ("/undergraduate/schoolofhealthandbehavioralsciences/departmentofpsychology/psychology_minor/", "minor"),
    # ---- Interdisciplinary concentrations ----
    ("/undergraduate/interdisciplinaryconcentrations/americanstudiesconcentration/", "concentration"),
    ("/undergraduate/interdisciplinaryconcentrations/appliedanalyticsconcentration/", "concentration"),
    ("/undergraduate/interdisciplinaryconcentrations/ethnicstudiesconcentration/", "concentration"),
    ("/undergraduate/interdisciplinaryconcentrations/sportsstudiesconcentration/", "concentration"),
    ("/undergraduate/interdisciplinaryconcentrations/womengendersexualstudiesconcentration/", "concentration"),
    # ---- Interdisciplinary minors ----
    ("/undergraduate/interdisciplinaryminors/africanablackstudiesminor/", "minor"),
    ("/undergraduate/interdisciplinaryminors/appliedartificialintelligenceminor/", "minor"),
    ("/undergraduate/interdisciplinaryminors/businessadministrationminor/", "minor"),
    ("/undergraduate/interdisciplinaryminors/environmentalstudiesminor/", "minor"),
    ("/undergraduate/interdisciplinaryminors/latinamericanlatinalatinostudiesminor/", "minor"),
    ("/undergraduate/interdisciplinaryminors/professionalcreativewritingminor/", "minor"),
    ("/undergraduate/interdisciplinaryminors/womengendersexualitystudiesminor/", "minor"),
]


def slugify(path: str) -> str:
    """Convert a catalog URL path into a stable program id slug."""
    leaf = path.rstrip("/").rsplit("/", 1)[-1]
    return re.sub(r"[^a-z0-9_]+", "_", leaf.lower()).strip("_")


def infer_college(path: str) -> str:
    """Map a catalog path to the owning college / school."""
    if "/collegeofbusiness/" in path:
        return "College of Business"
    if "/collegeofartsandsciences/" in path:
        return "College of Arts and Sciences"
    if "/schoolofhealthandbehavioralsciences/" in path:
        return "School of Health and Behavioral Sciences"
    if "/interdisciplinary" in path:
        return "Interdisciplinary"
    return "Unknown"


def infer_department(path: str) -> str | None:
    """Pull the department segment from a deeply nested catalog path."""
    parts = [p for p in path.split("/") if p]
    # Path looks like: undergraduate/<college>/<department>/<program>/
    if len(parts) >= 4:
        dept_slug = parts[2]
        # Pretty-print: insert spaces between camelCase-ish runs
        pretty = re.sub(r"(department|program|programs|major|minor)$", r" \1", dept_slug, flags=re.IGNORECASE)
        return pretty.replace("of", " of ").replace("and", " and ").title().strip()
    return None


def infer_degree_type(label: str, kind: str) -> str:
    """Return BS / BA / Minor / Concentration based on title and seed kind."""
    low = label.lower()
    if kind == "minor":
        return "Minor"
    if kind == "concentration":
        return "Concentration"
    # majors: distinguish BS vs BA
    if "bachelor of arts" in low or low.startswith("ba "):
        return "BA"
    if "bachelor of science" in low or low.startswith("bs "):
        return "BS"
    return "BS"  # majority of Bryant programs are BS


def fetch_html(session: requests.Session, url: str) -> str | None:
    """GET a catalog page; return the HTML body or None on failure.

    Retries once on transient failure with a short backoff. The catalog is
    served by a single Apache origin and occasionally drops connections.
    """
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            resp = session.get(url, timeout=TIMEOUT_SECONDS)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            last_exc = exc
            time.sleep(1.0)
    logger.warning("fetch.failed url=%s error=%s", url, last_exc)
    return None


def extract_description(container: Tag) -> str:
    """Pull the first 1-2 narrative paragraphs from the textcontainer.

    Many catalog pages start with a few <p> or <div> blocks before the first
    course list table. We grab those, skipping section headers and links to
    general education / minor requirement boilerplate.
    """
    paragraphs: list[str] = []
    for child in container.children:
        if not isinstance(child, Tag):
            continue
        if child.name == "table" and "sc_courselist" in (child.get("class") or []):
            break
        if child.name in {"p", "div"}:
            text = _clean(child.get_text(" ", strip=True))
            if not text or len(text) < 40:
                continue
            if "General Education Requirements" in text and len(text) < 80:
                continue
            if "University Minor Requirements" in text and len(text) < 80:
                continue
            paragraphs.append(text)
            if len(paragraphs) >= 2:
                break
    return "\n\n".join(paragraphs)


def _clean(text: str) -> str:
    """Normalize whitespace, including the non-breaking spaces CourseLeaf emits."""
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def parse_course_row(row: Tag) -> str | None:
    """Convert one <tr> from sc_courselist into a verbatim requirement line.

    Branches on the row class:
    - areaheader     -> "[HEADER] <text>"
    - orclass        -> "or <code> - <title>"
    - comment-only   -> "<text>"  (free-text rule like 'Two Additional Finance Electives')
    - normal course  -> "<code> - <title> (<n> credits)"
    """
    classes = row.get("class") or []

    # Header row: <span class="courselistcomment areaheader">
    if "areaheader" in classes:
        header_text = _clean(row.get_text(" ", strip=True))
        return f"[HEADER] {header_text}" if header_text else None

    code_cell = row.find("td", class_="codecol")
    title_cell = None
    hours_cell = row.find("td", class_="hourscol")

    # The title cell is the first td after codecol that is NOT codecol/hourscol.
    if code_cell is not None:
        for td in row.find_all("td"):
            if td is code_cell or "hourscol" in (td.get("class") or []) or "codecol" in (td.get("class") or []):
                continue
            title_cell = td
            break

    if "orclass" in classes and code_cell is not None:
        code = _clean(code_cell.get_text(" ", strip=True)).removeprefix("or").strip()
        title = _clean(title_cell.get_text(" ", strip=True)) if title_cell else ""
        return f"or {code} - {title}".strip(" -")

    if code_cell is not None:
        code = _clean(code_cell.get_text(" ", strip=True))
        title = _clean(title_cell.get_text(" ", strip=True)) if title_cell else ""
        hours = _clean(hours_cell.get_text(" ", strip=True)) if hours_cell else ""
        line = f"{code} - {title}".strip(" -")
        if hours:
            line = f"{line} ({hours} credits)"
        return line

    # Comment-only row (free-text rule, e.g. "Two Additional Finance Electives")
    comment = row.find("span", class_="courselistcomment")
    if comment is not None:
        return _clean(comment.get_text(" ", strip=True)) or None

    text = _clean(row.get_text(" ", strip=True))
    return text or None


def extract_requirements(container: Tag) -> list[str]:
    """Walk every sc_courselist on the page and emit verbatim rule lines.

    Multiple tables can appear on a single page (e.g. the page lists both a
    major and its concentration). We emit them in document order with header
    rows preserved so the structure is recoverable downstream.
    """
    lines: list[str] = []
    for table in container.find_all("table", class_="sc_courselist"):
        for row in table.find_all("tr"):
            line = parse_course_row(row)
            if line:
                lines.append(line)
    # Footnotes can carry real constraints ("Must include one 400-level elective")
    for footnotes in container.find_all("dl", class_="sc_footnotes"):
        for dd in footnotes.find_all("dd"):
            text = _clean(dd.get_text(" ", strip=True))
            if text:
                lines.append(f"[FOOTNOTE] {text}")
    return lines


def extract_total_credits(container: Tag) -> int | None:
    """Pull the 'minimum NN credit hours' number from page prose if present."""
    text = container.get_text(" ", strip=True)
    # Prefer the 'graduation' total over 'concentration' total when both exist.
    for pattern in (
        r"minimum of (\d{2,3}) credit hours? is required for graduation",
        r"(\d{2,3}) credit hours? required for graduation",
        r"minimum of (\d{2,3}) credit hours? is required for the (?:major|minor|concentration)",
        r"minimum of (\d{2,3}) credit hours? is required",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def parse_program(html: str, path: str, kind: str) -> dict[str, Any] | None:
    """Convert one catalog page into a Pathfinder program record.

    Some catalog pages use tabbed content -- the narrative lives in
    ``#textcontainer`` but the actual course requirements live in a sibling
    ``#degreetextcontainer`` (or similarly suffixed) div with class
    ``tab_content``. We scan all tab containers so requirements aren't lost.
    """
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.find("h1", class_="page-title")
    text_container = soup.find("div", id="textcontainer")
    if title_el is None or text_container is None:
        logger.warning("parse.no_content path=%s", path)
        return None

    label = _clean(title_el.get_text(" ", strip=True))
    description = extract_description(text_container)

    # Collect requirement-bearing containers: the main #textcontainer plus any
    # tab panels (e.g. #degreetextcontainer, #majorrequirementstext).
    containers: list[Tag] = [text_container]
    for tab in soup.find_all("div", class_="tab_content"):
        if tab is text_container:
            continue
        containers.append(tab)

    requirements: list[str] = []
    for container in containers:
        requirements.extend(extract_requirements(container))

    # total_credits: prefer the requirements tab (where graduation totals live)
    total_credits: int | None = None
    for container in containers:
        total_credits = extract_total_credits(container)
        if total_credits is not None:
            break

    return {
        "id": slugify(path),
        "label": label,
        "degree_type": infer_degree_type(label, kind),
        "college": infer_college(path),
        "department": infer_department(path),
        "total_credits": total_credits,
        "description": description,
        "requirements": requirements,
        "concentrations": [],
        "source_url": BASE + path,
    }


def main() -> int:
    """Fetch every program in the seed list and write data/bryant_programs.json."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    out_path = Path(__file__).resolve().parents[2] / "data" / "bryant_programs.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    programs: list[dict[str, Any]] = []
    minors: list[dict[str, Any]] = []
    concentrations: list[dict[str, Any]] = []
    failed: list[str] = []

    for i, (path, kind) in enumerate(PROGRAMS):
        url = BASE + path
        logger.info("fetch (%d/%d) %s", i + 1, len(PROGRAMS), url)
        html = fetch_html(session, url)
        if html is None:
            failed.append(url)
            time.sleep(SLEEP_SECONDS)
            continue
        try:
            record = parse_program(html, path, kind)
        except Exception as exc:  # noqa: BLE001 -- best effort scrape
            logger.warning("parse.crash path=%s error=%s", path, exc)
            record = None
        if record is None:
            failed.append(url)
        elif kind == "minor":
            minors.append(record)
        elif kind == "concentration":
            concentrations.append(record)
        else:
            programs.append(record)
        time.sleep(SLEEP_SECONDS)

    # Group concentrations under their parent BSBA / IB / Biology majors. We
    # don't have separate "Bachelor of Science in Business Administration" pages
    # in the seed list, so we just emit a synthetic parent for each cluster.
    payload = {
        "source": "https://catalog.bryant.edu/undergraduate/",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "programs": programs,
        "minors": minors,
        "concentrations": concentrations,
        "failed_urls": failed,
        "stats": {
            "majors": len(programs),
            "minors": len(minors),
            "concentrations": len(concentrations),
            "failed": len(failed),
            "total_attempted": len(PROGRAMS),
        },
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info(
        "done majors=%d minors=%d concentrations=%d failed=%d -> %s",
        len(programs),
        len(minors),
        len(concentrations),
        len(failed),
        out_path,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
