# 05 Constraint Solver — Construct

> WHAT does the solver build, and how is it structured?

---

## The `solve()` function

The solver's entry point is `solve()` in `backend/app/solver.py`.

### Inputs

| Parameter | Type | Description |
|---|---|---|
| `outstanding_requirements` | `list[OutstandingRequirement]` | All requirements from the parsed degree audit |
| `all_sections` | `list[Section]` | The full Fall 2026 catalog (291 sections from `data/sections.json`) |
| `preferences` | `SchedulePreferences` | Student preferences: target credits, blocked days, time windows, instructor preferences |

### Output

`list[ScheduleOption]` — up to 3 objects, sorted by score descending. Each `ScheduleOption` contains:

```python
class ScheduleOption(BaseModel):
    rank: int                        # 1, 2, or 3
    sections: list[Section]          # the chosen sections
    requirements_satisfied: list[str] # requirement IDs this schedule fulfills
    total_credits: float
    days_off: list[str]              # e.g. ["W", "F"]
    earliest_class: str              # e.g. "09:35"
    latest_class: str                # e.g. "17:10"
    score: float                     # solver's internal score
    explanation: str                 # filled later by Claude
```

---

## Algorithm steps

### Step 1: Expand requirements into candidate sections

For each requirement the student selected (via `preferences.selected_requirement_ids`), the solver calls `expand_requirement()` from `backend/app/requirement_expander.py`. The expander finds all sections in the catalog that could satisfy the requirement, filtered by rule type:

| Rule type | Expansion logic |
|---|---|
| `specific_course` | Match `section.course_code` against `requirement.options` (e.g., `["FIN 310"]`) |
| `choose_one_of` | Match `section.course_code` against any option in the list (e.g., `["FIN 370", "FIN 371", ...]`) |
| `wildcard` | Match `section.subject` and `section.course_number` against the pattern (e.g., `"FIN 4XX"` matches all 400-level FIN courses) |
| `course_with_lab` | Find all (lecture, lab) pairs where both codes match entries in `requirement.pairs` |

Full sections (`is_full == True`) and async sections (`is_async == True`) are excluded by default.

### Step 2: Filter by hard preference constraints

Each candidate section is checked against the student's hard constraints. Sections that fail are removed entirely — they never enter the combination space.

| Constraint | Filter logic |
|---|---|
| `blocked_days` | Remove if any meeting day is in the blocked list. E.g., `blocked_days=["F"]` removes FIN 310 sec A (TF 12:45-14:00) and sec B (TF 09:35-10:50). |
| `no_earlier_than` | Remove if any meeting starts before this time. E.g., `no_earlier_than="09:00"` removes ACG 203 sec D (TF 08:00-09:15). |
| `no_later_than` | Remove if any meeting ends after this time. |

Instructor preferences (preferred/avoided) are soft constraints — they affect scoring, not filtering.

### Step 3: Generate combinations with `itertools.product`

The solver builds a list of candidate pools, one per selected requirement. For normal requirements, each pool entry is a single-section list `[section]`. For `course_with_lab` requirements, each pool entry is a two-section list `[lecture, lab]`.

The solver then calls `itertools.product(*candidate_pools)` to generate every combination of one pool entry per requirement. Each combination represents a potential schedule.

**Safety cap:** `MAX_COMBINATIONS = 10_000`. If the search space exceeds this, the solver evaluates only the first 10,000 combinations and logs a warning. This prevents pathological cases (e.g., 10 requirements with 10 sections each = 10 billion combinations) from blowing up response time.

### Step 4: Pairwise conflict check

For each combination, the solver flattens all sections (including both lecture and lab for paired requirements) and checks every pair for time conflicts.

A combination is discarded if any pair of sections conflict. An additional pre-check discards combinations whose total credits are more than 3 away from `target_credits`.

### Step 5: Score valid combinations

Each conflict-free combination is scored by `score_combination()` on four dimensions.

### Step 6: Deduplicate and return top 3

Valid combinations are sorted by score descending. Duplicates (same set of CRNs) are removed. The top 3 distinct combinations become `ScheduleOption` objects with computed metadata (days off, earliest/latest class).

---

## Conflict detection

The `sections_conflict(a, b)` function checks whether two sections have overlapping meeting times.

### Logic

```python
def sections_conflict(a: Section, b: Section) -> bool:
    for meeting_a in a.meetings:
        for meeting_b in b.meetings:
            shared_days = set(meeting_a.days) & set(meeting_b.days)
            if not shared_days:
                continue
            a_start = to_minutes(meeting_a.start)
            a_end = to_minutes(meeting_a.end)
            b_start = to_minutes(meeting_b.start)
            b_end = to_minutes(meeting_b.end)
            if a_start < b_end and b_start < a_end:
                return True
    return False
```

### Half-open interval rule

Two time ranges overlap if each starts strictly before the other ends:

```
a_start < b_end AND b_start < a_end
```

This is the standard half-open interval overlap test. The critical consequence: back-to-back classes do NOT conflict. A class ending at 10:50 and another starting at 10:50 are not overlapping because `10:50 < 10:50` is false.

Bryant's block schedule is designed around this principle. The standard time blocks are:

| Block | Time |
|---|---|
| Block 1 | 08:00 - 09:15 |
| Block 2 | 09:35 - 10:50 |
| Block 3 | 11:10 - 12:25 |
| Block 4 | 12:45 - 14:00 |
| Block 5 | 14:20 - 15:35 |
| Block 6 | 15:55 - 17:10 |
| Evening | 18:30 - 21:10 |

Each block starts 20 minutes after the previous one ends, so standard blocks never conflict with each other on the same day.

### `to_minutes()` conversion

```python
def to_minutes(time_str: str) -> int:
    hours, minutes = time_str.split(":")
    return int(hours) * 60 + int(minutes)
```

Examples: `"08:00"` -> 480, `"09:35"` -> 575, `"14:00"` -> 840, `"17:10"` -> 1030.

### Multi-meeting sections

Some sections have two meetings (e.g., a MWR section that meets MR for lecture and W for recitation at a different time). The conflict check handles this by iterating over all pairs of meetings across the two sections. If any pair overlaps on a shared day, the sections conflict.

---

## Scoring function

`score_combination()` evaluates a valid, conflict-free schedule on four weighted dimensions.

### 1. Credit match (max +10)

```python
total_credits = sum(s.credits for s in sections)
credit_diff = abs(total_credits - preferences.target_credits)
if credit_diff <= 1:
    score += 10.0
else:
    score += max(0.0, 10.0 - credit_diff * 2)
```

If the total credits are within 1 of the target (e.g., 14-16 for a target of 15), the schedule gets the full +10. Beyond that, the score decreases by 2 per credit of distance, flooring at 0.

### 2. Instructor preferences (+5 preferred, -10 avoided)

```python
for section in sections:
    instructor_lower = section.instructor.lower()
    for pref in preferences.preferred_instructors:
        if pref.lower() in instructor_lower:
            score += 5.0
    for avoid in preferences.avoided_instructors:
        if avoid.lower() in instructor_lower:
            score -= 10.0
```

Preferred instructors get +5 per match. Avoided instructors get -10 per match — the penalty is asymmetric because avoiding a bad instructor matters more than getting a preferred one. The string matching is case-insensitive and uses substring matching (so "Kumar" matches "Kumar, Sonal").

### 3. Seat availability (+1 per section with >50% open)

```python
for section in sections:
    if section.seats_total > 0 and section.seats_open / section.seats_total > 0.5:
        score += 1.0
```

A small bonus for sections with ample availability. This nudges the solver toward schedules where the student is less likely to be closed out during registration.

### 4. Category balance (+3 per distinct category)

```python
categories = {r.category for r in requirements}
score += len(categories) * 3.0
```

Schedules that mix major, business core, and general education requirements score higher than schedules that load up on one category. A five-course schedule covering 3 distinct categories (e.g., 2 major + 2 business_core + 1 gen_ed) gets +9, while one covering only 1 category gets +3.

### Score range

For a typical five-course schedule with `target_credits=15`:
- Credit match: 0 to 10
- Instructor preferences: -50 to +25 (extreme case)
- Seat availability: 0 to 5
- Category balance: 3 to 15

A "good" schedule typically scores in the 25-35 range.

---

## Helper functions

### `_section_on_blocked_day(section, blocked_days)`

Returns `True` if any of the section's meetings fall on a blocked day. Used during the filter pass.

### `_section_outside_time_window(section, no_earlier_than, no_later_than)`

Returns `True` if any meeting starts before `no_earlier_than` or ends after `no_later_than`.

### `_has_avoided_instructor(section, avoided)`

Returns `True` if the section's instructor matches any avoided name (case-insensitive substring).

### `_get_schedule_metadata(sections)`

Computes derived metadata for a completed schedule: which days are off, the earliest start time, and the latest end time across all meetings.

---

## Data flow

```
OutstandingRequirement[]  ──┐
                            │
Section[] (291 from JSON) ──┼──> solve() ──> ScheduleOption[] (up to 3)
                            │
SchedulePreferences ────────┘
```

The solver is a pure function with no side effects. It reads no external state beyond its arguments. It writes nothing to disk or database. It makes no API calls. This makes it trivially testable and completely deterministic.
