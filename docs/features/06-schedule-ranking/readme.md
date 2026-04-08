# Feature 06 — Schedule Ranking

After the constraint solver returns three valid, conflict-free schedules, Claude writes natural-language explanations and performs a qualitative re-ranking. This is the only place in the pipeline where Claude's output affects which schedule the student sees first.

## The division of labor

The solver ranks by numeric score. It knows that a schedule has 15 credits, 3 distinct categories, and all sections with >50% seats open. But it cannot tell the student: "This schedule gives you Tuesdays and Fridays off and loads your four MR classes back-to-back from 9:35 to 14:00, so you're done by lunch on two days a week."

Claude adds that qualitative layer. It names the professors, mentions which days are free, calls out which requirement categories get knocked out, and flags any soft factors the scoring function misses — like the difference between a MR-heavy schedule and a schedule spread evenly across the week.

## Bounded re-ranking

Claude can reorder the three schedules but cannot inject new ones. The solver's correctness guarantees are never violated. Claude sees three already-valid options and decides which one a student would probably prefer, given context the scoring function cannot capture.

## Code

| File | Role |
|---|---|
| `backend/app/claude_client.py` | `explain_schedule()` and `rank_schedules()` functions |
| `backend/app/prompts.py` | `EXPLAIN_SCHEDULE_PROMPT` and `RANK_SCHEDULES_PROMPT` constants |
| `backend/app/models.py` | `ScheduleOption` (holds the explanation and final rank) |

## Claude model

All calls use `claude-sonnet-4-5-20250514`. The model is defined as a constant in `claude_client.py`.

## AIE documentation

- [1-align.md](1-align.md) — Why Claude explains and re-ranks after the solver
- [2-construct.md](2-construct.md) — The two prompts, their inputs, outputs, and temperatures
- [3-execute.md](3-execute.md) — Step-by-step flow with a real example
