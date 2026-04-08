# 06 Schedule Ranking — Align

> WHY does Claude explain and re-rank the solver's output?

---

## The gap between scores and understanding

The solver's scoring function outputs a number. A schedule might score 24.0 — composed of +10 for credit match, +5 for seat availability, +9 for category balance, and +0 for instructor preferences. That number is useful for sorting candidates, but it tells the student nothing about what the schedule actually feels like.

Students do not think in scoring dimensions. They think in concrete terms:

- "Do I have Fridays off?"
- "Who's teaching my finance class?"
- "When do I start? When am I done?"
- "Am I knocking out gen eds or just stacking business core?"
- "Are the classes spread across the week or crammed into two days?"

A numeric score cannot answer these questions. Natural language can. That is why Claude writes a two-sentence explanation for each schedule — it translates the abstract score into the specific, concrete terms students actually care about.

## Why the solver cannot do this alone

The scoring function captures four dimensions: credit match, instructor preferences, seat availability, and category balance. These are the dimensions that can be computed deterministically from structured data. But there are soft factors the scoring function deliberately does not try to quantify:

### Schedule shape

A schedule where all five classes are on MR from 09:35 to 17:10 is mechanically valid and might score identically to a schedule spread across MWR. But the MR-only schedule means Owen is in class for 7.5 hours straight on two days, while the spread schedule gives him shorter days. Claude can see this and comment on it. The scoring function would need a complex "compactness" metric that is hard to get right without over-fitting.

### Professor reputation

Owen listed "Kumar" as a preferred instructor, but the scoring function only knows whether Kumar appears in the schedule (+5) or not (+0). Claude can add context: "You get Kumar for FIN 310, who teaches both sections of Intermediate Corporate Finance this semester" or "Kumar was filtered out because both sections meet on Friday." The explanation makes the trade-off visible.

### Requirement strategy

Three business core courses and one major course is a different semester experience than two gen eds and two major courses. The category balance score treats both as "+3 per distinct category," but Claude can articulate the strategic implication: "This schedule front-loads your business core so you can focus on concentration courses next semester."

### Day structure

"Tuesdays and Fridays off" and "Wednesdays and Fridays off" are both "2 days off," but they create very different weekly rhythms. Claude can name the specific days.

## Why Claude re-ranks

The solver's numeric ranking is a reasonable first pass. But the scoring function's weights are fixed and generic — they do not adapt to individual student preferences beyond the explicit fields in `SchedulePreferences`.

Claude's re-ranking acts as a qualitative second pass. Given all three schedules and the student's preferences (including the free-text field, which the solver ignores entirely), Claude can make judgment calls:

- A schedule with slightly lower seat availability but a much better day structure might deserve rank 1.
- A schedule that happens to include the student's preferred professor, even if the score bonus was small, might matter more to the student than the solver's weights suggest.
- A schedule where all classes are back-to-back with no gaps might be preferable to one with a 3-hour gap in the middle, even though the scores are close.

The re-ranking is bounded. Claude can reorder the three schedules but cannot inject a fourth schedule, modify any section in a schedule, or override the conflict-free guarantee. The solver owns correctness; Claude owns presentation and qualitative judgment.

## The trust equation

This architecture creates a specific trust model:

1. **The solver is always right.** Every schedule it returns is conflict-free. No exceptions. No probability of error. The student can register for any returned schedule with confidence.
2. **Claude is always helpful.** The explanations are specific, concrete, and name real professors and real days. The student reads the explanation and immediately understands what the schedule will feel like.
3. **Neither layer is asked to do the other's job.** The solver does not try to write English. Claude does not try to solve combinatorial problems. Each system operates in its zone of reliability.

This is the same principle as ADR 0003: Claude where it shines, Python where it must be correct.

## The alternative: no Claude layer

Without the ranking feature, Pathfinder would return three schedules sorted by numeric score, each displayed as a raw list of sections. The student would have to:

1. Read five rows of course/time/instructor data per schedule.
2. Mentally compute which days are free.
3. Figure out which requirement categories are covered.
4. Compare across three options.
5. Make a decision without any qualitative guidance.

This is strictly worse than the current design. The two-sentence explanation does that mental work for the student in plain English, and the re-ranking ensures the best overall option appears first.

## References

- `backend/app/claude_client.py` — the `explain_schedule()` and `rank_schedules()` functions
- `backend/app/prompts.py` — the prompt templates
- `docs/adr/0003-deterministic-solver-vs-llm.md` — the broader principle
- [2-construct.md](2-construct.md) — the prompt specifications
- [3-execute.md](3-execute.md) — a worked example
