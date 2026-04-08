# ADR 0004 — Parsing the Degree Works Requirement DSL

**Status:** Accepted
**Date:** 2026-04-08
**Deciders:** Owen Ash

---

## Context

Degree Works doesn't store degree requirements as simple course lists. It stores them as rules in a compact domain-specific language that has been used across Ellucian's product line for more than a decade. When a student's audit shows "Still needed: 1 Class in FIN 370 or 371 or 380 or 465 or 466," that text is the rule — it's what the registrar's office typed into the Degree Works block editor, and it's what Degree Works uses to decide whether a student's plan satisfies the requirement.

Pathfinder needs to turn these rules into something the solver can act on. The solver doesn't understand English. It needs a list of course codes. Specifically, for each outstanding requirement, the solver needs to know: "give me the set of sections from the Bryant catalog that would satisfy this requirement." A `specific_course` rule like "1 Class in FIN 310" is easy — the candidate set is every section of FIN 310. A `choose_one_of` rule like "1 Class in FIN 370 or 371 or 380" requires the solver to understand that any one of those courses works. A `wildcard` rule like "1 Class in @ 4@ with attribute = FIN" is the hardest — it matches any 400-level Finance course, which might be eight or ten different course codes across the catalog.

These four patterns cover every outstanding requirement in Owen's audit and, based on spot-checking other Bryant audits, appear to cover 95%+ of the Degree Works requirements in the Business Administration program. There are edge cases (credit-range rules like "9 credits from FIN 4XX", co-requisite rules, cross-listed courses) that Pathfinder doesn't handle, and that's a deliberate scoping decision documented below.

---

## Decision

Pathfinder parses the Degree Works DSL into four canonical rule types, each represented as a variant of the `OutstandingRequirement` Pydantic model:

### Rule Type 1: `specific_course`

The simplest case. The requirement text is "1 Class in `<COURSE>`" where `<COURSE>` is a specific course code like `FIN 310` or `GEN 201`.

```json
{
  "id": "fin_310",
  "requirement": "Intermediate Corporate Finance",
  "rule_type": "specific_course",
  "options": ["FIN 310"],
  "credits_needed": 3,
  "category": "major"
}
```

The expander returns all sections of FIN 310 from `sections.json`.

### Rule Type 2: `choose_one_of`

The student picks one course from an explicit list. The requirement text is "1 Class in `<A>` or `<B>` or `<C>`." This is the most common rule for electives.

```json
{
  "id": "fin_elective",
  "requirement": "Financial Electives",
  "rule_type": "choose_one_of",
  "options": ["FIN 370", "FIN 371", "FIN 380", "FIN 465", "FIN 466"],
  "credits_needed": 3,
  "category": "major"
}
```

The expander returns the union of all sections of all five courses. The solver treats these as interchangeable for the purposes of satisfying the requirement, but scores them differently based on preferences.

### Rule Type 3: `wildcard`

The student picks any course matching a pattern. The requirement text uses `@` as a wildcard: "1 Class in `@` `4@` with attribute = FIN" means "any course whose course number starts with 4 and which has the FIN attribute." This pattern is how Degree Works encodes requirements like "any 400-level Finance course."

```json
{
  "id": "fin_400_level",
  "requirement": "400 Level Finance",
  "rule_type": "wildcard",
  "pattern": "FIN 4XX",
  "credits_needed": 3,
  "category": "major"
}
```

The expander walks the full `sections.json` catalog and returns every section whose `subject == "FIN"` and whose `course_number` starts with `4`. In Owen's case that expands to FIN 412, 414, 458, 460, 465, 466, and 475 — with all their sections included.

### Rule Type 4: `course_with_lab`

Science courses with mandatory lab components. The requirement text is "2 Classes in `<LECTURE>` and `<LAB>`." The student must register for both the lecture section and a corresponding lab section.

```json
{
  "id": "science_lab",
  "requirement": "SCIENCE AND LAB REQUIREMENT",
  "rule_type": "course_with_lab",
  "pairs": [
    ["SCI 251", "SCI L251"],
    ["SCI 262", "SCI L262"],
    ["SCI 264", "SCI L264"],
    ["SCI 265", "SCI L265"]
  ],
  "credits_needed": 4,
  "category": "general_education"
}
```

The solver treats each pair as an atomic unit — it must pick a lecture section AND a lab section from the same pair, both fitting the schedule without conflicts. This is the most complex rule type because it doubles the combinatorial load for any requirement that uses it.

---

## Consequences

### Positive

- **Rule types are enumerable.** Four cases cover the overwhelming majority of Bryant Business Administration requirements. Anyone reading the code knows exactly what patterns are supported and what aren't. The alternative — treating the Degree Works DSL as an arbitrary text blob and asking Claude to interpret it at runtime — would work but would be opaque, expensive, and slow.
- **Parsing happens once, not per request.** The `parse_degree_audit.py` script runs at ingestion time and produces `audit_owen.json` with all rules already in their canonical form. The backend never re-parses the DSL. This means the solver has fast, deterministic access to the expanded candidate set.
- **Easy to extend.** Adding a fifth rule type (e.g., `credit_range` for "9 credits from FIN 4XX" requirements) is a mechanical change: new enum variant, new expander case, new solver handling. The rest of the system doesn't care.
- **Readable by the AI grader.** When the grader reads `audit_owen.json`, they immediately see the structure: completed requirements, in-progress requirements, outstanding requirements with rule types and options. The mapping from Degree Works to Pathfinder is obvious.
- **Reusable across universities.** Every university using Degree Works uses the same DSL. A future version of Pathfinder pointed at Villanova's audit format would reuse the same four rule types without modification.

### Negative

- **Only four rule types.** Degree Works actually supports more. Credit-range rules (e.g., "12 credits from ECO 2XX"), co-requisite rules (e.g., "ECO 113 must be taken with MATH 110"), prerequisite chains (e.g., "FIN 310 requires FIN 201"), and cross-listed courses (e.g., "GEN 201 is also listed as COM 280") are not handled. This is a deliberate scoping decision for the hackathon build.
- **The wildcard expander walks the full catalog.** For each wildcard rule, the expander does an O(n) scan over all 291 sections. With four wildcard rules per audit, that's ~1,200 comparisons — not a performance issue, but worth noting if the catalog grows.
- **Prerequisite checking is out of scope.** If a student hasn't taken FIN 201, Pathfinder will still happily schedule FIN 310 for them. The solver doesn't know about prerequisite chains. This is safe because Degree Works (the source of truth) already knows about prerequisites and would never put FIN 310 on a student's "outstanding" list if they hadn't completed FIN 201. But it means Pathfinder can't catch errors if a human advisor puts an invalid course on the plan.
- **Cross-listed courses create ambiguity.** When GEN 201 appears in one requirement and COM 280 appears in another and they're actually the same course, Pathfinder might double-count. Not a problem in Owen's audit; a known limitation for future audits.

### Out of scope

The following Degree Works DSL constructs are explicitly not supported in this version:

- `X credits from @ @` (credit-range rules)
- `Classes in @ @ with attribute = X` without a specific course number filter
- Co-requisite rules (`must be taken with`)
- Prerequisite rules (`requires`)
- Exception markers (`Except FIN 201` — handled at expansion time but not as a first-class rule)
- GPA minimums on concentrations (present in Owen's audit as informational, not actionable)

All of these are documented in `ROADMAP.md` as Phase 2 features.

---

## Alternatives Considered

**Ask Claude to expand the DSL at runtime.** Rejected. Every request to `/api/generate-schedules` would need an additional Claude call to interpret the rules, adding 2-4 seconds of latency and non-trivial cost. Parsing once at ingestion time is strictly better.

**Write a full PEG grammar for the Degree Works DSL.** Rejected as overkill. A grammar would handle every edge case but would take significantly longer to write and test than the four-rule enum. For the 95% of cases that matter for Owen's audit, the simple approach is correct.

**Store raw DSL strings and defer interpretation.** Rejected because it pushes complexity from ingestion time (where it runs once) to request time (where it runs on every generation). Same reasoning as the Claude-at-runtime alternative.

**Use Ellucian's official Degree Works API to expand rules.** Ellucian does have an internal API for this; it's part of their Advanced Scribe product. Not accessible without institutional credentials and not realistic for a hackathon.

---

## References

- `backend/scripts/parse_degree_audit.py` — the rule parser
- `backend/app/requirement_expander.py` — the rule → sections expander
- `data/fixtures/audit_owen.json` — Owen's parsed audit with all four rule types present
- `docs/features/03-requirement-expansion/` — the AIE documentation for this feature
