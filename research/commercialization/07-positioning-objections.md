# 07 — Positioning & Objections

> How BryantPathfinder gets through a CIO's inbox, a Provost's calendar, a Registrar's risk register, and a Faculty Senate agenda — without dying. Written for Owen as the person actually in the room.

---

## Part 1 — The Top 15 Objections, with Structured Responses

Each objection is in the voice of the persona who would actually say it. The "real concern underneath" is what they mean but won't say. The "credible response" is what Owen says back, with specifics from the product baseline. The "proof point needed" is what BryantPathfinder must possess to make the response hold up under follow-up questions.

Sources for what these personas typically care about: EDUCAUSE Top 10 IT Issues 2025 (https://www.educause.edu/research-and-publications/research/top-10-it-issues), the 2024 EDUCAUSE AI Landscape Study (https://www.educause.edu/ecar/research-publications/2024/2024-educause-ai-landscape-study/introduction-and-key-findings), Inside Higher Ed's coverage of generative AI in advising (https://www.insidehighered.com/news/tech-innovation/artificial-intelligence), and the HECVAT program documentation (https://www.educause.edu/hecvat).

---

### 1. "We already have Degree Works."

- **Real concern underneath:** "We paid Ellucian a seven-figure contract three years ago and the Provost will ask why we're buying something else." Sunk-cost defense and procurement self-justification.
- **Credible response:** "Pathfinder doesn't replace Degree Works — it reads it. Degree Works tells a student *what* they still need; it does not tell them *which sections fit together this semester without a time conflict*. That second step is a 30-tab manual nightmare, and it's where the dropouts and 5-year graduations live. We sit between Degree Works and Banner. The audit you already paid for is our input. We make it actionable in two seconds."
- **Proof point needed:** A side-by-side screen recording — Degree Works on the left, Pathfinder on the right — showing the same student's outstanding requirements turning into three ranked, conflict-free schedules with weekly grids. Time-to-schedule baseline at Bryant (median minutes a student currently spends building a schedule manually) versus time-to-schedule with Pathfinder.

---

### 2. "Our data can't leave campus."

- **Real concern underneath:** "FERPA. If a journalist writes that an AI vendor leaked our student transcripts, I get fired." Risk transfer.
- **Credible response:** "We agree, and we've architected for that. The current path sends the screenshot to Anthropic for vision parsing — that's the one external call that touches student data. For a campus deployment, we offer two paths: (a) Anthropic Bedrock or Vertex tenancy in your existing AWS or GCP environment, where the data never leaves your VPC, or (b) a text-only ingestion path that reads the Degree Works export server-to-server with no Vision call at all. Either way, we sign a school official designation under FERPA's 99.31(a)(1) and we minimize: we keep the parsed requirements, not the raw audit."
- **Proof point needed:** A written data-flow diagram showing exactly which fields touch which service. A draft Data Processing Addendum. Documentation of the text-only ingestion path actually working end-to-end. Anthropic's enterprise privacy commitments (https://www.anthropic.com/legal/privacy) attached to the vendor packet.

---

### 3. "Anthropic isn't on our approved vendor list."

- **Real concern underneath:** "Adding a new AI vendor means another HECVAT cycle, another legal review, another six months. I don't want the work."
- **Credible response:** "Anthropic is already on a growing number of higher-ed approved lists — they're SOC 2 Type II audited, they're available through AWS Bedrock and Google Vertex, and many institutions consume them through an existing cloud master agreement rather than a direct contract. We can deploy through whichever cloud you already have a Business Associate Agreement or master services agreement with, so the vendor on paper is AWS or Google, not a new SKU."
- **Proof point needed:** Confirmation that Anthropic-via-Bedrock works for our pipeline (Vision + text) and a checklist showing how it maps to a typical HECVAT response. A reference to at least one peer institution that has cleared Anthropic. (Owen needs to call EDUCAUSE's Cybersecurity Program and ask which schools have approved Anthropic — that's the artifact.)

---

### 4. "What happens when Claude hallucinates a prereq and a student misses graduation?"

- **Real concern underneath:** "Liability. If a student sues, the dean wants to point at a vendor."
- **Credible response:** "Claude never decides whether a course satisfies a requirement in our architecture. That's the whole point of ADR 0003. The deterministic Python solver expands requirements from the Degree Works rule (which is your authoritative source), generates the candidate set, checks time conflicts with half-open intervals, and ranks. Claude only handles three things: (1) parsing the screenshot — and if that's a concern, we use the text path; (2) writing the explanation paragraph — which doesn't change the schedule; (3) ranking three already-valid candidates by fit. The student also still registers in Banner themselves; we output CRNs, we don't write back. The advisor remains the system of record for graduation eligibility. We are a productivity layer."
- **Proof point needed:** ADR 0003 in writing, accessible publicly. A deterministic-test suite showing the solver cannot return a time-conflicted schedule. A clear written delineation of "what Claude touches" versus "what the solver touches." A model card-style transparency document for the AI components.

---

### 5. "Faculty Senate will block this — we just had a fight about ChatGPT."

- **Real concern underneath:** "Faculty hate AI and I just spent six months in a brawl over the syllabus AI policy. I cannot eat another."
- **Credible response:** "Pathfinder is not a writing tool, it doesn't generate student work, and it doesn't replace anyone's labor. It removes a specific friction — the manual section-shopping step — that faculty don't do anyway. The audience is students and advisors, not classrooms. We can scope the pilot so it's opt-in for advisors and opt-in for students, with no curricular footprint. The faculty conversation we are *willing* to have is around the Professor Match agent, which surfaces RateMyProfessors data; if your senate doesn't want that, we can disable it tenant-wide via a feature flag."
- **Proof point needed:** A feature-flag-level off switch for the Professor Match agent already in the code. A written FAQ for Faculty Senate. An advisor co-signer at Bryant willing to say at the senate meeting "this is a productivity tool for my office, not a curricular intervention."

---

### 6. "How is this different from ChatGPT? A student could just ask ChatGPT."

- **Real concern underneath:** "If the answer is 'a slicker UI,' I can't justify the line item."
- **Credible response:** "ChatGPT does not have your live catalog, your enrollment caps, your prereq DSL, your professor data, or your Degree Works rules. Ask ChatGPT to schedule next semester and it confidently invents a section that doesn't exist, hallucinates a prereq chain, ignores time conflicts, and gives you a paragraph with no calendar grid and no CRNs. We've tested it. Pathfinder is not a chatbot wrapper — it's a deterministic constraint solver fed by your authoritative SIS data, with Claude only at the edges where language and judgment matter. The 291 Bryant Fall 2026 sections in our system are real; ChatGPT's are not."
- **Proof point needed:** A published side-by-side: the same student preference handed to ChatGPT, Gemini, and Pathfinder, with the hallucination rate annotated. Number of fictional sections ChatGPT invents per query (Owen needs to actually run this).

---

### 7. "What's your reference customer?"

- **Real concern underneath:** "I'm not buying first. Nobody wants to be the launch customer for a sophomore's project."
- **Credible response:** "Bryant is our pilot site this fall — sanctioned, scoped, opt-in, 50 students. We can put you on the standing call with the Bryant Director of Academic Advising once the pilot is live. We're not pitching you as a flagship deployment; we're proposing a structured 60-student opt-in cohort at your school in spring, parallel to ours, so you're not the only one and we have two data points to learn from. The pilot price is zero; the production price is on the second contract, after you've seen the lift."
- **Proof point needed:** A signed pilot agreement with Bryant. A director-of-advising willing to take a reference call. A quantitative pilot result (time-to-schedule, completion rate, NPS) before any second-school conversation goes commercial.

---

### 8. "Who are you, exactly?" (founder is a sophomore)

- **Real concern underneath:** "Will you be here in 18 months when our contract is up for renewal? Am I betting on a kid?"
- **Credible response:** "I'm a sophomore Finance major at Bryant. I built this solo in six hours for our AI hackathon and it's been hardened since — strict TypeScript, Pydantic v2 schemas, rate limiting, prompt-injection defense, accessibility audited. I'm clear-eyed: I am not a 35-year-old SaaS CEO. The question isn't whether I'm experienced; it's whether the architecture is sound, the design decisions documented, and the pilot results real. All three are checkable today. I'm also not asking you to bet a budget on me — I'm asking you to bet a free pilot. The commercial conversation is after Bryant's data lands."
- **Proof point needed:** Signed and public ADRs. A code repository the CIO's team can audit. A written commitment from a faculty advisor or technical mentor on the project. A roadmap doc that addresses the "what happens at graduation" question (see #9).

---

### 9. "What's your roadmap when you graduate?"

- **Real concern underneath:** "Continuity risk. Vendors that disappear cost us more than vendors we never bought."
- **Credible response:** "Three answers. First, the IP and the codebase are designed to be transferable from day one — there's no founder-only knowledge. Second, between now and 2029 the realistic paths are: (a) a co-founder with operational depth joins post-pilot; (b) the project is acquired by a higher-ed vendor that already has the sales motion (Stellic, Coursedog, Pathify are the obvious candidates); or (c) the codebase is structured so Bryant or a peer institution can fork and self-host under an MIT or Apache license. We can write that fork-and-self-host clause into the pilot agreement so you're never trapped. Third, the deterministic core — the solver, the requirement DSL — is plain Python you could maintain in-house with one developer."
- **Proof point needed:** A written exit-and-continuity plan attached to the pilot MSA. A source-escrow clause or an explicit "you can fork on termination" license grant. A short list of named potential successors (advisors, hiring plan).

---

### 10. "We'd need to see HECVAT and SOC 2."

- **Real concern underneath:** "Procurement will not let me sign anything without these. This is a hard gate."
- **Credible response:** "Today: we don't have either. Realistically, neither does most of the AI vendor landscape your team is currently fielding requests on. What we can offer right now is a HECVAT Lite response and a written security architecture document covering the items HECVAT actually asks about — encryption, authentication, data handling, vendor subprocessors, breach notification. SOC 2 Type II is a 12–18 month process and is on the roadmap once we have three paying institutions; for our first paid pilot it's bundled into the contract as a milestone rather than a precondition. We'd rather price honestly and earn the audit than hand-wave it."
- **Proof point needed:** A completed HECVAT Lite (https://www.educause.edu/hecvat). A 4-page security architecture brief. A written, dated SOC 2 plan from a named auditor (Prescient Assurance, Sensiba, A-LIGN are common). A subprocessor list (Anthropic, AWS or GCP, Vercel).

---

### 11. "We're a Workday Student / PeopleSoft school. You only support Banner."

- **Real concern underneath:** "Even if I love this, my SIS is not yours and integration is where projects die."
- **Credible response:** "True today — the Bryant pilot uses Banner section data scraped from Self-Service. The architecture is SIS-agnostic at the boundary: the catalog ingestion is a JSON contract, not a Banner contract. For Workday Student, the analogous integration is the Course Catalog API; for PeopleSoft Campus Solutions, it's the Class Search service. We'd add the connector during the pilot, with the institution's data team providing read credentials. The solver, the UI, and the AI layer are unchanged. Adding a second SIS connector is on the order of one engineering week, not one quarter."
- **Proof point needed:** A scoped integration spec for the second SIS, written before the conversation. An estimated effort and a named engineer responsible (even if it's still Owen). Reference to Ellucian Ethos or Workday Extend documentation showing the API surface.

---

### 12. "Our students don't want another app. We can barely get them into Navigate."

- **Real concern underneath:** "Adoption fatigue. We've spent on EAB and they don't log in."
- **Credible response:** "We're not asking for a separate login or a separate app habit. The student touches Pathfinder once a semester at the moment of registration — that's it. The acquisition path is a link in the registration-prep email your registrar already sends. Median session is under three minutes. We measure success by *time-to-schedule reduction* and *registration-day stress score*, not by daily-active users — because daily-active is the wrong metric for a tool you use four times a year."
- **Proof point needed:** A funnel measurement from the Bryant pilot: emails sent, students clicked, schedules generated, schedules used. A named metric the Provost actually cares about (e.g., "% of students registered before drop/add closes").

---

### 13. "What about students with accommodations or atypical paths?"

- **Real concern underneath:** "Accessibility, ADA, and equity scrutiny. If this works only for the median student, we get a complaint."
- **Credible response:** "Accessibility was designed in, not bolted on — WCAG AA contrast verified, focus-trapped modals, aria-modal patterns, full keyboard navigation. For atypical paths — transfer credits, course substitutions, double majors, accommodations like reduced-course-load — the solver respects whatever the Degree Works audit says, including substitutions the advisor has already approved. Edge cases (a student who needs a specific room type, or whose schedule is constrained by a job) are handled through the preferences layer: blocked days, time windows, and free-text natural-language preferences that the negotiator agent reads."
- **Proof point needed:** An accessibility audit by a third party (Deque, Level Access). Documented testing with the Disability Services office at Bryant. A free-text preference example library that proves edge cases work ("I have a 2pm kid pickup every Tuesday and Thursday").

---

### 14. "We are focused on retention this year. This isn't on the priority list."

- **Real concern underneath:** "I have one budget cycle of attention. AI scheduling sounds like a nice-to-have, not retention."
- **Credible response:** "Course-registration friction is *the* under-measured retention lever. The students who drop out between sophomore and junior year disproportionately are the students who could not get the courses they needed last spring. The 5-year and 6-year graduation rate gap is partially a scheduling failure dressed up as something else. We're not pitching against retention; we're pitching as a retention tool with a measurable outcome — % of students who get into all four required courses on first registration attempt."
- **Proof point needed:** A retention-framed case study from a peer institution, even if it has to come from EAB or Civitas published research (https://www.eab.com/research/student-success/). The Bryant pilot needs a registration-success metric, not a satisfaction metric, in the success criteria.

---

### 15. "We can't justify a per-student fee for something students could do themselves."

- **Real concern underneath:** "Pricing fight. The CFO will benchmark this against existing tools and ask why."
- **Credible response:** "We don't price per student. Pilot is free. Production is a flat institutional license tiered on enrollment band, comparable to what you pay for Degree Works seat licensing — typically in the low five figures for a school your size, well under the cost of one academic advisor's time on registration prep. The ROI math is in the advisor hours saved and the registration-cycle support tickets avoided, not in student fees."
- **Proof point needed:** A defensible pricing sheet. A benchmark against Stellic, Coursedog, and Pathify list prices. An advisor-hours-saved measurement from the Bryant pilot.

---

## Part 2 — Three Positioning Statements

These are written as Owen would actually say them, out loud, in 90 seconds. No marketing voice.

### For a Provost (career-and-graduation-rate framing)

"Most students at most universities lose between two and six weeks per academic year to one specific problem: figuring out which courses they need, which sections fit, and how to register without a time conflict. At Bryant we watched sophomores spend three nights in front of Degree Works with thirty browser tabs open. The students who fail at this don't fail dramatically — they pick up a 12-credit semester instead of 15, they take a course out of sequence, they push graduation to spring of senior year-plus-one. That's where your six-year graduation rate lives. Pathfinder reads the Degree Works audit you already own and produces three conflict-free schedules in two seconds, with the explanation a student needs to commit. We're piloting at Bryant this fall, free, opt-in, 50 students. The metric we'd ask you to care about is the percentage of students who finish registration with a full credit load that matches their plan — not satisfaction, completion. I'd like 30 minutes with you and your advising director to scope it."

### For a Director of Academic Advising (workload-relief and student-experience framing)

"Your advisors spend the two weeks before registration in thirty-minute appointments doing the same workflow over and over: pull up the audit, open the schedule of classes, look up RateMyProfessors, check time conflicts, repeat. Pathfinder does the mechanical part of that meeting before the student walks in. The student arrives with three drafts already built, ranked by fit, with the professor data and workload estimates on screen. Your advisor is now coaching, not section-shopping. We don't replace you — your office is still the system of record, the student still hits 'register' in Banner themselves, and you still approve the audit. We just give back the hours your team currently burns on logistics. Our pilot at Bryant this fall is opt-in for both advisors and students. I'd like to know which two of your advisors would be the right ones to run this with."

### For a CIO (security, integration, vendor risk framing)

"I know what's in your inbox, so I'll be direct. Pathfinder is a Next.js plus FastAPI app, single tenant per institution, deployable in your AWS or GCP environment with Anthropic running through Bedrock or Vertex, so no student data leaves your cloud. We sign a FERPA school-official agreement. We have a HECVAT Lite ready and SOC 2 Type II planned with a named auditor as a contract milestone. The integration footprint is one read-only connector to your SIS — Banner today, Workday or PeopleSoft on a one-week add. There's no SIS write-back, no SSO requirement we can't meet via SAML or Entra, and no PII retention beyond the registration cycle. The pilot is free and time-boxed. The thing I want from you specifically is 20 minutes to walk through the data-flow diagram and the failure modes, before we ever talk to procurement."

---

## Part 3 — One-Page Narrative Arc

For any pitch deck, sales conversation, or campus-visit meeting. Six beats, in order.

1. **The pain.** "Last spring, I watched my roommate spend a Sunday night with thirty Banner tabs open, a Degree Works PDF on his second monitor, and a notebook of pencil-drawn weekly grids. He still ended up in a section that conflicted with his lab. He's not stupid — the workflow is broken. Ask any sophomore at any school. They'll tell you the same story."

2. **The gap.** "Universities have already paid for two systems: Degree Works tells you *what* to take, Banner lets you *register* for it. Nothing connects them. The student is the integration. Advisors are the integration. That's the gap."

3. **The bet.** "Pathfinder reads the audit you already have, expands the requirements with a deterministic rule engine, solves the time-conflict problem with pure Python (the solver cannot return a conflicting schedule, period), and uses Claude only where language and judgment matter — parsing the screenshot, writing the explanation, ranking three valid candidates. The combinatorial math is Python. The voice is Claude. We don't blur that line."

4. **The wedge.** "We start at one school — Bryant — with one course catalog (291 sections), one cohort (50 opt-in students, fall semester), and one outcome metric (registration completion on first attempt). We don't try to support every SIS or every institution from day one. We win the wedge, then we earn the next school."

5. **The proof.** "After the Bryant pilot we'll publish three numbers: median time-to-schedule, percentage of students who registered for their full credit load on first attempt, and advisor hours returned. If the numbers don't move, we don't pitch a second school. If they do, we have something to point at."

6. **The ask.** "What I need from you today is 30 minutes on your calendar with your advising director, an introduction to your registrar, or — if you're a CIO — a walkthrough of your SIS read-credentials process. I'm not asking for budget, I'm not asking for a contract. I'm asking for the conversation that lets me come back with the pilot proposal."

---

## Part 4 — Rebuttals to Soft No's

Soft no's are how higher ed rejects you. They look like maybe. Each gets a reframe, in Owen's voice.

### "Interesting, send me a deck."

- **Reframe 1:** "Happy to. I'll send a 6-pager today, but I'd rather get 20 minutes on your calendar with the advising director in the room — the deck flattens the most important parts. Can your assistant find a 20-minute window in the next two weeks?"
- **Reframe 2:** "Sending. Can I include two specific questions in the email so you can respond async? Saves a meeting if the answer's no, makes the meeting sharper if the answer's yes."
- **Reframe 3:** "Will do. Quick check before I send: who else on your team should be on the email so I'm not making you the forwarding bottleneck?"

### "Let me run it past my team."

- **Reframe 1:** "Of course. Who specifically — registrar, advising, IT? I'll send tailored one-pagers for each so the conversation starts with the relevant context, not a generic deck."
- **Reframe 2:** "Helpful — and I want to make that easier. Can I draft a 5-line internal summary you can paste into the email or Slack thread? Removes the writing tax for you."
- **Reframe 3:** "Totally. What's the realistic timeline on that conversation? I'd rather know if it's two weeks or two months so I can follow up at the right moment instead of pestering you."

### "We're focused on retention this year."

- **Reframe 1:** "That's exactly the framing I'd want to be on the agenda for. The students who slip on retention disproportionately slip at registration — they take 12 credits instead of 15, fall behind, and never catch up. The Bryant pilot's success metric is on-time-credit-load, not satisfaction. Can I send the one-pager that connects scheduling friction to the retention number you're already reporting on?"
- **Reframe 2:** "Understood. If retention's the lens, the 90-second version is: this is a registration-completion tool framed as a productivity tool. Different sales conversation, same product. Want me to come back with the retention-framed pitch?"
- **Reframe 3:** "Got it. Then maybe the right person isn't you — it's whoever owns retention metrics. Who's that on your team and is a warm intro reasonable?"

---

*End of file. Inline sources used: EDUCAUSE Top 10 IT Issues (https://www.educause.edu/research-and-publications/research/top-10-it-issues), 2024 EDUCAUSE AI Landscape Study (https://www.educause.edu/ecar/research-publications/2024/2024-educause-ai-landscape-study/introduction-and-key-findings), HECVAT (https://www.educause.edu/hecvat), Anthropic privacy (https://www.anthropic.com/legal/privacy), EAB student success research (https://www.eab.com/research/student-success/), Inside Higher Ed AI coverage (https://www.insidehighered.com/news/tech-innovation/artificial-intelligence).*
