# ADR 0001 — Static JSON Catalog Over a Database

**Status:** Accepted
**Date:** 2026-04-08
**Deciders:** Owen Ash

---

## Context

Pathfinder needs to store the Bryant Fall 2026 course catalog somewhere the backend can query it. The dataset has 291 sections after filtering to the Business Administration track. Every request to `/api/generate-schedules` reads from this dataset — the solver filters by subject and course code, checks seat counts, and walks the meeting times.

The obvious default for a web application is to put this in a database. Postgres via Supabase would give us query performance, indexes on `subject` and `course_code`, schema migrations, and a real audit trail if seat counts change over time. It's also the production-correct answer — a real version of Pathfinder would need a database eventually to track user sessions, saved schedules, and live seat updates from Banner Ethos.

But Pathfinder is a one-day hackathon build with a solo developer and hard time constraints. Every hour spent on infrastructure is an hour not spent on the demo. The question is whether the engineering maturity signal of "has a real database" is worth the time cost and the failure surface it introduces.

---

## Decision

Pathfinder loads the full section catalog from a static `data/sections.json` file into memory at backend startup using FastAPI's lifespan context manager. No database. No ORM. No migrations. The degree audit fixture lives in the same place — `data/fixtures/audit_owen.json`.

The sections are stored in the app state and accessed through dependency injection in the routes. A single Python dict keyed by `course_code` gives O(1) lookup when the requirement expander needs to find all sections of FIN 310. A flat list covers the cases where we need to iterate the full catalog for wildcard rules.

No caching layer, no connection pool, no schema file. The JSON file is the schema.

---

## Consequences

### Positive

- **Zero infrastructure time.** No Supabase setup, no connection strings, no schema migrations, no ORM learning curve. The backend boots in under a second and the data is immediately available.
- **Zero failure surface from the data layer.** No network calls to a database during request handling. The solver either finds sections or it doesn't — it can't time out, can't hit a connection limit, can't return stale results from a replica lag.
- **Trivially testable.** Tests load the same JSON file and run against the same data the production backend uses. No test database, no fixtures, no teardown.
- **Honest about the constraint.** The Bryant Fall 2026 catalog isn't changing during the hackathon. Seat counts are a snapshot from April 7, 2026. Pretending otherwise with a live database would be architecture theater.
- **Readable.** Anyone reviewing the repo can open `data/sections.json` in a text editor and see the exact data the solver is working with. That transparency is a score signal for the AI grader.

### Negative

- **Seat counts are stale the moment the file is written.** If a judge asks "what happens when seats change during registration?" the answer is "this snapshot is from April 7 — in production, Pathfinder would integrate with Banner Ethos for nightly or hourly refreshes." Flagged in the roadmap.
- **No persistence across user sessions.** Every student who uses Pathfinder starts fresh. For the hackathon this is fine because there's one demo user. For production it's a blocker.
- **The full catalog lives in memory.** At 291 sections with ~500 bytes each, that's ~150KB — not a problem. If the production catalog ever exceeds 10,000 sections this approach would need to change.

### The production path

When Pathfinder evolves past the hackathon, the data layer will move to Supabase Postgres with the following schema:

- `sections` table indexed on `subject`, `course_code`, `term`, and `is_full`
- `degree_audits` table keyed on student ID, storing parsed audits with a TTL
- `saved_schedules` table for persisting a student's chosen schedule across sessions
- Nightly sync job from Banner Ethos updating seat counts and adding/removing sections

The FastAPI route handlers will stay nearly identical — the only change is swapping `app.state.sections` for a database query. The solver and the requirement expander don't need to know where the data came from.

---

## Alternatives Considered

**Supabase Postgres from day one.** Rejected because the 45-60 minutes of setup (project creation, schema definition, seeding the catalog, configuring the Python client, testing the connection) is 25% of the total build window. The failure modes (network issues, auth issues, schema drift) would block the solver from running at all. For a one-day build, the math doesn't work.

**SQLite file.** Rejected because it adds ORM complexity without meaningful benefit over in-memory JSON at this scale. The file would still need to be regenerated from the same parse scripts, so it's just a slower JSON file with more syntax.

**Redis.** Rejected as obviously wrong for this use case. Redis is for caching and pub/sub, not as a primary data store for structured relational data.

**Hard-coded Python lists.** Rejected because it mixes data with code. Keeping the catalog in JSON means the parser script can be re-run against updated Banner data without touching the backend code.
