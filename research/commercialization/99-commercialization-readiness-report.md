# 99 — BryantPathfinder Commercialization Readiness Report

> Synthesis of files 00–07. Threshold for "ready" throughout this report is **a paid pilot at a second, non-Bryant institution** — not the sanctioned Bryant pilot, and not a multi-tenant SaaS. Decisions, not options.

---

## 1. Verdict

BryantPathfinder is **not** commercialization-ready against the second-institution paid-pilot threshold today, and will not be in the next 90 days. The product itself is unusually strong for its stage — the deterministic-solver-plus-Claude split (file 00, ADR 0003) is a defensible architectural insight, the data foundation covers 97% of Bryant instructors and 291 live sections, and the engineering hardening (Pydantic v2, rate limiting, prompt-injection defense, WCAG AA) is well past hackathon-grade. What is missing is everything *around* the product: no legal entity, no FERPA-compliant data flow, no HECVAT, no SOC 2, no SSO, no multi-tenancy, no Degree Works REST integration, no second SIS, no insurance, no reference customer, and no founder bandwidth because Owen is a sophomore through May 2029. The next six months should be spent converting Bryant into a sanctioned, published pilot and clearing the cheapest 80% of the compliance gates in parallel. A second paid pilot is realistically a Q1 2027 event, gated on Bryant pilot data plus a NACADA October 2026 presentation. A multi-tenant SaaS conversation is a 2028 event.

| Dimension | Score | One-line justification |
|---|---|---|
| Product depth | **Green** | Solver + Claude split solves a real, repeated, unpriced pain (file 00, file 03 wedges). |
| Data foundation | **Yellow** | 291-section Bryant catalog and 97% RMP coverage are real (file 00); zero coverage at any second institution and no live SIS pull (file 05). |
| Multi-tenancy & integrations | **Red** | Single-tenant, static JSON, screenshot ingest, no SSO, no Ethos, no Degree Works REST (file 00, file 05). |
| Compliance (FERPA, HECVAT, SOC 2) | **Red** | Non-compliant with §99.31 in any institutional sense; no HECVAT submitted; no SOC 2 of any type (file 02). |
| Security posture | **Red** | No entity to sign a DPA, no audit log, no retention/deletion policy, no cyber insurance, no penetration test (file 02 §6). |
| Pricing & packaging clarity | **Yellow** | Three coherent models proposed (file 03); none yet picked, no price on a website, no website. |
| Distribution capability | **Red** | Solo founder, no warm network outside Bryant, no published case study, no NACADA platform (file 04). |
| Founder fit / capacity | **Yellow** | Owen built the product solo and understands the architecture cold; he is also a full-time sophomore with no co-founder and no enterprise-sales experience (file 00, file 04). |

---

## 2. Top 10 Gaps, Ranked by Severity

1. **No corporate entity.** Pathfinder cannot sign a school-official agreement, hold cyber insurance, execute an Anthropic Zero-Data-Retention addendum, or accept payment as Owen-personally. **Why it blocks:** every downstream gate (FERPA, HECVAT, SOC 2, NET+, insurance) requires a counterparty that exists in law. **Cost to close:** Stripe Atlas Delaware C-Corp, ~$500 + $250/yr Delaware franchise; 1–2 weeks elapsed (file 02 item #1). **Owner:** Owen, this month.

2. **No FERPA-compliant data flow.** Audit content (student name, ID, GPA) is sent to the Anthropic API today with no school-official agreement, no §99.33 flow-down to Anthropic, no ZDR addendum, and no audit log (file 02 §1.7). **Why it blocks:** any sanctioned deployment — including the Bryant pilot — is non-compliant on day one without it. **Cost to close:** $2K–$8K legal + 4–8 weeks for Bryant DPA negotiation; ZDR addendum included with Anthropic enterprise tier (file 02 items #2, #3, #5, #6). **Owner:** Owen + Bryant General Counsel + Anthropic enterprise sales.

3. **No HECVAT 4 submission.** Every institution outside Bryant requires this before procurement opens a folder (file 02 §5.1, file 04 §3). **Why it blocks:** procurement gate at every R1, every regional comprehensive, and most community colleges. NET+ listing also requires it. **Cost to close:** 80–160 hours self-effort or $5K–$15K outsourced; 6–12 weeks elapsed (file 02 item #10). **Owner:** Owen, draftable in parallel with Bryant pilot.

4. **No SOC 2.** Required by virtually every R1; required by most regional comprehensives; sometimes waived for sub-$50K liberal-arts deals (file 01 §3, file 02 §5.2). **Why it blocks:** without at least Type I in flight with a named auditor, the second-school CIO conversation stalls at the security-review gate. **Cost to close:** Type I ~$15K–$30K, 3–4 months. Type II adds ~$40K–$90K all-in over 12–15 months (file 02 items #11, #14). **Owner:** Owen + Vanta or Drata + named auditor (Prescient, Sensiba, A-LIGN per file 07).

5. **No multi-tenancy.** The codebase is single-tenant: one `sections.json`, one institution, one set of secrets (file 00, file 05 §7). **Why it blocks:** a second institution cannot be onboarded without per-tenant catalog, per-tenant auth scope, per-tenant audit log, and per-tenant config. Every HECVAT response will fail without it. **Cost to close:** 4–6 person-weeks engineering (file 05 MVI table). **Owner:** Owen, summer 2026.

6. **No SSO.** Single-fixture demo with no SAML, no Shibboleth, no Entra (file 00, file 05 §4). **Why it blocks:** no campus IT will sanction a tool that asks for new credentials, even at Bryant beyond N=5 students. **Cost to close:** 1–2 weeks for single-tenant SAML against Bryant Shibboleth using `python3-saml` for the pilot; 6–10 weeks for multi-tenant; or use WorkOS for the first paid pilot at $0.50–$5/MAU (file 05 §4.2). **Owner:** Owen, May 2026.

7. **No Degree Works REST integration.** Today Pathfinder ingests audits via Claude Vision on a screenshot — fragile, FERPA-exposed, and demo-risky (file 00, file 05 §2.1). **Why it blocks:** every CIO will ask "why are you OCRing a screenshot when the data is in our database?" The answer "we haven't built that yet" is fine for Bryant; it's disqualifying for paid pilot #2. **Cost to close:** 4–5 person-weeks for `getAudit` REST integration plus service-account provisioning (file 05 MVI). **Owner:** Owen, summer 2026.

8. **No second-SIS support.** Banner is 24% market share (file 05 §1.1). 76% of the market needs Workday Student, PeopleSoft, Colleague, or Jenzabar. **Why it blocks:** narrows the addressable second-pilot pool to Banner+Degree-Works campuses, of which the right targets are Bentley, Babson, Providence College, Stonehill, and similar Northeast privates (file 04 §6). **Cost to close:** stay Banner-only for 12 months; defer per file 05 §9 recommendation. **Owner:** Defer until paid customer #2 is signed.

9. **No reference customer / no published pilot data.** Bryant pilot has not run; no advisor co-signer; no time-to-schedule metric, no registration-completion delta, no NPS (file 04 §6, file 07 objection #7). **Why it blocks:** every cold email and every conference conversation post-Bryant-pilot converts at 5–10x the rate of the same email pre-pilot. **Cost to close:** signed College of Business MOU by May 1, 2026; pilot runs Aug–Nov 2026; case study published by November (file 04 §9). **Owner:** Owen + Bryant Director of Academic Advising + Provost Paliwal.

10. **Founder is full-time student through May 2029.** Solo, no co-founder, no warm network outside Bryant, summer May–August is the only contiguous build window (file 00, file 04 §9). **Why it blocks:** every other gap above competes for the same hours. Realistic capacity is ~15 hrs/week during the academic year and ~50 hrs/week May–August. **Cost to close:** structurally unfixable until either (a) the project is acquired, (b) Owen takes a leave, or (c) a co-founder with operational depth joins post-pilot (file 07 objection #9). **Owner:** Owen, post-pilot decision in Q4 2026.

---

## 3. 30-60-90 Day Action Plan

**Day 1–30 (now through late May 2026)**

1. **Incorporate as a Delaware C-corp via Stripe Atlas; execute founder IP assignment.** → Legal entity capable of signing (closes gap #1).
2. **Deliver one-page brief in person to Provost Paliwal and the Bryant Director of Academic Advising; secure a sanctioned, opt-in, 50-student fall pilot MOU with the College of Business by May 1.** → Signed MOU (closes gap #9, unblocks gap #2).
3. **Open a Bryant data-sharing memo conversation with Bryant General Counsel; designate Pathfinder a §99.31(a)(1)(i)(B) school official with sub-processor flow-down to Anthropic.** → Draft memo in legal review (closes gap #2).
4. **Initiate Anthropic enterprise sales conversation; execute Zero-Data-Retention addendum at signature stage.** → ZDR contract executed (closes gap #2, file 02 item #3).
5. **Buy a $1M cyber + tech-E&O policy at the Bryant level; quote $5M policy for second-school readiness.** → Policy in force (closes gap #2 sub-item, file 02 item #9).
6. **Submit NACADA 2026 concurrent-session proposal co-authored with a Bryant advisor before the spring CFP closes.** → Proposal accepted by July (unblocks distribution per file 04 §9, closes gap #9 distribution sub-item).
7. **Apply to LearnLaunch (rolling) and start tracking the GSV Cup 2027 fall application window.** → Pipeline of soft-money options open (file 04 §7).

**Day 31–60 (June 2026)**

1. **Build multi-tenancy primitives: tenant-scoped audit log, deletion endpoint, magic-link auth, per-institution config table.** → Bryant-only multi-tenant (closes gap #5 partially).
2. **Stand up Bryant Shibboleth SAML SSO using `python3-saml` against the Bryant IdP; document the SP metadata exchange.** → SSO live for Bryant pilot (closes gap #6 for Bryant).
3. **Begin Degree Works REST integration: provision Bryant service account for `ArticulateAuditService`; parse PESC `RequestDA` XML deterministically.** → Vision path becomes the fallback, not the primary (closes gap #7).
4. **Engage Vanta or Drata; start the SOC 2 Type I readiness window with a named auditor.** → Audit clock running (closes gap #4).
5. **Draft HECVAT 4 questionnaire to 80% complete using the file 00 baseline as raw material; submit triage version to a friendly CIO for a redline.** → Submittable HECVAT (closes gap #3).
6. **Identify next 10 Banner+DegreeWorks Northeast targets per file 04 §9 (Bentley, Babson, Providence College, Stonehill, Assumption, Salve Regina, Roger Williams, Suffolk, Saint Anselm, Endicott); cold-email a single advisor at each — not the Provost — with the Bryant brief.** → 2–3 discovery calls booked (closes gap #9 distribution sub-item).
7. **Apply to the Ellucian Partner Network Build track and the Instructure Edtech Collective.** → Partner conversations open (file 04 §8).

**Day 61–90 (July–August 2026)**

1. **Ship Bryant pilot v1 to the College of Business for advisor sign-off; instrument the four metrics that go in the case study — time-to-schedule, registration-completion-on-first-attempt, advisor hours returned, NPS.** → Pilot live (closes gap #9).
2. **Soft-launch to 50 sophomore opt-ins via the Associate Dean's distribution list in the first week of August.** → 50 students enrolled (closes gap #9).
3. **Complete EDSAFE AI Industry Council application; publish a public AI transparency model card per NIST AI RMF Map artifact (file 02 §3.1).** → Procurement-credibility signal (closes gap #4 sub-item, gap #3 sub-item).
4. **Publish the privacy notice, sub-processor disclosure page, and incident-response runbook on the Pathfinder marketing site (which also gets built this quarter).** → Public compliance posture (closes gap #2 sub-items, file 02 items #4, #19, #20).
5. **Lock pricing: Bronze $30K / Silver $75K / Gold $175K flat institutional license, posted on the website with a "free pilot" call-to-action.** → Defensible pricing on paper (closes gap "Pricing & packaging clarity" yellow status).
6. **Submit EDUCAUSE 2027 session proposal "An AI Course Scheduler That Actually Knows Your Catalog" before the late-summer CFP.** → Speaker slot pipeline (file 04 §9).
7. **Triage decision at end of August: if SOC 2 Type I is on track and HECVAT is submittable, proceed with second-school discovery in September. If either is slipping, push the second-school motion to January 2027.** → Honest gate before NACADA October 2026.

---

## 4. First 5 Target Campuses

**1. Bryant University** — Small private liberal-arts/business, AACSB, ~3,800 undergrads, Banner+Degree Works, MSCHE-accredited. Owen has direct access; the Provost is the only person on Earth who can sanction a Pathfinder pilot using a real Bryant student's audit (file 01 §1.h). **Named buyer:** Dr. Rupendra Paliwal, Provost and Chief Academic Officer (file 01 §4). **What to ask for:** signed MOU with the College of Business for an opt-in fall 2026 pilot, no money, anonymized results publishable. **Unlock:** in-person 30-minute meeting before May 1, 2026, with the Director of Academic Advising in the room.

**2. Bentley University** — Small private business-focused (5,500 students), Waltham, MA, AACSB, Banner. Closest peer to Bryant in mission and curriculum; advising staff visible on NACADA Region 1 listservs. **Named buyer:** Director of Academic Advising in the McCallum Graduate School and Undergraduate College — start with the role, not the Provost (file 04 §1, file 04 §6). **What to ask for:** spring 2027 opt-in pilot with 60 sophomores from the business core, structured parallel to the Bryant cohort, $5K one-time pilot fee out of dean's discretionary funds (file 06 §5.4). **Unlock:** Bryant pilot's published time-to-schedule and registration-completion numbers + an introduction from a Bryant advisor to a Bentley counterpart at NACADA October 2026.

**3. Maricopa Community Colleges** — Largest community college system in the U.S. (10 colleges, ~140,000 students), Banner, registration friction is most acute in this segment per file 01 §3. **Named buyer:** Dr. Jess Evans, Vice Chancellor and CIO (file 01 §4). She has explicitly stated she wants to move "beyond AI-washing to responsible innovation," which maps to Pathfinder's deterministic-solver-plus-Claude positioning. **What to ask for:** scoped 90-day evaluation at one Maricopa college (Phoenix College or Mesa Community College), with Maricopa system IT validating the FERPA-compliant integration. **Unlock:** completed HECVAT 4 + SOC 2 Type I in flight + Bryant case study + a 20-minute call by Q1 2027.

**4. Providence College** — Small private (4,000 undergrads), Banner+Degree Works, Rhode Island, 25-minute drive from Bryant. NECHE-accredited, similar buying-committee shape to Bryant per file 01 §3. **Named buyer:** Associate Dean for Academic Services (or equivalent advising lead). **What to ask for:** an unpaid letter-of-interest pilot for fall 2027 contingent on a successful Bryant-and-Bentley reference pair. **Unlock:** Owen drives down for a 30-minute coffee in October 2026 with two Bryant advisors who can vouch for the workflow change.

**5. Arizona State University (long-shot reference call, not a pilot target)** — R1, ~80,000 undergrads, public ASU is the AI-in-higher-ed press reference. The realistic ask is *not* a pilot; ASU has 15-person AI Acceleration team building competing in-house tools (file 01 §4). **Named buyer:** Dr. Elizabeth Reilley, Executive Director of AI Acceleration — operator-level, evaluates dozens of vendors monthly. **What to ask for:** a 20-minute consultation call to pressure-test the architecture. **Unlock:** post-Bryant-pilot data + a peer-builder framing rather than a vendor framing. Reilley's feedback is the highest-quality external signal Owen can buy with one cold email; if it converts to a champion, ASU is a year-three deal, not a year-one deal.

---

## 5. Pricing Recommendation

**One sticker structure: Bronze $30,000 / Silver $75,000 / Gold $175,000 flat-rate annual institutional license**, tiered by undergraduate FTE bands at <3,000 / 3,000–15,000 / 15,000+. Pilot is free for the first 90 days at any tier. No per-FTE surcharge, no per-seat fee.

This synthesizes file 03's Model B (procurement-friendly flat tiers) with file 06's payback math (a 4,000-FTE school recovers ~$140K/year in advisor capacity and replacement-cost savings, so a $30K Bronze price has sub-3-month payback even without claiming retention lift) and file 07 objection #15 (Owen needs to say "low five figures" and have a number behind it). File 03 also proposed a $25K/$75K/$200K version and a $8/FTE per-FTE long-term version; the synthesis ladder $30K/$75K/$175K resolves the contradiction by keeping the flat-tier procurement story but pulling the Gold tier slightly down to stay below EAB Navigate360's $278K Austin Peay benchmark (file 03) and pushing Bronze slightly up to clear $25K psychological pricing. Per-FTE pricing is the year-three growth-stage move once a sales motion exists.

---

## 6. Honest Assessment

**Where BryantPathfinder will lose to incumbents.** Pathfinder loses to **Stellic** in any deal at a Banner+Degree-Works R1 where the Provost has already signed an audit-replacement MSA — Stellic now ships its own scheduling product (Stellic Progress, launched Fall 2026 at Indiana University per file 05 §2.2), the procurement gravity is on Stellic's side, and the deal economics on the second product are bundled. Pathfinder loses to **EAB Navigate360** at any institution where the CFO already has an EAB line item and is unwilling to add a second student-success vendor — EAB's $278K Austin Peay contract pattern (file 03) shows that once a school is committed to Navigate, additional advising spend goes through EAB regardless of feature gap. Pathfinder loses to **Ellucian Degree Works** in any RFP that frames the problem as "audit + planner" rather than "scheduling autopilot" — Degree Works is an Ellucian Partner Network deal where the institution gets a 15–25% module add-on bundled with Banner SaaS renewal (file 03), and procurement teams will choose the single-vendor relationship by default. Pathfinder will also lose at every institution running Workday Student, PeopleSoft Campus Solutions, Colleague, or Jenzabar for the next 12–24 months because Pathfinder has zero integration on those SISes (file 05 §1).

**Where BryantPathfinder can win.** Pathfinder wins at **small private Banner+Degree-Works business schools in the Northeast** (Bryant, Bentley, Babson, Providence College, Stonehill, Saint Anselm, Endicott — file 04 §9). These institutions: (a) have the simplest buying committee, often one person wearing Provost-and-CIO hats (file 01 §3); (b) have low-five-figure budget thresholds where a $30K Bronze license fits in a dean's discretionary fund without procurement-committee involvement (file 06 §5.4); (c) are AACSB-accredited with finite course catalogs (~80–150 courses) that match Pathfinder's data-foundation pattern; (d) have NECHE accreditation rather than the more AI-policy-mature SACSCOC or HLC, meaning faster decisions; and (e) typically don't already own Stellic. The wedge is "**ride-along with Degree Works, not replace it**" (file 03), targeted at the **Director of Academic Advising or Associate Dean of the College of Business** as champion — never the Provost as primary buyer (file 04 §1) — with the Bryant pilot's registration-completion-on-first-attempt metric as the headline number. The single defensible technical moat is the deterministic Python solver: any LLM-only competitor (Element451, Mainstay) will eventually return a time-conflicted schedule, and Pathfinder physically cannot (file 03 wedge #1, ADR 0003).

---

## 7. The One Decision

**If Owen does only ONE thing in the next 30 days, it should be: secure a signed, sanctioned, opt-in fall 2026 pilot MOU with the Bryant College of Business, designating Pathfinder a FERPA §99.31(a)(1)(i)(B) school official, by May 1, 2026.**

That single document unlocks every other gate. Without it, the FERPA architecture is theoretical, the HECVAT is unanswerable on the institutional-control questions, the cold emails to Bentley and Maricopa stall at "send us a reference," the NACADA 2026 session proposal is rejected for lack of pilot data, the SOC 2 readiness audit has nothing to point at, the Anthropic ZDR conversation has no contracting party on the school side, and Internet2 NET+ has no sponsor institution. With it, every one of those becomes a parallel workstream rather than a sequential blocker. Owen has the access — Provost Paliwal is one walk across the Smithfield campus, the Director of Academic Advising is one introduction, the General Counsel is one warm intro from Paliwal. The 60-second version of the ask, in Owen's voice from file 07 Part 3, is already written. The only remaining work is to put it on a calendar before the semester ends.
