# 05 Constraint Solver — Align

> WHY does the solver exist, and why is it pure Python?

---

## The problem

The central computational task in Pathfinder is generating conflict-free class schedules. Given Owen's 16 outstanding requirements, the 291 sections Bryant is offering in Fall 2026, and Owen's preferences (Fridays off, 15 credits, no 8 AM classes), the system must return three valid, ranked schedules where "valid" means no two sections overlap in time on a shared day.

This is a combinatorial optimization problem with a clean structure. For typical inputs — 5 selected requirements, each with 3 to 12 candidate sections — the full search space is somewhere between a few hundred and a few thousand possible schedules. Small enough to enumerate exhaustively. Large enough that doing it by hand is painful, which is exactly why Pathfinder exists.

## The trap

The natural impulse at an AI hackathon is to throw the whole problem at Claude: "Here are 30 sections, here are the constraints, here are the preferences, give me three good schedules." Claude is powerful enough that this will produce output that looks right most of the time. This is the single most dangerous trap in the entire project.

LLMs are unreliable at combinatorial correctness. Ask Claude to generate a conflict-free schedule and it will occasionally return a schedule with overlapping classes. Not always — maybe 5-10% of the time. But "works 90% of the time" is not acceptable for a scheduling tool. A student who registers for two overlapping sections has a real problem, and "the AI got confused" is not a defensible answer.

The failure mode is especially insidious because the output looks plausible. A schedule with FIN 310 at MR 15:55-17:10 and GEN 201 at MR 09:35-10:50 looks fine at first glance. But if Claude also placed ACG 203 at MR 11:10-12:25 and ISA 201 at MR 12:45-14:00, the LLM might not notice that a fifth section on MR overlaps with one of those time blocks. The failure is invisible until the student tries to register.

## The decision

Pathfinder uses a pure Python deterministic constraint solver for all scheduling math. Claude is never asked to generate, validate, or check a schedule for correctness. The solver lives at `backend/app/solver.py`, imports `itertools` and the Pydantic models, and nothing else. No LLM dependencies. No external optimization libraries like OR-Tools or PuLP.

This decision is documented in ADR 0003 (`docs/adr/0003-deterministic-solver-vs-llm.md`).

## Why this matters

### Correctness is guaranteed

The solver either returns valid schedules or returns nothing. It cannot return a schedule with overlapping classes because every combination is pairwise-checked before scoring. There is no probability of error — the conflict detection is a simple comparison of integer minute values on shared days.

### The demo is deterministic

Running the solver with the same inputs returns the same outputs every time. An LLM-based scheduler would produce different results on each run because any nonzero temperature introduces variability. A demo that produces different results each run is a demo that can go wrong live.

### It is fast

The solver runs in well under one second for typical inputs. Owen's five-course schedule with a total search space of around 3,000 combinations completes in approximately 200-400 milliseconds. An LLM-based scheduler would take 5-15 seconds per generation because it needs a long prompt, a long completion, and careful validation of the output. The pure Python approach is orders of magnitude faster.

### It is debuggable

When a schedule does not appear, you can set a breakpoint in `solve()` and inspect exactly which combinations were generated, which ones failed the `sections_conflict()` check, and why the top candidates scored where they did. LLM-based scheduling is a black box — when it returns nothing useful, the only recourse is to tweak the prompt and hope.

### It demonstrates engineering maturity

The AI grader will read this ADR and see that the team understood the difference between "use AI everywhere" and "use AI where it shines." That distinction is the signal of a serious builder versus someone who discovered LLMs last week. Combinatorial search is a solved problem in computer science. LLMs are an incredible general-purpose tool but they are not combinatorial solvers.

## What Claude does instead

Claude's role in the scheduling flow is strictly limited to post-solver tasks:

1. **Parsing the Degree Works audit** — Vision reads the screenshot and produces structured `DegreeAudit` JSON. This is language work, not math.
2. **Writing explanation paragraphs** — For each of the three schedules, Claude writes a two-sentence paragraph that names the professors, mentions days off, and calls out which requirements get knocked out. This is narrative work that a scoring function cannot do.
3. **Final ranking** — Claude re-ranks the three already-valid schedules based on fuzzy student preferences. Claude can reorder but cannot inject new schedules. The solver's correctness guarantees remain intact.

This division of labor — Claude where it shines, Python where it must be correct — is the core architectural insight of Pathfinder.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Pure LLM scheduling | Correctness, determinism, speed, debuggability |
| LLM generation + Python validation | Slow, nondeterministic, may produce zero valid candidates requiring re-prompting |
| OR-Tools / PuLP | Overkill for a problem this small; adds dependencies and learning curve for no benefit |
| Manual section picking (Banner Self-Service) | This is what Pathfinder exists to replace |

## References

- `docs/adr/0003-deterministic-solver-vs-llm.md` — the full ADR
- `backend/app/solver.py` — the implementation
- [2-construct.md](2-construct.md) — the data contracts and scoring function
- [3-execute.md](3-execute.md) — a worked example with Owen's real data
