# CLAUDE.md — Claude Code Configuration for BryantPathfinder

> This file tells Claude Code everything it needs to know to work on this project effectively. Read this first when starting a new session.

---

## Project Identity

**Name:** BryantPathfinder
**Tagline:** The missing layer between Degree Works and Banner.
**One-liner:** An AI course scheduling assistant that reads your Degree Works audit, knows the full Bryant course catalog, and generates conflict-free class schedules in seconds.

**Builder:** Owen Ash — sophomore Finance major at Bryant University.
**Built for:** Bryant University AI Hack-a-thon, April 8, 2026.
**Repo:** github.com/Oman6/bryantpathfinder

---

## The Core Insight

Pathfinder uses Claude where language and perception matter, and deterministic Python where combinatorial correctness matters. **This split is non-negotiable.** Do not ask Claude to generate a schedule. Do not ask Python to write an explanation paragraph. Each tool stays in its lane.

- **Claude parses** the messy Degree Works screenshot (Vision)
- **Claude explains** the finished schedules in plain English
- **Claude ranks** three valid candidates by fit to student preferences
- **Python expands** `FIN 4XX` into a real list of courses
- **Python detects** time conflicts with deterministic math
- **Python searches** the combination space and returns valid schedules
- **Python scores** schedules on credit match, preference fit, and seat availability

This decision is documented in detail in `docs/adr/0003-deterministic-solver-vs-llm.md`. If you find yourself tempted to have Claude do the scheduling math, re-read that ADR first.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Python 3.12, Pydantic v2 |
| AI | Anthropic Claude (claude-sonnet-4-5) via the official Python SDK |
| Data | Static JSON loaded at startup — `sections.json` (291 Bryant Fall 2026 sections) |
| State | Zustand on the frontend, in-memory on the backend |
| Icons | `@phosphor-icons/react` (light weight only) |
| Fonts | Instrument Serif (display), Geist (UI), Geist Mono (data) via `next/font/google` |

---

## Build Order

When starting a fresh build from scratch, follow this order. Each step depends on the previous one.

1. **Parse the raw data.** Run `backend/scripts/parse_banner_dump.py` to produce `data/sections.json`. Run `backend/scripts/parse_degree_audit.py` to produce `data/fixtures/audit_owen.json`. Verify the section count is 291.
2. **Write the Pydantic models** at `backend/app/models.py`. These are the source of truth for every data contract in the system.
3. **Write the constraint solver** at `backend/app/solver.py`. Start with conflict detection, then combination generation, then scoring. No Claude calls in this file.
4. **Write the Claude prompts** at `backend/app/prompts.py`. Three constants: `VISION_AUDIT_PROMPT`, `EXPLAIN_SCHEDULE_PROMPT`, `RANK_SCHEDULES_PROMPT`.
5. **Build the FastAPI routes** at `backend/app/main.py`. Three endpoints: `/api/parse-audit`, `/api/generate-schedules`, `/api/health`. Use the lifespan context manager to load sections.json once at startup.
6. **Scaffold the Next.js frontend.** Install shadcn/ui, configure the fonts and Tailwind theme, read the design skills before writing any UI code.
7. **Build the three pages** in order: homepage with upload zone, preferences page, schedules page.
8. **Wire frontend to backend** and test the full flow with `audit_owen.json` as the fixture.
9. **Test the Vision parsing path** with a real Degree Works screenshot.
10. **Polish pass** — run `redesign-existing-projects` audit, fix any generic patterns, add loading and empty states.

---

## Design System — Non-Negotiable

Pathfinder has a specific aesthetic. **Before writing any frontend code, read these skills in order:**

1. `/mnt/skills/user/high-end-visual-design/SKILL.md`
2. `/mnt/skills/user/design-taste-frontend/SKILL.md`
3. `/mnt/skills/public/frontend-design/SKILL.md`
4. `/mnt/skills/user/minimalist-ui/SKILL.md`

### Locked aesthetic direction

- **Vibe:** Editorial minimalism, warm monochrome. Linear meets a school newspaper.
- **Background:** `#FAFAF7` (warm cream, not pure white)
- **Text:** `#1A1A1A` primary, `#787774` secondary
- **Accent:** `#B8985A` (Bryant gold) used only for primary CTAs and active states
- **Display font:** Instrument Serif for hero headlines
- **UI font:** Geist for body and interface text
- **Mono font:** Geist Mono for course codes (FIN 310), CRNs, and stat rows
- **Icons:** Phosphor Light from `@phosphor-icons/react`. Nothing else.
- **Layout:** Asymmetric. Massive typography on the left, interactive content on the right. Never center a hero.
- **Whitespace:** `py-24` to `py-32` between major sections. The layout breathes heavily.
- **Cards:** Double-bezel nested architecture from `high-end-visual-design`. Outer shell with hairline border, inner core with its own background and concentric radius.
- **CTAs:** Pill-shaped buttons with a button-in-button trailing arrow icon.
- **Motion:** Custom cubic-bezier easings (`cubic-bezier(0.32, 0.72, 0, 1)`). Scroll-triggered fade-ups with blur. Staggered reveals on the schedules page (delay-100, delay-200, delay-300).

### Banned

- `Inter`, `Roboto`, `Arial`, `Helvetica`, `Open Sans` as fonts
- `Lucide`, `Material Icons`, `FontAwesome` as icon libraries
- `shadow-md`, `shadow-lg`, `shadow-xl` (use ultra-diffuse custom shadows only)
- Purple or blue gradients anywhere
- Centered hero sections
- `h-screen` (use `min-h-[100dvh]` to avoid iOS Safari viewport jumping)
- Emojis in code, markup, or copy
- AI copywriting clichés: "Elevate", "Seamless", "Unleash", "Next-Gen", "Game-changer"
- Generic placeholder names like "John Doe" or "Lorem Ipsum"
- `localStorage` or `sessionStorage` in any artifact (banned by the environment)

---

## Code Standards

### Python

- **Every function has type annotations.** Not optional. `def solve(audit: DegreeAudit, sections: list[Section]) -> list[ScheduleOption]:` — not `def solve(audit, sections):`.
- **Every class and every public function has a docstring.** Include Args, Returns, and Raises sections. The solver especially.
- **All request and response bodies are Pydantic models.** Never raw `dict`. Never `**kwargs` for external data.
- **All Anthropic API calls are wrapped in try/except** with specific exception handling. Retry once on malformed JSON; fail loudly on auth errors.
- **Use structured logging.** `logger.info("solver.completed", combinations=n, duration_ms=d)` — not `print()`.
- **No comments explaining what code does.** Good naming makes that unnecessary. Comments explain *why* a non-obvious decision was made.

### TypeScript

- **Strict mode on.** `"strict": true` in `tsconfig.json`. No `any` escape hatches.
- **Every API call is typed end-to-end.** The `api.ts` client matches the Pydantic models on the backend. Use shared types in `lib/types.ts`.
- **React components use functional form with explicit prop types.** `export function ScheduleCard({ schedule }: { schedule: ScheduleOption })` — not `React.FC`.
- **No inline styles.** Tailwind utility classes only, composed with `clsx` + `tailwind-merge` via a `cn()` helper.
- **State lives in Zustand or local `useState`.** Never prop-drill more than two levels.

### File layout

```
backend/
├── app/
│   ├── main.py                 # FastAPI routes
│   ├── models.py               # Pydantic models
│   ├── solver.py               # Constraint solver (no Claude calls)
│   ├── prompts.py              # Claude prompt constants
│   ├── claude_client.py        # Anthropic API wrapper
│   └── requirement_expander.py # DSL → candidate sections
├── scripts/
│   ├── parse_banner_dump.py
│   └── parse_degree_audit.py
├── requirements.txt
└── .env.example

frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── preferences/page.tsx
│   └── schedules/page.tsx
├── components/
│   ├── UploadZone.tsx
│   ├── ScheduleCard.tsx
│   ├── WeeklyCalendar.tsx
│   ├── CourseBlock.tsx
│   ├── EyebrowTag.tsx
│   └── PillButton.tsx
├── lib/
│   ├── api.ts
│   ├── store.ts
│   ├── types.ts
│   └── utils.ts
├── tailwind.config.ts
└── package.json
```

---

## Critical Gotchas

Things that will bite you if you forget them.

### The solver runs on a subset, not the full catalog

Do not feed all 291 sections into the solver at once. The requirement expander first filters down to the candidate sections for each selected requirement — typically 15 to 40 total — and the solver searches that space. Feeding the full catalog in turns a 300ms operation into a 30-second one.

### Time conflict detection uses half-open intervals

Two sections overlap if each starts strictly before the other ends. Do not use `<=` — back-to-back classes (one ending at 10:50 and another starting at 10:50) should NOT be flagged as conflicts. Bryant's block schedule is designed this way.

### Day encoding: Thursday is R, not T or Th

The solver uses `M, T, W, R, F` for Monday through Friday. T is Tuesday, R is Thursday. This is standard for Banner data. If you see `Th` or `Tu` in the codebase, it's a bug.

### Time normalization: async courses get `null`, not `"00:00"`

Async/online sections in the Banner data have `"00:00 AM - 00:01 AM"` as a sentinel. The parser converts these to `is_async=true` and `meetings=[]`. The solver skips them unless preferences explicitly allow async. Never store `"00:00"` as a real time.

### Multi-meeting sections are real

Some sections (FIN 371 AR, FIN 454) have two different meeting blocks per week — a regular MWR class block plus a Wednesday evening recitation, for example. The `meetings` field is a list because of this. The conflict detector must check all pairs across both sections' meeting lists.

### The Vision parser can fail

Claude Vision occasionally returns malformed JSON or hallucinates a requirement that isn't in the audit. The `/api/parse-audit` endpoint retries once on malformed JSON. For the hackathon demo, always have `audit_owen.json` loaded as a fallback via a "Use sample audit" button on the homepage. If Vision fails during the live demo, click the sample button and keep going.

### FastAPI lifespan loads sections.json once

The sections list is loaded in the lifespan context manager at startup, stored in the app state, and accessed from the routes. Don't re-load it on every request. Don't store it as a module-level global either — that breaks testing.

---

## Demo Path — What Has to Work

The demo is the thing that wins. If everything else is broken but the demo flow works cleanly, you're fine. If the code is beautiful but the demo crashes, you're done. Protect the demo path above all else.

**The happy path:**

1. Student lands on the homepage. Hero renders with the right fonts and aesthetic.
2. Student clicks "Use sample audit" (or uploads a real screenshot, but the sample button is the safe path).
3. Preferences page loads with Owen's parsed outstanding requirements visible.
4. Student toggles "No Friday classes" and sets target credits to 15.
5. Student clicks "Generate my schedules."
6. Within 2 seconds, three schedule cards appear on the schedules page, each with a weekly calendar grid and a Claude-generated explanation.
7. FIN 310 appears in at least one of the three schedules.
8. Student clicks "Use this schedule" on the top option.
9. A dialog shows the CRNs as copyable monospace text.

**If any step above breaks during the build, fix it before touching anything else.** Features that aren't on the demo path can wait.

---

## When You Get Stuck

**The solver returns zero schedules.** Check preferences — the student probably over-constrained the problem. Try with an empty preferences object and see if the solver returns anything.

**Vision parsing returns garbage.** Check the prompt in `prompts.py`. Verify the two worked examples are still in the prompt. Try with temperature 0. If it's still bad, use the fixture fallback.

**Frontend doesn't render correctly.** Re-read `/mnt/skills/user/high-end-visual-design/SKILL.md`. Ninety percent of frontend issues come from missing one of the rules in that skill — wrong font, wrong icon library, centered layout, pure white background.

**Backend crashes on startup.** Check that `data/sections.json` exists and is valid JSON. Check that `.env` has `ANTHROPIC_API_KEY` set. Run `uvicorn app.main:app --reload --port 8000` directly and read the stack trace.

**A test fails.** Good. Tests are working. Read the failure, fix the bug, move on.

---

## Don't Do This

- Don't add new features that aren't on the demo path. Scope is locked.
- Don't rewrite the solver to use an external optimization library. The pure-Python version is the right choice for the hackathon and it's fast enough.
- Don't add a database. Static JSON is the architectural decision.
- Don't add authentication. No one is logging in. The demo is a single fixture.
- Don't switch to another AI provider. Pathfinder is built with Claude, for a Claude hackathon.
- Don't change the design direction mid-build. Editorial minimalism is locked. Don't suddenly go brutalist at 1pm because it seems fun.
- Don't try to support the full 784-section Bryant catalog. The 291-section subset covers every course on Owen's audit.
- Don't ship without rehearsing the demo three times. Polished 90-second demos beat buggy 4-minute ones.

---

## The One Thing

If you can only do one thing in a session, **make the demo path work end to end.** Everything else is polish.
