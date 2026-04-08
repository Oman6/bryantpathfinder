# Feature 03 — Requirement Expansion: Construct

> WHAT is the interface and how does each rule type expand?

---

## The Public API

The module exposes a single public function:

```python
def expand_requirement(
    requirement: OutstandingRequirement,
    all_sections: list[Section],
    *,
    include_full: bool = False,
    include_async: bool = False,
) -> list[Section] | list[tuple[Section, Section]]:
```

### Parameters

| Parameter | Type | Description |
|---|---|---|
| `requirement` | `OutstandingRequirement` | The requirement to expand. Contains `rule_type`, `options`, `pattern`, and `pairs`. |
| `all_sections` | `list[Section]` | The full catalog loaded from `data/sections.json`. 291 sections in Fall 2026. |
| `include_full` | `bool` | If `True`, keep sections where `is_full == True`. Default `False`. |
| `include_async` | `bool` | If `True`, keep sections where `is_async == True`. Default `False`. |

### Return Type

- For `specific_course`, `choose_one_of`, and `wildcard`: returns `list[Section]`.
- For `course_with_lab`: returns `list[tuple[Section, Section]]`, where each tuple is `(lecture_section, lab_section)`.

The caller (the solver) checks `requirement.rule_type` to know which shape to expect.

---

## The Input Model: OutstandingRequirement

```python
class OutstandingRequirement(BaseModel):
    id: str
    requirement: str
    rule_type: Literal["specific_course", "choose_one_of", "wildcard", "course_with_lab"]
    options: list[str] = Field(default_factory=list)
    pattern: str | None = None
    pairs: list[list[str]] | None = None
    credits_needed: float
    category: Literal["general_education", "business_core", "major", "elective", "minor"]
```

Each rule type uses different fields:

| Rule type | `options` | `pattern` | `pairs` |
|---|---|---|---|
| `specific_course` | Single course code, e.g. `["FIN 310"]` | unused | unused |
| `choose_one_of` | Multiple course codes, e.g. `["FIN 370", "FIN 380", ...]` | unused | unused |
| `wildcard` | empty list | Pattern string, e.g. `"FIN 4XX"` | unused |
| `course_with_lab` | empty list | unused | List of [lecture, lab] pairs |

---

## Expansion Logic by Rule Type

### Rule Type 1: `specific_course`

The simplest case. Filter `all_sections` to those where `section.course_code` matches the single entry in `options`.

```python
# Pseudocode
candidates = [s for s in all_sections if s.course_code in requirement.options]
```

**Example:** `fin_310` has `options: ["FIN 310"]`. The expander scans all 291 sections and returns every section whose `course_code == "FIN 310"`. In the Fall 2026 catalog, that is three sections: A (CRN 1045), B (CRN 1046), and C (CRN 1047).

Note that `specific_course` and `choose_one_of` share the same matching logic internally — both filter on `s.course_code in requirement.options`. The difference is semantic: `specific_course` has exactly one option, `choose_one_of` has multiple.

---

### Rule Type 2: `choose_one_of`

Same filter as `specific_course`, but `options` contains multiple course codes. The result is the union of all sections for all listed courses.

```python
# Pseudocode — identical to specific_course
candidates = [s for s in all_sections if s.course_code in requirement.options]
```

**Example:** `fin_elective` has `options: ["FIN 370", "FIN 371", "FIN 380", "FIN 465", "FIN 466"]`. The expander checks each course code against the catalog:

| Course code | Sections found | Notes |
|---|---|---|
| FIN 370 | 4 sections (A, B, C, D) | Zbib, Cerutti, Fellingham |
| FIN 371 | 0 sections | Not offered Fall 2026 |
| FIN 380 | 2 sections (A, B) | Ramirez |
| FIN 465 | 2 sections (A, B) | Inci |
| FIN 466 | 1 section (A) | Patel |

**Total:** 9 candidate sections. The solver treats all nine as interchangeable for satisfying the `fin_elective` requirement, but scores them differently based on instructor preferences and seat availability.

---

### Rule Type 3: `wildcard`

Parses the `pattern` field into a subject prefix and a level digit, then matches against each section's `subject` and `course_number`.

```python
def _expand_wildcard(pattern: str | None, all_sections: list[Section]) -> list[Section]:
    parts = pattern.split()          # ["FIN", "4XX"]
    subject_prefix = parts[0]        # "FIN"
    number_pattern = parts[1]        # "4XX"

    results = []
    for section in all_sections:
        if section.subject != subject_prefix:
            continue

        if number_pattern == "XXX":
            # Match any course number for this subject
            results.append(section)
        elif number_pattern.endswith("XX") and len(number_pattern) == 3:
            # Match by first digit (level), e.g., "4XX" matches 400-499
            level_digit = number_pattern[0]
            if section.course_number.startswith(level_digit):
                results.append(section)

    return results
```

**Pattern formats supported:**

| Pattern | Meaning | Match condition |
|---|---|---|
| `FIN 4XX` | Any 400-level Finance course | `subject == "FIN"` and `course_number` starts with `"4"` |
| `FIN XXX` | Any Finance course at any level | `subject == "FIN"` |

**Example:** `fin_400_level` has `pattern: "FIN 4XX"`. The expander walks all 291 sections and returns every section where `subject == "FIN"` and `course_number.startswith("4")`. Result: 8 sections across 7 course codes (FIN 412, 414, 458, 460, 465 x2, 466, 475).

**Example:** `fin_general_elective` has `pattern: "FIN XXX"`. This matches every Finance section regardless of level. Result: all FIN sections in the catalog.

---

### Rule Type 4: `course_with_lab`

The most complex rule type. Each entry in `requirement.pairs` is a two-element list `[lecture_code, lab_code]`. For each pair, the expander finds all sections of the lecture course and all sections of the lab course, then generates the cross product.

```python
def _expand_course_with_lab(
    requirement: OutstandingRequirement,
    all_sections: list[Section],
    *,
    include_full: bool = False,
    include_async: bool = False,
) -> list[tuple[Section, Section]]:
    results = []
    for pair in requirement.pairs:
        lecture_code, lab_code = pair[0], pair[1]

        lectures = [s for s in all_sections if s.course_code == lecture_code]
        labs = [s for s in all_sections if s.course_code == lab_code]

        # Apply filters to each side independently
        lectures = _apply_filters(lectures, include_full=include_full, include_async=include_async)
        labs = _apply_filters(labs, include_full=include_full, include_async=include_async)

        # Cross product: every lecture paired with every lab
        for lecture in lectures:
            for lab in labs:
                results.append((lecture, lab))

    return results
```

**Key behavior:** Filters are applied to lectures and labs independently before the cross product. If a lecture section is FULL, none of its lab pairings are generated. If a lab section is FULL, it is excluded from all pairings.

**Example:** `science_lab` has 10 pairs. For the `["SCI 251", "SCI L251"]` pair: 4 lecture sections x 3 lab sections = 12 candidate tuples from this pair alone.

---

## The Filter Layer

```python
def _apply_filters(
    sections: list[Section],
    *,
    include_full: bool = False,
    include_async: bool = False,
) -> list[Section]:
    result = sections
    if not include_full:
        result = [s for s in result if not s.is_full]
    if not include_async:
        result = [s for s in result if not s.is_async]
    return result
```

Filters run after matching, before the result is returned. For `course_with_lab`, filters run on each side of the pair before the cross product is computed.

**Current catalog impact:**
- 1 section is FULL in the entire catalog: COM 230 Section A (CRN 1335). This affects the `lcs_course` requirement — COM 230 is in its options list, but the only section of COM 230 is full, so it contributes zero candidates.
- 0 sections are async. The async filter is currently a no-op but is included for forward compatibility.

---

## Internal Architecture

```
expand_requirement()
    │
    ├── rule_type == "course_with_lab"?
    │       └── _expand_course_with_lab()
    │               ├── find lectures for each pair
    │               ├── find labs for each pair
    │               ├── _apply_filters() on each side
    │               └── cross product → list[tuple[Section, Section]]
    │
    └── all other rule types
            ├── _get_matching_sections()
            │       ├── specific_course / choose_one_of → filter by course_code in options
            │       └── wildcard → _expand_wildcard(pattern)
            ├── _apply_filters()
            └── return list[Section]
```

The dispatch is a simple `if/else` on `rule_type`. The `course_with_lab` path is separated because its return type is different and its filter application is more complex (filters apply per-side before cross product, not to the final result).

---

## Logging

The expander logs one structured event per call:

```python
logger.info(
    "expander.expanded",
    extra={
        "requirement_id": requirement.id,
        "rule_type": requirement.rule_type,
        "candidates": len(candidates),
    },
)
```

For `course_with_lab`, a separate event logs the pair count:

```python
logger.info(
    "expander.expanded_lab",
    extra={
        "requirement_id": requirement.id,
        "pairs": len(results),
    },
)
```

These log lines are the primary observability mechanism for debugging "why did the solver find zero schedules?" — if the expander returns zero candidates for any requirement, the solver's combination space collapses to zero.

---

## References

- `backend/app/requirement_expander.py` — the full implementation (~155 lines)
- `backend/app/models.py` — `OutstandingRequirement`, `Section`
- `backend/app/solver.py` — the consumer, specifically `solve()` lines 267-295
- `docs/adr/0004-requirement-rule-dsl.md` — design rationale for the four rule types
