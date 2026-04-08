# Feature 03 — Requirement Expansion: Execute

> HOW does the expander work with real data? Step-by-step with actual catalog entries.

---

## Setup: The Inputs

Every worked example below uses:

- **Catalog:** `data/sections.json` — 291 sections, 117 unique courses, Fall 2026 term.
- **Audit:** `data/fixtures/audit_owen.json` — Owen Ash's parsed degree audit with 16 outstanding requirements.
- **Filters:** Default behavior — `include_full=False`, `include_async=False`.

The expander is called from `solver.py` at line 268:

```python
expanded = expand_requirement(req, all_sections)
```

No override flags, so FULL and async sections are excluded.

---

## Worked Example 1: `specific_course` — FIN 310

**Requirement:**

```json
{
  "id": "fin_310",
  "requirement": "Intermediate Corporate Finance",
  "rule_type": "specific_course",
  "options": ["FIN 310"],
  "credits_needed": 3.0,
  "category": "major"
}
```

**Step 1: Match.** The expander calls `_get_matching_sections()`, which filters `all_sections` by `s.course_code in requirement.options`. With `options = ["FIN 310"]`, it finds every section whose `course_code == "FIN 310"`.

**Step 2: Results before filtering.**

| CRN | Section | Instructor | Seats Open | is_full | is_async |
|-----|---------|------------|------------|---------|----------|
| 1045 | A | Kumar, Sonal | 18 | False | False |
| 1046 | B | Kumar, Sonal | 16 | False | False |
| 1047 | C | TBA | 22 | False | False |

**Step 3: Apply filters.** No sections are FULL. No sections are async. All three pass.

**Result:** 3 candidate sections.

**Log output:**

```
expander.expanded  requirement_id=fin_310  rule_type=specific_course  candidates=3
```

---

## Worked Example 2: `specific_course` — GEN 201

**Requirement:**

```json
{
  "id": "gen_201",
  "requirement": "Intercultural Communication",
  "rule_type": "specific_course",
  "options": ["GEN 201"],
  "credits_needed": 3.0,
  "category": "general_education"
}
```

**Step 1: Match.** Filter for `course_code == "GEN 201"`.

**Step 2: Results.** GEN 201 has 12 sections in the Fall 2026 catalog (Sections B through M), taught by six instructors: Robins, Pearce, Zammarelli (x2), Gallo, Kanemoto (x2), Zdravkovic (x2), and Williams (x3). CRNs range from 1686 to 1697.

**Step 3: Filter.** None are FULL. None are async. All 12 pass.

**Result:** 12 candidate sections — the largest pool for any `specific_course` requirement in Owen's audit. This pool significantly impacts the solver's search space because it multiplies against every other requirement's pool.

---

## Worked Example 3: `choose_one_of` — Financial Electives

**Requirement:**

```json
{
  "id": "fin_elective",
  "requirement": "Financial Electives",
  "rule_type": "choose_one_of",
  "options": ["FIN 370", "FIN 371", "FIN 380", "FIN 465", "FIN 466"],
  "credits_needed": 3.0,
  "category": "major"
}
```

**Step 1: Match.** The expander uses the same `s.course_code in requirement.options` logic. It checks all 291 sections against the five course codes.

**Step 2: Results by course code.**

| Course | Sections | Instructors | Notes |
|--------|----------|-------------|-------|
| FIN 370 | 4 (A, B, C, D) | Zbib, Cerutti, Fellingham | Largest contributor |
| FIN 371 | 0 | -- | Not offered Fall 2026 |
| FIN 380 | 2 (A, B) | Ramirez | Both sections same instructor |
| FIN 465 | 2 (A, B) | Inci | Also satisfies fin_400_level |
| FIN 466 | 1 (A) | Patel | Also satisfies fin_400_level |

**Step 3: Filter.** All 9 sections pass (none FULL, none async).

**Result:** 9 candidate sections from 4 out of 5 listed courses.

Note that FIN 371 having zero sections does not cause an error. The expander silently returns what is available. If all five courses had zero sections, the result would be an empty list, and the solver would log a warning and skip this requirement.

Also note the overlap with `fin_400_level`: FIN 465 and FIN 466 appear in both requirements' candidate pools. The solver handles this correctly — it picks one section per requirement, and if FIN 465 Section A satisfies `fin_elective`, a different FIN 4XX section must satisfy `fin_400_level`.

---

## Worked Example 4: `wildcard` — FIN 4XX (400-Level Finance)

**Requirement:**

```json
{
  "id": "fin_400_level",
  "requirement": "400 Level Finance",
  "rule_type": "wildcard",
  "pattern": "FIN 4XX",
  "credits_needed": 3.0,
  "category": "major"
}
```

**Step 1: Parse pattern.** `_expand_wildcard("FIN 4XX", all_sections)` splits the pattern into `subject_prefix = "FIN"` and `number_pattern = "4XX"`.

**Step 2: Walk the catalog.** For each of the 291 sections:
- Check `section.subject == "FIN"` — this filters to ~30 FIN sections.
- Check `section.course_number.startswith("4")` — this filters to 400-level only.

**Step 3: Results.**

| Course Code | CRN | Section | Instructor |
|-------------|-----|---------|------------|
| FIN 412 | 1072 | A | Zbib, Leila |
| FIN 414 | 1073 | A | Kuang, Huan |
| FIN 458 | 1075 | A | Maloney, Kevin |
| FIN 460 | 1076 | A | Kumar, Sonal |
| FIN 465 | 1077 | A | Inci, A. Can |
| FIN 465 | 1078 | B | Inci, A. Can |
| FIN 466 | 1079 | A | Patel, Poojan |
| FIN 475 | 1080 | A | Nigro, Peter |

**Step 4: Filter.** All 8 pass (none FULL, none async).

**Result:** 8 candidate sections across 7 unique course codes.

This is the power of wildcard expansion. The rule `"FIN 4XX"` in Owen's audit is a compact representation that the expander resolves into a concrete set of options by walking the real catalog. If Bryant added FIN 480 next semester, the expander would automatically include it without any change to Owen's audit data.

---

## Worked Example 5: `wildcard` — FIN XXX (Any Finance Course)

**Requirement:**

```json
{
  "id": "fin_general_elective",
  "requirement": "Finance Electives",
  "rule_type": "wildcard",
  "pattern": "FIN XXX",
  "credits_needed": 3.0,
  "category": "major"
}
```

**Step 1: Parse pattern.** `number_pattern = "XXX"` triggers the "match any course number" branch.

**Step 2: Walk the catalog.** Every section where `subject == "FIN"` matches.

**Result:** All Finance sections in the catalog, regardless of level. This includes FIN 201, FIN 310, FIN 312, FIN 315, FIN 370, FIN 380, and every 400-level course. The solver scores these differently but treats them all as valid candidates.

---

## Worked Example 6: `course_with_lab` — Science and Lab Requirement

**Requirement:** `science_lab` — `course_with_lab` rule with 10 pairs: `["SCI 251", "SCI L251"]` through `["SCI 371", "SCI L371"]`. Credits needed: 4.0. Category: general_education.

**Step 1: Process each pair.** The expander iterates over the 10 pairs and, for each pair, finds lectures and labs separately.

**Pair 1: SCI 251 + SCI L251**

- Lectures found: 4 sections (A, B, E, F)
- Labs found: 3 sections (B, C, E)
- Both sides filtered (none FULL, none async)
- Cross product: 4 x 3 = **12 tuples**

First three of the 12 tuples (showing the pattern):

| Lecture | Lab |
|---------|-----|
| SCI 251 A (CRN 1440, Weicksel) | SCI L251 B (CRN 1483) |
| SCI 251 A (CRN 1440, Weicksel) | SCI L251 C (CRN 1484) |
| SCI 251 A (CRN 1440, Weicksel) | SCI L251 E (CRN 1486) |
| ... 9 more tuples for sections B, E, F x labs B, C, E ... |

**Pair 2: SCI 262 + SCI L262**

- Lectures found: 1 section (A, Anwar)
- Labs found: 1 section (A, Pietraszek)
- Cross product: 1 x 1 = **1 tuple**

**Pair 3: SCI 264 + SCI L264**

- Lectures found: 1 section (A, Blais)
- Labs found: 1 section (A, Blais)
- Cross product: 1 x 1 = **1 tuple**

Pairs where either the lecture or lab course has zero sections in the catalog contribute zero tuples. The expander does not raise an error — it simply produces nothing for that pair.

**Step 2: Aggregate.** All tuples from all 10 pairs are collected into a single list.

**Result:** The total number of (lecture, lab) tuples depends on how many pairs have both lecture and lab sections in the catalog. The SCI 251 pair dominates with 12 tuples. Pairs with one lecture and one lab each contribute 1 tuple. Pairs with no sections in the catalog contribute 0.

**Log output:**

```
expander.expanded_lab  requirement_id=science_lab  pairs=<total_count>
```

---

## Worked Example 7: FULL Section Exclusion

**The setup:** COM 230 Section A (CRN 1335, Falso-Capaldi) is the only FULL section in the catalog. It has `seats_open=0` and `seats_total=7`.

**The requirement:** `lcs_course` (Literary and Cultural Studies Course) is a `choose_one_of` rule with 20 options, including `COM 230`.

**What happens:**

1. The expander matches all sections whose `course_code in options`.
2. COM 230 Section A matches on `course_code == "COM 230"`.
3. `_apply_filters()` runs with `include_full=False` (the default).
4. COM 230 Section A has `is_full == True`. It is removed.
5. The remaining LCS sections (12 sections across LCS 221, 223, 250, 251, 260, 270) all pass the filter.

**Result:** 12 candidate sections. COM 230 is silently excluded. Owen will not see COM 230 as an option in any generated schedule.

**What if `include_full=True`?** COM 230 Section A would be included, bringing the total to 13 candidates. The solver would evaluate combinations including this section, but the student would not be able to register for it. This override exists for testing and for a future waitlist-aware mode.

---

## Candidate Count Summary for Owen's Audit

When the solver expands Owen's key outstanding requirements (before preference-based filtering), the verified candidate counts are:

| Requirement ID | Rule Type | Candidates |
|---|---|---|
| `fin_310` | specific_course | 3 sections |
| `fin_312` | specific_course | 7 sections |
| `gen_201` | specific_course | 12 sections |
| `acg_203` | specific_course | 13 sections |
| `isa_201` | specific_course | 9 sections |
| `mkt_201` | specific_course | 6 sections |
| `lcs_course` | choose_one_of | 12 sections |
| `fin_elective` | choose_one_of | 9 sections |
| `fin_400_level` | wildcard | 8 sections |

The solver does not expand all 16 at once. Owen selects a subset via `selected_requirement_ids` on the preferences page — typically 5 to 6 requirements that fit a 15-credit target.

---

## Performance

The expander runs in under 1ms for all rule types at the current catalog size (291 sections). Even the wildcard expansion, which does a full catalog walk, is negligible. The solver's `solve()` function spends its time in the combination and conflict-checking loop, not in expansion.

If the catalog grew to Bryant's full ~784 sections, the wildcard expansion would do ~784 comparisons per rule instead of ~291 — still trivially fast.

---

## References

- `backend/app/requirement_expander.py` — the implementation
- `data/sections.json` — the 291-section catalog used in all examples
- `data/fixtures/audit_owen.json` — Owen's audit with all 16 outstanding requirements
- `backend/app/solver.py` lines 267-295 — where expansion is called from the solver
