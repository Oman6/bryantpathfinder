# 06 Schedule Ranking — Execute

> HOW does the Claude layer run after the solver returns three schedules?

---

## Starting point

The solver has returned three `ScheduleOption` objects from `solve()`. Each has:
- A list of sections (conflict-free, guaranteed)
- A numeric score
- Computed metadata (days off, earliest/latest class, total credits)
- An empty `explanation` field

The calling code in `POST /api/generate-schedules` now passes these to the Claude layer.

---

## Step 1: Format each schedule for the explain prompt

For each of the three schedules, the `explain_schedule()` function in `claude_client.py` extracts the sections data into a JSON list.

Example for Schedule A (Owen's top-scored option):

```json
[
  {
    "course_code": "FIN 310",
    "title": "Intermediate Corporate Finance",
    "section": "C",
    "instructor": "TBA",
    "meetings": [{"days": ["M", "R"], "start": "15:55", "end": "17:10"}],
    "credits": 3.0,
    "seats_open": 22,
    "seats_total": 30
  },
  {
    "course_code": "GEN 201",
    "title": "Intercultural Communication",
    "section": "D",
    "instructor": "Zammarelli, Thomas",
    "meetings": [{"days": ["M", "R"], "start": "11:10", "end": "12:25"}],
    "credits": 3.0,
    "seats_open": 18,
    "seats_total": 30
  },
  {
    "course_code": "ACG 203",
    "title": "Prin. of Financial Accounting",
    "section": "I",
    "instructor": "Beausejour, David",
    "meetings": [{"days": ["M", "R"], "start": "09:35", "end": "10:50"}],
    "credits": 3.0,
    "seats_open": 22,
    "seats_total": 30
  },
  {
    "course_code": "ISA 201",
    "title": "Intro to Information Tech and Analytics",
    "section": "H",
    "instructor": "Chaudhury, Abhijit",
    "meetings": [{"days": ["M", "R"], "start": "12:45", "end": "14:00"}],
    "credits": 3.0,
    "seats_open": 24,
    "seats_total": 30
  },
  {
    "course_code": "MKT 201",
    "title": "Foundations of Marketing Management",
    "section": "A",
    "instructor": "Bell-Lombardo, Hannah",
    "meetings": [{"days": ["W"], "start": "08:00", "end": "10:40"}],
    "credits": 3.0,
    "seats_open": 27,
    "seats_total": 30
  }
]
```

This JSON is inserted into the `EXPLAIN_SCHEDULE_PROMPT` template along with Owen's preferences and the list of satisfied requirement IDs.

---

## Step 2: Call Claude for each schedule explanation

Three API calls are made sequentially, one per schedule. Each call:

```python
message = client.messages.create(
    model="claude-sonnet-4-5-20250514",
    max_tokens=300,
    temperature=0.3,
    messages=[{"role": "user", "content": prompt}],
)
return message.content[0].text.strip()
```

### Example output for Schedule A

> This puts all four of your MR classes back-to-back from Beausejour at 9:35 through Chaudhury at 14:00, with Zammarelli for GEN 201 in between, leaving you Tuesdays and Fridays completely free. Bell-Lombardo's Wednesday morning MKT 201 is the only non-MR class, and all five sections have plenty of seats.

### Example output for Schedule B

> You get Fridays off with a lighter Monday/Thursday load, spacing Precourt's accounting section and Sousa's ISA 201 across midday, while Lenz's Wednesday marketing block fills the midweek gap. Three business core courses and one gen ed get knocked out alongside your FIN 310 concentration starter.

### Example output for Schedule C

> This schedule pushes your classes toward the afternoon, with nothing before 11:10 except Pasha's evening MKT 201 on Mondays and Thursdays, giving you mornings free four days a week. You cover one major, one gen ed, and three business core requirements, though the 17:30 start for marketing means a late Monday and Thursday.

Each explanation string is attached to the corresponding `ScheduleOption.explanation` field.

---

## Step 3: Format all three schedules for the rank prompt

The `rank_schedules()` function builds a text summary for each schedule. The summaries are more compact than the explain prompt's JSON because Claude needs to compare all three at once.

Example summary for Schedule A:

```
Total credits: 15
Days off: T, F
Time range: 09:35 - 17:10
Score: 24.0
Sections:
  - FIN 310 (Intermediate Corporate Finance) sec C - TBA - MR 15:55-17:10 - 22/30 seats
  - GEN 201 (Intercultural Communication) sec D - Zammarelli, Thomas - MR 11:10-12:25 - 18/30 seats
  - ACG 203 (Prin. of Financial Accounting) sec I - Beausejour, David - MR 09:35-10:50 - 22/30 seats
  - ISA 201 (Intro to Information Tech and Analytics) sec H - Chaudhury, Abhijit - MR 12:45-14:00 - 24/30 seats
  - MKT 201 (Foundations of Marketing Management) sec A - Bell-Lombardo, Hannah - W 08:00-10:40 - 27/30 seats
```

All three summaries and Owen's preferences are inserted into the `RANK_SCHEDULES_PROMPT` template.

---

## Step 4: Call Claude for ranking

One API call with temperature 0:

```python
message = client.messages.create(
    model="claude-sonnet-4-5-20250514",
    max_tokens=500,
    temperature=0,
    messages=[{"role": "user", "content": prompt}],
)
parsed = _parse_json_response(message.content[0].text)
return parsed["rankings"]
```

### Example ranking output

```json
{
  "rankings": [
    {
      "schedule": "A",
      "rank": 1,
      "rationale": "Back-to-back MR classes with Tuesdays and Fridays off is the most compact layout, and all five sections have strong availability."
    },
    {
      "schedule": "B",
      "rank": 2,
      "rationale": "Fridays off matches the stated preference and the class spread is reasonable, but the midweek gap is less efficient than Schedule A's MR block."
    },
    {
      "schedule": "C",
      "rank": 3,
      "rationale": "Late afternoon and evening classes give free mornings, but the 17:30 marketing section extends the day significantly and may conflict with extracurriculars."
    }
  ]
}
```

### JSON parsing

The `_parse_json_response()` helper strips markdown code fences if present. Claude sometimes wraps the JSON in ` ```json ... ``` ` even when instructed not to. The helper handles both cases transparently.

### Retry on parse failure

If `json.loads()` fails on the first attempt, the function retries the entire API call once. If the second attempt also fails, a `ValueError` is raised with the parse error details. In practice, `claude-sonnet-4-5` reliably produces valid JSON at temperature 0; the retry is a safety net.

---

## Step 5: Apply ranking and return

The calling code maps the ranking labels ("A", "B", "C") back to the original `ScheduleOption` objects and updates each one's `rank` field to match Claude's ordering.

Before ranking:
```
Schedule A: rank=1, score=24.0, explanation="This puts all four..."
Schedule B: rank=2, score=23.5, explanation="You get Fridays off..."
Schedule C: rank=3, score=22.0, explanation="This schedule pushes..."
```

After ranking (in this example, Claude agreed with the solver's order):
```
Schedule A: rank=1, score=24.0, explanation="This puts all four..."
Schedule B: rank=2, score=23.5, explanation="You get Fridays off..."
Schedule C: rank=3, score=22.0, explanation="This schedule pushes..."
```

If Claude had re-ranked — say, promoting B to rank 1 because Fridays off was an explicit preference — the rank fields would be updated but the schedules themselves remain unchanged.

The final list of three `ScheduleOption` objects is returned in the API response as `GenerateSchedulesResponse.schedules`.

---

## Timing breakdown

For a typical request with Owen's inputs:

| Step | Duration | Notes |
|---|---|---|
| Solver (`solve()`) | ~280ms | 1,540 combinations evaluated |
| Explain call 1 | ~800ms | Claude API round trip |
| Explain call 2 | ~800ms | Claude API round trip |
| Explain call 3 | ~800ms | Claude API round trip |
| Rank call | ~900ms | Slightly larger prompt |
| Total | ~3.6s | Dominated by 4 Claude API calls |

The solver accounts for less than 10% of the total response time. The Claude calls dominate. This is acceptable for a planning tool — the student submits preferences and waits a few seconds for results. If latency mattered more, the three explain calls could be parallelized with `asyncio.gather()`, reducing total time to ~2s.

---

## Error scenarios

### Claude API key missing or invalid

`explain_schedule()` returns `"Schedule explanation unavailable."` and the schedule is still returned. `rank_schedules()` raises `RuntimeError` with a message about the missing key. The API endpoint catches this and returns a 500 with diagnostic info.

### Claude returns malformed JSON (rank call)

First attempt fails, retry fires. If both attempts fail, `ValueError` is raised. The API endpoint catches this and falls back to the solver's original ranking (which is already a reasonable ordering by score).

### Rate limiting

If the Anthropic API returns a 429, the `anthropic.RateLimitError` is raised immediately (no retry). The API endpoint returns a 503 with a "try again in a moment" message.

### Solver returns fewer than 3 schedules

If the solver returns 1 or 2 schedules (because constraints are tight), the explain calls are made for however many exist. The rank call is skipped if there is only 1 schedule — ranking a single option is meaningless. If there are 2, the rank call is made with only schedules A and B.

---

## What the student sees

The frontend receives the final `GenerateSchedulesResponse`:

```json
{
  "schedules": [
    {
      "rank": 1,
      "sections": [...],
      "requirements_satisfied": ["fin_310", "gen_201", "acg_203", "isa_201", "mkt_201"],
      "total_credits": 15,
      "days_off": ["T", "F"],
      "earliest_class": "08:00",
      "latest_class": "17:10",
      "score": 24.0,
      "explanation": "This puts all four of your MR classes back-to-back..."
    },
    { "rank": 2, ... },
    { "rank": 3, ... }
  ],
  "solver_stats": {
    "combinations_evaluated": 1540,
    "valid_combinations": 47,
    "duration_ms": 280
  }
}
```

The explanation appears on each schedule card, directly below the weekly calendar grid. See [Feature 07 — Calendar UI](../07-calendar-ui/readme.md) for the frontend rendering.
