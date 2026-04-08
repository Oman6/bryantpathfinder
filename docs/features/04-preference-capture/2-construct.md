# Feature 04 — Preference Capture: Construct

> WHAT is the data model and how do hard vs soft constraints work?

---

## The SchedulePreferences Model

Defined in `backend/app/models.py`:

```python
class SchedulePreferences(BaseModel):
    target_credits: int = 15
    blocked_days: list[Literal["M", "T", "W", "R", "F"]] = Field(default_factory=list)
    no_earlier_than: str | None = None
    no_later_than: str | None = None
    preferred_instructors: list[str] = Field(default_factory=list)
    avoided_instructors: list[str] = Field(default_factory=list)
    free_text: str = ""
    selected_requirement_ids: list[str] = Field(default_factory=list)
```

Every field has a sensible default. A completely empty `SchedulePreferences` object (no blocked days, no time window, no instructor preferences, no free text) is valid and produces schedules with no preference-based filtering — just the default FULL/async exclusions from the requirement expander.

---

## Field-by-Field Specification

### `target_credits: int = 15`

The student's desired credit load for the semester. Default is 15 (a standard full-time load at Bryant).

**How the solver uses it:** In `score_combination()`, the total credits of a schedule are compared to this target:
- Within 1 credit of target: +10 score
- More than 1 credit away: +max(0, 10 - credit_diff * 2) score
- 6+ credits away: +0 score

The solver also enforces a hard cap: combinations where `abs(total_credits - target_credits) > 3` are rejected before conflict checking. This prevents the solver from wasting time on 9-credit or 21-credit schedules when the student wants 15.

### `blocked_days: list[Literal["M", "T", "W", "R", "F"]]`

Days when the student cannot or will not attend class.

**How the solver uses it:** Hard constraint. In `filter_candidates_by_preferences()`, any section that meets on a blocked day is removed from the candidate pool. The check uses `_section_on_blocked_day()`:

```python
def _section_on_blocked_day(section: Section, blocked_days: list[str]) -> bool:
    for meeting in section.meetings:
        if set(meeting.days) & set(blocked_days):
            return True
    return False
```

**Day encoding:** Bryant/Banner uses single-character codes: M (Monday), T (Tuesday), W (Wednesday), R (Thursday), F (Friday). Thursday is R, not Th. This is standard Banner convention.

**Common patterns:**
- `["F"]` — no Friday classes (the most popular preference at Bryant)
- `["W", "F"]` — no Wednesday or Friday classes (aggressive but achievable with MWF block courses removed)
- `["M", "W", "F"]` — only Tuesday/Thursday classes (limits options significantly)

### `no_earlier_than: str | None = None`

The earliest acceptable class start time, in 24-hour "HH:MM" format.

**How the solver uses it:** Hard constraint. If set, any section whose meeting starts before this time is excluded. The check uses `to_minutes()` to convert both times to minutes since midnight for clean integer comparison:

```python
if no_earlier_than and to_minutes(meeting.start) < to_minutes(no_earlier_than):
    return True  # outside window
```

**Examples:**
- `"10:00"` — no classes before 10am (a common request from students who value sleep)
- `"08:00"` — accepts Bryant's earliest block (8:00-9:15)
- `None` — no lower bound, all start times accepted

### `no_later_than: str | None = None`

The latest acceptable class end time, in 24-hour "HH:MM" format.

**How the solver uses it:** Hard constraint. If set, any section whose meeting ends after this time is excluded.

```python
if no_later_than and to_minutes(meeting.end) > to_minutes(no_later_than):
    return True  # outside window
```

**Examples:**
- `"17:00"` — no evening classes (common for students with part-time jobs)
- `"15:00"` — only morning and early afternoon classes
- `None` — no upper bound, all end times accepted

**Multi-meeting sections:** Both `no_earlier_than` and `no_later_than` check every meeting block in the section. A section with meetings at 09:00-10:15 and 18:00-19:15 would pass a `no_earlier_than: "08:00"` check but fail a `no_later_than: "17:00"` check because the evening meeting ends after 17:00.

### `preferred_instructors: list[str]`

Instructors the student would like to have. Substring matching, case-insensitive.

**How the solver uses it:** Soft constraint, applied in `score_combination()`:

```python
for pref in preferences.preferred_instructors:
    if pref.lower() in instructor_lower:
        score += 5.0
```

**Substring matching rationale:** Banner stores instructor names in "Last, First" format (e.g., "Kumar, Sonal"). The student might type "Kumar" or "Sonal Kumar" or "kumar" — substring matching handles all of these without requiring the student to know the exact Banner format.

**Example:** `preferred_instructors: ["Kumar"]` would match "Kumar, Sonal" (FIN 310 A/B) and any other instructor whose name contains "Kumar."

### `avoided_instructors: list[str]`

Instructors the student wants to avoid. Same substring matching as preferred.

**How the solver uses it:** Soft constraint:

```python
for avoid in preferences.avoided_instructors:
    if avoid.lower() in instructor_lower:
        score -= 10.0
```

Note the asymmetry: avoided instructors penalize at -10, twice the magnitude of the +5 preferred instructor bonus. This is intentional — avoidance is a stronger signal.

**Important:** Avoided instructors are a soft constraint, not hard. The section is not removed from the candidate pool. If the only section of a required course is taught by an avoided instructor, the solver will still include it but score it lower. This prevents the student from accidentally making the solver return zero schedules.

### `free_text: str = ""`

Open-ended text input for preferences that do not fit the structured fields.

**How the solver uses it:** The deterministic solver ignores this field entirely. It is passed to Claude in two contexts:

1. **Explanation writing.** When Claude generates the 2-sentence explanation for each schedule, the prompt includes the student's free text so Claude can reference it. If the student wrote "I want to start the finance concentration" and the schedule includes FIN 310, Claude can say "This schedule starts your finance concentration with Kumar."

2. **Final ranking.** When Claude re-ranks the three candidate schedules, it reads the free text to determine which schedule best matches the student's expressed goals.

**Examples:**
- `"I want to start the finance concentration"`
- `"Prefer back-to-back classes to minimize gaps"`
- `"I work at the writing center Tuesday/Thursday afternoons"`
- `""` (empty — perfectly valid, Claude will rank on structured factors only)

### `selected_requirement_ids: list[str]`

The requirement IDs (from `OutstandingRequirement.id`) that the student wants to schedule this term.

**How the solver uses it:** The solver filters `outstanding_requirements` to only the selected subset before expansion:

```python
selected_ids = set(preferences.selected_requirement_ids)
if selected_ids:
    requirements = [r for r in outstanding_requirements if r.id in selected_ids]
else:
    requirements = list(outstanding_requirements)
```

If `selected_requirement_ids` is empty, the solver uses all outstanding requirements (fallback for testing). In normal operation, the student always selects a subset.

**Examples from Owen's audit:**
- `["fin_310", "gen_201", "acg_203", "isa_201", "mkt_201"]` — five courses, targeting 15 credits
- `["fin_310", "fin_312", "gen_201", "science_lab"]` — three 3-credit courses plus one 4-credit lab, targeting 13 credits

---

## Hard Constraints vs Soft Constraints: Decision Boundary

The classification of each field as hard or soft was deliberate:

| Field | Classification | Rationale |
|-------|---------------|-----------|
| `blocked_days` | Hard | A Friday class on a blocked Friday is unusable. No score penalty can fix that. |
| `no_earlier_than` | Hard | An 8am class when the student said "nothing before 10" is a deal-breaker. |
| `no_later_than` | Hard | An evening class when the student has a job is a deal-breaker. |
| `preferred_instructors` | Soft | The student wants Kumar but will accept others. Should not eliminate non-Kumar sections. |
| `avoided_instructors` | Soft | A strong signal but not absolute. If the only FIN 310 section available has an avoided instructor, the student needs to see it. |
| `target_credits` | Soft (scoring) + Hard (range) | Exact match is soft (+10 score). But the 3-credit range limit is hard — 9-credit or 21-credit schedules are never returned. |
| `free_text` | Neither | Not processed by the solver at all. Claude-only. |
| `selected_requirement_ids` | Scoping | Not a constraint on sections — it controls which requirements enter the solver. |

---

## The Request Shape

Preferences are sent as part of the `GenerateSchedulesRequest`:

```python
class GenerateSchedulesRequest(BaseModel):
    audit: DegreeAudit
    preferences: SchedulePreferences
```

The full request to `POST /api/generate-schedules`:

```json
{
  "audit": { "...DegreeAudit..." },
  "preferences": {
    "target_credits": 15,
    "blocked_days": ["F"],
    "no_earlier_than": "10:00",
    "no_later_than": null,
    "preferred_instructors": ["Kumar"],
    "avoided_instructors": [],
    "free_text": "I want to start the finance concentration",
    "selected_requirement_ids": [
      "fin_310", "gen_201", "acg_203", "isa_201", "mkt_201"
    ]
  }
}
```

---

## Validation Rules

Pydantic enforces the following at parse time:

- `blocked_days` elements must be one of `"M", "T", "W", "R", "F"`. A value like `"Th"` or `"Friday"` will raise a 422 validation error.
- `no_earlier_than` and `no_later_than` are strings, not times. The solver parses them with `to_minutes()`, which expects "HH:MM" format. Malformed values like "10am" or "1000" will cause a runtime error in the solver, not a Pydantic validation error. This is a known limitation — a custom validator could be added but was not prioritized for the hackathon.
- `selected_requirement_ids` values are not validated against the audit's actual requirement IDs. If the student sends an ID that does not exist in the audit, the solver silently ignores it (the filter produces an empty match). If all selected IDs are invalid, the solver falls back to using all outstanding requirements.
- `target_credits` is an `int`, not a `float`. This is correct — Bryant courses are all whole-number credits (1, 3, or 4).

---

## Frontend-Backend Contract

The preferences page on the frontend constructs a `SchedulePreferences` object and stores it in the Zustand store. When the student clicks "Generate my schedules," the frontend sends the full `GenerateSchedulesRequest` (audit + preferences) to the backend.

The Zustand store shape mirrors the Pydantic model:

```typescript
// frontend/lib/types.ts
interface SchedulePreferences {
  target_credits: number;
  blocked_days: ("M" | "T" | "W" | "R" | "F")[];
  no_earlier_than: string | null;
  no_later_than: string | null;
  preferred_instructors: string[];
  avoided_instructors: string[];
  free_text: string;
  selected_requirement_ids: string[];
}
```

The TypeScript types in `frontend/lib/types.ts` are manually kept in sync with the Pydantic models in `backend/app/models.py`. There is no code generation step — this is a deliberate hackathon simplification.

---

## References

- `backend/app/models.py` lines 98-112 — `SchedulePreferences` definition
- `backend/app/solver.py` lines 115-144 — `filter_candidates_by_preferences()`
- `backend/app/solver.py` lines 147-199 — `score_combination()`
- `frontend/lib/types.ts` — TypeScript mirror of the model
- `frontend/lib/store.ts` — Zustand store for preferences state
- `docs/api.md` — full request/response documentation for `/api/generate-schedules`
