# Feature 03 — Requirement Expansion

> Turning "what the student needs" into "which sections could satisfy it."

---

## Summary

The requirement expander is the bridge between Degree Works and the constraint solver. It takes a single `OutstandingRequirement` object and the full 291-section Bryant Fall 2026 catalog, then returns the subset of sections that could satisfy that requirement.

The code lives at `backend/app/requirement_expander.py`. It is roughly 155 lines of pure Python with no external dependencies beyond the Pydantic models defined in `backend/app/models.py`.

---

## What It Does

The expander handles all four rule types defined in ADR 0004:

| Rule type | Input | Output | Example |
|---|---|---|---|
| `specific_course` | `options: ["FIN 310"]` | All sections of FIN 310 | 3 sections (A, B, C) |
| `choose_one_of` | `options: ["FIN 370", "FIN 380", ...]` | Union of sections for all listed courses | 9 sections across 3 courses |
| `wildcard` | `pattern: "FIN 4XX"` | All sections matching the pattern | 8 sections across 7 course codes |
| `course_with_lab` | `pairs: [["SCI 251", "SCI L251"], ...]` | Tuples of (lecture, lab) section pairs | 12 valid (lecture, lab) combinations |

After matching, the expander applies two default filters:

- **FULL sections** are excluded (seats_open == 0). Override with `include_full=True`.
- **Async sections** are excluded (is_async == True). Override with `include_async=True`.

---

## Entry Point

```python
def expand_requirement(
    requirement: OutstandingRequirement,
    all_sections: list[Section],
    *,
    include_full: bool = False,
    include_async: bool = False,
) -> list[Section] | list[tuple[Section, Section]]:
```

The function dispatches on `requirement.rule_type`. For `specific_course`, `choose_one_of`, and `wildcard`, it returns a flat `list[Section]`. For `course_with_lab`, it returns a `list[tuple[Section, Section]]` where each tuple is a (lecture, lab) pair.

---

## How It Fits Into the Pipeline

```
DegreeAudit.outstanding_requirements
        │
        ▼
  expand_requirement()  ← this module
        │
        ▼
  filter_candidates_by_preferences()  (solver.py)
        │
        ▼
  itertools.product(...)  (solver.py)
        │
        ▼
  conflict check → score → top 3 schedules
```

The solver calls `expand_requirement()` once per selected requirement, then applies its own preference-based filters on top of the expander's output. The expander handles catalog-level filtering (FULL, async); the solver handles preference-level filtering (blocked days, time windows).

---

## Key Design Decisions

1. **Expansion happens at request time, not ingestion time.** The rule types and options are parsed once into `audit_owen.json`, but the actual section matching runs fresh on every `/api/generate-schedules` call. This means the expander always works against the current state of `sections.json`. If seat counts change (a section fills up), the next expansion reflects that.

2. **No prerequisite checking.** The expander does not verify that the student has completed prerequisites for a course. This is safe because Degree Works already handles prerequisite gating — a course only appears in `outstanding_requirements` if the student is eligible to take it. FIN 310 requires FIN 201, but Owen's audit only lists FIN 310 as outstanding because Degree Works already confirmed FIN 201 is in progress.

3. **The wildcard expander is O(n).** For each wildcard rule, the expander walks all 291 sections. With Owen's audit containing two wildcard rules (`FIN 4XX` and `FIN XXX`), that is roughly 582 comparisons per request — negligible at this catalog size.

4. **Filters are conservative by default.** FULL sections and async sections are excluded unless the caller explicitly opts in. This keeps the candidate pools honest — every returned section is one the student can actually register for today.

5. **The return type varies by rule type.** Most rules return `list[Section]`, but `course_with_lab` returns `list[tuple[Section, Section]]`. The solver handles this fork at the call site (lines 270-295 of `solver.py`). This is a pragmatic choice — a uniform return type would require wrapping single sections in tuples, adding complexity for the 75% of requirements that are not lab courses.

---

## Documentation Structure

| File | Framework | Question |
|------|-----------|----------|
| `1-align.md` | Align | Why does this module exist? |
| `2-construct.md` | Construct | What does the interface look like? |
| `3-execute.md` | Execute | How does it work with real data? |

---

## References

- `backend/app/requirement_expander.py` — the implementation
- `backend/app/models.py` — `OutstandingRequirement` and `Section` models
- `docs/adr/0004-requirement-rule-dsl.md` — the rule type design decision
- `data/fixtures/audit_owen.json` — Owen's parsed audit with all four rule types
- `data/sections.json` — the 291-section Fall 2026 catalog
