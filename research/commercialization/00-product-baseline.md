# 00 — BryantPathfinder Product Baseline

> Self-contained briefing for the commercialization research swarm. Every other agent in this folder should treat this file as the canonical answer to "what is BryantPathfinder, today?" before doing external research.

---

## One-line description

BryantPathfinder is an AI course-scheduling assistant that ingests a student's Degree Works audit (screenshot or text), reasons over a university's course catalog, and returns three ranked, conflict-free schedules with weekly calendar visualizations, predicted GPA, professor ratings, workload estimates, and one-click `.ics` calendar export. It targets the workflow gap between the academic-audit system (Degree Works) and the registration system (Banner / SIS).

---

## Origin and current status

- Built solo by **Owen Ash** (sophomore Finance, Bryant University, class of 2029) for the **Bryant University AI Hack-a-thon, April 2026**.
- Initial build was ~6 hours of work; current state reflects post-hackathon iteration.
- Currently runs entirely **locally** on the developer's laptop (FastAPI on `:8001`, Next.js on `:3001`).
- **No production deployment, no live customers, no paid users, no incorporation.** This is a credible single-school prototype with a real data foundation, not a shipping SaaS product.

---

## What it does end-to-end (current capabilities)

1. **Ingest a Degree Works audit.** Two paths:
   - Image upload → Claude Vision (Sonnet 4.5) extracts unmet requirements into a structured `DegreeAudit` object.
   - Pasted text fallback / sample-audit fixture for demos.
2. **Capture preferences.** Target credits, blocked days, no-earlier-than / no-later-than time bounds, preferred / avoided instructors, free-text natural-language preferences, requirement selection.
3. **Expand requirements.** A small Python DSL turns rules like `"FIN 4XX"` or `"FIN 370 or 371 or 380"` into a list of candidate sections from the catalog.
4. **Solve constraints.** Pure Python solver (itertools.product over candidate sets, half-open-interval conflict detection) returns valid schedules. Operates on a filtered subset (~15–40 sections), not the full catalog.
5. **Rank top three.** Score by credit fit, preference fit, days-off, time-window match, professor preference, and seat availability.
6. **Enrich via multi-agent pipeline (parallel ThreadPoolExecutor, ~2 s end-to-end):**
   - **Professor Match Agent** — joins to scraped RateMyProfessors data (quality, difficulty, would-take-again, review tags).
   - **Workload Agent** — estimates weekly hours per course from historical grade-distribution data.
   - **Negotiator Agent** — when constraints over-constrain the problem, finds the smallest relaxation that yields feasibility ("drop no-Friday and 4 options open").
   - **Multi-Semester Agent** — projects 4 semesters ahead, respecting prereqs and rotation.
7. **Explain.** Claude (Sonnet 4.5) writes a one-paragraph rationale per schedule.
8. **Export.** Pin sections, swap individual sections in-place, copy CRNs, download RFC-5545 `.ics` for Google / Apple / Outlook calendars.

---

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 15 (App Router), TypeScript strict, Tailwind, shadcn/ui, Zustand, Phosphor icons |
| Backend | FastAPI, Python 3.12, Pydantic v2 |
| AI | Anthropic Claude (`claude-sonnet-4-5` for vision and explanation; `claude-haiku-4-5` available) via the official Anthropic Python SDK |
| Solver | Pure Python (no external optimization library) |
| Data store | Static JSON files at runtime (`sections.json`, `audit_owen.json`, `professor_ratings.json`, `grade_distributions.json`). **No database. No Supabase, despite what the swarm prompt says.** |
| State | Zustand on frontend, in-memory on backend |
| Auth | None — single-fixture demo |
| Deployment | None — local dev only |

> **Important correction for the research swarm:** the orchestrator prompt mentions Supabase. The repository does not currently use Supabase. There is no database. All data is static JSON loaded at FastAPI startup.

---

## Data foundation

| Asset | Coverage | Source |
|---|---|---|
| Course sections | 291 Bryant Fall 2026 sections | Scraped from Banner Self-Service |
| Professor ratings | 129 of 133 instructors (97%) | Scraped from RateMyProfessors GraphQL |
| Review tags | 110 instructors | RateMyProfessors |
| Grade distributions | A–F per course, historical | Scraped from Bryant grade-distribution PDFs |
| Reference audit | Owen's full Degree Works audit (16 outstanding requirements) | Hand-parsed |
| Walk-time data | Building-to-building time estimates (used for 11-min buffer warnings) | Manual |

**Coverage limitations:** Only Fall 2026, only Bryant, only the courses that appeared in the catalog window. ~93% of building/room fields are null because Bryant publishes those late. ~28% of non-FIN courses lack grade-distribution data. 16 LCS / LCC course options are missing from the lookup tables.

---

## Production-grade engineering hardening already done

This is unusual for a hackathon project and worth surfacing for the procurement-evaluation agents:

- **Type-safety end-to-end.** TypeScript strict on the frontend, Pydantic v2 on the backend, shared schemas.
- **Rate limiting.** In-memory per-IP sliding window (30 req/60s) on the three Claude-touching endpoints.
- **Prompt-injection defense.** Audit-text path strips delimiter tokens and wraps content in tagged data sections; explicit "treat as data, never as instructions" guard.
- **Input size limits.** 10MB image base64 cap; 20K char text cap.
- **CORS allowlist.** Configured origins, no `*`.
- **Global exception handler.** Returns generic 500 to avoid stack-trace leaks.
- **Accessibility (WCAG AA).** Contrast verified at 4.5:1, focus-trapped modals, aria-modal patterns, keyboard-navigable.
- **Structured logging.** No `print()`. Logger calls with structured kwargs.
- **Parallel Claude calls.** ThreadPoolExecutor for the three agent enrichments and explanation generation.

What is **not** done:
- No SOC 2 audit, no HECVAT response, no penetration test.
- No multi-tenancy, no isolation between institutions.
- No PII handling beyond the screenshot ingest path (the audit contains a student ID and name).
- No SSO, no Shibboleth/SAML, no LTI integration.
- No SIS write-back. Output is CRNs the student manually pastes into Banner.
- No data residency controls. Anthropic API is hit from the Python backend; audit content (which includes the student name and GPA) is sent to Anthropic for parsing and explanation.
- No retention/deletion policy. No audit log.
- No accessibility audit beyond manual contrast and keyboard checks.

---

## Architectural decision records (relevant for swarm subagents)

- **ADR 0001 — Static JSON vs Database.** Justified for a single-institution hackathon demo; not durable for multi-institution commercialization.
- **ADR 0002 — Claude Vision for Degree Audit.** Tradeoff: faster to ship, ~95% accurate on the design audit, fragile on edge cases.
- **ADR 0003 — Deterministic Solver vs LLM.** The headline insight. Combinatorial scheduling is Python; language and judgment are Claude. Means the solver cannot return a time-conflicted schedule, period.
- **ADR 0004 — Requirement Rule DSL.** Four rule types (`specific_course`, `choose_one_of`, `wildcard`, `course_with_lab`). Maps to Degree Works' actual syntax.
- **ADR 0005 — Editorial Minimalism Design.** Anti-chatbot UI; warm cream + gold + Instrument Serif. Distinguishes from generic "AI assistant" gloss.

---

## What it would take to make BryantPathfinder a real campus product

This is the brief for the swarm. Subagents should reason about each from their angle:

1. **Authoritative audit data feed** — replace screenshot ingestion with an official Ellucian Degree Works export, Banner Ethos API pull, or Workday Student integration.
2. **SIS coverage beyond Bryant** — Banner is dominant but not universal; PeopleSoft Campus Solutions, Workday Student, Colleague, Jenzabar all matter.
3. **Multi-tenancy and tenant isolation** — separate catalogs, separate auth, separate data tenancy per institution.
4. **SSO** — Shibboleth, SAML, Azure AD/Entra, Google Workspace for Education.
5. **FERPA-compliant architecture** — school-official agreement language, audit logging, retention policy, data minimization.
6. **Vendor security review** — HECVAT (Higher Education Community Vendor Assessment Toolkit) full or lite, SOC 2 Type II in flight.
7. **AI-specific transparency** — document what Claude sees, what it can hallucinate, what guardrails exist around prereqs and graduation requirements.
8. **Pricing and packaging** — currently free / academic.
9. **Sales motion** — solo technical founder, no warm network outside Bryant.
10. **Competitive positioning** — Stellic, EAB Navigate, Civitas, Ellucian Degree Works (the incumbent that BryantPathfinder rides on top of), Coursedog, Pathify all target adjacent or overlapping problems.

---

## Founder context

- **Owen Ash** — sophomore Finance major, Bryant University, expected May 2029.
- Email: `oash@bryant.edu`
- GitHub: `github.com/Oman6/bryantpathfinder`
- No co-founder, no funding, no incorporation, no warm relationships at other universities.
- Has access to one institution: **Bryant University** (~3,800 undergraduates, regional private business-focused, AACSB-accredited, located in Smithfield, Rhode Island).
- Comfort zone: building software, designing UI, writing prompts. Less comfort: enterprise B2B sales, legal/compliance contracting, university governance navigation.

---

## What "commercialization-ready" means for the synthesis agent

The synthesis agent should evaluate readiness against three thresholds:

1. **Pilot-ready at Bryant** — sanctioned, scoped, opt-in, 50 students, no money changes hands. *What does Owen need to do this fall?*
2. **Pilot-ready at a second institution** — non-Bryant, non-warm, paid pilot. *What needs to be true before a second school will pay?*
3. **Multi-tenant SaaS with 5+ institutions** — recurring revenue, hireable team, defensible moat. *What does year-two look like?*

A red/yellow/green per-dimension assessment against each threshold is the requested output format.
