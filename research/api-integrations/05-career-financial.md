# 05 — Career, Outcomes & Financial APIs

> Subagent A5 deliverable for the BryantPathfinder API integration swarm.
> Pathfinder today optimizes "what do I take this semester?" The bigger question — *"is this major and these electives going to get me a job, and is it worth the money?"* — sits one layer up. This file inventories the APIs that could close that gap, ranks them by pilot-stage value-for-effort, and maps each to a concrete Pathfinder feature.

---

## Framing — why this layer matters for Pathfinder

Today the solver returns a conflict-free 15-credit schedule. It does *not* answer:

- Will FIN 470 (Investments) actually help me get an IB analyst seat?
- Are Bryant Finance grads with a CIS minor earning more than ones who picked Marketing?
- Is the median wage for my major above the all-in cost of attendance, debt-adjusted?
- What scholarships am I leaving on the table given my GPA and major?

Adding even a thin career-outcomes layer would change which *electives* a student picks — and elective selection is exactly the decision Pathfinder mediates. That makes this layer unusually high-leverage: small data integration, real influence on the student's choices.

The brief asked me to be skeptical of expensive enterprise APIs at pilot scale. I am. The recommendation up top: build v1 from public-data combos (BLS + College Scorecard + the NCES CIP/SOC crosswalk), ignore Lightcast and LinkedIn Talent Insights until there is paying revenue, and treat Handshake EDU API as a campus-relationship play rather than an integration to ship from a laptop.

---

## 1. Career outcomes data (public, free, durable)

### 1.1 BLS Public Data API — Occupational Employment & Wage Statistics

- **URL:** https://www.bls.gov/developers/home.htm , https://www.bls.gov/oes/
- **Auth:** Free registered API key (email + organization). Public Data API v2.0.
- **Limits:** 500 queries/day per registered key, up to 50 series and 20 years per request. Historical OEWS data tied to the 2018 SOC; May 2024 estimates are the latest annual OEWS release (per https://www.bls.gov/developers/home.htm and https://www.bls.gov/oes/).
- **Coverage:** ~830 detailed occupations, national + state + MSA wages and employment. Separate Employment Projections series gives 10-year projected growth by SOC.
- **Licensing:** US government work, public domain. Display, republish, redistribute — all fine. Attribution requested.
- **Integration effort:** Tiny. One Python script at build time pulls the OEWS series for the ~50 SOC codes mapped to Bryant majors and writes a static `occupations.json`. No runtime API calls needed.
- **Pathfinder feature unlocked:**
  - On the Preferences page, when a student selects a major: *"Finance majors most commonly become Financial Analysts (median $99,890), Personal Financial Advisors ($99,580), or Financial Managers ($156,100). Projected 10-yr growth: 8–17%."*
  - On the Schedule page, tag courses that align with high-wage SOCs ("aligns with: Financial Analyst, +13% growth").

### 1.2 O*NET Web Services — skills, knowledge, work activities

- **URL:** https://services.onetcenter.org/ , https://www.onetcenter.org/database.html
- **Auth:** Free registration; email + app description. 5,100+ registered users (per https://services.onetcenter.org/about). API v2.0; XML by default, JSON with `Accept: application/json`.
- **Coverage:** 900+ occupations, the full O*NET database (skills, abilities, knowledge, tasks, work activities, technology skills, "Bright Outlook" flags, salary, education).
- **Licensing:** Free, federally-funded, redistributable with attribution to O*NET.
- **Integration effort:** Small. Best used as a one-time pull, not live. Cache the skill profile per occupation.
- **Pathfinder feature unlocked:**
  - "Courses you've taken so far cover 6 of the 12 skills O*NET lists for Financial Analyst. The 3 highest-impact skills you're missing — Critical Thinking, Complex Problem Solving, Mathematical Reasoning — map to the following electives."
  - This is the most defensible *curriculum-recommendation* engine you can build without proprietary data, because the O*NET skill ontology is the federal standard.

### 1.3 U.S. Census ACS — wages by field of bachelor's degree

- **URL:** https://api.census.gov/ , 2022 ACS Detailed Tables: https://www.census.gov/data/tables/2022/demo/educational-attainment/acs-detailed-tables.html , Field-of-Degree report ACS-59 (2025): https://www.census.gov/library/publications/2025/acs/acs-59.html
- **Auth:** Free API key, generous rate limits.
- **Coverage:** Median annual earnings by field of bachelor's degree, age, sex, demographics. National only at field-of-degree granularity.
- **Licensing:** Public domain.
- **Integration effort:** Minimal — single CSV pull, store statically.
- **Pathfinder feature unlocked:** Headline number on the Preferences page: *"Median earnings for Finance majors aged 25–34: $78,400 (national, ACS 2022)."* A grounded, source-attributed number is a credibility-builder no LLM-generated salary estimate can match.

### 1.4 College Scorecard — program-level wage outcomes

- **URL:** https://collegescorecard.ed.gov/data/api-documentation/ , https://collegescorecard.ed.gov/data/api/
- **Auth:** Free api.data.gov key.
- **Coverage:** Field-of-Study dataset gives median earnings 1, 4, and 10 years post-completion at the **4-digit CIP × institution** level. Plus debt, completion, repayment.
- **Licensing:** Public domain.
- **Integration effort:** Minimal. One query: `school.name=Bryant University` returns the full program-level outcomes row.
- **Pathfinder feature unlocked:** *"Bryant Finance graduates earn a median $76,300 four years after completion (College Scorecard, latest cohort). Debt-to-earnings ratio: 0.34."* The most powerful single sentence Pathfinder could add to the homepage.
- **Note:** A1 already covers this API for institutional comparisons; the A5-specific use is **wage outcomes**, which is where the API earns its keep.

### 1.5 NCES CIP-to-SOC Crosswalk — major-to-occupation mapping

- **URL:** https://nces.ed.gov/ipeds/cipcode/crosswalk.aspx?y=56 , Excel: https://nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx
- **Auth:** None. Static download.
- **Coverage:** 6-digit CIP-2020 → 6-digit SOC-2018, joint NCES + BLS production. Many-to-many.
- **Licensing:** Public domain.
- **Integration effort:** 30 minutes — pandas-read the xlsx, store as `cip_soc.json`.
- **Pathfinder feature unlocked:** This is the **glue** that makes everything else work. Bryant's Finance major (CIP 52.0801) → SOC 13-2051 (Financial Analyst), 13-2052 (Personal Financial Advisor), 13-2099, 11-3031 (Financial Manager), etc. Without this, BLS and O*NET can't be joined to a major.

**The public-data v1 stack is: CIP/SOC crosswalk + BLS OEWS + O*NET + College Scorecard + ACS. Total cost: $0. Total integration effort: roughly two engineering days. This is the recommended starting point.**

---

## 2. Job-listing data

### 2.1 Greenhouse Job Board API — recommended for v1

- **URL:** https://developers.greenhouse.io/job-board.html
- **Auth:** None for GET endpoints. Public board tokens.
- **Limits:** Cached and not rate limited per Greenhouse docs.
- **Coverage:** Per-company, not aggregate. Companies that use Greenhouse ATS expose `https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs`. Many Bryant-relevant employers (Fidelity, CVS Health, Hasbro, Citizens Bank — all public Greenhouse boards) are reachable.
- **Licensing:** Public job board content, intended for redistribution by partner career sites.
- **Integration effort:** Small. Curate a list of ~40 Bryant-feeder employer boards; pull nightly.
- **Pathfinder feature unlocked:** *"Open analyst roles right now at Bryant-feeder employers requiring skills you'd gain from FIN 470: 12 jobs."* Concrete, current, free.

### 2.2 Adzuna API — aggregate job listings, free tier

- **URL:** https://developer.adzuna.com/
- **Auth:** Free app_id + app_key.
- **Limits:** Free tier exists with reasonable rate limits (Adzuna is intentionally vague about the ceiling; per https://developer.adzuna.com/overview free is suitable for "most use cases"). Endpoints: search, salary histograms, regional vacancy counts, top-companies-by-occupation.
- **Coverage:** US, UK, 10+ other countries. Aggregates from ~50 sources.
- **Licensing:** Free tier permits app integration; redistribution of bulk data prohibited. Display-only.
- **Integration effort:** Small. Salary histogram and "top companies hiring for SOC X near 02917" are the most useful endpoints.
- **Pathfinder feature unlocked:** *"For Financial Analyst roles within 50mi of Smithfield RI, the 25th–75th percentile salary band is $62k–$94k (Adzuna, last 30 days)."* — a *local* salary signal that BLS state averages cannot give.

### 2.3 The Muse API — public, no key, curated employers

- **URL:** https://www.themuse.com/developers/api/v2 , https://www.themuse.com/api/public
- **Auth:** Recently went public — no key required.
- **Coverage:** Curated mid-market employer set, lighter than Greenhouse aggregate.
- **Integration effort:** Trivial. JSON GET.
- **Pathfinder feature unlocked:** Nice-to-have, secondary aggregator. Lower priority than Greenhouse + Adzuna.

### 2.4 USAJOBS API — federal jobs, free

- **URL:** https://developer.usajobs.gov/
- **Auth:** Free key.
- **Coverage:** All federal job openings.
- **Pathfinder feature unlocked:** Niche but high-signal for Accounting / Econ majors interested in Treasury, IRS, FDIC, GAO. Cheap to add.

### 2.5 Indeed Publisher API — DEAD, do not pursue

- The Publisher (Job Search / Get Job) API was deprecated in 2020 and is closed to new integrations (https://developer.indeed.com/docs/publisher-jobs/job-search). What remains is the Job Sync API, which goes the *other* direction — employers pushing jobs *into* Indeed. Not useful for Pathfinder. Skip.

### 2.6 LinkedIn Talent Insights — DO NOT pursue at pilot stage

- **Pricing:** $6,000–$20,000/year minimum; full API suite for partners typically $50k–$300k/year (per https://www.getphyllo.com/post/how-much-does-the-linkedin-api-cost-iv and Vendr 2026 marketplace data).
- **Access:** Limited to approved Talent Solutions Partners; application-gated.
- **Verdict:** This is the gold standard for "X% of Bryant Finance grads work at Goldman" insights, but the price and partner-application gate make it a Series A conversation, not a hackathon-followup conversation. Park it.

### 2.7 Glassdoor API — DEAD

- Public access closed in 2021 (https://www.glassdoor.com/developer/index.htm). Legacy partner API not granting new access. Skip.

### 2.8 Levels.fyi API — useful but tech-heavy

- **URL:** https://www.levels.fyi/api-access/
- **Coverage:** 85+ tech / FAANG / top-tier finance companies. SWE, PM, Data Scientist heavy.
- **Pricing:** Premium / Enterprise tiers, contact-sales (no public price). Apify scraper alternative ~$1.50 per 1,000 records.
- **Verdict:** Mismatched to Bryant's heavily Finance/Accounting/Marketing student body. Levels.fyi shines on tech compensation; Bryant's CIS cohort would benefit, but it's a narrow slice. Defer.

---

## 3. Bryant-specific career data

### 3.1 Handshake EDU API — strategic, not tactical

- **URL:** https://support.joinhandshake.com/hc/en-us/articles/31061076506391-Getting-Started-with-EDU-API
- **Status:** Currently in **beta**, scoped to Career Services partners. Read-only, institution-scoped, supports delta fetching. Access is gated through the institution's Handshake Relationship Manager.
- **Pricing:** Bundled with the institution's Handshake contract; no à-la-carte developer access.
- **Integration effort:** Low *engineering* effort, **high relationship effort**. The blocker is institutional sponsorship, not code.
- **Pathfinder feature unlocked (huge if achieved):** *"73% of Bryant alumni now in Investment Banking analyst roles took FIN 470 and one of [ECON 414, ACG 415]."* This is the killer feature — alumni-curriculum correlation. Nothing else in this document delivers it.
- **Verdict:** **Pursue, but as a Bryant Career Center conversation, not as a code task.** Owen needs a meeting with Bryant's Amica Center for Career Education to scope a sanctioned data-sharing arrangement. Until that exists, this stays parked.

### 3.2 Bryant Career Center outcomes report — scrape now

- Bryant publishes annual outcomes reports (post-graduation employment rates, median salary by college, top employers). Static PDFs / HTML on the Amica Center site.
- **Effort:** One afternoon of scraping into `bryant_outcomes.json`.
- **Pathfinder feature unlocked:** *"96% of Bryant Class of 2024 reported a positive outcome within six months. Top Finance employers: Fidelity, Citizens, MassMutual, John Hancock, BlackRock."* Real, on-brand, free.

### 3.3 PeopleGrove / Graduway

- **URL:** https://www.peoplegrove.com/platform/add-ons-integrations/
- **Status:** Has integrations with Salesforce, Cronofy, Google Analytics, MS Dynamics, Zoom — but **no public developer API** for vendor-side ingestion of alumni profiles. Could not confirm Bryant uses PeopleGrove.
- **Verdict:** Defer; depends on the same career-services relationship as Handshake.

---

## 4. Scholarships & financial aid

### 4.1 IPEDS (institution-level cost) — already covered by A1, free

- IPEDS Compare API gives tuition, fees, room+board, average aid by institution. Use for the "is this worth it" framing on the homepage.

### 4.2 Scholarships.com / Niche / Sallie Mae

- **Findings:** None of these expose a documented public developer API for scholarship matching at the time of this research. Niche.com surfaces ~$6B in scholarship listings via its consumer site; no developer portal. Scholarships.com is a search experience, not an API. Sallie Mae's Scholarship Search is consumer-facing only.
- **ScholarshipOwl For Business** does expose a JSON:API at https://docs.business.scholarshipowl.com/api/scholarships.html — but this is a B2B product targeting other scholarship platforms, with private commercial pricing.
- **Verdict:** No clean path to a "scholarships you qualify for" feature without striking a partnership. Skip for v1; consider as a v2 partnership if a scholarship discovery feature becomes a roadmap priority.

### 4.3 FAFSA / Federal Student Aid data exchange

- Institution-side, gated through the Department of Education's COD (Common Origination & Disbursement) and ISIR systems. Not relevant for a student-facing app at this stage. Skip.

---

## 5. Skills & curriculum signal

### 5.1 Lightcast (Emsi Burning Glass) — DO NOT pursue at pilot stage

- **URL:** https://lightcast.io/products/pricing , https://docs.lightcast.dev/
- **Pricing:** Quote-based; higher-ed contracts typically start in the **low-to-mid five figures annually** (industry-reported; Lightcast does not publish list prices).
- **Verdict:** Lightcast is the labor-market intelligence standard for state workforce agencies and university provosts. The data is genuinely better than the public-data stack — real-time job posting counts, skill-extraction NLP, hiring company data. But the price is institutional, not founder-budget. Re-evaluate when a paid pilot exists.

### 5.2 Coursera & edX — affiliate, not API

- Coursera runs an affiliate program (Impact platform, 15–45% commission per https://about.coursera.org/affiliates) but **no documented public Catalog API** for course recommendations. edX similar. Affiliate links can be hand-curated for the top ~20 courses Bryant Finance grads should consider; not an automatable feed.
- **Pathfinder feature unlocked (manual curation):** *"Round out your FIN 470 with this Coursera Investment Management specialization (Yale, 4.7★)."* — copy-pasted, not API-driven. Acceptable for v1.

### 5.3 AWS / Google Cloud / CompTIA certifications

- AWS Training & Certification has no public catalog API. CompTIA likewise. These are **manual recommendation lists** keyed to SOC codes from O*NET ("technology skills" field).
- **Verdict:** O*NET's `technology_skills` endpoint already names the certifications/tools per occupation. Use that, link out to the cert provider's static landing page.

---

## 6. Top-3 ranked recommendation

Ranking by "would actually change a student's elective choice at pilot scale, today":

| Rank | API / dataset | Cost | Effort | Feature unlocked |
|---|---|---|---|---|
| **1** | **NCES CIP-SOC crosswalk + BLS OEWS + O*NET (combined)** | $0 | ~2 eng-days | "Your major leads to these top-5 occupations, median wage $X, 10-yr growth Y%. Courses aligning with these occupations are starred." This is the foundation. Without it, none of the other features can be grounded. |
| **2** | **College Scorecard (Field-of-Study endpoint)** | $0 | ~2 hours | "Bryant Finance graduates earn a median $76k four years after completion. Debt-to-earnings: 0.34." A single sentence on the homepage that re-frames the entire product from "scheduling tool" to "ROI-aware advising tool." |
| **3** | **Greenhouse Job Board API + Adzuna free tier** | $0 | ~1 day | "12 open roles at Bryant-feeder employers right now require skills from FIN 470." Real-time labor-market signal beats any static dataset for student perception of relevance. |

**Honorable mention — pursue as a relationship, not a code task:** Handshake EDU API. Alumni-curriculum correlation ("73% of Bryant IB analysts took FIN 470") is the single most valuable feature in this category, but it's gated through Bryant Career Services, not through code. Owen should book a meeting with the Amica Center this fall.

**Explicitly defer:** LinkedIn Talent Insights ($6k–$300k/yr), Lightcast (mid-five-figures), Levels.fyi (tech-only), Glassdoor (closed), Indeed Publisher (closed), Coursera/edX (no Catalog API), Scholarships.com / Niche / Sallie Mae (no public API).

---

## 7. Recommended Pathfinder v2 architecture changes

Concrete additions to the codebase if these recommendations are acted on:

- New static asset: `data/career/cip_soc.json` (NCES crosswalk, ~10 KB).
- New static asset: `data/career/occupations.json` (BLS OEWS + O*NET skill list, joined; pulled by a `scripts/build_career_data.py` script run at build time, not at runtime — preserves the static-JSON ADR).
- New static asset: `data/career/scorecard_bryant.json` (College Scorecard institution + field-of-study row).
- New backend module `app/career.py` exposing `get_occupations_for_major(major: str) -> list[Occupation]` and `score_course_career_alignment(course: Course, occupations: list[Occupation]) -> float`.
- Frontend addition: an "Outcomes" eyebrow card on the Preferences page; a "Career fit" tag on each `CourseBlock` on the Schedule page (gold pill, only when alignment score is high — sparing use, on-brand with the editorial-minimalism design system).
- The Greenhouse + Adzuna live calls live in a new endpoint `/api/labor-market` rate-limited the same way the Claude endpoints are. Cache results for 24 hours in-memory.

This stays inside the existing architecture — static JSON for ground truth, ThreadPoolExecutor for the parallel labor-market enrichment alongside the existing Professor / Workload / Negotiator agents.

---

## Sources

Primary documentation referenced:

- BLS Public Data API — https://www.bls.gov/developers/home.htm
- BLS Occupational Employment & Wage Statistics — https://www.bls.gov/oes/
- O*NET Web Services reference — https://services.onetcenter.org/reference/
- O*NET about — https://services.onetcenter.org/about
- College Scorecard API — https://collegescorecard.ed.gov/data/api-documentation/
- College Scorecard Field-of-Study documentation — https://collegescorecard.ed.gov/assets/FieldOfStudyDataDocumentation.pdf
- NCES CIP-SOC Crosswalk site — https://nces.ed.gov/ipeds/cipcode/crosswalk.aspx?y=56
- NCES CIP-SOC 2020 Excel — https://nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx
- Census ACS Field-of-Degree report — https://www.census.gov/library/publications/2025/acs/acs-59.html
- Census ACS detailed earnings tables 2022 — https://www.census.gov/data/tables/2022/demo/educational-attainment/acs-detailed-tables.html
- Greenhouse Job Board API — https://developers.greenhouse.io/job-board.html
- Adzuna Developer overview — https://developer.adzuna.com/overview
- The Muse API — https://www.themuse.com/developers/api/v2
- USAJOBS Developer — https://developer.usajobs.gov/
- Indeed Publisher API deprecation notices — https://developer.indeed.com/docs/publisher-jobs/job-search
- Glassdoor Developer status — https://www.glassdoor.com/developer/index.htm
- Levels.fyi API access — https://www.levels.fyi/api-access/
- LinkedIn Talent Insights pricing — https://www.getphyllo.com/post/how-much-does-the-linkedin-api-cost-iv and https://www.linkedin.com/help/talent-insights/answer/a526048
- Handshake EDU API — https://support.joinhandshake.com/hc/en-us/articles/31061076506391-Getting-Started-with-EDU-API
- PeopleGrove integrations — https://www.peoplegrove.com/platform/add-ons-integrations/
- Lightcast pricing — https://lightcast.io/products/pricing , docs https://docs.lightcast.dev/
- Coursera Affiliates — https://about.coursera.org/affiliates
- ScholarshipOwl For Business API — https://docs.business.scholarshipowl.com/api/scholarships.html
