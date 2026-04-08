# BryantPathfinder

> The missing layer between Degree Works and Banner.

**BryantPathfinder** is an AI course scheduling assistant that reads your Degree Works audit, knows the full Bryant course catalog, and generates conflict-free class schedules that actually fit your life — in seconds.

**Built for the Bryant University AI Hack-a-thon, April 8, 2026.** Built solo by Owen Ash.

---

## Quick Demo

1. Open `http://localhost:3000`
2. Click **"Use sample audit"** on the homepage
3. Set your preferences (try "No Friday classes", 15 credits)
4. Click **"Generate my schedules"**
5. Three conflict-free schedules appear in under 2 seconds
6. Click **"Use this schedule"** and copy the CRNs into Banner

Full demo script: [docs/demo-script.md](docs/demo-script.md)

---

## The Problem

Every semester, every Bryant student goes through the same broken process. Your advisor sits down with you in Degree Works and builds a plan — a list of courses you need to take. You leave that meeting and open Banner Self-Service. You search each course. You check which sections still have seats. You cross-reference the times so nothing conflicts. You try to keep your Fridays free, avoid the 8 a.m.s, and dodge the professor with the bad reviews. You write it all down on a sticky note, rebuild it three times, and eventually register for something that kind of works.

It takes hours. Everyone hates it. And nothing connects the two systems.

BryantPathfinder is the bridge. You upload a screenshot of your Degree Works audit. Claude Vision reads it and figures out exactly what you still need to take. You set your preferences. It runs against the full Bryant Fall 2026 catalog and generates three complete, conflict-free schedules in two seconds. Each one shows you the weekly calendar, the professors, the seats remaining, and a short explanation of why it's a good pick. You click the one you like, copy the CRNs, walk into Banner, and register in thirty seconds.

---

## How It Works

### The core insight

Pathfinder uses Claude where language and perception matter, and deterministic code where correctness matters. Claude reads messy screenshots and writes natural-language explanations. Python does the combinatorial math. Each tool does what it's good at.

```
Degree Works audit (screenshot)
    +
Claude Vision -> structured requirements
    +
Bryant Fall 2026 catalog (291 sections)
    +
Student preferences (plain English)
    =
Three ranked, conflict-free schedules with explanations
```

### System overview

```
User (web browser)
        |
        v
Next.js 15 (App Router, TypeScript)
        | REST + JSON
        v
FastAPI Backend
  |-- Audit Parser       -> Claude Vision reads the Degree Works screenshot
  |-- Requirement Expander -> turns "FIN 4XX" into a list of real courses
  |-- Constraint Solver  -> pure Python, picks sections, checks conflicts
  |-- Schedule Ranker    -> Claude explains the top 3 options
        |
        v
Anthropic API (claude-sonnet-4-5)
        |
        v
Static JSON catalog
  |-- sections.json      -> 291 Bryant Fall 2026 sections
  |-- audit_owen.json    -> test fixture for the demo
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Python 3.12, Pydantic v2 |
| AI | Anthropic Claude (claude-sonnet-4-5) |
| Data | Static JSON snapshots (sections.json, audit_owen.json) |
| Fonts | Instrument Serif (display), Geist (UI), Geist Mono (data) |
| Icons | Phosphor Light |

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+ and pnpm
- An Anthropic API key

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000
```

Verify: `http://localhost:8000/api/health` should return `{"status":"ok","sections_loaded":291}`.

### Frontend

```powershell
cd frontend
pnpm install
pnpm dev
```

Open `http://localhost:3000`.

---

## Repository Structure

```
bryantpathfinder/
|-- README.md              This file
|-- ARCHITECTURE.md        Full system design and data models
|-- CLAUDE.md              Claude Code configuration and build instructions
|-- ROADMAP.md             What's built, what's next
|
|-- docs/
|   |-- data-model.md      Canonical Pydantic schemas
|   |-- api.md             REST endpoint reference
|   |-- demo-script.md     3-minute demo flow
|   |-- adr/
|   |   |-- 0001-static-json-vs-database.md
|   |   |-- 0002-claude-vision-for-degree-audit.md
|   |   |-- 0003-deterministic-solver-vs-llm.md
|   |   |-- 0004-requirement-rule-dsl.md
|   |   |-- 0005-editorial-minimalism-design.md
|   |-- features/           7 features x 4 files each (AIE framework)
|
|-- backend/
|   |-- app/
|   |   |-- main.py         FastAPI routes and lifespan
|   |   |-- models.py       Pydantic data models
|   |   |-- solver.py       Pure Python constraint solver
|   |   |-- prompts.py      Claude prompt strings
|   |   |-- claude_client.py  Anthropic API wrapper
|   |   |-- requirement_expander.py  DSL -> candidate sections
|   |-- scripts/
|   |   |-- parse_banner_dump.py     Raw Banner -> sections.json
|   |   |-- parse_degree_audit.py    Raw audit -> audit_owen.json
|   |-- requirements.txt
|   |-- .env.example
|
|-- frontend/
|   |-- app/
|   |   |-- page.tsx                Homepage with upload zone
|   |   |-- preferences/page.tsx    Preferences capture
|   |   |-- schedules/page.tsx      Generated schedules display
|   |-- components/
|   |   |-- UploadZone.tsx
|   |   |-- ScheduleCard.tsx
|   |   |-- WeeklyCalendar.tsx
|   |   |-- CourseBlock.tsx
|   |   |-- EyebrowTag.tsx
|   |   |-- PillButton.tsx
|   |-- lib/
|   |   |-- api.ts          Typed API client
|   |   |-- store.ts        Zustand state store
|   |   |-- types.ts        TypeScript interfaces
|
|-- data/
    |-- sections.json       291 parsed Bryant sections
    |-- fixtures/
        |-- audit_owen.json Owen's parsed degree audit
```

---

## Architecture Decision Records

- [ADR 0001 — Static JSON vs Database](docs/adr/0001-static-json-vs-database.md)
- [ADR 0002 — Claude Vision for Degree Audit](docs/adr/0002-claude-vision-for-degree-audit.md)
- [ADR 0003 — Deterministic Solver vs LLM](docs/adr/0003-deterministic-solver-vs-llm.md)
- [ADR 0004 — Requirement Rule DSL](docs/adr/0004-requirement-rule-dsl.md)
- [ADR 0005 — Editorial Minimalism Design](docs/adr/0005-editorial-minimalism-design.md)

---

## Built For

Bryant University AI Hack-a-thon, April 8, 2026.
Research and Engagement Day, BELC S157.

Built solo in one day by Owen Ash with Claude.
