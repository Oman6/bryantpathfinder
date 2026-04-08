# BryantPathfinder — API Reference

> REST endpoint documentation for the FastAPI backend. Base URL: `http://localhost:8000`.

---

## POST /api/parse-audit

Parse a Degree Works audit screenshot into structured JSON using Claude Vision.

### Request

```json
{
  "image_base64": "iVBORw0KGgoAAAANSuhEUgAA..."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image_base64` | `string` | Yes | Base64-encoded PNG, JPEG, or PDF of the Degree Works audit. |

### Response (200)

Returns a full `DegreeAudit` object.

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
    }
  ],
  "in_progress_requirements": [
    {
      "requirement": "Macroeconomic Principles",
      "course": "ECO 114",
      "grade": "REG",
      "credits": 3.0,
      "term": "Spring 2026"
    }
  ],
  "outstanding_requirements": [
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
  ]
}
```

### Errors

| Status | Condition |
|--------|-----------|
| `400` | Uploaded file is not a supported format (PNG, JPEG, PDF). |
| `422` | Claude returned malformed JSON after one retry. |
| `500` | Anthropic API authentication or rate limit error. |

### curl Example

```bash
# Encode a screenshot and parse it
BASE64=$(base64 -w0 degree_works_screenshot.png)
curl -X POST http://localhost:8000/api/parse-audit \
  -H "Content-Type: application/json" \
  -d "{\"image_base64\": \"$BASE64\"}"
```

---

## POST /api/generate-schedules

Generate three ranked, conflict-free schedules from a parsed degree audit and student preferences.

### Request

```json
{
  "audit": {
    "student_id": "001118725",
    "name": "Owen Ash",
    "major": "Finance",
    "expected_graduation": "May 2029",
    "credits_earned_or_inprogress": 42,
    "credits_required": 120,
    "completed_requirements": [],
    "in_progress_requirements": [],
    "outstanding_requirements": [
      {
        "id": "fin_310",
        "requirement": "Intermediate Corporate Finance",
        "rule_type": "specific_course",
        "options": ["FIN 310"],
        "pattern": null,
        "credits_needed": 3.0,
        "category": "major"
      }
    ]
  },
  "preferences": {
    "target_credits": 15,
    "blocked_days": ["F"],
    "no_earlier_than": "10:00",
    "no_later_than": null,
    "preferred_instructors": [],
    "avoided_instructors": [],
    "free_text": "I want to start the finance concentration",
    "selected_requirement_ids": ["fin_310", "gen_201", "acg_203", "isa_201", "mkt_201"]
  }
}
```

### Response (200)

```json
{
  "schedules": [
    {
      "rank": 1,
      "sections": [
        {
          "crn": "1045",
          "subject": "FIN",
          "course_number": "310",
          "course_code": "FIN 310",
          "title": "Intermediate Corporate Finance",
          "section": "A",
          "credits": 3.0,
          "instructor": "Kumar, Sonal",
          "meetings": [
            {
              "days": ["T", "F"],
              "start": "12:45",
              "end": "14:00",
              "building": null,
              "room": null
            }
          ],
          "seats_open": 18,
          "seats_total": 30,
          "is_full": false,
          "is_async": false,
          "schedule_type": "Lecture",
          "term": "Fall 2026"
        }
      ],
      "requirements_satisfied": ["fin_310", "gen_201", "acg_203", "isa_201", "mkt_201"],
      "total_credits": 15.0,
      "days_off": ["W", "F"],
      "earliest_class": "09:35",
      "latest_class": "15:35",
      "score": 24.0,
      "explanation": "This schedule gives you Fridays off and starts your finance concentration with Kumar, plus knocks out one gen ed and two business core requirements. All five sections still have seats."
    }
  ],
  "solver_stats": {
    "combinations_evaluated": 847,
    "valid_combinations": 12,
    "duration_ms": 340
  }
}
```

### Errors

| Status | Condition |
|--------|-----------|
| `422` | Preferences over-constrain the problem (zero valid schedules). Response includes a suggestion to loosen constraints. |
| `500` | Internal server error during solving or Claude API call. |

### curl Example

```bash
curl -X POST http://localhost:8000/api/generate-schedules \
  -H "Content-Type: application/json" \
  -d @request.json
```

---

## GET /api/health

Confirm the backend is running and the section catalog is loaded.

### Response (200)

```json
{
  "status": "ok",
  "sections_loaded": 291,
  "term": "Fall 2026",
  "anthropic_api": "reachable"
}
```

### curl Example

```bash
curl http://localhost:8000/api/health
```

---

## Error Response Format

All error responses follow this structure:

```json
{
  "detail": "Human-readable error message explaining what went wrong and how to fix it."
}
```
