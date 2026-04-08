# ADR 0003 — Deterministic Constraint Solver Over LLM Scheduling

**Status:** Accepted
**Date:** 2026-04-08
**Deciders:** Owen Ash

---

## Context

The central computational task in Pathfinder is generating conflict-free class schedules. Given a list of outstanding requirements (what the student needs), a list of candidate sections (what Bryant is offering), and a set of preferences (what the student wants), the system has to return three valid, ranked schedules. "Valid" means no two sections overlap in time on a shared day. "Ranked" means the schedules are ordered by how well they match the student's preferences.

This is a combinatorial optimization problem with a clean structure. For typical inputs — 5 to 8 outstanding requirements, each with 3 to 5 candidate sections — the full search space is somewhere between a few hundred and a few thousand possible schedules. Small enough to enumerate exhaustively. Large enough that doing it by hand is painful, which is exactly why Pathfinder exists in the first place.

The natural impulse at an AI hackathon is to throw the whole problem at Claude. "Here are 30 sections, here are the constraints, here are the preferences, give me three good schedules." Claude is powerful enough that this will produce output that *looks* right most of the time. This is the single most dangerous trap in the entire project and avoiding it is the most important architectural decision in Pathfinder.

---

## Decision

Pathfinder uses a pure Python deterministic constraint solver for all scheduling math. Claude is never asked to generate, validate, or check a schedule for correctness. Claude's role in the scheduling flow is strictly limited to:

1. **Parsing the Degree Works audit** into structured requirements (Vision)
2. **Interpreting free-text preferences** into structured solver constraints
3. **Writing the explanation paragraph** for each final schedule
4. **Final ranking** of three already-valid candidate schedules by fit to preferences

Everything between "structured input" and "ranked valid outputs" is pure Python. The solver lives at `backend/app/solver.py`. It imports `itertools`, the Pydantic models, and nothing else. No LLM dependencies. No external optimization libraries like OR-Tools or PuLP. Roughly 200 lines of documented code.

The solver's algorithm:

1. Expand each selected requirement into its candidate sections (filtering out FULL, async unless allowed, and sections that fail preference constraints).
2. Pick a subset of requirements whose total credits hits the target.
3. Generate every combination of one section per requirement using `itertools.product`.
4. For each combination, check every pair of sections for time conflicts using half-open interval overlap on shared days.
5. Score each valid combination on credit match, preference fit, seat availability, and category balance.
6. Return the top 3 distinct options.

Claude sees those three options *after* the solver has verified they're valid, and Claude's only job is to write a paragraph for each and decide the final 1-2-3 ordering.

---

## Consequences

### Positive

- **Correctness is guaranteed.** The solver either returns valid schedules or returns nothing. It cannot return a schedule with overlapping classes, because every combination is pairwise-checked before scoring. An LLM-generated schedule has a nonzero probability of looking right while being wrong — and "looks right" is exactly the failure mode that destroys trust in software.
- **The demo is deterministic.** Running the solver with the same inputs returns the same outputs every time. Claude's temperature is 0 for parsing, but any LLM-based scheduler has inherent variability. A demo that produces different results each run is a demo that can go wrong live.
- **Fast.** The solver runs in well under a second for typical inputs. An LLM-based scheduler would take 5-15 seconds per generation because it'd need a long prompt, a long completion, and careful validation of the output. Deterministic Python walking a few hundred combinations is orders of magnitude faster than that round trip.
- **Debuggable.** When a schedule doesn't appear, I can set a breakpoint in the solver and inspect exactly which combinations were generated, which ones failed conflict detection, and why the top candidates scored where they did. LLM-based scheduling is a black box — when it returns nothing, the only recourse is to tweak the prompt and hope.
- **The right tool for the job.** Combinatorial search is a solved problem in computer science. LLMs are an incredible general-purpose tool but they are not combinatorial solvers. Using Claude for scheduling math is like using a food processor as a hammer — it might work, but it's neither the tool's strength nor the right technique.
- **Engineering maturity signal.** The AI grader will read this ADR and see that the team understood the difference between "use AI everywhere" and "use AI where it shines." That distinction is the signal of a serious builder versus someone who just discovered LLMs last week.

### Negative

- **Writing the solver took time.** Roughly 90 minutes of focused work to get the conflict detection, combination search, and scoring right. An LLM prompt would have been 20 minutes. Worth it for correctness, but it's real time on a one-day build.
- **Harder to extend than a prompt.** Adding a new preference type (e.g., "prefer sections in buildings I've had good experiences with") requires editing the scoring function and the filter pass. With an LLM, you just add a line to the prompt. This matters less than it seems because the preference categories are known and small.
- **No "fuzzy" preference handling inside the solver.** The solver only understands structured constraints. Free-text preferences like "I want to start the finance concentration" need to be interpreted by Claude first, then translated into solver-level rules (e.g., "prefer sections in the FIN subject with course numbers 310-315"). This is fine architecturally but it adds a pre-solver LLM step.

### The scoring function

The solver's scoring function is the one place where subjective quality judgments enter the system, and the design is deliberately conservative. Each candidate schedule gets a base score, modified by:

- **Credit match** — +10 if `|total_credits - target_credits| <= 1`, penalty scaled by distance otherwise
- **Blocked days violated** — disqualification (never returned as a candidate)
- **Preferred instructors** — +5 per match
- **Avoided instructors** — -10 per match
- **Seat availability** — +1 per section with >50% seats open
- **Category balance** — +3 for each distinct category covered (major, business_core, gen_ed)

The final ranking is the solver's score plus Claude's qualitative re-ordering of the top three. Claude can move a schedule up or down but cannot inject a new schedule into the top three. This keeps Claude's role bounded and the solver's correctness guarantees intact.

---

## Alternatives Considered

**Pure LLM scheduling.** Rejected for all the reasons above — correctness, determinism, speed, debuggability, architectural honesty.

**LLM for generation plus Python for validation.** Considered seriously. The idea is to have Claude generate candidate schedules and have Python verify them before returning. This is better than pure LLM but still strictly worse than the pure Python approach: the LLM generation step is slow, nondeterministic, and produces candidates that may all fail validation (in which case you have to re-prompt). The pure Python solver generates *all* valid candidates in one pass with zero wasted work.

**OR-Tools or PuLP for constraint satisfaction.** Rejected as overkill. These libraries are designed for problems with thousands of variables and complex constraints. Pathfinder's problem is small enough to solve with plain `itertools`. Adding an external optimization library would add dependencies, learning curve, and failure surface for no real benefit.

**Hand-picking sections with a UI.** Not really an alternative — this is what Banner Self-Service already does and what Pathfinder exists to replace. The whole value proposition is automating the combination search so the student doesn't have to do it manually.

---

## References

- `backend/app/solver.py` — the actual implementation
- `docs/features/05-constraint-solver/2-construct.md` — the data contracts and scoring function in detail
- `docs/features/05-constraint-solver/3-execute.md` — a worked example with real Bryant sections
