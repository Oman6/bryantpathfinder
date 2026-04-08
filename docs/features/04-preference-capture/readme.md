# Feature 04 — Preference Capture

> Collecting what the student wants so the solver knows what to optimize for.

---

## Summary

Preference capture is the step between audit parsing and schedule generation. After the student's Degree Works audit has been parsed into structured JSON, the preferences page lets them tell Pathfinder what kind of schedule they want: which requirements to take this semester, which days to block off, what time window to constrain, and any free-text preferences that Claude can interpret at ranking time.

The preferences are sent as a `SchedulePreferences` Pydantic model to `POST /api/generate-schedules` alongside the parsed `DegreeAudit`. The solver uses the structured fields directly; Claude reads the free-text field when writing explanation paragraphs and performing the final ranking.

---

## What It Captures

The preference capture system handles three categories of input:

### 1. Structured hard constraints

These are enforced by the solver as absolute rules. Sections that violate a hard constraint are removed entirely from the candidate pool before combination search begins.

| Field | Type | Effect |
|-------|------|--------|
| `blocked_days` | `list["M","T","W","R","F"]` | Sections meeting on blocked days are excluded |
| `no_earlier_than` | `str` (HH:MM) | Sections starting before this time are excluded |
| `no_later_than` | `str` (HH:MM) | Sections ending after this time are excluded |

### 2. Structured soft constraints

These affect the solver's scoring function but do not exclude sections outright.

| Field | Type | Effect |
|-------|------|--------|
| `preferred_instructors` | `list[str]` | +5 score per match |
| `avoided_instructors` | `list[str]` | -10 score per match |
| `target_credits` | `int` | Schedules within 1 credit of target get +10 score |

### 3. Free-text preferences

The `free_text` field is a string that Claude reads at ranking time. It has no effect on the deterministic solver. Examples: "I want to start the finance concentration," "Prefer morning classes," "I work Tuesday evenings."

### 4. Requirement selection

The `selected_requirement_ids` field is a list of requirement IDs from the parsed audit. The solver only expands and schedules the selected requirements. This is how the student controls which courses to take this term.

---

## The Model

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

Defined in `backend/app/models.py` at line 98.

---

## Where It Lives

| Component | Location |
|-----------|----------|
| Pydantic model | `backend/app/models.py` — `SchedulePreferences` |
| Frontend page | `frontend/app/preferences/page.tsx` |
| State management | `frontend/lib/store.ts` — Zustand store |
| API endpoint | `POST /api/generate-schedules` — receives preferences in request body |
| Solver consumption | `backend/app/solver.py` — `filter_candidates_by_preferences()` and `score_combination()` |

---

## Key Design Decisions

1. **Hard vs soft is a deliberate classification.** Blocked days and time windows are hard constraints (sections excluded entirely) because violating them makes a schedule unusable. Instructor preferences are soft constraints (scoring adjustments) because a non-preferred instructor is still acceptable — just less desirable.

2. **Free text is Claude-only.** The deterministic solver never reads `free_text`. This prevents natural language ambiguity from affecting the correctness of conflict detection and constraint enforcement. Claude reads it only at the end, when ranking three already-valid schedules.

3. **Requirement selection controls scope, not just preference.** The `selected_requirement_ids` field determines which requirements the solver expands at all. Unselected requirements are not expanded, not scored, not considered. This is the primary mechanism for keeping the solver's combination space manageable.

4. **No persistence for the hackathon.** Preferences live in the Zustand store on the frontend. If the student refreshes the page, they re-enter preferences. A production version would persist them in Supabase.

5. **The asymmetric instructor scoring is intentional.** Avoided instructors get -10, preferred get +5. Avoidance is a stronger signal than preference in the student registration context — students actively avoid a bad experience more strongly than they seek a good one.

---

## Documentation Structure

| File | Framework | Question |
|------|-----------|----------|
| `1-align.md` | Align | Why do we capture preferences this way? |
| `2-construct.md` | Construct | What does the data model look like? |
| `3-execute.md` | Execute | How does the user flow work end to end? |

---

## References

- `backend/app/models.py` — `SchedulePreferences` model
- `backend/app/solver.py` — `filter_candidates_by_preferences()`, `score_combination()`
- `frontend/app/preferences/page.tsx` — the preferences UI
- `docs/api.md` — the `/api/generate-schedules` request schema
- `CLAUDE.md` — demo path step 4 (preferences page)
