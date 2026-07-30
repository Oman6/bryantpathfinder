# 99 — API Integration Roadmap

> Synthesis of research files A1–A7. The scoring frame is the **Bryant fall 2026 pilot** (50 students). Year-2 multi-tenant economics are tiebreakers. Cited by file letter+section, not external URLs. Decisions, not options.

---

## 1. The Top 10 APIs to Integrate, Ranked

Ranked by (feature impact × FERPA defensibility) ÷ engineering effort.

| # | API / Service | What it unlocks (Pathfinder feature) | Effort | Cost @ pilot | Cost @ 5K students | FERPA | Source |
|---|---|---|---|---|---|---|---|
| 1 | **Anthropic Prompt Caching** | ~90% cost cut on every `/api/generate-schedules` call; 5x faster cold starts | 0.5 PD | $0 | $0 (saves ~$350K/yr) | None | A6 §1 |
| 2 | **Bryant Banner SSB live feed** (`reg-prod.bryantec.bryant.edu/StudentRegistrationSsb`) | Real-time seat counts, replaces the static 291-section snapshot, enables "alert when seat opens" | 3–5 PD | $0 | $0 | None (public catalog) | A1 §1 |
| 3 | **U.S. Dept. of Education College Scorecard API** | "Bryant Finance grads earn median $76k 4 yrs out" credibility panel; reframes from scheduler to ROI tool | 0.5 PD | $0 | $0 | None | A5 #2, A1 #2 |
| 4 | **Subscribed iCal feed (publish-only)** | Universal calendar push to Apple, Google, Outlook, Notion — auto-refreshes when student swaps section | 1 PD | $0 | $0 | Low | A2 #3 |
| 5 | **Open-Meteo weather API** | "Rain expected Wed — your Smithfield→Fisher walk-between-classes is 8 min outdoors" | 0.5 PD | $0 | $0 | None | A3 #6 |
| 6 | **Bryant academic calendar scrape** | Drop/add, finals week, break reminders; turns Pathfinder from once-per-semester into monthly tool | 0.5 PD | $0 | $0 | None | A7 #1 |
| 7 | **Google Distance Matrix (one-time precompute)** | Real walk times between every Bryant building pair — kills the manual 11-min constant; ~870 elements cached once, $0 ongoing | 1 PD | $0 | $0 | None | A3 #1 |
| 8 | **Resend transactional email** | Registration-window reminder, "advisor commented on your draft," "your top 3 are ready" | 1 PD | $20/mo | $80/mo | Low (PII-stripped payloads) | A4 #1 |
| 9 | **Voyage 3.5 embeddings + Postgres pgvector** | "Show me a class like FIN 310 but easier" semantic search; 200M token free tier covers the entire pilot corpus | 2 PD | $0 | ~$200/mo | None (no PII) | A6 #3 |
| 10 | **Bryant Bulldogs SIDEARM iCal feeds** | Athletic-conflict warnings ("your class clashes with hockey vs URI Oct 15"); per-sport iCal endpoints exposed by SIDEARM | 0.5 PD | $0 | $0 | None | A7 #3 |

**Total Sprint-1+2 effort to ship #1–10: ~10 person-days. Total cost at pilot scale: ~$20/mo.**

---

## 2. The Three-Sprint Build Order

Three two-week sprints. Each ends with a demo line you can put in the Paliwal MOU meeting.

### Sprint 1 (Weeks 1–2): Cheap wins, visible features

1. **Anthropic Prompt Caching** (#1) — wrap the catalog block in `cache_control: ephemeral`, set 1-hour TTL explicitly (Anthropic regressed the default to 5 min in early 2026 per A6 §1). Measure cost-per-generate before and after; the ~10× drop is the demo.
2. **Bryant Academic Calendar scrape** (#6) — one cron job pulls catalog.bryant.edu twice a year, stores 16 dates in `events.json`, surfaces drop-add and finals reminders in the schedule UI.
3. **Bryant Bulldogs SIDEARM iCal** (#10) — read 19 sport iCal feeds nightly into a flat athletic-events JSON; warn when a student's sections overlap a Bryant home game.
4. **Open-Meteo** (#5) — 7-day forecast injected into the WeeklyCalendar's tooltip per class block.
5. **College Scorecard wage panel** (#3) — single static fetch at build time; "Bryant Finance majors: median $76k @ 4yrs" badge on the schedule page.

> **Demo line:** *"Pathfinder now shows real wage outcomes for your major, knows your finals week, warns when classes hit a home game, and runs at 10× lower cost on every generate."*

### Sprint 2 (Weeks 3–4): The big one — live data

1. **Bryant Banner SSB live feed** (#2) — the highest-impact item in the roadmap. Reverse-engineer the unauthenticated `/StudentRegistrationSsb/ssb/searchResults/searchResults` JSON endpoint per A1 §1. Build a 5-min poller that updates `seats_open` for every section in the catalog. Replaces the static snapshot.
2. **Google Distance Matrix one-time precompute** (#7) — single batch call with all building pairs; cache results in `walk_times.json`; delete the manual 11-min constant; warn at <10 min.
3. **Subscribed iCal feed** (#4) — `/api/calendar/{student_id}.ics` returns the saved schedule; students paste the URL into Google/Apple/Outlook once, schedule auto-syncs forever.

> **Demo line:** *"Live seat counts, real campus walk distances, and one-click calendar that auto-updates when you swap a section."*

### Sprint 3 (Weeks 5–6): Communication + recommendation depth

1. **Resend** (#8) — transactional emails for the four canonical alerts; React Email components compose with the existing Tailwind/shadcn frontend.
2. **Voyage 3.5 + pgvector** (#9) — embed all 291 sections + course descriptions; ship "courses similar to FIN 310" recommendation in the elective picker.
3. **Stretch:** the BLS + O*NET + NCES CIP-SOC crosswalk from A5 #1 (~2 PD); maps Finance → top 5 occupations, surfaces aligned electives.

> **Demo line:** *"You get the schedule, then we email you when registration opens, and we show you which 4XX electives align with the jobs Bryant Finance grads actually take."*

---

## 3. The "Don't Build" List

| API | Why it's tempting | Why it's wrong (now) |
|---|---|---|
| **SMS via Twilio / Telnyx** | Fastest delivery for "seat just dropped" alerts | A2P 10DLC is a 4-week procurement project requiring an EIN; Sole-Prop throughput won't survive registration day; web push covers ~70% of the latency win for free (A4 #2) |
| **Anthropic Computer Use** | "Auto-register on Banner" is the demo dream | Bryant AUP risk + Anthropic usage-policy risk; instant-disqualifier with General Counsel (A6 §5) |
| **Perplexity Sonar / Brave Search** | Real-time professor grounding | Sonar 2–4s latency blows the 2s pipeline budget; Brave free tier was killed Feb 2026 (A6 §4) |
| **LinkedIn Talent Insights / Lightcast** | Best labor-market data on Earth | $6K–$300K/yr enterprise contract, partner-application gated, wrong scale for pilot (A5 deferred) |
| **iCloud / CalDAV OAuth-write** | Native Apple Calendar sync | iCloud has no OAuth path; only Basic Auth + app-specific password — students will never do that. The subscribed feed handles them (A2 §3) |
| **Mappedin / indoor positioning** | "Step-by-step inside Unistructure" | $85–165/map/mo; overkill for ~30 buildings; year-2 differentiator at best (A3 #9) |
| **Bryant Rave / CodeRED alerts** | Safety integration | Push-only by design; no consumer API; correctly closed for security (A7 hard skip) |
| **Pinecone / managed vector DB** | "Real" infrastructure | pgvector + HNSW hits 95%+ recall in 5–20ms at 1M vectors; defer to ~50M (A6 §2) |

---

## 4. Strategic Asks (Relationships, Not Code)

Highest-leverage APIs in the swarm that require an introduction or a meeting, not a coding session. Each goes on Owen's email list, not the build backlog.

| Ask | Who to contact | Specific request |
|---|---|---|
| **Open Syllabus institutional access** | `info@opensyllabus.org` (their commercial team) | Pathfinder is preparing a Bryant pilot; need read access to syllabi for the 80 most-taught Bryant courses to power the Workload Agent. ($2.5K–$10K/yr per A1 #3.) |
| **Handshake EDU API beta** | Bryant's Amica Center for Career Education (their assigned Handshake Customer Success Manager) | Owen wants to surface "73% of Bryant IB analysts took FIN 470" from anonymized Handshake placement data. Handshake gates this through the institution, not the developer. (A5 honorable mention.) |
| **Anthology Engage v3 REST API key** | Bryant Engaged office (`engaged.bryant.edu` admin) | Pathfinder wants to surface club meeting times alongside the schedule. Anthology requires both Bryant approval and an Anthology partner key. (A7 §2.) |
| **Springshare LibCal API key** | Bryant Krupp Library systems librarian | LibCal REST 1.1 is gated by a per-institution key. Owen needs read access to study-room availability and library hours. (A7 #2.) |
| **Sodexo / Nutrislice menu feed** | Bryant Dining Services + Sodexo regional account manager | "Salmon House lunch hours within walking distance of your next class" — needs Nutrislice cooperation timed to their migration. (A7 vendor stack.) |

These are 5 emails, not 5 codebases. Send them in parallel; none of them block any of the top-10 ships.

---

## 5. The Cost Reality Check

**Bryant pilot (50 students, fall 2026): ~$20/month.**
Resend $20/mo (the only paid item) plus $0 across Banner SSB, College Scorecard, Open-Meteo, Google Distance Matrix (one-time within free cap), prompt caching (saves money), Voyage embeddings (200M-token free tier), iCal feed, SIDEARM. Anthropic API spend at the same scale is roughly $50–80/mo per the baseline doc.

**Bryant + 1 second school (~600 students, spring 2027): ~$150/month.**
Resend ~$35/mo, prompt-caching savings already amortized, Voyage stays free, Google Distance Matrix one-time precompute per school = $0 ongoing, FCM web push $0, Novu cloud $0 at this scale (sub-30K monthly notifications). Anthropic API spend ~$400/mo. Add Sentry $26/mo, PostHog $0–50/mo. **Real running cost: ~$500/mo total infrastructure including AI.**

**5-school multi-tenant (~5,000 students, fall 2027): ~$2,500/month.**
Resend $80/mo, Voyage tips into paid tier (~$200/mo), Anthropic with prompt caching ~$1,500/mo (vs ~$15K/mo without — A6 §1), Google Distance Matrix still $0 (precomputed per school, cached forever), notification orchestration $200/mo, Postgres + pgvector hosted ~$200/mo, observability ~$300/mo. **No single line item exceeds $2K/mo. The whole API surface stays well under 3% of a single $30K Bronze license.**

---

## 6. The Single Highest-ROI API

**Ship Anthropic Prompt Caching this week.**

It's the lowest-risk, lowest-effort, highest-margin change in the roadmap. ~0.5 person-days to implement (`cache_control: ephemeral` on the catalog block in every Claude call, plus an explicit 1-hour TTL because Anthropic silently regressed the default to 5 minutes in early 2026 per A6 §1). It cuts ~90% off the input-token cost of every `/api/generate-schedules` call and every audit-parse retry, makes cold starts noticeably faster, has zero FERPA implications, requires zero new vendors, zero new contracts, and zero new dependencies. At pilot scale it saves ~$10/day; at year-2 scale it's the difference between $1.5K/mo and $15K/mo of Anthropic spend (A6 §1). Nothing else in the swarm clears that bar on day one.

**Ship #2 (Bryant Banner SSB live feed) the week after.** It's the single largest *product* upgrade in the roadmap — the screenshot demo gets replaced with a real-time data product, and the "we use a static snapshot" objection from every CIO conversation disappears. 3–5 person-days, $0 ongoing.
