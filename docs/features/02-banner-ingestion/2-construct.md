# Feature 02 -- Banner Catalog Ingestion

## 2-Construct: What We Are Building

---

### The Section Model

Defined in `backend/app/models.py`, the `Section` model is the atomic unit of scheduling. Every section in the catalog is one instance of this model.

```python
class Section(BaseModel):
    crn: str
    subject: str
    course_number: str
    course_code: str
    title: str
    section: str
    credits: float
    instructor: str | None = None
    meetings: list[Meeting]
    seats_open: int
    seats_total: int
    waitlist_open: int = 0
    waitlist_total: int = 0
    is_full: bool
    is_async: bool
    schedule_type: str
    term: str
    start_date: str | None = None
    end_date: str | None = None
```

**Field-by-field breakdown:**

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `crn` | `str` | `"1425"` | Course Reference Number, unique per section per term |
| `subject` | `str` | `"SOAN"` | Department abbreviation |
| `course_number` | `str` | `"242"` | Course number within the subject |
| `course_code` | `str` | `"SOAN 242"` | `subject + " " + course_number`, used for matching |
| `title` | `str` | `"Principles of Anthropology"` | Full course title from the catalog |
| `section` | `str` | `"B"` | Section letter (A, B, C, HN for honors, etc.) |
| `credits` | `float` | `3.0` | Credit hours (1.0 for 1-credit courses like GEN 100) |
| `instructor` | `str or None` | `"Dygert, Holly"` | Last, First format. `None` when listed as TBA |
| `meetings` | `list[Meeting]` | 1 item typically | Empty for async. May have 2 for multi-meeting sections |
| `seats_open` | `int` | `2` | Remaining open seats at snapshot time |
| `seats_total` | `int` | `4` | Total enrollment capacity |
| `waitlist_open` | `int` | `0` | Remaining waitlist spots |
| `waitlist_total` | `int` | `0` | Total waitlist capacity |
| `is_full` | `bool` | `false` | True when seats_open == 0. Set from the "FULL:" prefix |
| `is_async` | `bool` | `false` | True for online/async sections with no meeting times |
| `schedule_type` | `str` | `"Lecture"` | "Lecture", "Lab", or "Lecture/Lab" |
| `term` | `str` | `"Fall 2026"` | Always "Fall 2026" for this dataset |
| `start_date` | `str or None` | `"2026-08-31"` | ISO format, converted from MM/DD/YYYY |
| `end_date` | `str or None` | `"2026-12-18"` | ISO format |

---

### The Meeting Model

```python
class Meeting(BaseModel):
    days: list[Literal["M", "T", "W", "R", "F"]]
    start: str  # "HH:MM" 24-hour format
    end: str    # "HH:MM" 24-hour format
    building: str | None = None
    room: str | None = None
```

Most sections have exactly one meeting. The `days` list contains single-letter codes for each day the section meets. A Monday/Thursday class has `["M", "R"]`. A Monday/Wednesday/Friday class has `["M", "W", "F"]`.

Multi-meeting sections (rare but real) have two entries in the `meetings` list -- for example, a section that meets Monday/Thursday 09:35-10:50 for lecture and also Wednesday 18:00-20:30 for a recitation.

Async sections have `meetings: []` (empty list).

---

### The Raw Text Format

The raw Banner dump (`data/raw/banner_fall2026_raw.txt`) contains one block per section, separated by lines of 40 or more dashes:

```
Subject: SOAN
Course Number: 242
Title: Principles of Anthropology
Section: B
CRN: 1425
Hours: 3
Instructor: Dygert, Holly
Meeting Days: Monday,Thursday
Meeting Time: 09:35 AM - 10:50 AM
Building: None
Room: None
Start Date: 08/31/2026
End Date: 12/18/2026
Schedule Type: Lecture
Status: 2 of 4 seats remain.
Waitlist: 0 of 0 waitlist seats remain.
----------------------------------------
```

Each block is a sequence of `Key: Value` lines. The parser splits on lines containing 40+ dashes, then parses each block into a field dictionary by splitting on the first colon in each line.

---

### Parsing Rules

#### Day Mapping

Banner uses full day names. Pathfinder uses single-letter codes matching the standard Banner/Degree Works convention:

```python
DAY_MAP = {
    "Monday": "M",
    "Tuesday": "T",
    "Wednesday": "W",
    "Thursday": "R",
    "Friday": "F",
}
```

**Thursday is R, not T or Th.** This is the standard Banner convention and avoids ambiguity with Tuesday. The `parse_meeting_days()` function splits the comma-separated day string and maps each full name:

```
"Monday,Thursday" -> ["M", "R"]
"Tuesday,Friday"  -> ["T", "F"]
"Monday,Wednesday,Thursday" -> ["M", "W", "R"]
```

#### Time Conversion (12-hour to 24-hour)

Banner uses 12-hour format with AM/PM. Pathfinder normalizes all times to 24-hour HH:MM format for clean arithmetic in the conflict detector:

```python
def parse_time_12_to_24(time_str: str) -> str:
    match = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)", time_str.strip())
    hour, minute, period = int(match.group(1)), match.group(2), match.group(3)
    if period == "PM" and hour != 12:
        hour += 12
    elif period == "AM" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute}"
```

Conversion examples:

| Banner format | Pathfinder format | Notes |
|---------------|-------------------|-------|
| `08:00 AM` | `08:00` | Standard morning |
| `09:35 AM` | `09:35` | Bryant's block start |
| `12:45 PM` | `12:45` | Noon stays 12 |
| `02:00 PM` | `14:00` | PM adds 12 |
| `05:10 PM` | `17:10` | Latest standard block |
| `12:00 AM` | `00:00` | Midnight edge case |

The full time range is parsed from `"09:35 AM - 10:50 AM"` by splitting on the dash and converting each half.

#### Status Line Parsing

The status line indicates seat availability and whether the section is full:

```python
def parse_status(status_line: str) -> dict:
    is_full = status_line.startswith("FULL:")
    match = re.search(r"(\d+)\s+of\s+(\d+)\s+seats?\s+remain", status_line)
    seats_open = int(match.group(1))
    seats_total = int(match.group(2))
    return {
        "seats_open": seats_open,
        "seats_total": seats_total,
        "is_full": is_full,
    }
```

Examples:

| Status line | seats_open | seats_total | is_full |
|-------------|-----------|-------------|---------|
| `"18 of 30 seats remain."` | 18 | 30 | false |
| `"2 of 4 seats remain."` | 2 | 4 | false |
| `"FULL: 0 of 7 seats remain."` | 0 | 7 | true |
| `"25 of 25 seats remain."` | 25 | 25 | false |

The `FULL:` prefix is the authoritative signal for full sections, not just `seats_open == 0`, because Banner may show "FULL: 0 of 7" where the zero confirms the FULL status.

#### Waitlist Handling

Waitlist information follows the same pattern:

```python
def parse_waitlist(waitlist_line: str) -> dict:
    match = re.search(r"(\d+)\s+of\s+(\d+)\s+waitlist\s+seats?\s+remain", waitlist_line)
    return {
        "waitlist_open": int(match.group(1)),
        "waitlist_total": int(match.group(2)),
    }
```

Many sections have `"0 of 0 waitlist seats remain."` -- waitlists are configured per-section by the registrar and many sections do not use them.

#### Async Section Detection

Async/online sections appear in Banner with sentinel time values or missing meeting days. The parser detects three indicators:

```python
is_async = False
if not meeting_days_raw or meeting_days_raw == "None" or "00:00 AM" in meeting_time_raw:
    is_async = True
```

When `is_async` is true, the `meetings` list is left empty. The solver skips async sections by default unless the student's preferences explicitly allow them. This prevents the solver from generating schedules full of online sections when the student expects in-person classes.

#### Instructor Normalization

Instructors are stored in "Last, First" format as they appear in Banner. When the field contains "TBA", the parser sets `instructor: null`. A null instructor does not affect conflict detection but prevents the scoring function from awarding preferred instructor bonuses.

---

### Validation Contract

The parser enforces two post-conditions:

1. **Section count must equal 291.** If wrong, the script exits nonzero. This catches parsing errors and data corruption.
2. **Required fields present.** Blocks lacking `Subject` or `CRN` are silently skipped. The count check ensures nothing important was lost.

The script also prints the subject distribution as a sanity check.
