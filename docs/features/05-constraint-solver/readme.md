# Feature 05 — Constraint Solver

The constraint solver is the heart of Pathfinder. It lives at `backend/app/solver.py` — roughly 250 lines of pure Python with no external optimization library. The only non-standard import is `itertools.product`.

Given a list of outstanding requirements, the full Fall 2026 section catalog (291 sections), and the student's preferences, the solver returns the top three valid, conflict-free schedules ranked by a multi-factor scoring function.

The solver guarantees correctness: every returned schedule is conflict-free. No LLM is involved in generating or validating schedules. Claude is called only after the solver finishes, to explain and re-rank the top three options.

## Why pure Python?

The natural impulse at an AI hackathon is to throw the scheduling problem at Claude. That approach produces output that looks right most of the time — and fails silently when it does not. An LLM-generated schedule has a nonzero probability of containing overlapping classes, and "looks right but is wrong" is the exact failure mode that destroys trust in software.

Pathfinder uses deterministic code for all scheduling math and reserves Claude for what it does best: parsing messy inputs, writing natural-language explanations, and making qualitative ranking judgments. See ADR 0003 (`docs/adr/0003-deterministic-solver-vs-llm.md`) for the full rationale.

## Key properties

- **Deterministic.** Same inputs produce the same outputs every time. No temperature, no variability, no prompt sensitivity.
- **Fast.** Well under one second for typical inputs (5 requirements, 3-12 sections each). The safety cap at 10,000 combinations prevents pathological blowups.
- **Debuggable.** When a schedule does not appear, you can set a breakpoint and inspect exactly which combinations were generated, which failed conflict detection, and why the top candidates scored where they did.
- **Correct by construction.** Every combination is pairwise-checked for time conflicts before scoring. The solver either returns valid schedules or returns nothing.

## Algorithm summary

1. Expand each selected requirement into candidate sections (filtering out full, async, and preference-violating sections).
2. Generate every combination of one section per requirement using `itertools.product`.
3. For each combination, check pairwise time conflicts using half-open intervals.
4. Score each valid combination on credit match, preference fit, seat availability, and category balance.
5. Deduplicate by CRN set, sort by score, return the top 3.

## Conflict detection

The solver uses the half-open interval rule to determine whether two sections overlap:

```
a_start < b_end AND b_start < a_end
```

This means back-to-back classes do NOT conflict. A section ending at 10:50 and another starting at 10:50 are correctly identified as non-overlapping. Bryant's standard block schedule is designed around this principle, with 20-minute gaps between standard blocks (e.g., Block 2 ends at 10:50, Block 3 starts at 11:10).

The conflict check handles multi-meeting sections by iterating over all pairs of meetings across two sections. If any pair overlaps on a shared day, the sections conflict.

## Scoring dimensions

The solver scores each valid schedule on four dimensions:

| Dimension | Points | Description |
|---|---|---|
| Credit match | +10 max | Full points if within 1 credit of `target_credits`. Scales down by 2 per credit of distance. |
| Preferred instructors | +5 each | Case-insensitive substring match against `preferences.preferred_instructors`. |
| Avoided instructors | -10 each | Asymmetric penalty — avoiding a bad professor matters more than getting a good one. |
| Seat availability | +1 each | Per section with >50% seats open. Nudges toward sections less likely to close. |
| Category balance | +3 each | Per distinct requirement category covered (major, business_core, general_education). |

A typical five-course schedule scores in the 20-35 range.

## Search space

For Owen's typical input (5 requirements, 1-12 sections each after filtering), the product space is 1,000-3,000 combinations. The solver evaluates all of them in under 300ms.

The `MAX_COMBINATIONS = 10,000` safety cap protects against pathological cases. If a student selects 8 requirements each with 6 sections, the product space is 1.7 million — the cap cuts evaluation at 10,000 and logs a warning. In practice, the cap rarely triggers because students typically select 5-6 requirements per semester.

## Requirement expansion

Before the solver runs, each requirement is expanded into candidate sections by `requirement_expander.py`. The expansion logic varies by rule type:

| Rule type | Example | Expansion |
|---|---|---|
| `specific_course` | FIN 310 | Find all sections where `course_code == "FIN 310"` |
| `choose_one_of` | FIN 370 or 371 or 380 | Find sections matching any option in the list |
| `wildcard` | FIN 4XX | Match `subject == "FIN"` and `course_number` starts with "4" |
| `course_with_lab` | SCI 251 + L251 | Find all (lecture, lab) pairs and return tuples |

Full sections and async sections are excluded by default.

## Data flow

```
POST /api/generate-schedules
  │
  ├── Parse request body (DegreeAudit + SchedulePreferences)
  │
  ├── Load sections.json (291 sections, loaded once at server startup)
  │
  ├── solve(outstanding_requirements, all_sections, preferences)
  │     ├── Expand requirements
  │     ├── Filter by hard constraints (blocked days, time windows)
  │     ├── itertools.product -> pairwise conflict check -> score
  │     └── Return top 3 ScheduleOption objects
  │
  ├── Claude: explain_schedule() x 3
  ├── Claude: rank_schedules() x 1
  │
  └── Return GenerateSchedulesResponse
```

## Files

| File | Role |
|---|---|
| `backend/app/solver.py` | The solver implementation (~250 lines) |
| `backend/app/models.py` | `Section`, `ScheduleOption`, `SchedulePreferences`, `OutstandingRequirement` |
| `backend/app/requirement_expander.py` | Expands requirements into candidate sections (~155 lines) |

## AIE documentation

- [1-align.md](1-align.md) — Why the solver exists and why it is pure Python
- [2-construct.md](2-construct.md) — The `solve()` function, conflict detection, and scoring
- [3-execute.md](3-execute.md) — Worked example with Owen's real data
