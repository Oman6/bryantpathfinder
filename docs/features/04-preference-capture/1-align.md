# Feature 04 — Preference Capture: Align

> WHY do we capture preferences, and why in this specific way?

---

## The Problem

Students have strong opinions about their schedules. Ask any sophomore what matters to them during registration and you will hear some combination of: no Friday classes, nothing before 10am, avoid a specific professor, take the same instructor for lecture and lab, keep Wednesdays open for club meetings, get to 15 credits exactly.

These preferences constrain the solver's search space and influence its scoring function. Without them, the solver would return three technically valid schedules — conflict-free and requirement-satisfying — but schedules the student would never actually register for. A schedule with 8am classes on all five days that perfectly satisfies degree requirements is useless if the student refuses to wake up before 10.

The challenge is capturing both **structured constraints** (the solver can enforce mechanically) and **fuzzy preferences** (only a language model can interpret).

---

## Two Types of Preferences

### Hard constraints narrow the search space

When Owen says "no Friday classes," every section that meets on Friday must be excluded from the candidate pool before the solver begins its combinatorial search. This is not a scoring preference — it is an absolute constraint. Including Friday sections and penalizing them would waste solver time evaluating combinations that Owen will never accept.

Hard constraints include:
- **Blocked days.** Any day in `["M", "T", "W", "R", "F"]`. Sections meeting on a blocked day are removed.
- **Time window.** `no_earlier_than` and `no_later_than` define an acceptable window. A section starting at 08:00 when `no_earlier_than = "10:00"` is excluded.

These constraints are applied by `filter_candidates_by_preferences()` in `solver.py`, which runs after the requirement expander and before the combination search.

### Soft constraints influence scoring

When Owen says "I prefer Kumar for finance," the solver should not exclude every non-Kumar section. Kumar might only teach FIN 310 Sections A and B. If those conflict with Owen's other courses, the solver needs non-Kumar options available. Instead, Kumar sections get a +5 score bonus, making them more likely to appear in the top three schedules.

Soft constraints include:
- **Preferred instructors.** +5 score per section taught by a preferred instructor.
- **Avoided instructors.** -10 score per section taught by an avoided instructor. The asymmetry is intentional — avoidance is a stronger signal than preference.
- **Target credits.** Combinations within 1 credit of the target get +10. The penalty scales linearly as the credit count diverges.

These are applied by `score_combination()` in `solver.py`, which runs after conflict checking.

### Free-text preferences are for Claude

Some preferences cannot be captured as structured fields. "I want to start the finance concentration" is a statement about academic strategy, not a time or instructor constraint. "I work Tuesday evenings" could be modeled as a hard constraint (block Tuesday after 17:00) but the student expressed it as natural language.

The `free_text` field captures these. The deterministic solver ignores it entirely. Claude reads it when writing explanation paragraphs and when performing the final ranking of the three candidate schedules. If the student wrote "I want to start the finance concentration" and one schedule includes FIN 310 while another does not, Claude will rank the FIN 310 schedule higher and explain why.

This split — structured fields for the solver, free text for Claude — is a direct application of Pathfinder's core design principle: Claude where language matters, Python where correctness matters.

---

## Why Not Just Use Free Text for Everything?

The tempting alternative: a single text box where the student types all their preferences, and Claude interprets everything. "No Fridays, nothing before 10, avoid Dr. Smith, target 15 credits, I want finance classes."

This was rejected for three reasons:

1. **Deterministic enforcement.** When Owen blocks Fridays, every Friday section must be excluded from the candidate pool. If Claude interprets "no Fridays" and occasionally misses one, Owen sees a schedule with a Friday class and loses trust. Structured fields give deterministic guarantees.

2. **Solver efficiency.** Hard constraints reduce the search space before the combinatorial explosion. Blocking Friday might remove 40% of candidate sections, shrinking the combination count from 25,000 to 5,000. If constraints are only applied at ranking time (after the solver has already evaluated all combinations), the solver does 5x more work for no benefit.

3. **Latency.** Calling Claude to interpret preferences before the solver runs adds 2-3 seconds of API latency. Structured fields are parsed in microseconds. Free text is only sent to Claude after the solver has already produced three candidates — it does not block the critical path.

The hybrid approach captures the best of both: structured fields for anything the solver can enforce mechanically, free text for everything else.

---

## Why Does the Student Select Requirements?

The `selected_requirement_ids` field is not a preference in the traditional sense — it is a scoping decision. Owen has 16 outstanding requirements but cannot take all 16 in one semester. He needs to pick 5 or 6 that fit his target credit load and his progression plan.

The preferences page shows all outstanding requirements from the parsed audit with toggles. Owen turns on the ones he wants to schedule this term. The solver only expands and evaluates the selected subset.

This design has three benefits:

1. **Reduces the search space.** 16 requirements with 5-10 sections each would produce a combination space in the billions. 5 requirements with 3-12 sections each produces thousands — well within the solver's 10,000-combination safety cap.

2. **Matches the advising workflow.** When Owen meets with his advisor, they discuss which courses to take next semester, not all remaining courses. The selection step mirrors that conversation.

3. **Enables the target credit constraint.** By selecting specific requirements, Owen implicitly targets a credit range. Five 3-credit courses target 15 credits. The solver uses `target_credits` to score combinations, but the student's selection is the primary mechanism for controlling semester load.

---

## Why Asymmetric Instructor Scoring?

Preferred instructors get +5. Avoided instructors get -10. The penalty for an avoided instructor is twice the reward for a preferred one.

This reflects how students actually feel about instructors. "I would like Kumar" is a mild preference — Owen is happy with Kumar but also fine with other instructors. "Avoid Dr. Smith" is a strong signal — Owen had a bad experience or heard negative reviews and does not want to be in that class. The asymmetry ensures that avoiding a bad instructor is weighted more heavily than seeking a good one.

The specific values (+5 and -10) were chosen to interact well with the other scoring dimensions. The credit match dimension has a max of +10, so a single avoided instructor (-10) can offset a perfect credit match. This is intentional: Owen would rather have 14 credits with a good instructor than 15 credits with an instructor he actively dislikes.

---

## Summary

Preference capture exists because valid schedules are not the same as good schedules. The solver can find hundreds of conflict-free combinations. The student's preferences narrow that set to schedules they would actually register for. Structured fields give the solver hard constraints and scoring inputs. Free text gives Claude context for ranking and explanation. The student's requirement selection controls the scope of the search. Together, these three layers turn an abstract optimization problem into a personalized recommendation.

---

## References

- `backend/app/models.py` — `SchedulePreferences` model definition
- `backend/app/solver.py` — `filter_candidates_by_preferences()` (hard constraints) and `score_combination()` (soft constraints)
- `backend/app/claude_client.py` — where `free_text` is passed to Claude
- `docs/adr/0003-deterministic-solver-vs-llm.md` — the Claude vs Python design split
- `ARCHITECTURE.md` — system overview and scoring function documentation
