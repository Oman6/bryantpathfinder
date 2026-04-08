# BryantPathfinder — Demo Script

> 3-minute live demo for the Bryant University AI Hack-a-thon, April 8, 2026. BELC S157.

---

## Setup (before you walk up)

- Backend running: `uvicorn app.main:app --port 8000` in `backend/`
- Frontend running: `pnpm dev` in `frontend/`
- Browser open to `http://localhost:3000` — homepage visible
- Browser zoom at 100%, full screen, no bookmarks bar
- Demo laptop charged, Wi-Fi connected (for Anthropic API calls)
- Have `data/fixtures/audit_owen.json` ready as fallback — the "Use sample audit" button loads it

---

## Minute-by-Minute Script

### 0:00 -- 0:20 | The Problem

> "Every semester, every Bryant student goes through the same broken process. Your advisor builds your plan in Degree Works. You leave that meeting, open Banner, and spend the next two hours searching courses one by one, cross-referencing times, checking seats, trying to avoid conflicts. Nothing connects these two systems. Pathfinder is the bridge."

**On screen:** Homepage is visible. The headline reads *"Your advisor tells you what to take. Pathfinder tells you when."* Let the audience read it.

### 0:20 -- 0:40 | The Upload

> "I'm Owen Ash, sophomore Finance major. My advisor just built my Fall 2026 plan. I'll use my pre-parsed audit to keep the demo moving."

**Action:** Click **"Or use sample audit"** below the upload zone.

> "That loaded my real Degree Works data. Sixteen outstanding requirements across my major, business core, and gen eds. Everything I still need to graduate."

**On screen:** Preferences page loads. Outstanding requirements are visible, grouped by category (Major, Business Core, Gen Ed). All checkboxes are checked.

### 0:40 -- 1:10 | The Preferences

> "I want 15 credits this semester. No Friday classes — that's non-negotiable."

**Action:** Confirm target credits slider is at 15. Toggle **"No Friday classes"** on. The switch turns gold.

> "I can also block early mornings, avoid evening classes, or type preferences in plain English. For now, I just want Fridays off."

**Action:** Optionally scroll through the requirement list. Point out FIN 310, ACG 203, ISA 201, MKT 201, GEN 201 are all checked.

> "I'll generate with five requirements selected. That's 15 credits."

**Action:** Click **"Generate my schedules."**

### 1:10 -- 2:00 | The Payoff

> "Two seconds."

**On screen:** Three schedule cards appear with staggered animation. Each has a weekly calendar grid.

> "Three complete, conflict-free schedules. The solver checked every valid combination of sections and scored them on credit match, seat availability, and professor preferences."

**Action:** Point to Schedule 1 (Top pick).

> "The top pick gives me FIN 310 — Intermediate Corporate Finance. GEN 201 for Intercultural Communication. ACG 203 for accounting, ISA 201 for analytics, and MKT 201 for marketing. Fifteen credits, Fridays completely empty."

**Action:** Point to the weekly calendar — show the empty Friday column. Point to the course list below showing instructor names and seat counts.

> "Every section still has open seats. The schedule runs from 9:35 to about 9 PM on a couple days, but nothing on Friday."

**Action:** If a Claude-generated explanation is visible, read it. If not, skip — the visual tells the story.

> "I click 'Use this schedule' — and here are my CRNs."

**Action:** Click **"Use this schedule"** on the top card. The CRN dialog opens showing all five CRNs in monospace.

> "I copy these, walk into Banner, paste them in, and I'm registered. Thirty seconds. The manual version takes two hours."

### 2:00 -- 2:30 | The Architecture

> "The key insight is what Claude does and what it doesn't do. Claude Vision reads the messy Degree Works audit — that's a perception task, and Claude is great at it. Claude also writes the schedule explanations in plain English. But the actual scheduling math — the conflict detection, the combinatorial search, the scoring — that's pure deterministic Python. About 250 lines. No LLM in the loop for correctness."

> "Claude is amazing at language and perception. It's not a combinatorial solver. We use each tool where it shines."

### 2:30 -- 3:00 | The Close

> "There are 4,000 students at Bryant. Every one of them does this work manually, twice a year. We built a tool that does it in two seconds. Built solo in one day, with Claude, for this hackathon."

> "The repo is public at github.com/Oman6/bryantpathfinder. Thank you."

---

## Fallback Plan

| Failure | Recovery |
|---------|----------|
| Vision parsing fails | Click "Use sample audit" — loads the fixture instantly |
| Backend crashes | Restart: `uvicorn app.main:app --port 8000` (boots in <1 second) |
| No schedules returned | Uncheck "No Friday classes" or reduce selected requirements |
| Claude API rate limited | Schedules still generate — explanations show "unavailable" but the solver runs independently |
| Wi-Fi dies | The solver and sample audit work offline. Only Claude explanations and Vision parsing need the network. |

## Key Numbers to Memorize

- **291** sections in the Fall 2026 catalog
- **16** outstanding requirements in Owen's audit
- **3** schedules generated in under **2 seconds**
- **250** lines in the constraint solver
- **1 day** to build, **1 person**, with Claude
