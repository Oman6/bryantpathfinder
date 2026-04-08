# Feature 03 — Requirement Expansion: Align

> WHY does this module exist?

---

## The Problem

The constraint solver needs a pool of candidate sections for each outstanding requirement. It cannot work with the raw Degree Works DSL. When Degree Works says "1 Class in FIN 370 or 371 or 380 or 465 or 466," the solver has no idea what to do with that string. It needs a concrete list: here are the nine sections from the Fall 2026 catalog that would satisfy this requirement, with their CRNs, meeting times, instructors, and seat counts.

The gap between "what the student needs" and "what Bryant is offering this semester" is exactly what the requirement expander bridges.

---

## Why Not Just Use a Lookup Table?

The simplest approach would be a static mapping: requirement ID to list of CRNs. That would work for `specific_course` rules like FIN 310 (where the mapping is trivial), but it breaks for the other three rule types:

**`choose_one_of` rules change per student.** The `fin_elective` requirement in Owen's audit lists five courses: FIN 370, FIN 371, FIN 380, FIN 465, and FIN 466. But FIN 371 has zero sections in the Fall 2026 catalog — it is not being offered this term. A static lookup table would either include a course with no sections (useless) or require manual curation every semester (fragile). The expander handles this by filtering against the live catalog: it tries all five course codes and returns only the ones that actually have sections.

**`wildcard` rules are open-ended by definition.** The `fin_400_level` requirement says "any 400-level Finance course." Which specific courses that includes depends entirely on what Bryant is offering in Fall 2026. The expander walks the full catalog and discovers FIN 412, 414, 458, 460, 465, 466, and 475 — seven course codes across eight sections. A static table cannot know this without being regenerated every time the catalog changes.

**`course_with_lab` rules require pairing logic.** The `science_lab` requirement has ten valid (lecture, lab) pairs. Each pair produces a cross product of lecture sections and lab sections. SCI 251 has four lecture sections and three lab sections, yielding twelve possible combinations for that pair alone. The expander generates all valid combinations and filters out FULL or async sections from either side of the pair.

---

## What the Solver Expects

The solver's `solve()` function calls `expand_requirement()` once per selected requirement. It expects back either:

- A `list[Section]` — for `specific_course`, `choose_one_of`, and `wildcard` rules. The solver wraps each section in a single-element list and feeds them into `itertools.product` to generate combinations.
- A `list[tuple[Section, Section]]` — for `course_with_lab` rules. Each tuple is an atomic (lecture, lab) pair that the solver treats as a unit. Both sections must fit the schedule without conflicts.

The solver does not care about rule types after expansion. It operates on a uniform `list[list[Section]]` where each inner list represents one "slot" to fill — one section for normal requirements, two sections (lecture + lab) for lab requirements.

---

## Why Filter at Expansion Time?

The expander applies two filters before returning candidates:

1. **Exclude FULL sections.** A section with `seats_open == 0` cannot be registered for. Including it in the candidate pool wastes solver time evaluating combinations that the student cannot actually use. In the Fall 2026 catalog, one section is FULL: COM 230 Section A (CRN 1335, Falso-Capaldi). This section would otherwise match the `lcs_course` requirement (COM 230 is in the options list). The expander removes it, so the solver never considers it.

2. **Exclude async sections.** Bryant's Fall 2026 catalog has zero async sections in the 291-section subset, so this filter is currently a no-op. It exists because the Banner parser flags online sections with `is_async=True`, and a future catalog pull could include them. Async sections have no meeting times and cannot participate in conflict detection, so they need special handling that the current solver does not implement.

Both filters have override flags (`include_full`, `include_async`) for cases where the caller wants the full, unfiltered candidate set — useful for testing and for future features like waitlist-aware scheduling.

---

## The Combinatorial Impact

The expander's output directly determines the solver's search space. Tighter expansion means fewer candidates per requirement, which means fewer total combinations to evaluate. This matters because the solver uses `itertools.product` — the total combination count is the product of all pool sizes.

Consider Owen selecting five requirements for Fall 2026:

| Requirement | Rule type | Candidates after expansion |
|---|---|---|
| `fin_310` | specific_course | 3 sections |
| `gen_201` | specific_course | 12 sections |
| `acg_203` | specific_course | 13 sections |
| `isa_201` | specific_course | 9 sections |
| `mkt_201` | specific_course | 6 sections |

Total combinations: 3 x 12 x 13 x 9 x 6 = **25,272**. That is above the solver's 10,000-combination safety cap, so the solver will stop early and return the best schedules found so far. If Owen also selects `science_lab` (a `course_with_lab` rule), the candidate pool grows further.

The expander's job is to produce an honest, filtered candidate set — not to artificially shrink it. The solver's safety cap handles pathological cases. But by excluding FULL and async sections at expansion time, the expander removes candidates that could never lead to a valid registration, keeping the search space as tight as possible.

---

## Why Not Ask Claude to Expand?

This was considered and rejected (see ADR 0004, "Alternatives Considered"). Having Claude interpret the Degree Works DSL at runtime would add 2-4 seconds of latency and a non-trivial API cost to every schedule generation request. The expansion logic is purely mechanical — pattern matching and filtering — and deterministic Python does it in under a millisecond. Claude's strengths (language understanding, reasoning about ambiguity) are not needed here. The rule types are enumerable and the catalog is structured data.

The division of labor is clear: Claude parses the Degree Works audit screenshot into structured `OutstandingRequirement` objects (a language task). The expander resolves those objects into concrete section candidates (a data task). Each tool does what it is good at.

---

## Why Not Expand at Ingestion Time?

An alternative design would pre-compute the candidate sections when `audit_owen.json` is created, storing the matching CRNs directly in the fixture file. This was rejected because it couples the audit data to a specific snapshot of the catalog. If a section fills up between ingestion and request time, the pre-computed list would include a FULL section. By expanding at request time, the expander always reflects the current state of `sections.json`.

For the hackathon, the catalog is static (it does not change during the demo), so this distinction is academic. But the design is correct for a production scenario where seat counts update nightly via Banner Ethos.

---

## Summary

The requirement expander exists because the solver cannot work with raw Degree Works rules. It translates four rule types into concrete section lists, filters out sections the student cannot register for, and produces the candidate pools that drive the solver's combinatorial search. Without it, the solver would have no inputs. Without the solver, the expander's output would have no consumer. They are tightly coupled by design.

---

## References

- `backend/app/requirement_expander.py` — the implementation
- `backend/app/solver.py` — the consumer of expanded candidates
- `backend/app/models.py` — `OutstandingRequirement` and `Section` model definitions
- `docs/adr/0004-requirement-rule-dsl.md` — why four rule types, not a PEG grammar
- `data/fixtures/audit_owen.json` — the `OutstandingRequirement` objects this module processes
- `data/sections.json` — the 291-section catalog the expander matches against
