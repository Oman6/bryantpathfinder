# Feature 01 -- Degree Audit Parsing

## 3-Execute: How It Runs

---

### The Live Vision Path -- Step by Step

#### Step 1: User uploads a screenshot

The student drags a Degree Works screenshot (PNG, JPEG, or PDF) onto the `UploadZone` component on the homepage, or clicks the upload area to open a file picker. The frontend reads the file using the browser's `FileReader` API and converts it to a base64 string.

```
Input:  degree_works_screenshot.png (raw file from student)
Output: "iVBORw0KGgoAAAANSuhEUgAA..." (base64 string, typically 200-500KB)
```

#### Step 2: POST /api/parse-audit

The frontend sends the base64 string to the backend:

```json
{
  "image_base64": "iVBORw0KGgoAAAANSuhEUgAA..."
}
```

The FastAPI route validates the request body against the `ParseAuditRequest` model, which confirms `image_base64` is a non-empty string.

#### Step 3: Claude Vision call

`parse_audit_vision()` in `backend/app/claude_client.py` builds the Anthropic API request:

```python
message = client.messages.create(
    model="claude-sonnet-4-5-20250514",
    max_tokens=4096,
    temperature=0,
    system=VISION_AUDIT_PROMPT,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_base64,
                    },
                },
                {
                    "type": "text",
                    "text": "Parse this Degree Works audit and return the structured JSON.",
                },
            ],
        }
    ],
)
```

Key configuration: `claude-sonnet-4-5-20250514`, `max_tokens=4096`, `temperature=0`. The image is sent inline as base64 alongside a text instruction.

#### Step 4: JSON parsing and validation

Claude sometimes wraps JSON in markdown fences. The `_parse_json_response()` helper strips any ```` ``` ```` lines before calling `json.loads()`. The parsed dict is then validated through `DegreeAudit(**parsed)` -- Pydantic checks every field type, validates `rule_type` against the four allowed literals, validates `category` against the five allowed literals, and applies defaults for optional fields. If validation fails, a `ValidationError` triggers the retry logic.

---

### The Retry-on-Malformed-JSON Logic

The Vision parsing runs inside a two-attempt loop:

```python
last_error = None

for attempt in range(2):
    try:
        # ... Claude API call ...
        response_text = message.content[0].text
        parsed = _parse_json_response(response_text)
        audit = DegreeAudit(**parsed)
        return audit

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        last_error = e
        if attempt == 0:
            continue  # retry once

    except anthropic.AuthenticationError:
        raise  # do not retry auth errors

    except anthropic.RateLimitError:
        raise  # do not retry rate limits

raise ValueError(f"Claude returned malformed JSON after 2 attempts: {last_error}")
```

**What gets retried:** `json.JSONDecodeError` (Claude returned text that is not valid JSON), `KeyError` (JSON is valid but missing a required field), `TypeError` (field has the wrong type and Pydantic cannot coerce it).

**What does not get retried:** `AuthenticationError` and `RateLimitError` -- these are propagated immediately.

### The Fixture Fallback Path

When the student clicks "Use sample audit", the frontend loads `audit_owen.json` directly into the Zustand store and navigates to preferences. No API call, no Claude tokens. This path works regardless of network connectivity or API key configuration.

---

### Worked Example: Owen Ash's Audit

Starting input: A Degree Works screenshot showing Owen Ash's progress in the Finance B.S.B.A. program.

**Claude reads the screenshot and produces:**

```json
{
  "student_id": "001118725",
  "name": "Owen Ash",
  "major": "Finance",
  "expected_graduation": "May 2029",
  "credits_earned_or_inprogress": 42,
  "credits_required": 120,
  "completed_requirements": [
    {
      "requirement": "Student Success at Bryant Univ",
      "course": "GEN 100",
      "grade": "A",
      "credits": 1.0,
      "term": "Fall 2025"
    },
    {
      "requirement": "Statistics I",
      "course": "MATH 201",
      "grade": "A",
      "credits": 3.0,
      "term": "Fall 2025"
    }
  ],
  "in_progress_requirements": [
    {
      "requirement": "Financial Management",
      "course": "FIN 201",
      "grade": "REG",
      "credits": 3.0,
      "term": "Spring 2026"
    }
  ],
  "outstanding_requirements": [
    ...
  ]
}
```

(Completed and in-progress lists abbreviated for clarity. Full output has 6 completed, 9 in-progress, 16 outstanding.)

**The outstanding requirements demonstrate each rule type:**

FIN 310 as `specific_course` -- the audit says "Still needed: 1 Class in FIN 310" and Claude produces:

```json
{
  "id": "fin_310",
  "requirement": "Intermediate Corporate Finance",
  "rule_type": "specific_course",
  "options": ["FIN 310"],
  "pattern": null,
  "pairs": null,
  "credits_needed": 3.0,
  "category": "major"
}
```

FIN 370/371/380/465/466 as `choose_one_of` -- the audit says "Still needed: 1 Class in FIN 370 or 371 or 380 or 465 or 466" and Claude produces:

```json
{
  "id": "fin_elective",
  "requirement": "Financial Electives",
  "rule_type": "choose_one_of",
  "options": ["FIN 370", "FIN 371", "FIN 380", "FIN 465", "FIN 466"],
  "pattern": null,
  "pairs": null,
  "credits_needed": 3.0,
  "category": "major"
}
```

Note how Claude correctly propagates the "FIN" prefix to "371", "380", "465", and "466". This is the most error-prone part of parsing -- the VISION_AUDIT_PROMPT includes a worked example specifically for this case.

FIN 4XX as `wildcard` -- the audit says "Still needed: 1 Class in @ 4@ with attribute = FIN" and Claude produces:

```json
{
  "id": "fin_400_level",
  "requirement": "400 Level Finance",
  "rule_type": "wildcard",
  "options": [],
  "pattern": "FIN 4XX",
  "pairs": null,
  "credits_needed": 3.0,
  "category": "major"
}
```

Claude translates the Degree Works `@` wildcard syntax into Pathfinder's `XX` format. The expander will later resolve `FIN 4XX` against the catalog to find FIN 412, FIN 414, FIN 458, FIN 460, FIN 465, FIN 466, and FIN 475.

Science Lab as `course_with_lab` -- the audit lists "2 Classes in SCI 251 and L251" for each valid pair:

```json
{
  "id": "science_lab",
  "requirement": "Science and Lab Requirement",
  "rule_type": "course_with_lab",
  "options": [],
  "pattern": null,
  "pairs": [
    ["SCI 251", "SCI L251"],
    ["SCI 262", "SCI L262"],
    ["SCI 264", "SCI L264"]
  ],
  "credits_needed": 4.0,
  "category": "general_education"
}
```

(Abbreviated to 3 of 10 pairs for clarity.)

---

### What Happens After Parsing

The validated `DegreeAudit` flows to two consumers:

1. **The preferences page** reads `outstanding_requirements` and renders a checklist. Owen sees 16 requirements grouped by category. He selects which ones to schedule for Fall 2026 and sets preferences (target credits, blocked days, time windows).

2. **The generate-schedules endpoint** receives the full `DegreeAudit` along with `SchedulePreferences`. The requirement expander uses each outstanding requirement's `rule_type`, `options`, `pattern`, and `pairs` to find candidate sections in `sections.json`.

For Owen's `fin_310` requirement, the expander finds 3 sections: FIN 310 A (CRN 1045, Kumar), FIN 310 B (CRN 1046, Kumar), FIN 310 C (CRN 1047, TBA). For his `fin_elective`, it finds 9 sections across FIN 370, FIN 380, FIN 465, and FIN 466. The solver takes these candidate lists and generates every valid combination, filtering out time conflicts.

---

### Error Scenarios

| Scenario | What happens | Retry? |
|----------|-------------|--------|
| Claude returns trailing comma in JSON | `json.JSONDecodeError` caught, second attempt made | Yes |
| Claude wraps JSON in markdown fences | `_parse_json_response()` strips fences before parsing | No (handled first try) |
| Claude returns unknown `rule_type` | Pydantic `Literal` validation fails, retry triggered | Yes |
| API key missing or invalid | `AuthenticationError` propagated immediately, 500 returned | No |
| Blurry or cropped screenshot | Claude omits unreadable fields, Pydantic fails, retry unlikely to help | Yes (then fails) |
