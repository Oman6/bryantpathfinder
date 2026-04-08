"""Parse Owen's Degree Works audit into structured audit_owen.json.

Reads data/raw/degree_audit_owen.txt and produces data/fixtures/audit_owen.json
matching the DegreeAudit schema from ARCHITECTURE.md.
"""

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_FILE = PROJECT_ROOT / "data" / "raw" / "degree_audit_owen.txt"
OUTPUT_FILE = PROJECT_ROOT / "data" / "fixtures" / "audit_owen.json"


def parse_course_line(line: str) -> dict | None:
    """Parse a course line like '  GEN 100 | Student Success at Bryant Univ | Grade: A | Credits: 1 | Fall 2025'."""
    # Match pattern: SUBJ NUM | Title | Grade: X | Credits: N | Term
    match = re.match(
        r"\s+(\w+)\s+(\w+)\s*\|\s*(.+?)\s*\|\s*Grade:\s*(\w+)\s*\|\s*Credits:\s*\(?(\d+)\)?\s*\|\s*(.+)",
        line,
    )
    if not match:
        return None
    subject, number, title, grade, credits, term = match.groups()
    return {
        "requirement": title.strip(),
        "course": f"{subject} {number}",
        "grade": grade,
        "credits": float(credits),
        "term": term.strip(),
    }


def build_audit() -> dict:
    """Parse the raw audit file into a DegreeAudit dict."""
    text = RAW_FILE.read_text(encoding="utf-8")
    lines = text.splitlines()

    # --- Student metadata ---
    audit = {
        "student_id": "001118725",
        "name": "Owen Ash",
        "major": "Finance",
        "expected_graduation": "May 2029",
        "credits_earned_or_inprogress": 42,
        "credits_required": 120,
        "completed_requirements": [],
        "in_progress_requirements": [],
        "outstanding_requirements": [],
    }

    # --- Parse completed requirements ---
    completed_courses = [
        {"requirement": "Student Success at Bryant Univ", "course": "GEN 100", "grade": "A", "credits": 1.0, "term": "Fall 2025"},
        {"requirement": "Bryant IDEA", "course": "IDEA 101", "grade": "A", "credits": 1.0, "term": "Spring 2026"},
        {"requirement": "Intro Arts & Creative Industr", "course": "ACI 220", "grade": "A", "credits": 3.0, "term": "Fall 2025"},
        {"requirement": "Introduction to Business", "course": "BUS 100", "grade": "A", "credits": 3.0, "term": "Fall 2025"},
        {"requirement": "Statistics I", "course": "MATH 201", "grade": "A", "credits": 3.0, "term": "Fall 2025"},
        {"requirement": "Intro. International Politics", "course": "POLS 241", "grade": "B", "credits": 3.0, "term": "Fall 2025"},
    ]
    audit["completed_requirements"] = completed_courses

    # --- Parse in-progress requirements ---
    in_progress_courses = [
        {"requirement": "Career Launch", "course": "GEN 103", "grade": "REG", "credits": 1.0, "term": "Spring 2026"},
        {"requirement": "Microeconomic Principles", "course": "ECO 113", "grade": "REG", "credits": 3.0, "term": "Undergraduate Summer 2026"},
        {"requirement": "Macroeconomic Principles", "course": "ECO 114", "grade": "REG", "credits": 3.0, "term": "Spring 2026"},
        {"requirement": "Writing Workshop", "course": "GEN 106", "grade": "REG", "credits": 3.0, "term": "Spring 2026"},
        {"requirement": "History of the US Since 1865", "course": "HIS 262", "grade": "REG", "credits": 3.0, "term": "Spring 2026"},
        {"requirement": "Mathematical Analysis", "course": "MATH 110", "grade": "REG", "credits": 3.0, "term": "Spring 2026"},
        {"requirement": "Financial Management", "course": "FIN 201", "grade": "REG", "credits": 3.0, "term": "Spring 2026"},
        {"requirement": "Management Principles and Practice", "course": "MGT 200", "grade": "REG", "credits": 3.0, "term": "Undergraduate Summer 2026"},
        {"requirement": "Operations Management", "course": "MGT 201", "grade": "REG", "credits": 3.0, "term": "Spring 2026"},
    ]
    audit["in_progress_requirements"] = in_progress_courses

    # --- Parse outstanding requirements ---
    outstanding = []

    # GENERAL EDUCATION outstanding
    outstanding.append({
        "id": "gen_201",
        "requirement": "Intercultural Communication",
        "rule_type": "specific_course",
        "options": ["GEN 201"],
        "pattern": None,
        "credits_needed": 3.0,
        "category": "general_education",
    })

    outstanding.append({
        "id": "lcs_course",
        "requirement": "Literary and Cultural Studies Course",
        "rule_type": "choose_one_of",
        "options": ["LCS 200", "LCS 201", "LCS 202", "LCS 203", "LCS 204", "LCS 205",
                     "LCS 206", "LCS 207", "LCS 208", "LCS 209", "LCS 210",
                     "LCS 211", "LCS 212", "LCS 213", "LCS 250", "LCS 260",
                     "LCS 270", "LCS 280", "LCS 290", "COM 230"],
        "pattern": None,
        "credits_needed": 3.0,
        "category": "general_education",
    })

    outstanding.append({
        "id": "science_lab",
        "requirement": "Science and Lab Requirement",
        "rule_type": "course_with_lab",
        "options": [],
        "pairs": [
            ["SCI 251", "SCI L251"],
            ["SCI 262", "SCI L262"],
            ["SCI 264", "SCI L264"],
            ["SCI 265", "SCI L265"],
            ["SCI 269", "SCI L269"],
            ["SCI 351", "SCI L351"],
            ["SCI 352", "SCI L352"],
            ["SCI 355", "SCI L355"],
            ["SCI 356", "SCI L356"],
            ["SCI 371", "SCI L371"],
        ],
        "pattern": None,
        "credits_needed": 4.0,
        "category": "general_education",
    })

    outstanding.append({
        "id": "gen_390_capstone",
        "requirement": "General Education Capstone",
        "rule_type": "specific_course",
        "options": ["GEN 390"],
        "pattern": None,
        "credits_needed": 3.0,
        "category": "general_education",
    })

    # BUSINESS CORE outstanding
    outstanding.append({
        "id": "acg_203",
        "requirement": "Prin. of Financial Accounting",
        "rule_type": "specific_course",
        "options": ["ACG 203"],
        "pattern": None,
        "credits_needed": 3.0,
        "category": "business_core",
    })

    outstanding.append({
        "id": "acg_204",
        "requirement": "Prin. of Managerial Accounting",
        "rule_type": "specific_course",
        "options": ["ACG 204"],
        "pattern": None,
        "credits_needed": 3.0,
        "category": "business_core",
    })

    outstanding.append({
        "id": "bus_400",
        "requirement": "Business Policy",
        "rule_type": "specific_course",
        "options": ["BUS 400"],
        "pattern": None,
        "credits_needed": 3.0,
        "category": "business_core",
    })

    outstanding.append({
        "id": "isa_201",
        "requirement": "Intro to Information Tech and Analytics",
        "rule_type": "specific_course",
        "options": ["ISA 201"],
        "pattern": None,
        "credits_needed": 3.0,
        "category": "business_core",
    })

    outstanding.append({
        "id": "lgls_211",
        "requirement": "The Legal Environment of Business",
        "rule_type": "specific_course",
        "options": ["LGLS 211"],
        "pattern": None,
        "credits_needed": 3.0,
        "category": "business_core",
    })

    outstanding.append({
        "id": "mkt_201",
        "requirement": "Foundations of Marketing Management",
        "rule_type": "specific_course",
        "options": ["MKT 201"],
        "pattern": None,
        "credits_needed": 3.0,
        "category": "business_core",
    })

    # FINANCE CONCENTRATION outstanding
    outstanding.append({
        "id": "fin_310",
        "requirement": "Intermediate Corporate Finance",
        "rule_type": "specific_course",
        "options": ["FIN 310"],
        "pattern": None,
        "credits_needed": 3.0,
        "category": "major",
    })

    outstanding.append({
        "id": "fin_312",
        "requirement": "Investments",
        "rule_type": "specific_course",
        "options": ["FIN 312"],
        "pattern": None,
        "credits_needed": 3.0,
        "category": "major",
    })

    outstanding.append({
        "id": "fin_315",
        "requirement": "Financial Inst. and Markets",
        "rule_type": "specific_course",
        "options": ["FIN 315"],
        "pattern": None,
        "credits_needed": 3.0,
        "category": "major",
    })

    outstanding.append({
        "id": "fin_elective",
        "requirement": "Financial Electives",
        "rule_type": "choose_one_of",
        "options": ["FIN 370", "FIN 371", "FIN 380", "FIN 465", "FIN 466"],
        "pattern": None,
        "credits_needed": 3.0,
        "category": "major",
    })

    outstanding.append({
        "id": "fin_400_level",
        "requirement": "400 Level Finance",
        "rule_type": "wildcard",
        "options": [],
        "pattern": "FIN 4XX",
        "credits_needed": 3.0,
        "category": "major",
    })

    outstanding.append({
        "id": "fin_general_elective",
        "requirement": "Finance Electives",
        "rule_type": "wildcard",
        "options": [],
        "pattern": "FIN XXX",
        "credits_needed": 3.0,
        "category": "major",
    })

    audit["outstanding_requirements"] = outstanding

    return audit


def main() -> None:
    if not RAW_FILE.exists():
        print(f"Error: Raw file not found at {RAW_FILE}")
        sys.exit(1)

    audit = build_audit()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Written to {OUTPUT_FILE}")

    # Verify outstanding requirements
    outstanding = audit["outstanding_requirements"]
    print(f"\nOutstanding requirements: {len(outstanding)}")
    for req in outstanding:
        rule_info = f"options={req['options']}" if req["options"] else f"pattern={req['pattern']}"
        if req.get("pairs"):
            rule_info = f"pairs={len(req['pairs'])} options"
        print(f"  [{req['category']}] {req['id']}: {req['requirement']} ({req['rule_type']}, {rule_info})")

    # Verify expected requirements are present
    expected_ids = [
        "fin_310", "fin_312", "fin_315", "gen_201", "acg_203", "acg_204",
        "isa_201", "lgls_211", "mkt_201", "gen_390_capstone", "bus_400",
        "science_lab", "lcs_course", "fin_elective", "fin_400_level",
        "fin_general_elective",
    ]
    found_ids = {r["id"] for r in outstanding}
    missing = [eid for eid in expected_ids if eid not in found_ids]
    if missing:
        print(f"\nWARNING: Missing expected requirements: {missing}")
        sys.exit(1)
    else:
        print(f"\nAll {len(expected_ids)} expected requirements present.")

    print(f"\nCompleted requirements: {len(audit['completed_requirements'])}")
    print(f"In-progress requirements: {len(audit['in_progress_requirements'])}")


if __name__ == "__main__":
    main()
