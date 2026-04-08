# 06 Schedule Ranking — Construct

> WHAT are the two Claude calls, their inputs, outputs, and constraints?

---

## Overview

The schedule ranking feature makes two distinct Claude API calls, each with its own prompt template, temperature, and output format. Both prompts live as module-level string constants in `backend/app/prompts.py`. Both calls are made from `backend/app/claude_client.py`.

The model for all calls is `claude-sonnet-4-5-20250514`, defined as the `MODEL` constant in `claude_client.py`.

---

## Call 1: EXPLAIN_SCHEDULE_PROMPT

### Purpose

Generate a two-sentence explanation for a single schedule. Called once per schedule (3 times total for the top 3).

### Function signature

```python
def explain_schedule(
    schedule: ScheduleOption,
    preferences: SchedulePreferences,
    requirements_satisfied: list[str],
) -> str
```

### Input assembly

The function builds the prompt by formatting three JSON blocks into the template:

1. **schedule_json** — A list of section objects, each containing:
   - `course_code`, `title`, `section`, `instructor`
   - `meetings` (list of `{days, start, end}`)
   - `credits`, `seats_open`, `seats_total`

2. **preferences_json** — The full `SchedulePreferences` object serialized via `model_dump()`:
   - `target_credits`, `blocked_days`, `no_earlier_than`, `no_later_than`
   - `preferred_instructors`, `avoided_instructors`
   - `free_text`, `selected_requirement_ids`

3. **requirements_json** — A list of requirement ID strings (e.g., `["fin_310", "gen_201", "acg_203", "isa_201", "mkt_201"]`).

### Prompt template

The prompt instructs Claude to write exactly two sentences with these constraints:

- Name the professors by last name.
- Mention which days are free (if any).
- Mention which requirement categories get knocked out (major, gen ed, business core).
- If the schedule matches a stated preference, call it out.
- Mention seat availability if relevant.
- Tone: helpful upperclassman giving advice, not a marketing brochure. No exclamation points. No "This schedule offers..." or "You'll enjoy..." — just state the facts.

The prompt includes an example output:

> "This schedule gives you Fridays off and starts your finance concentration with Kumar for FIN 310, plus knocks out one gen ed and two business core requirements. All five sections still have seats, and nothing starts before 9:35."

### API call parameters

| Parameter | Value |
|---|---|
| model | `claude-sonnet-4-5-20250514` |
| max_tokens | 300 |
| temperature | 0.3 |
| system | (none — prompt is in the user message) |

Temperature 0.3 is deliberately nonzero to allow slight variation in phrasing across the three schedules. At temperature 0, all three explanations would use nearly identical sentence structures.

### Output

A plain string — the two-sentence paragraph. No JSON wrapping. No markdown. The string is stored in `ScheduleOption.explanation`.

### Error handling

If the API call fails (any `anthropic.APIError`), the function returns the fallback string `"Schedule explanation unavailable."` and logs the error. The schedule is still returned to the student — only the explanation is missing.

---

## Call 2: RANK_SCHEDULES_PROMPT

### Purpose

Rank three candidate schedules with a one-sentence rationale per schedule. Called once with all three schedules.

### Function signature

```python
def rank_schedules(
    schedules: list[ScheduleOption],
    preferences: SchedulePreferences,
) -> list[dict]
```

### Input assembly

The function builds a text summary for each schedule using `schedule_to_summary()`:

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

Three summaries are formatted into the prompt as Schedule A, Schedule B, and Schedule C, along with the student's preferences.

### Prompt template

The prompt instructs Claude to rank the three schedules 1, 2, 3 based on:

- How well each schedule matches stated preferences (blocked days, time windows, preferred instructors).
- Category balance (mixing major, gen ed, and business core is better than loading up on one category).
- Seat availability (more open seats = less risk of being closed out).
- Schedule compactness and quality of life (fewer gaps, reasonable start/end times).

### API call parameters

| Parameter | Value |
|---|---|
| model | `claude-sonnet-4-5-20250514` |
| max_tokens | 500 |
| temperature | 0 |
| system | (none — prompt is in the user message) |

Temperature 0 because the ranking should be deterministic. Given the same three schedules and preferences, Claude should return the same ranking every time.

### Output format

Claude returns a JSON object:

```json
{
  "rankings": [
    {"schedule": "A", "rank": 1, "rationale": "one sentence explaining why this is #1"},
    {"schedule": "B", "rank": 2, "rationale": "one sentence"},
    {"schedule": "C", "rank": 3, "rationale": "one sentence"}
  ]
}
```

The function extracts the `rankings` array and returns it.

### JSON parsing

The `_parse_json_response()` helper handles Claude's tendency to wrap JSON in markdown code fences:

```python
def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    return json.loads(cleaned)
```

### Error handling and retry

If JSON parsing fails on the first attempt (malformed response), the function retries once. After two failures, it raises a `ValueError`. This retry logic also applies to `KeyError` and `TypeError`, which catch cases where Claude returns valid JSON but in the wrong shape (e.g., missing the `rankings` key).

Authentication errors (`anthropic.AuthenticationError`) are raised immediately without retry.

---

## Bounded re-ranking contract

The re-ranking has a critical architectural constraint: Claude can reorder the three schedules but cannot inject new ones.

| Claude CAN | Claude CANNOT |
|---|---|
| Reorder schedules A, B, C to any permutation | Add a schedule D |
| Write a rationale explaining the ranking | Modify sections within a schedule |
| Disagree with the solver's numeric ranking | Override the conflict-free guarantee |
| Consider soft factors the scoring function misses | Remove a schedule from the results |

This constraint is not enforced in the prompt alone — it is enforced structurally. The `rank_schedules()` function passes three schedule summaries labeled A, B, C and expects back a JSON array with those same three labels. The calling code maps the labels back to the original `ScheduleOption` objects and updates their `rank` field. Even if Claude hallucinated a fourth schedule in the rationale text, it would have no structural effect.

---

## Token budget

### EXPLAIN_SCHEDULE_PROMPT

- Input: ~500-800 tokens (schedule JSON + preferences + requirements)
- Output: ~50-80 tokens (two sentences)
- max_tokens: 300 (generous ceiling to avoid truncation)

### RANK_SCHEDULES_PROMPT

- Input: ~1,200-1,800 tokens (three schedule summaries + preferences)
- Output: ~100-150 tokens (JSON with three ranking entries)
- max_tokens: 500 (generous ceiling)

### Total API cost per request

3 explain calls + 1 rank call = 4 Claude API calls per `/api/generate-schedules` request. At current Sonnet 4.5 pricing, this is approximately $0.02-0.04 per student request.

---

## Prompt iteration notes

The prompts were iterated during the build. Key changes:

1. **Added the "no exclamation points" rule.** Early versions of the explain prompt produced enthusiastic copy ("Great news! You get Fridays off!") that sounded like a marketing brochure. Adding the tone constraint fixed this.
2. **Added the example output.** Without a concrete example, Claude would write generic explanations ("This is a balanced schedule with good availability"). The example anchors the style: name professors, name days, name categories.
3. **Switched rank prompt to temperature 0.** Early versions at temperature 0.3 would occasionally produce different rankings on repeated calls with the same inputs, which made testing unreliable.
