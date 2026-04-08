# Feature 02 -- Banner Catalog Ingestion

## 3-Execute: How It Runs

---

### Step-by-Step Parsing Pipeline

#### Step 1: Read the raw file

```python
RAW_FILE = PROJECT_ROOT / "data" / "raw" / "banner_fall2026_raw.txt"
text = RAW_FILE.read_text(encoding="utf-8")
```

The raw file is UTF-8 encoded plain text, approximately 15,000 lines. Each section occupies 15-17 lines, followed by a separator line of 40+ dashes.

#### Step 2: Split on separator lines

```python
blocks = re.split(r"-{40,}", text)
```

The regex `r"-{40,}"` matches any line containing 40 or more consecutive dashes. This splits the full text into one block per section, plus potential empty blocks from leading/trailing separators.

After splitting, each block is a multi-line string like:

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
```

#### Step 3: Parse each block into a field dictionary

For each non-empty block, the parser splits lines on the first colon to build a `key: value` dictionary:

```python
fields: dict[str, str] = {}
for line in lines:
    if ":" in line:
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
```

Using `partition(":")` instead of `split(":")` ensures that colons in the value (such as in time strings "09:35 AM - 10:50 AM") are preserved correctly. Only the first colon in each line is treated as a separator.

**Skip condition:** If the resulting dictionary does not contain both `"Subject"` and `"CRN"`, the block is skipped. This handles header blocks, empty blocks from double separators, and any other non-section content in the raw file.

#### Step 4: Convert days, times, and status

**Days:** `"Monday,Thursday"` becomes `["M", "R"]` via the `DAY_MAP` lookup.

**Times:** `"09:35 AM - 10:50 AM"` is split on the dash. Each half is converted from 12-hour to 24-hour format: `"09:35"` and `"10:50"`.

**Status:** `"2 of 4 seats remain."` is parsed to `seats_open=2, seats_total=4, is_full=false`.

**Async detection:** If the meeting days field is empty, is `"None"`, or the time field contains `"00:00 AM"`, the section is marked `is_async=true` with an empty meetings list.

**Instructor:** If the instructor field is `"TBA"`, it is set to `None`.

**Dates:** `"08/31/2026"` is converted to ISO format `"2026-08-31"`.

**Building/Room:** If either field is the string `"None"`, it is set to `null`.

#### Step 5: Build the Section dictionary

All parsed and converted fields are assembled into a dictionary matching the `Section` Pydantic model:

```python
return {
    "crn": crn,
    "subject": subject,
    "course_number": course_number,
    "course_code": f"{subject} {course_number}",
    "title": title,
    "section": section_letter,
    "credits": credits,
    "instructor": instructor,
    "meetings": meetings,
    "seats_open": status_info["seats_open"],
    "seats_total": status_info["seats_total"],
    "waitlist_open": waitlist_info["waitlist_open"],
    "waitlist_total": waitlist_info["waitlist_total"],
    "is_full": status_info["is_full"],
    "is_async": is_async,
    "schedule_type": schedule_type,
    "term": "Fall 2026",
    "start_date": start_date,
    "end_date": end_date,
}
```

The `course_code` field is computed by concatenating `subject` and `course_number` with a space. This is the field the requirement expander uses for matching -- when the expander looks for all sections of `"FIN 310"`, it compares against `course_code`.

#### Step 6: Validate and write

The script asserts `len(sections) == 291` and exits with a nonzero code if wrong -- a hard gate against silent data corruption. On success, it writes `sections.json` with 2-space indentation and `ensure_ascii=False`.

---

### Worked Example: SOAN 242 B

**Raw input block:**

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
```

**Parsing trace:**

1. `fields["Subject"]` = `"SOAN"`, `fields["CRN"]` = `"1425"` -- block is valid, proceed
2. `subject` = `"SOAN"`, `course_number` = `"242"`, `course_code` = `"SOAN 242"`
3. `title` = `"Principles of Anthropology"`, `section` = `"B"`, `credits` = `3.0`
4. `instructor` = `"Dygert, Holly"` (not TBA, kept as-is)
5. `meeting_days_raw` = `"Monday,Thursday"` -> `parse_meeting_days()` -> `["M", "R"]`
6. `meeting_time_raw` = `"09:35 AM - 10:50 AM"` -> `parse_meeting_time()` -> `("09:35", "10:50")`
7. Neither days nor time triggers async detection -> `is_async = False`
8. `meetings` = `[{"days": ["M", "R"], "start": "09:35", "end": "10:50", "building": null, "room": null}]`
9. `status` = `"2 of 4 seats remain."` -> `parse_status()` -> `seats_open=2, seats_total=4, is_full=False`
10. `waitlist` = `"0 of 0 waitlist seats remain."` -> `waitlist_open=0, waitlist_total=0`
11. `start_date` = `"08/31/2026"` -> `parse_date()` -> `"2026-08-31"`
12. `end_date` = `"12/18/2026"` -> `parse_date()` -> `"2026-12-18"`

**JSON output** (key fields shown):

```json
{
  "crn": "1425", "course_code": "SOAN 242", "section": "B",
  "instructor": "Dygert, Holly", "credits": 3.0,
  "meetings": [{"days": ["M", "R"], "start": "09:35", "end": "10:50"}],
  "seats_open": 2, "seats_total": 4,
  "is_full": false, "is_async": false, "term": "Fall 2026"
}
```

---

### Worked Example: FULL Section (COM 230 A)

**Raw input** includes `Status: FULL: 0 of 7 seats remain.` -- the `FULL:` prefix triggers `is_full=True`. The parsed section has `seats_open: 0`, `seats_total: 7`, `is_full: true`. COM 230 is one of Owen's 20 options for the `lcs_course` choose_one_of requirement, but the expander excludes it because `is_full` is true.

---

### Subject Distribution

The parser prints the subject distribution as a sanity check after writing `sections.json`. The expected output for the Fall 2026 dataset:

```
  ACG: 42
  BUS: 6
  COM: 6
  ECO: 28
  FIN: 45
  GEN: 28
  HIS: 16
  ISA: 9
  LCS: 12
  LGLS: 8
  MATH: 10
  MGT: 19
  MKT: 10
  POLS: 6
  PSY: 6
  SCI: 26
  SOAN: 14
```

**Total: 291 sections across 17 subjects.**

Notable patterns:
- FIN (45) and ACG (42) dominate because Finance and Accounting have many sections per course to accommodate large enrollment
- SCI (26) is high because it includes both lecture and lab sections (SCI 251 + SCI L251 count as two sections)
- GEN (28) reflects the multiple sections of GEN 201 (Intercultural Communication) -- Owen's audit shows 12 sections of GEN 201 alone
- Single-digit subjects (BUS: 6, COM: 6, POLS: 6, PSY: 6) are gen ed elective options with fewer section offerings

---

### What Happens After Ingestion

At FastAPI startup, the lifespan context manager loads `sections.json` into `app.state.sections` as a `list[Section]`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    sections_path = Path("data/sections.json")
    raw = json.loads(sections_path.read_text())
    app.state.sections = [Section(**s) for s in raw]
    yield
```

Each raw dict is validated through the `Section` Pydantic model on load. If any section in the JSON file has invalid data (wrong type, missing field, invalid day code), the server crashes at startup with a clear validation error rather than silently serving bad data.

The sections are then available to every route handler through dependency injection. The requirement expander receives the full `list[Section]` and filters it down to candidates for each outstanding requirement. The health endpoint reports `sections_loaded: 291` to confirm the data is present.

---

### Running the Parser

From the project root:

```bash
python backend/scripts/parse_banner_dump.py
```

Expected output: `Parsed 291 sections`, `Section count verified: 291`, followed by the subject distribution. The script is idempotent: running it multiple times produces identical output as long as the raw file has not changed.

---

### Edge Cases Handled

| Edge case | How the parser handles it |
|-----------|--------------------------|
| Empty blocks from consecutive separators | `re.split()` produces empty strings; skipped with `if not block: continue` |
| Blocks without Subject or CRN | Header or metadata blocks are detected by checking for both fields; skipped if either is missing |
| Colons in time values | `str.partition(":")` splits only on the first colon, preserving `"09:35 AM - 10:50 AM"` intact |
| Building/Room set to `"None"` | The literal string "None" is converted to Python `None`, serialized as JSON `null` |
| Credits as string | `float(fields.get("Hours", "3"))` converts from string with a default of 3 credits |
