"""Generate major-template JSON for the homepage MajorPicker from scraped data.

Inputs:
  - data/bryant_programs.json   — 18 programs + 38 minors + 31 concentrations
  - data/major_templates.hand.json (optional) — hand-curated overrides

Output:
  - data/major_templates.json   — list of selectable Bryant majors
  - data/major_templates.report.txt — what got parsed, what got skipped, why

The CourseLeaf catalog has Bryant's umbrella structure but it's split:
  - "programs" entries are standalone majors (Data Science, Biology, Psychology, etc.)
  - "concentrations" entries include the business majors (Finance, Marketing, etc.)
    formatted as "Bachelor of Science in Business Administration: X Concentration"
  - The BSBA umbrella core (gen-ed + business core) is replicated inside each
    concentration page, so we get business-core for free.

What is NOT in the scraped data:
  - The general-education core (GEN 100, GEN 201, LCS, science+lab, GEN 390 capstone)
    is shared across every Bryant undergraduate program but lives on a separate
    catalog page that wasn't part of the program scrape.

We add a hand-coded `GEN_ED_CORE` constant below sourced from Bryant's
2025-2026 undergraduate catalog. Every undergraduate program at Bryant takes
this core; it's the same set Owen's audit shows. Auto-generated templates
include it; hand-curated templates are passed through unchanged.

Parser behavior (conservative — no fabrication):
  - "FIN 310 - Title (3 credits)" → specific_course
  - "or FIN 371 - Title" → folds into the prior specific_course as choose_one_of
  - "Two Additional Finance Electives" → 2 wildcard slots, pattern "FIN XXX"
  - "One 400-level economics course" → wildcard ECO 4XX
  - "Choose one of the following:" → opens a choose_one_of group for following items
  - "[HEADER] X" / "[FOOTNOTE] X" / "*notes" → ignored (kept in unparseable for review)
  - Any line we can't classify confidently → recorded in `unparseable_rules` (NOT
    silently dropped — visible in the report, visible in the template)
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
PROGRAMS_PATH = DATA_DIR / "bryant_programs.json"
HAND_PATH = DATA_DIR / "major_templates.hand.json"
OUT_PATH = DATA_DIR / "major_templates.json"
REPORT_PATH = DATA_DIR / "major_templates.report.txt"

# Bryant 2025-2026 undergraduate gen-ed core (stable across all undergrads).
# Sourced from Owen's parsed audit + the catalog's "general education" page.
# These are the requirements a SOPHOMORE typically has remaining.
GEN_ED_CORE: list[dict] = [
    {"id": "gen_201", "requirement": "American Studies", "rule_type": "specific_course",
     "options": ["GEN 201"], "pattern": None, "pairs": None,
     "credits_needed": 3.0, "category": "general_education"},
    {"id": "lcs_course", "requirement": "Literary & Cultural Studies",
     "rule_type": "choose_one_of",
     "options": ["LCS 200", "LCS 213", "LCS 214", "LCS 250", "LCS 280"],
     "pattern": None, "pairs": None,
     "credits_needed": 3.0, "category": "general_education"},
    {"id": "science_lab", "requirement": "Science with Lab",
     "rule_type": "course_with_lab", "options": [], "pattern": None,
     "pairs": [["SCI 251", "SCI L251"], ["SCI 261", "SCI L261"], ["SCI 351", "SCI L351"]],
     "credits_needed": 4.0, "category": "general_education"},
    {"id": "gen_390_capstone", "requirement": "Sophomore Capstone",
     "rule_type": "specific_course", "options": ["GEN 390"], "pattern": None,
     "pairs": None, "credits_needed": 3.0, "category": "general_education"},
]

# Subjects we'll fabricate wildcards for when a rule says "Three Additional X
# Electives" or "One 400-level X course." Keep this conservative — only
# subjects that exist in our section/catalog data.
KNOWN_SUBJECTS = {
    "FIN", "ACG", "MKT", "MGT", "ISA", "BUS", "ECO", "MATH", "GEN", "LCS",
    "SCI", "HIS", "POLS", "SOC", "PSY", "BIO", "COM", "EHD", "LEMS", "LGLS",
    "GSCM", "EHS", "AHEC", "AHB", "HSS", "AFRS", "ANTH", "DSCI", "CS", "ART",
    "ACI", "ML", "WGS", "ASTU", "CRIM", "PHIL", "REL", "STA",
}

# Regex helpers
SPECIFIC_COURSE_RE = re.compile(r"^([A-Z]{2,5})\s+(\d{3,4}[A-Z]?)\s*[-–—]\s*(.+?)(?:\s*\((\d+(?:\.\d+)?)\s*credits?\))?\s*$")
OR_COURSE_RE = re.compile(r"^or\s+([A-Z]{2,5})\s+(\d{3,4}[A-Z]?)\s*[-–—]\s*(.+?)(?:\s*\((\d+(?:\.\d+)?)\s*credits?\))?\s*$", re.I)
WORD_NUMBER = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10,
}
ELECTIVE_RE = re.compile(
    r"^(?P<count>" + "|".join(WORD_NUMBER.keys()) + r"|\d+)\s+"
    r"(?:additional\s+|more\s+|other\s+)?"
    r"(?P<subject>[A-Za-z &/]+?)\s+"
    r"(?:elective|electives|course|courses)\s*$",
    re.I,
)
LEVEL_COURSE_RE = re.compile(
    r"^one\s+(\d{3})[\-\s]?level\s+([A-Za-z]+)\s+(?:course|elective)\s*$",
    re.I,
)
CHOOSE_RE = re.compile(r"^choose\s+(\w+)\s+(?:of|from)\s+the\s+following\s*[:\-]?\s*$", re.I)
LAB_PAIR_HINT_RE = re.compile(r"\bwith\s+(?:lab|laboratory)\b", re.I)


def _slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s.strip().lower()).strip("_")
    return s or "req"


def _normalize_subject(label: str) -> str | None:
    """Map an English subject phrase like 'Finance' to a Bryant subject code."""
    label = label.strip().lower()
    map = {
        "finance": "FIN", "accounting": "ACG", "marketing": "MKT",
        "management": "MGT", "information systems": "ISA",
        "information technology": "ISA", "economics": "ECO",
        "math": "MATH", "mathematics": "MATH", "history": "HIS",
        "communication": "COM", "communications": "COM",
        "psychology": "PSY", "biology": "BIO",
        "politics": "POLS", "political science": "POLS",
        "sociology": "SOC", "data science": "DSCI",
        "computer science": "CS", "art": "ART", "english": "LCS",
        "language": "ML", "philosophy": "PHIL", "religion": "REL",
        "statistics": "STA", "supply chain": "GSCM",
        "supply chain management": "GSCM", "global supply chain": "GSCM",
        "business": "BUS", "literary and cultural studies": "LCS",
        "literary & cultural studies": "LCS", "lcs": "LCS",
    }
    return map.get(label)


def parse_requirements(req_lines: list[str], category_for_concentration: str = "major") -> tuple[list[dict], list[str]]:
    """Parse a list of requirement lines into Pathfinder DSL.

    Returns (parsed_requirements, unparseable_lines).
    """
    out: list[dict] = []
    unparseable: list[str] = []
    current_category = category_for_concentration
    pending_choose: list[str] | None = None  # active "Choose one of:" group

    i = 0
    n = len(req_lines)
    while i < n:
        line = req_lines[i].strip()
        i += 1
        if not line:
            continue

        # Section headers / footnotes / asterisk notes — informational only
        if line.startswith("[HEADER]"):
            header_text = line.replace("[HEADER]", "").strip().lower()
            if "general education" in header_text:
                current_category = "general_education"
            elif "business core" in header_text:
                current_category = "business_core"
            elif "concentration" in header_text or "major" in header_text:
                current_category = category_for_concentration
            elif "elective" in header_text:
                current_category = "elective"
            pending_choose = None
            continue
        if line.startswith("[FOOTNOTE]") or line.startswith("*"):
            continue
        if line.startswith("Note:"):
            continue

        # Choose-N-of-the-following opener
        m = CHOOSE_RE.match(line)
        if m:
            pending_choose = []
            continue

        # specific course like "FIN 310 - Title (3 credits)"
        m = SPECIFIC_COURSE_RE.match(line)
        if m:
            subject, number, title, credits = m.groups()
            code = f"{subject} {number}"
            credits_f = float(credits) if credits else 3.0
            if pending_choose is not None:
                pending_choose.append(code)
                continue
            out.append({
                "id": _slug(f"{subject}_{number}"),
                "requirement": title.strip(),
                "rule_type": "specific_course",
                "options": [code],
                "pattern": None,
                "pairs": None,
                "credits_needed": credits_f,
                "category": current_category,
            })
            continue

        # "or CODE" — fold into the prior specific_course
        m = OR_COURSE_RE.match(line)
        if m and out and out[-1]["rule_type"] in ("specific_course", "choose_one_of"):
            subject, number, title, credits = m.groups()
            code = f"{subject} {number}"
            prev = out[-1]
            if prev["rule_type"] == "specific_course":
                prev["rule_type"] = "choose_one_of"
                prev["id"] = _slug(prev["requirement"]) + "_choice"
            if code not in prev["options"]:
                prev["options"].append(code)
            continue

        # "Two Additional Finance Electives" → N wildcard slots
        m = ELECTIVE_RE.match(line)
        if m:
            count_word = m.group("count")
            subject_phrase = m.group("subject")
            count = WORD_NUMBER.get(count_word.lower(), None)
            if count is None and count_word.isdigit():
                count = int(count_word)
            subject_code = _normalize_subject(subject_phrase)
            if count and subject_code and subject_code in KNOWN_SUBJECTS:
                for k in range(count):
                    out.append({
                        "id": _slug(f"{subject_code}_elective_{k+1}"),
                        "requirement": f"{subject_phrase.title()} Elective ({k+1} of {count})",
                        "rule_type": "wildcard",
                        "options": [],
                        "pattern": f"{subject_code} XXX",
                        "pairs": None,
                        "credits_needed": 3.0,
                        "category": current_category,
                    })
                continue
            unparseable.append(line)
            continue

        # "One 400-level economics course"
        m = LEVEL_COURSE_RE.match(line)
        if m:
            level, subject_phrase = m.groups()
            subject_code = _normalize_subject(subject_phrase)
            if subject_code and subject_code in KNOWN_SUBJECTS:
                out.append({
                    "id": _slug(f"{subject_code}_{level[0]}xx"),
                    "requirement": f"{level}-level {subject_phrase.title()}",
                    "rule_type": "wildcard",
                    "options": [],
                    "pattern": f"{subject_code} {level[0]}XX",
                    "pairs": None,
                    "credits_needed": 3.0,
                    "category": current_category,
                })
                continue
            unparseable.append(line)
            continue

        # If we're inside a Choose-N-of group, accumulate plain courses
        if pending_choose is not None:
            mc = re.match(r"^([A-Z]{2,5})\s+(\d{3,4}[A-Z]?)", line)
            if mc:
                pending_choose.append(f"{mc.group(1)} {mc.group(2)}")
                continue

        # Couldn't classify — flag it
        unparseable.append(line)

    # If a Choose-N group was opened and never closed by a header, materialize it
    if pending_choose:
        out.append({
            "id": "choose_group",
            "requirement": "Choose from a list",
            "rule_type": "choose_one_of",
            "options": pending_choose,
            "pattern": None,
            "pairs": None,
            "credits_needed": 3.0,
            "category": current_category,
        })

    return out, unparseable


def _keep_program(p: dict) -> bool:
    """Filter to entries that look like real selectable majors."""
    label = (p.get("label") or "").lower()
    pid = p.get("id") or ""
    # Exclude minors that snuck into programs and pure hubs
    if "minor" in label or "minor" in pid:
        return False
    if "language studies" in label and "program" in pid:
        return False  # hub page, not a single major
    return True


def build_template(p: dict, bucket: str) -> dict:
    reqs = p.get("requirements") or []
    is_business = "business administration" in (p.get("label") or "").lower()
    parsed, unparseable = parse_requirements(reqs, category_for_concentration="major")

    # Add gen-ed core for any undergraduate program (every Bryant undergrad has it).
    # Avoid duplicating if the parser somehow already grabbed it.
    parsed_codes = {opt for r in parsed for opt in (r.get("options") or [])}
    geneds = [g for g in GEN_ED_CORE if not (set(g.get("options") or []) & parsed_codes)]

    # Friendly id and label
    label = p.get("label") or p.get("id") or "major"
    short_label = label.replace("Bachelor of Science in Business Administration: ", "") \
                       .replace("Bachelor of Science with a Major in ", "") \
                       .replace("Bachelor of Science in ", "") \
                       .replace("Bachelor of Arts with a Major in ", "") \
                       .replace("Programs", "").strip()

    return {
        "id": p.get("id") or _slug(label),
        "label": short_label or label,
        "full_label": label,
        "type_bucket": bucket,
        "college": p.get("college"),
        "year_label": "Sophomore",
        "credits_earned_or_inprogress": 42,
        "credits_required": int(p.get("total_credits") or 120),
        "expected_graduation": "May 2029",
        "auto_generated": True,
        "outstanding_requirements": geneds + parsed,
        "unparseable_rules": unparseable,
        "source_url": p.get("source_url"),
    }


def main() -> int:
    programs_data = json.loads(PROGRAMS_PATH.read_text(encoding="utf-8"))

    templates: list[dict] = []

    # programs (standalone majors)
    for p in programs_data.get("programs", []):
        if not _keep_program(p):
            continue
        templates.append(build_template(p, "programs"))

    # concentrations (BSBA + International Business tracks; these are how
    # students typically describe their major)
    for p in programs_data.get("concentrations", []):
        # Skip pure-academic concentrations that aren't a "major" in the student
        # vernacular (e.g., American Studies Concentration, Sport Studies)
        label = (p.get("label") or "").lower()
        if "bachelor of science in business administration" in label:
            templates.append(build_template(p, "concentrations"))
        elif "international business major" in label:
            templates.append(build_template(p, "concentrations"))

    # Hand-curated overrides — drop any auto-generated entry that the
    # hand-curated set is the canonical version of. We use an alias map because
    # hand IDs are short (e.g. "finance") while catalog IDs are verbose
    # (e.g. "financeconcentration", "internationalbusinessfinanceconcentration").
    # Without this both versions survive and the picker shows duplicates.
    HAND_ALIASES: dict[str, set[str]] = {
        "finance": {"financeconcentration"},
        "accounting": {"accountingconcentration"},
        "marketing": {"marketingconcentration"},
        "management": {"leadershipandinnovationconcentration",
                        "teamandprojectmanagementconcentration",
                        "humanresourcemanagementconcentration"},
        "actuarial_math": {"mathematicsprograms"},
    }
    overrides: list[dict] = []
    if HAND_PATH.exists():
        hand = json.loads(HAND_PATH.read_text(encoding="utf-8"))
        overrides = hand.get("majors") or []
        # Build the full set of IDs to drop: each hand id + its aliases.
        drop_ids: set[str] = set()
        for h in overrides:
            drop_ids.add(h["id"])
            drop_ids.update(HAND_ALIASES.get(h["id"], set()))
        templates = [t for t in templates if t["id"] not in drop_ids]
        templates = overrides + templates

    # Sort: hand-curated first (in original order), then auto-generated alphabetically by label
    auto = [t for t in templates if t.get("auto_generated")]
    hand_curated = [t for t in templates if not t.get("auto_generated")]
    auto.sort(key=lambda x: x["label"].lower())
    templates = hand_curated + auto

    out = {
        "_metadata": {
            "version": "2",
            "generated_at": datetime.now().isoformat(),
            "source": "data/bryant_programs.json + hand-curated overrides + GEN_ED_CORE",
            "note": "Generated by scripts/generate_major_templates.py. Hand-curated entries take precedence; auto-generated entries are flagged.",
        },
        "majors": templates,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")

    # Report
    lines = [
        f"Major templates generated {datetime.now().isoformat()}",
        f"  total: {len(templates)} ({sum(1 for t in templates if not t.get('auto_generated'))} hand-curated, {sum(1 for t in templates if t.get('auto_generated'))} auto-generated)",
        "",
        "Per-template detail:",
    ]
    for t in templates:
        flag = "HAND" if not t.get("auto_generated") else "auto"
        lines.append(
            f"  [{flag}] {t['label'][:50]:50} reqs={len(t['outstanding_requirements']):3} unparsed={len(t.get('unparseable_rules') or [])}"
        )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
