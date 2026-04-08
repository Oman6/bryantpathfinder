# BryantPathfinder — Roadmap

> What was built in the hackathon, what comes next.

---

## Hackathon Build (April 8, 2026)

Everything below was built in a single day for the Bryant University AI Hack-a-thon.

### Completed

- **Banner catalog parser** — Parses the raw Fall 2026 Banner dump into 291 structured sections in `data/sections.json`.
- **Degree Works audit parser** — Parses Owen Ash's real Degree Works audit into `data/fixtures/audit_owen.json` with 16 outstanding requirements across four rule types.
- **Pydantic data models** — Full type-safe data contracts for Section, Meeting, DegreeAudit, OutstandingRequirement, SchedulePreferences, and ScheduleOption.
- **Requirement expander** — Expands all four rule types (specific_course, choose_one_of, wildcard, course_with_lab) into candidate sections from the catalog.
- **Pure Python constraint solver** — Generates every valid combination of sections, checks pairwise time conflicts with the half-open interval rule, scores on credit match / preference fit / seat availability / category balance, and returns the top 3 schedules.
- **Claude Vision audit parsing** — Upload a Degree Works screenshot, get structured JSON back via Claude Vision.
- **Claude schedule explanations** — Two-sentence natural-language explanations per schedule, naming professors and days off.
- **Claude schedule ranking** — Final 1-2-3 ranking of solver candidates with per-schedule rationale.
- **FastAPI backend** — Three endpoints: `/api/parse-audit`, `/api/generate-schedules`, `/api/health`.
- **Next.js frontend** — Three pages: homepage with upload zone, preferences capture, schedule display with weekly calendar grids.
- **Editorial minimalism design system** — Warm cream palette, Instrument Serif + Geist typography, Phosphor Light icons, double-bezel card architecture.

---

## Phase 2 — Production Path

These features turn Pathfinder from a hackathon demo into a real tool Bryant students use during registration.

### Live Banner Ethos Integration

Replace the static `sections.json` with a nightly sync from Ellucian's Banner Ethos REST API. Seat counts update every 15 minutes during the registration window. Students see real-time availability as they generate schedules.

**Why:** The hackathon snapshot freezes seat counts at April 7, 2026. During actual registration, seats change by the minute. Live data is the difference between a demo and a product.

### Supabase Persistence

Add Supabase Postgres for storing parsed degree audits, generated schedules, and student preferences across sessions. Students log in with their Bryant email via Supabase Auth + Google Workspace SSO.

**Why:** The hackathon build is stateless — every session starts fresh. Real students need their work to persist between advising meetings and registration windows.

### Prerequisite Checking

Extend the solver to respect prerequisite chains. FIN 310 requires FIN 201. FIN 312 requires FIN 310. The solver should never schedule a course the student hasn't completed the prerequisites for, even if Degree Works lists it as outstanding.

**Why:** Degree Works shows what you need, not what you're eligible for right now. A student could see FIN 312 on their outstanding list but not be eligible until they complete FIN 310 this semester.

### Multi-Semester Planning

Extend the solver to plan two to four semesters at a time, respecting prerequisite chains and course rotation patterns (some courses are only offered in Fall, some only in Spring). Show the student a roadmap to graduation, not just next semester.

**Why:** The biggest value Pathfinder can deliver is showing a student the fastest path to graduation. Single-semester scheduling is useful but doesn't answer the question students actually care about: "Am I on track?"

### Advisor Workflow

Add a separate advisor view where Kristina Anthony and other Bryant advisors can review, comment on, and pre-approve generated schedules before the student registers. Turn Pathfinder into a collaboration tool between student and advisor.

**Why:** Advisors are the expert in the loop. They know about course rotation, professor quality, and program-specific nuances that the solver doesn't. The advisor view is where institutional knowledge meets algorithmic scheduling.

### SyllabusIQ Integration (Phase 3)

Connect to SyllabusIQ (if built) to pull professor ratings, workload estimates, and grade distributions into the solver's scoring function. Students see not just whether a section fits their schedule, but whether the professor is a good match for their learning style.

**Why:** The most common complaint about course scheduling is not about time conflicts — it's about ending up with a professor whose teaching style doesn't work for you. Data-driven professor matching is the next layer of value after time-conflict resolution.

---

## Not Planned

These were considered and explicitly rejected for the foreseeable roadmap.

- **Mobile app.** The web app works on mobile browsers. A native app adds distribution complexity without clear value until the user base is large enough to justify it.
- **External optimization libraries (OR-Tools, PuLP).** The pure Python solver handles Bryant's problem size easily. External dependencies add complexity and failure surface for no performance benefit at this scale.
- **Support for non-Bryant universities.** The Degree Works DSL parsing is portable, but the Banner data integration and catalog structure are Bryant-specific. Multi-university support is a different product.
- **AI-generated course recommendations.** Pathfinder schedules courses the student already needs. Recommending electives or career paths is a different problem with different data requirements.
