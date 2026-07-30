# BryantPathfinder — Speaker Script

**Total runtime: ~5–6 minutes.** Press `n` in the deck to toggle inline speaker notes during rehearsal.

---

## Before you start

- Open `pitch/index.html` in Chrome full-screen (F11).
- Have the live app open in a second tab at `localhost:3000` in case someone asks for a demo.
- Have `audit_owen.json` fixture ready — never run the live Vision parse during the pitch.
- Arrows navigate. `n` toggles speaker notes. `Home` / `End` jump to ends.

---

## Slide 1 — Title (20s)

> Hi, I'm Owen Ash. I'm a sophomore finance major, and this is BryantPathfinder — the missing layer between Degree Works and Banner.
>
> For the next five minutes I'll show you what it does, how it works, and why I think it belongs at Bryant.

**Pause.** Breathe. Click next.

## Slide 2 — The Gap (40s)

> Every semester, every Bryant undergrad does the same painful ritual.
>
> Open Degree Works to see what's left. Open Banner to find sections. Open a spreadsheet to hand-check time conflicts. Email your advisor three times.
>
> Two to four hours of friction — and you can still end up with a broken schedule when a section closes the morning of registration.
>
> Degree Works tells you *what* you owe. Banner shows you *what's offered*. Nothing shows you how those two things fit together on a Tuesday morning at 9:30.

## Slide 3 — The Bet (25s)

> So here's the bet. What if registration took ninety seconds instead of four hours?
>
> Upload your audit. Pick your preferences. Get three conflict-free schedules — with predicted GPA, professor ratings, weekly workload, and a calendar file you can drop straight into Google Calendar.

## Slide 4 — Demo (45s)

> Three steps.
>
> **Step one — Upload.** Drop a screenshot of your Degree Works audit. Claude Vision reads your outstanding requirements — FIN 4XX electives, LCS choices, LCC cores — and returns structured data.
>
> **Step two — Prefer.** Target credits. No-Friday classes. Earliest start time. Preferred professors. Avoided buildings. Sliders and toggles, not forms.
>
> **Step three — Pick.** Three schedule cards, each with a weekly calendar grid, the CRNs you paste into Banner, a plain-English explanation of why the schedule fits you, and a one-click calendar export.

*(If time allows, click to the live app and run the flow. Budget 30 seconds. If anything feels off, pivot back to the deck — never debug on stage.)*

## Slide 5 — The Insight (50s)

> Here's the architectural decision that makes this work.
>
> Claude is extraordinary at language, vision, and judgment. So Claude parses the audit, ranks candidates, and writes the explanation.
>
> But Claude is the wrong tool to solve a combinatorial constraint problem. That's deterministic Python. Each tool stays in its lane.
>
> Asking an LLM to generate a conflict-free schedule is how you get seventy-three percent accuracy. Asking Python to do it is how you get one hundred percent.
>
> This one decision — the split — is why the whole thing runs in two hundred milliseconds and never, ever gives you a schedule with two classes at the same time.

## Slide 6 — The Agents (40s)

> Once the solver returns three valid schedules, a pipeline of specialized agents enriches each one.
>
> **Professor Match** pulls RateMyProfessors data and flags red-flag instructors.
>
> **Workload** looks at historical grade distributions to estimate weekly hours.
>
> **Negotiator** activates when your constraints are too tight and finds the smallest relaxation that makes the problem feasible — "drop no-Friday and you unlock four options."
>
> **Multi-Semester** looks four semesters ahead so you don't paint yourself into a corner on a prereq chain.

## Slide 7 — The Flow (25s)

> End to end, two seconds. Purple nodes are Claude, white nodes are Python. Four agents run in parallel. Full pipeline from audit screenshot to three ranked, explained schedules in the time it takes you to finish a sip of coffee.

## Slide 8 — The Data (35s)

> The data foundation matters. None of this is mock data.
>
> I scraped every Fall 2026 section from Banner — two hundred and ninety-one of them, with seat counts and locations. I pulled RateMyProfessors data for one hundred and twenty-nine of one hundred and thirty-three instructors, with review tags for one hundred and ten. And I have historical grade distributions for every course.
>
> The scraping was a full weekend. Banner's HTML is hostile. The payoff: the solver reasons about FIN 371 knowing it's a 4.1-star professor, 3.2 average GPA, tagged "tough grader."

## Slide 9 — Why It Works (40s)

> Why does this feel different from the dozens of "AI course scheduler" side projects out there? Four things.
>
> **One** — it's built by a finance major who *lived* the pain. I failed to register for FIN 210 three times last semester. Every design choice is a pain point I actually felt.
>
> **Two** — editorial UI, not chatbot gloss. No purple gradient. No "Hi, I'm an AI assistant."
>
> **Three** — production-grade. Rate limiting, prompt-injection defense, accessibility contrast, focus-trapped modals, typed end-to-end.
>
> **Four** — it solves the full problem. Not just "generates a schedule" — it ranks, explains, warns on seats, exports to calendar, plans four semesters out.

## Slide 10 — Impact (30s)

> Who benefits? Every undergrad at Bryant — about four thousand students — goes through this ritual twice a year.
>
> If Pathfinder saves each one two hours per registration, that's sixteen thousand student-hours a year reclaimed. For advisors, it's fewer "help me figure out my schedule" emails and more time for the conversations that actually matter — career planning, graduate school, study abroad.

## Slide 11 — Roadmap (30s)

> Where does this go? Fall '26, pilot with fifty Finance majors. Spring '27, full College of Business. Fall '27, Bryant-wide.
>
> The dream phase — a real data feed from the Registrar's office so students don't have to screenshot their audit in the first place. That's where I need Bryant's help.

## Slide 12 — The Ask (25s)

> Three things.
>
> **One**, an introduction to the Registrar's office to explore a data feed.
>
> **Two**, a sanctioned pilot with fifty Finance students this fall.
>
> **Three**, honest feedback from advising on what would make this genuinely useful in their workflow.
>
> Thank you. I'd love to take any questions.

---

## Q&A prep — likely questions

**"How do you handle students on other majors / colleges?"**
> The solver is college-agnostic. The data foundation — Banner sections, professor ratings, grade distributions — is Bryant-wide. I focused Fall '26 on Finance because it's my major and I can be the first user. Adding other majors is a catalog-expansion problem, not a rewrite.

**"What about FERPA / student data privacy?"**
> Today, the audit is a screenshot the student uploads — they choose what to share. No data is stored server-side beyond the current session. If we move to a Registrar feed, that's a conversation with IT and legal, and I'd want to do it right — SSO, audit logs, data minimization.

**"What if Claude is wrong?"**
> The solver is not Claude. It's deterministic Python. Claude cannot return a schedule with a time conflict because Claude doesn't generate schedules — Python does. The worst Claude can do is misrank three valid schedules, and the student sees all three anyway.

**"How accurate is the Vision parsing?"**
> On Owen's audit — the one I tested against — it's been 100% for a week. On adversarial cases I don't have coverage yet, which is why there's a "use sample audit" fallback and a text-paste path. For a pilot we'd want a 50-student accuracy study before relying on it without fallbacks.

**"Why build this solo? Why not as a class project?"**
> It started as a hackathon build and I couldn't stop working on it. I'd welcome collaborators — especially someone on the data/Registrar side.

**"What does this cost to run?"**
> Claude API costs per student registration session are roughly 5–10 cents at current pricing. At 4,000 students × 2 registrations/year, we're talking well under $1,000/year in model costs. The biggest expense is someone's time to keep the scrapers working.

**"Who owns the IP?"**
> I do, as a student project. Happy to discuss — open source, license to Bryant, spin out, whatever makes sense.

---

## Backup slides / topics (if you have extra time)

- The solver algorithm walk-through (itertools.product + half-open interval conflict detection)
- The negotiator's trade-off UX ("relax no-Friday to unlock 4 options")
- The walk-time warning feature (11-minute building-to-building buffer)
- The calendar export (RFC 5545 compliant .ics with RRULE BYDAY)

---

## If things break on stage

- **Live demo crashes:** Pivot to the deck. "The live build is on localhost — happy to show after if time allows." Don't debug on stage, ever.
- **Vision parse returns garbage:** Click "Use sample audit." Keep talking.
- **Backend is down:** The whole deck runs without the backend. You lose nothing.
- **Someone asks a question you can't answer:** "That's a great question — I want to give you a real answer rather than a guess. Can I follow up on that?"
