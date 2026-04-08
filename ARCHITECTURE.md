# BryantPathfinder — Architecture

> This document describes the full system design, data models, API contracts, and the architectural decisions that shape the codebase. If you're trying to understand how Pathfinder works end-to-end, start here.

---

## System Overview

Pathfinder is a three-tier application with a clean separation between language work (handled by Claude) and combinatorial work (handled by deterministic Python). The frontend is a thin client. The backend owns all the logic.

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend — Next.js 15 (browser)                                │
│                                                                 │
│  /                 Homepage + Degree Works upload zone          │
│  /preferences      Captures student preferences                 │
│  /schedules        Renders the three generated schedules        │
└──────────────────────────────┬──────────────────────────────────┘
                               │ REST + JSON
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Backend — FastAPI (Python 3.12)                                │
│                                                                 │
│  POST /api/parse-audit                                          │
│    → Claude Vision reads the screenshot                         │
│    → Returns a structured DegreeAudit object                    │
│                                                                 │
│  POST /api/generate-schedules                                   │
│    → Expands requirements into candidate sections               │
│    → Runs the pure-Python constraint solver                     │
│    → Calls Claude to explain and rank the top 3                 │
│    → Returns three enriched ScheduleOption objects              │
│                                                                 │
│  GET /api/health                                                │
│    → Confirms sections.json loaded and server is ready          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
             ┌─────────────────┴─────────────────┐
             ▼                                   ▼
┌──────────────────────────┐         ┌───────────────────────────┐
│  Anthropic API           │         │  Static JSON (in memory)  │
│  claude-sonnet-4-5       │         │                           │
│                          │         │  sections.json (291)      │
│  - Vision parsing        │         │  audit_owen.json (fixture)│
│  - Schedule ranking      │         │                           │
│  - Explanation writing   │         │  Loaded once at startup   │
└──────────────────────────┘         └───────────────────────────┘
```

---

## Core Design Principles

### 1. Claude where it shines, Python where it must be correct

The most important architectural decision in Pathfinder is the division of labor between Claude and deterministic code. LLMs are excellent at parsing messy inputs and writing natural-language explanations. They are unreliable at combinatorial correctness — ask Claude to generate a conflict-free schedule and it will occasionally return a schedule with overlapping classes. Ask Claude to rank three valid schedules and explain why one is best, and it nails it every time.

Pathfinder uses Claude for three things:

- **Parsing the Degree Works audit** (Vision) — taking a messy screenshot and producing clean structured JSON
- **Writing the explanation paragraphs** — taking a schedule and describing in plain English what makes it good
- **Final ranking** — choosing between three valid candidate schedules based on fuzzy student preferences

And uses deterministic Python for everything else:

- **Requirement expansion** — turning `FIN 4XX` into an actual list of courses
- **Conflict detection** — checking whether two sections overlap on time and day
- **Combinatorial search** — generating all valid schedules from the candidate pool
- **Scoring** — computing credit match, preference fit, and seat availability

This split is the core architectural insight of the project and is documented in detail in `docs/adr/0003-deterministic-solver-vs-llm.md`.

### 2. Static data for the hackathon, integration path for production

Pathfinder loads the entire Bryant Fall 2026 catalog from a static JSON file at server startup. No database. No Banner API calls at runtime. This is the correct choice for a one-day build because the data is frozen in time (the Fall 2026 catalog isn't changing tomorrow) and because it eliminates an entire category of failure modes.

The production path is documented in `docs/adr/0001-static-json-vs-database.md`: Pathfinder would integrate with Banner Ethos (Ellucian's REST API for Banner) to pull live seat counts nightly, and would store parsed degree audits and generated schedules in Supabase for persistence across sessions. The hackathon build is a snapshot of what the full product would look like.

### 3. The AIE documentation framework

Every feature in Pathfinder has its own folder under `docs/features/` with three files: `1-align.md`, `2-construct.md`, and `3-execute.md`. Align explains why the feature exists. Construct specifies what we're building — schemas, contracts, component boundaries. Execute walks through how it actually runs, step by step, with real worked examples. This pattern is applied consistently across all seven features in the system, giving any reader (human or AI) a predictable way to understand the codebase.

---

## The Data Model

### Section

A single offering of a course at a specific time, taught by a specific instructor, with a specific seat count. The atomic unit of scheduling.

```python
class Meeting(BaseModel):
    days: list[Literal["M", "T", "W", "R", "F"]]
    start: str  # "HH:MM" 24-hour
    end: str    # "HH:MM" 24-hour
    building: str | None
    room: str | None

class Section(BaseModel):
    crn: str                    # "1045"
    subject: str                # "FIN"
    course_number: str          # "310"
    course_code: str            # "FIN 310"
    title: str                  # "Intermediate Corporate Finance"
    section: str                # "A"
    credits: float              # 3.0
    instructor: str | None      # "Kumar, Sonal" or None for TBA
    meetings: list[Meeting]     # usually 1, sometimes 2
    seats_open: int
    seats_total: int
    waitlist_open: int
    waitlist_total: int
    is_full: bool
    is_async: bool              # true for online/async sections
    schedule_type: str          # "Lecture" | "Lab" | "Lecture/Lab"
    term: str                   # "Fall 2026"
```

### DegreeAudit

The parsed output of a Degree Works screenshot. Contains student metadata, completed requirements, in-progress requirements, and the outstanding requirements that Pathfinder will try to schedule.

```python
class CompletedRequirement(BaseModel):
    requirement: str            # "Student Success at Bryant Univ"
    course: str                 # "GEN 100"
    grade: str                  # "A"
    credits: float              # 1.0
    term: str                   # "Fall 2025"

class OutstandingRequirement(BaseModel):
    id: str                     # "fin_310"
    requirement: str            # "Intermediate Corporate Finance"
    rule_type: Literal["specific_course", "choose_one_of", "wildcard", "course_with_lab"]
    options: list[str]          # ["FIN 310"] or ["FIN 370", "FIN 371", ...]
    pattern: str | None         # "FIN 4XX" for wildcard rules
    credits_needed: float       # 3.0
    category: Literal["general_education", "business_core", "major", "elective", "minor"]

class DegreeAudit(BaseModel):
    student_id: str
    name: str
    major: str
    expected_graduation: str
    credits_earned_or_inprogress: int
    credits_required: int
    completed_requirements: list[CompletedRequirement]
    in_progress_requirements: list[CompletedRequirement]
    outstanding_requirements: list[OutstandingRequirement]
```

### SchedulePreferences

Captured from the student on the preferences page. A mix of structured toggles and free-text that Claude can interpret.

```python
class SchedulePreferences(BaseModel):
    target_credits: int = 15
    blocked_days: list[Literal["M", "T", "W", "R", "F"]] = []
    no_earlier_than: str | None = None      # "10:00"
    no_later_than: str | None = None        # "17:00"
    preferred_instructors: list[str] = []
    avoided_instructors: list[str] = []
    free_text: str = ""                     # "I want to start the finance concentration"
    selected_requirement_ids: list[str]     # which requirements to schedule this term
```

### ScheduleOption

One of the three schedules returned by the solver, enriched with a Claude-generated explanation.

```python
class ScheduleOption(BaseModel):
    rank: int                               # 1, 2, or 3
    sections: list[Section]                 # the chosen sections
    requirements_satisfied: list[str]       # requirement IDs this schedule fulfills
    total_credits: float
    days_off: list[str]                     # ["W", "F"]
    earliest_class: str                     # "09:35"
    latest_class: str                       # "15:35"
    score: float                            # solver's internal score
    explanation: str                        # Claude-generated 2-sentence paragraph
```

---

## The Degree Works Rule DSL

Degree Works stores its requirement rules in a compact DSL that Pathfinder parses at ingestion time. The four rule types cover every requirement in Owen's audit and almost every requirement in the Bryant Business Administration program.

| Degree Works syntax | Pathfinder rule_type | Example |
|---|---|---|
| `1 Class in COURSE` | `specific_course` | "1 Class in FIN 310" → options: ["FIN 310"] |
| `1 Class in A or B or C` | `choose_one_of` | "1 Class in FIN 370 or 371 or 380" → options: ["FIN 370", "FIN 371", "FIN 380"] |
| `1 Class in @ 4@ with attribute = FIN` | `wildcard` | pattern: "FIN 4XX" → expands to all 400-level FIN courses in sections.json |
| `2 Classes in SCI 251 and L251` | `course_with_lab` | pairs: [("SCI 251", "SCI L251")] — solver must pick both |

The wildcard syntax uses `@` as a single-character wildcard. `4@` means "any course number starting with 4" (i.e., 400-level). `2@` means "any 200-level course." The `with attribute = FIN` clause filters by course attribute (Finance elective, in this case). Pathfinder's expander walks the full sections.json catalog and returns every section whose `subject + course_number` matches the pattern and attributes.

This DSL is documented in detail in `docs/adr/0004-requirement-rule-dsl.md`.

---

## The Constraint Solver

The heart of Pathfinder. A pure Python module at `backend/app/solver.py`, about 400 lines, no external optimization library.

### Inputs

- The list of `OutstandingRequirement` objects (what the student still needs)
- The list of `Section` objects loaded from `sections.json` (what's being offered)
- The `SchedulePreferences` object (what the student wants)

### Algorithm

```
1. For each requirement the student selected, expand the options into a
   list of candidate Sections. Filter out sections that are FULL, async
   (unless preferences allow it), or that meet during blocked time ranges
   or on blocked days.

2. Pick a subset of requirements whose total credits is within ±3 of the
   target_credits preference. Start with the student's selected requirement
   IDs; if too many, drop the lowest-priority categories first.

3. For each subset, use itertools.product to generate every combination
   of one section per requirement.

4. For each combination, check for pairwise time conflicts. A conflict
   exists when two sections share at least one day and their time ranges
   overlap. Drop the combination if any conflict is found.

5. Score each valid combination on four dimensions:
     - Credit match: how close to target_credits
     - Preference fit: avoided instructors -20, preferred +10, etc.
     - Seat availability: higher is better
     - Category balance: reward combinations that mix major + gen ed + core

6. Sort by score, take the top 3 distinct options, return.
```

The search space per student is small in practice — five to ten candidate requirements with three to five sections each — so the solver runs in well under a second for typical inputs. An early termination cap at 10,000 combinations protects against pathological cases.

### Conflict detection

```python
def sections_conflict(a: Section, b: Section) -> bool:
    for meeting_a in a.meetings:
        for meeting_b in b.meetings:
            shared_days = set(meeting_a.days) & set(meeting_b.days)
            if not shared_days:
                continue
            a_start = to_minutes(meeting_a.start)
            a_end = to_minutes(meeting_a.end)
            b_start = to_minutes(meeting_b.start)
            b_end = to_minutes(meeting_b.end)
            if a_start < b_end and b_start < a_end:
                return True
    return False
```

Times are normalized to minutes since midnight for clean arithmetic. The overlap check uses the classic half-open interval rule: two ranges overlap if each starts strictly before the other ends.

---

## The Claude Layer

Pathfinder makes three distinct Claude API calls, each with its own prompt. All prompts live in `backend/app/prompts.py` as module-level string constants so they're easy to audit and iterate on.

### 1. VISION_AUDIT_PROMPT

Called from `POST /api/parse-audit`. The endpoint accepts a base64-encoded image or PDF of the Degree Works audit. The prompt instructs Claude to:

- Extract every requirement from the audit page
- Classify each as completed, in-progress, or outstanding
- For each outstanding requirement, identify the rule type (`specific_course`, `choose_one_of`, `wildcard`, or `course_with_lab`)
- Return strict JSON matching the `DegreeAudit` schema

The prompt includes two worked examples — one for a `specific_course` rule ("1 Class in FIN 310") and one for a `choose_one_of` rule ("1 Class in FIN 370 or 371 or 380 or 465 or 466") — so Claude has concrete templates to match. Temperature is 0 because we want deterministic parsing, not creative interpretation.

### 2. EXPLAIN_SCHEDULE_PROMPT

Called once per candidate schedule from `POST /api/generate-schedules` after the solver has returned the top three options. Given the schedule, the student's preferences, and the requirements it satisfies, Claude produces a two-sentence paragraph that names the professors, mentions the days off, and calls out which requirement categories get knocked out. The tone is direct and specific, not generic.

Example output:

> This schedule gives you Fridays off and starts your finance concentration with Kumar, plus knocks out one gen ed and two business core requirements. All five sections still have seats.

Temperature is 0.3 for a little variation in phrasing across the three schedules.

### 3. RANK_SCHEDULES_PROMPT

Called once with all three candidate schedules. Claude outputs the final ranking (which is #1, #2, #3) and a one-sentence rationale per schedule. This is the only place Claude's output affects which schedule the student sees first, and it only re-ranks among three already-valid options chosen by the deterministic solver. Claude never creates a schedule from scratch.

---

## API Contracts

### POST /api/parse-audit

**Request:**
```json
{
  "image_base64": "iVBORw0KGgoAAAANS..."
}
```

**Response:** A full `DegreeAudit` object (see schema above).

**Errors:**
- `422` if Claude returns malformed JSON after one retry
- `400` if the uploaded file isn't a supported format

### POST /api/generate-schedules

**Request:**
```json
{
  "audit": { ... DegreeAudit ... },
  "preferences": { ... SchedulePreferences ... }
}
```

**Response:**
```json
{
  "schedules": [
    { ... ScheduleOption rank 1 ... },
    { ... ScheduleOption rank 2 ... },
    { ... ScheduleOption rank 3 ... }
  ],
  "solver_stats": {
    "combinations_evaluated": 847,
    "valid_combinations": 12,
    "duration_ms": 340
  }
}
```

**Errors:**
- `422` if preferences over-constrain the problem (e.g., no Fridays AND no mornings AND no evenings leaves zero valid schedules). Response includes a suggestion to loosen specific constraints.

### GET /api/health

**Response:**
```json
{
  "status": "ok",
  "sections_loaded": 291,
  "term": "Fall 2026",
  "anthropic_api": "reachable"
}
```

### GET /api/sample-audit

Returns the pre-parsed fixture at `data/fixtures/audit_owen.json` as a `DegreeAudit` object. This is the demo fallback path — if Vision parsing fails during the live demo, the frontend calls this endpoint via the "Use sample audit" button.

**Response:** A full `DegreeAudit` object (identical schema to the `/api/parse-audit` response).

---

## Repository Structure

```
bryantpathfinder/
├── README.md              Product overview
├── ARCHITECTURE.md        This file
├── CLAUDE.md              Claude Code configuration
├── ROADMAP.md             What's built, what's next
│
├── docs/
│   ├── data-model.md      Canonical schemas
│   ├── api.md             REST endpoint reference
│   ├── demo-script.md     3-minute demo flow
│   ├── adr/
│   │   ├── 0001-static-json-vs-database.md
│   │   ├── 0002-claude-vision-for-degree-audit.md
│   │   ├── 0003-deterministic-solver-vs-llm.md
│   │   ├── 0004-requirement-rule-dsl.md
│   │   └── 0005-editorial-minimalism-design.md
│   └── features/
│       ├── 01-degree-audit-parsing/
│       ├── 02-banner-ingestion/
│       ├── 03-requirement-expansion/
│       ├── 04-preference-capture/
│       ├── 05-constraint-solver/
│       ├── 06-schedule-ranking/
│       └── 07-calendar-ui/
│
├── backend/
│   ├── app/
│   │   ├── main.py                FastAPI routes and lifespan
│   │   ├── models.py               Pydantic data models
│   │   ├── solver.py               Pure Python constraint solver
│   │   ├── prompts.py              Claude prompt strings
│   │   ├── claude_client.py        Anthropic API wrapper
│   │   └── requirement_expander.py DSL → candidate sections
│   ├── scripts/
│   │   ├── parse_banner_dump.py
│   │   └── parse_degree_audit.py
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── preferences/page.tsx
│   │   └── schedules/page.tsx
│   ├── components/
│   │   ├── UploadZone.tsx          Drag-and-drop audit upload
│   │   ├── ScheduleCard.tsx        Double-bezel card with calendar
│   │   ├── WeeklyCalendar.tsx      5-column grid Mon-Fri
│   │   ├── CourseBlock.tsx         Single section on the calendar
│   │   ├── EyebrowTag.tsx          Uppercase pill above headlines
│   │   └── PillButton.tsx          CTA with button-in-button arrow
│   ├── lib/
│   │   ├── api.ts
│   │   ├── store.ts                Zustand state store
│   │   ├── types.ts
│   │   └── utils.ts                cn() helper (clsx + tailwind-merge)
│   ├── tailwind.config.ts
│   └── package.json
│
└── data/
    ├── raw/
    │   ├── banner_fall2026_raw.txt
    │   └── degree_audit_owen.txt
    ├── sections.json               291 parsed sections
    └── fixtures/
        └── audit_owen.json         Owen's parsed degree audit
```

---

## Design System

Pathfinder uses editorial minimalism with a warm monochrome palette. The full design spec is enforced through the skills loaded in `CLAUDE.md`, but the core decisions are:

- **Background:** `#FAFAF7` (warm cream, not pure white)
- **Text:** `#1A1A1A` primary, `#787774` secondary
- **Accent:** `#B8985A` (Bryant gold) — one accent color only, used sparingly for primary CTAs
- **Display font:** Instrument Serif (hero headlines)
- **UI font:** Geist (body and interface)
- **Mono font:** Geist Mono (course codes, CRNs, timestamps)
- **Icons:** Phosphor Light only. No Lucide, no Material, no FontAwesome.
- **Layout:** Asymmetric 50/50 splits, never centered. `py-24`+ between sections.
- **Cards:** Double-bezel architecture — outer shell with hairline border, inner core with own background, concentric radii.
- **CTAs:** Pill-shaped with button-in-button trailing arrow icon.
- **Motion:** Custom cubic-bezier easings, scroll-triggered fade-ups, staggered reveals on the schedules page.

Pure white, Inter, Lucide icons, purple gradients, and `shadow-lg` are banned.

---

## Scaling Notes

Pathfinder is built for a hackathon and runs on a laptop. Here's what changes on the path to production.

**Data layer.** Replace the static `sections.json` with a nightly sync from Banner Ethos. Store in Supabase (Postgres) with indexes on `subject`, `course_code`, and `term`. Cache hot reads in memory on the backend.

**Authentication.** Add Supabase Auth with Bryant SSO via Google Workspace. Students log in with their Bryant email. Their degree audits, saved schedules, and preferences persist across sessions.

**Advisor workflow.** Add a separate advisor view where Kristina Anthony and other Bryant advisors can pre-approve or comment on generated schedules before the student registers. This turns Pathfinder into a collaboration tool, not a solo scheduler.

**Multi-semester planning.** Extend the solver to plan four semesters at a time, respecting prerequisite chains (e.g., FIN 310 must come before FIN 312) and course rotation (some courses are only offered in Spring).

**Real-time seat counts.** Poll Banner Ethos every 15 minutes during the registration window instead of relying on a nightly snapshot. Students see live seat availability as they generate schedules.

**Mobile app.** Wrap the frontend in Expo React Native for an iOS app students can use during advising meetings. The Vision parsing flow is especially natural on mobile — just snap a photo of the advisor's screen.
