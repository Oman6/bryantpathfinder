"""Build a unified Bryant master catalog from the 4 scrape outputs.

Inputs (in data/):
  - sections_history.json   — every Banner section across the last 10 terms
  - courses_catalog.json    — canonical CourseLeaf course descriptions + prereqs
  - bryant_programs.json    — 87 programs (majors / minors / concentrations)
  - bryant_faculty.json     — 162 faculty with title / department / email
  - professor_ratings.json  — RMP data already in repo (optional)

Output (in data/):
  - bryant_master_catalog.json
  - bryant_master_catalog.report.txt

Cross-references built:
  - Each course gets:
      * historical_offerings: [(term, section_count), ...]  (last 10 terms)
      * total_sections: int
      * unique_instructors: [name, ...]
      * programs_requiring_it: [program_id, ...]
  - Each program gets:
      * required_course_codes: parsed from requirements text
  - Each faculty gets:
      * courses_taught: [course_code, ...]  (distinct, last 10 terms)
      * rmp: {quality, difficulty, num_ratings, would_take_again}  (if matched)
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

COURSE_CODE_RE = re.compile(r"\b([A-Z]{2,5})\s*-?\s*(\d{3,4}[A-Z]?)\b")


def _load(name: str) -> dict | list:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def normalize_code(subject: str, number: str) -> str:
    return f"{subject} {number}".strip()


def parse_course_codes(text: str) -> set[str]:
    if not text:
        return set()
    out: set[str] = set()
    for m in COURSE_CODE_RE.finditer(text):
        out.add(f"{m.group(1)} {m.group(2)}")
    return out


def main() -> int:
    sections_history = _load("sections_history.json")
    courses_catalog = _load("courses_catalog.json")
    programs_data = _load("bryant_programs.json")
    faculty_data = _load("bryant_faculty.json")
    try:
        ratings = _load("professor_ratings.json")
    except FileNotFoundError:
        ratings = {}

    # ---- Build course → offerings index ----
    course_offerings: dict[str, list[tuple[str, int]]] = defaultdict(list)
    course_instructors: dict[str, set[str]] = defaultdict(set)
    instructor_courses: dict[str, set[str]] = defaultdict(set)
    seen_course_in_term: dict[str, set[str]] = defaultdict(set)

    for term in sections_history.get("terms", []):
        term_desc = term.get("description") or term.get("code")
        per_term_count: dict[str, int] = defaultdict(int)
        for sec in term.get("sections", []):
            code = sec.get("course_code")
            if not code:
                continue
            per_term_count[code] += 1
            instr = sec.get("instructor")
            if instr:
                course_instructors[code].add(instr)
                instructor_courses[instr].add(code)
            seen_course_in_term[code].add(term_desc)
        for code, n in per_term_count.items():
            course_offerings[code].append((term_desc, n))

    # ---- Build program → required course codes index ----
    program_courses: dict[str, set[str]] = {}
    course_in_programs: dict[str, set[str]] = defaultdict(set)
    program_buckets = ("programs", "minors", "concentrations")
    for bucket in program_buckets:
        for prog in programs_data.get(bucket, []) or []:
            pid = prog.get("id") or prog.get("label")
            req_text = " \n ".join(prog.get("requirements") or [])
            codes = parse_course_codes(req_text)
            program_courses[pid] = codes
            for code in codes:
                course_in_programs[code].add(pid)

    # ---- Build courses with cross-references ----
    enriched_courses: list[dict] = []
    catalog_codes: set[str] = set()
    for c in courses_catalog.get("courses", []):
        code = c.get("course_code")
        if not code:
            continue
        catalog_codes.add(code)
        offerings = course_offerings.get(code, [])
        offerings_sorted = sorted(offerings, key=lambda x: x[0], reverse=True)
        enriched_courses.append({
            **{k: v for k, v in c.items() if k != "_metadata"},
            "historical_offerings": [{"term": t, "section_count": n} for t, n in offerings_sorted],
            "total_sections": sum(n for _, n in offerings),
            "terms_offered": len(seen_course_in_term.get(code, [])),
            "unique_instructors": sorted(course_instructors.get(code, [])),
            "programs_requiring_it": sorted(course_in_programs.get(code, [])),
        })

    # Add ghost courses that appear in Banner but not in the active catalog (dropped or graduate-only)
    banner_only = sorted(set(course_offerings.keys()) - catalog_codes)
    for code in banner_only:
        m = re.match(r"^([A-Z]+)\s+(\S+)$", code)
        if not m:
            continue
        offerings = course_offerings[code]
        enriched_courses.append({
            "course_code": code,
            "subject": m.group(1),
            "course_number": m.group(2),
            "title": "",
            "credits": None,
            "description": "",
            "prerequisites": "",
            "corequisites": "",
            "attributes": "",
            "when_offered": "",
            "cross_listed": "",
            "in_active_catalog": False,
            "historical_offerings": [{"term": t, "section_count": n} for t, n in sorted(offerings, reverse=True)],
            "total_sections": sum(n for _, n in offerings),
            "terms_offered": len(seen_course_in_term.get(code, [])),
            "unique_instructors": sorted(course_instructors.get(code, [])),
            "programs_requiring_it": sorted(course_in_programs.get(code, [])),
        })

    enriched_courses.sort(key=lambda x: x["course_code"])

    # ---- Build programs with parsed required course codes ----
    enriched_programs: list[dict] = []
    for bucket in program_buckets:
        for prog in programs_data.get(bucket, []) or []:
            pid = prog.get("id") or prog.get("label")
            enriched_programs.append({
                **prog,
                "type_bucket": bucket,
                "required_course_codes": sorted(program_courses.get(pid, [])),
            })

    # ---- Build faculty with courses-taught + RMP ----
    enriched_faculty: list[dict] = []
    matched_rmp = 0
    for fac in faculty_data.get("faculty", []) or []:
        name = fac.get("name") or fac.get("display_name")
        rmp = ratings.get(name)
        if rmp:
            matched_rmp += 1
        enriched_faculty.append({
            **fac,
            "courses_taught": sorted(instructor_courses.get(name, [])),
            "rmp": rmp,
        })

    # ---- Master document ----
    master = {
        "_metadata": {
            "version": "1",
            "generated_at": datetime.now().isoformat(),
            "sources": {
                "sections_history": sections_history.get("_metadata") or "10-term Banner SSB sweep",
                "courses_catalog": courses_catalog.get("source"),
                "programs": programs_data.get("source"),
                "faculty": faculty_data.get("source"),
            },
        },
        "stats": {
            "courses_total": len(enriched_courses),
            "courses_in_active_catalog": sum(1 for c in enriched_courses if c.get("in_active_catalog")),
            "courses_banner_only": len(banner_only),
            "programs_total": len(enriched_programs),
            "majors": sum(1 for p in enriched_programs if p["type_bucket"] == "programs"),
            "minors": sum(1 for p in enriched_programs if p["type_bucket"] == "minors"),
            "concentrations": sum(1 for p in enriched_programs if p["type_bucket"] == "concentrations"),
            "faculty_total": len(enriched_faculty),
            "faculty_matched_to_rmp": matched_rmp,
            "sections_indexed": sum(t.get("section_count", 0) for t in sections_history.get("terms", [])),
            "terms_indexed": len(sections_history.get("terms", [])),
            "unique_instructors_in_sections": len(instructor_courses),
        },
        "courses": enriched_courses,
        "programs": enriched_programs,
        "faculty": enriched_faculty,
    }

    out_path = DATA_DIR / "bryant_master_catalog.json"
    out_path.write_text(json.dumps(master, indent=2), encoding="utf-8")

    # Compact frontend variant — just stats + course summaries (no descriptions)
    compact = {
        "_metadata": master["_metadata"],
        "stats": master["stats"],
        "courses": [
            {
                "course_code": c["course_code"],
                "title": c.get("title", ""),
                "credits": c.get("credits"),
                "subject": c.get("subject"),
                "in_active_catalog": c.get("in_active_catalog", True),
                "total_sections": c["total_sections"],
                "terms_offered": c["terms_offered"],
                "when_offered": c.get("when_offered", ""),
                "programs_requiring_it": c["programs_requiring_it"],
            }
            for c in enriched_courses
        ],
        "programs": [
            {
                "id": p.get("id"),
                "label": p.get("label"),
                "type_bucket": p["type_bucket"],
                "college": p.get("college"),
                "department": p.get("department"),
                "required_course_codes": p["required_course_codes"],
            }
            for p in enriched_programs
        ],
    }
    compact_path = DATA_DIR / "bryant_master_catalog.compact.json"
    compact_path.write_text(json.dumps(compact, indent=2), encoding="utf-8")

    # Report
    s = master["stats"]
    report = (
        f"Bryant master catalog built {master['_metadata']['generated_at']}\n"
        f"  courses (total / active catalog / banner-only): {s['courses_total']} / {s['courses_in_active_catalog']} / {s['courses_banner_only']}\n"
        f"  programs: {s['programs_total']} ({s['majors']} majors, {s['minors']} minors, {s['concentrations']} concentrations)\n"
        f"  faculty: {s['faculty_total']} ({s['faculty_matched_to_rmp']} matched to RMP)\n"
        f"  sections indexed across {s['terms_indexed']} terms: {s['sections_indexed']}\n"
        f"  unique instructors in sections data: {s['unique_instructors_in_sections']}\n"
        f"  outputs: {out_path.name}, {compact_path.name}\n"
    )
    (DATA_DIR / "bryant_master_catalog.report.txt").write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
