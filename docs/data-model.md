# BryantPathfinder — Data Model Reference

> Canonical data model documentation. For the full Pydantic source, see `backend/app/models.py`. For the system design context, see `ARCHITECTURE.md`.

---

## Core Models

### Meeting

A single meeting block for a course section. Most sections have one meeting; some (like FIN 371 AR) have two.

| Field | Type | Description |
|-------|------|-------------|
| `days` | `list[Literal["M","T","W","R","F"]]` | Days of the week. Thursday is `R`, not `T` or `Th`. |
| `start` | `str` | Start time in 24-hour `HH:MM` format, e.g. `"12:45"`. |
| `end` | `str` | End time in 24-hour `HH:MM` format, e.g. `"14:00"`. |
| `building` | `str \| None` | Building code, or `null` if TBA. |
| `room` | `str \| None` | Room number, or `null` if TBA. |

### Section

The atomic unit of scheduling. One offering of a course at a specific time, taught by a specific instructor.

| Field | Type | Description |
|-------|------|-------------|
| `crn` | `str` | Course Registration Number, e.g. `"1045"`. |
| `subject` | `str` | Subject code, e.g. `"FIN"`. |
| `course_number` | `str` | Course number, e.g. `"310"`. |
| `course_code` | `str` | `subject + " " + course_number`, e.g. `"FIN 310"`. |
| `title` | `str` | Full course title. |
| `section` | `str` | Section letter, e.g. `"A"`, `"HN"`. |
| `credits` | `float` | Credit hours, typically `3.0` or `1.0`. |
| `instructor` | `str \| None` | Instructor name in `"Last, First"` format, or `null` for TBA. |
| `meetings` | `list[Meeting]` | Meeting blocks. Usually 1, sometimes 2 for multi-meeting sections. |
| `seats_open` | `int` | Currently available seats. |
| `seats_total` | `int` | Total seat capacity. |
| `waitlist_open` | `int` | Available waitlist spots. |
| `waitlist_total` | `int` | Total waitlist capacity. |
| `is_full` | `bool` | True if `seats_open == 0`. |
| `is_async` | `bool` | True for online/asynchronous sections with no meeting times. |
| `schedule_type` | `str` | `"Lecture"`, `"Lab"`, or `"Lecture/Lab"`. |
| `term` | `str` | Term identifier, e.g. `"Fall 2026"`. |

### CompletedRequirement

A degree requirement that the student has already satisfied.

| Field | Type | Description |
|-------|------|-------------|
| `requirement` | `str` | Requirement name as it appears in Degree Works. |
| `course` | `str` | Course code that satisfied it, e.g. `"GEN 100"`. |
| `grade` | `str` | Letter grade or `"REG"` for in-progress. |
| `credits` | `float` | Credit hours. |
| `term` | `str` | Term when taken, e.g. `"Fall 2025"`. |

### OutstandingRequirement

A degree requirement the student still needs to complete. The `rule_type` field determines how the requirement expander finds candidate sections.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Stable snake_case identifier, e.g. `"fin_310"`. |
| `requirement` | `str` | Human-readable requirement name. |
| `rule_type` | `Literal[...]` | One of: `specific_course`, `choose_one_of`, `wildcard`, `course_with_lab`. |
| `options` | `list[str]` | Course codes for `specific_course` and `choose_one_of` rules. |
| `pattern` | `str \| None` | Wildcard pattern like `"FIN 4XX"` for `wildcard` rules. |
| `pairs` | `list[list[str]] \| None` | Lecture/lab pairs for `course_with_lab` rules. |
| `credits_needed` | `float` | Credit hours this requirement contributes. |
| `category` | `Literal[...]` | One of: `general_education`, `business_core`, `major`, `elective`, `minor`. |

### DegreeAudit

The complete parsed output of a Degree Works audit.

| Field | Type | Description |
|-------|------|-------------|
| `student_id` | `str` | Bryant student ID. |
| `name` | `str` | Student's full name. |
| `major` | `str` | Declared major. |
| `expected_graduation` | `str` | Expected graduation date. |
| `credits_earned_or_inprogress` | `int` | Total credits completed or in progress. |
| `credits_required` | `int` | Total credits required for graduation. |
| `completed_requirements` | `list[CompletedRequirement]` | Requirements already satisfied. |
| `in_progress_requirements` | `list[CompletedRequirement]` | Requirements being completed this term. |
| `outstanding_requirements` | `list[OutstandingRequirement]` | Requirements still needed. |

### SchedulePreferences

Student preferences captured on the preferences page.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `target_credits` | `int` | `15` | Desired credit load for the semester. |
| `blocked_days` | `list[str]` | `[]` | Days to keep free, e.g. `["F"]`. |
| `no_earlier_than` | `str \| None` | `null` | Earliest acceptable class start time. |
| `no_later_than` | `str \| None` | `null` | Latest acceptable class end time. |
| `preferred_instructors` | `list[str]` | `[]` | Instructor names to prefer. |
| `avoided_instructors` | `list[str]` | `[]` | Instructor names to avoid. |
| `free_text` | `str` | `""` | Natural-language preferences for Claude to interpret. |
| `selected_requirement_ids` | `list[str]` | `[]` | Which outstanding requirements to schedule this term. |

### ScheduleOption

One of the three schedules returned by the solver.

| Field | Type | Description |
|-------|------|-------------|
| `rank` | `int` | 1, 2, or 3. |
| `sections` | `list[Section]` | The sections in this schedule. |
| `requirements_satisfied` | `list[str]` | Requirement IDs this schedule fulfills. |
| `total_credits` | `float` | Sum of credits across all sections. |
| `days_off` | `list[str]` | Weekdays with no classes. |
| `earliest_class` | `str` | Start time of the earliest class. |
| `latest_class` | `str` | End time of the latest class. |
| `score` | `float` | Solver's internal score. |
| `explanation` | `str` | Claude-generated two-sentence explanation. |

---

## Rule Type Reference

See `docs/adr/0004-requirement-rule-dsl.md` for the full decision record.

| Rule Type | Degree Works Syntax | Example |
|-----------|-------------------|---------|
| `specific_course` | `1 Class in FIN 310` | One specific course required. |
| `choose_one_of` | `1 Class in FIN 370 or 371 or 380` | Pick one from a list. |
| `wildcard` | `1 Class in @ 4@ with attribute = FIN` | Any course matching a pattern. |
| `course_with_lab` | `2 Classes in SCI 251 and L251` | Lecture + lab, must take both. |

---

## Data Sources

| File | Contents | Record Count |
|------|----------|-------------|
| `data/sections.json` | Parsed Bryant Fall 2026 catalog | 291 sections |
| `data/fixtures/audit_owen.json` | Owen Ash's parsed degree audit | 16 outstanding requirements |
| `data/raw/banner_fall2026_raw.txt` | Raw Banner text dump | 291 section blocks |
| `data/raw/degree_audit_owen.txt` | Raw Degree Works audit text | Full audit document |
