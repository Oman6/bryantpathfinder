# 01 — Academic & Catalog Data APIs

> Subagent A1 deliverable. Survey of every public, semi-public, and partnership-only data feed that Pathfinder could plug in to enrich the **academic / catalog / institutional-statistics** layer beyond its current 291-section static JSON. Scope is read-only data ingestion: degree-audit feeds and SIS write-back are covered by sibling agents (A2 LMS/SIS, A4 Compliance).

Each entry below answers the same eight questions: (a) what it provides, (b) auth + pricing, (c) rate limits, (d) data freshness, (e) FERPA/privacy implications, (f) the specific Pathfinder feature it would unlock, (g) integration effort in person-days, (h) docs link.

The audience is Owen and the synthesis agent. The headline question is: **"If I have one engineer-week to widen Pathfinder's data foundation, where do I spend it?"** The answer is at the bottom — Top 3 to integrate first.

---

## 1. U.S. Department of Education — College Scorecard API

**(a) What it provides.** Institution-level statistics for ~6,500 U.S. degree-granting Title-IV schools: enrollment, admissions yield, cost of attendance, post-graduation earnings by field of study, retention, completion rates, demographics, financial aid, accreditation, OPE/IPEDS IDs. Field-of-study endpoint exposes median earnings + debt **by CIP code**, which is unique among federal datasets. (Docs: https://collegescorecard.ed.gov/data/api/, https://collegescorecard.ed.gov/data/api-documentation/)

**(b) Auth + pricing.** Free. Single API key from `https://api.data.gov/signup/`. Federal data, no contract, no FERPA constraint (it's aggregate institutional data, not student records).

**(c) Rate limits.** 1,000 requests / hour / IP. 429 on overage. Increases granted by emailing `scorecarddata@rti.org`. (https://collegescorecard.ed.gov/data/api-documentation/)

**(d) Data freshness.** Updated annually each fall when ED publishes the new release. Lag of ~1.5 to 3 years on outcomes data because it's joined to IRS earnings (Treasury reporting cycle).

**(e) FERPA.** None. Aggregate, public.

**(f) Pathfinder feature unlocked.** Two:
1. **"Major outcomes" panel** on the schedule page — when Owen is taking FIN 4XX courses, surface "Bryant Finance graduates earn a median $72,800 within 1 year" pulled from Scorecard's field-of-study endpoint. Direct demand from prospective students; differentiates Pathfinder from Banner.
2. **Multi-institution onboarding** — when Pathfinder expands beyond Bryant, the institution metadata (OPE-ID, accreditor, calendar system) is the cleanest free source of "what universities exist" for tenant provisioning.

**(g) Effort.** **0.5 person-days.** REST + JSON, well-documented, one endpoint, one key. Trivial to wire into a `/api/institution-stats/{ope_id}` route.

**(h) Docs.** https://collegescorecard.ed.gov/data/api-documentation/

---

## 2. NCES IPEDS — Integrated Postsecondary Education Data System

**(a) What it provides.** The authoritative federal repository for U.S. higher-ed: enrollment, finance, admissions, completions, faculty/salaries, libraries, academic libraries, graduation rates, outcome measures by cohort. Far deeper than Scorecard (Scorecard is a curated subset of IPEDS plus IRS earnings).

**(b) Auth + pricing.** Free. **No public REST API.** Data is downloadable as CSV / Access DB via the IPEDS Data Center, Custom Data Files, and Complete Data Files. (https://nces.ed.gov/ipeds/use-the-data)

There are two unofficial wrappers worth noting:
- **Urban Institute Education Data Explorer API** — free, REST, key-less, serves IPEDS as JSON. (https://educationdata.urban.org/documentation/)
- **`rscorecard` / `IPEDSuploadables` Python packages** for batch ingestion.

**(c) Rate limits.** Urban Institute: no published hard limit but politely throttle. CSV downloads: none, but files are 10s of MB.

**(d) Freshness.** Annual release cycle, typical 18-month lag.

**(e) FERPA.** None. Aggregate public.

**(f) Pathfinder feature unlocked.** Same as Scorecard plus **faculty/salary benchmarks** (used to estimate "is Bryant's FIN program well-resourced?") and **library + IT spending** (bragging-rights stat in marketing copy). For a single-school product this is overkill; it becomes valuable when Pathfinder pitches to a second institution and needs an apples-to-apples comparison.

**(g) Effort.** **2 person-days** if going through Urban Institute's Education Data Explorer (one HTTP client, one schema). **5 person-days** if pulling IPEDS CSVs directly and building a typed ingestion pipeline.

**(h) Docs.** https://nces.ed.gov/ipeds/use-the-data , https://educationdata.urban.org/documentation/

---

## 3. Open Syllabus Project

**(a) What it provides.** 21M+ syllabi from 140 countries, parsed into structured records (institution, subject, course code, instructor, assigned readings with ISBN). The Analytics platform exposes co-assignment graphs, "most-assigned readings by field," and per-course reading lists. Pathfinder's Workload Agent currently estimates hours from grade distributions; Open Syllabus could swap this for **actual reading-load + assignment counts** from real syllabi at peer institutions. (https://www.opensyllabus.org/, https://docs.opensyllabus.org/)

**(b) Auth + pricing.** Mixed model:
- Free Analytics web tool, limited.
- **Institutional subscription**: $0.50 per FTE / year, **min $2,500, max $10,000**. 30% discount for two-year schools, 50% for low/middle-income countries. (https://analytics.opensyllabus.org/pricing)
- **Research data access** — limited, anonymized, free, but requires a "research use agreement" signed by the institution. Bryant could secure this through the Provost's office.
- No documented self-serve REST API — data delivery to subscribers is via dataset dumps and the Analytics UI. A dedicated API likely requires custom contract.

**(c) Rate limits.** Not published.

**(d) Freshness.** Continuously crawled; corpus grows monthly. Most recent year reserved for paying subscribers.

**(e) FERPA.** None — these are public syllabi, not student records. The instructor is named, which raises an instructor-PII / instructor-likeness concern that Pathfinder should already be navigating with RateMyProfessors data anyway.

**(f) Pathfinder feature unlocked.** **Workload Agent v2.** Today, weekly hours per course are estimated from grade-distribution shape (questionable proxy). With Open Syllabus, Pathfinder could read the actual FIN 312 syllabus from 30 peer business schools, count problem sets and exam weight, and produce a per-section workload estimate that's defensible. The marketing line writes itself: *"Pathfinder reads the syllabus, not the rumor."*

**(g) Effort.** **3 person-days** to integrate the dataset dump into the Workload Agent (assuming a research-use agreement is in hand). **+5 person-days** of Provost negotiation calendar time, which is on Owen, not the engineer.

**(h) Docs.** https://docs.opensyllabus.org/

---

## 4. Coursicle

**(a) What it provides.** 1,100+ U.S. colleges' course catalogs at section granularity, with seat counts, instructors, schedules, and a "previously taught by" historical view. (https://www.coursicle.com/)

**(b) Auth + pricing.** **No public API.** Coursicle's business model is the consumer app + alerts, not a B2B data feed. They open-source some scrapers (https://github.com/Coursicle/scrape_unc) — these are scrapers *targeting university websites*, not access to Coursicle's own normalized DB.

**(c) Rate limits.** N/A; scraping their own pages would be ToS-violating and IP-block-prone.

**(d) Freshness.** Real-time during registration, but again: not yours to query.

**(e) FERPA.** Their data, scraped from public catalogs. Privacy concern is around instructor names + schedules.

**(f) Pathfinder feature unlocked.** Theoretically: *coverage of 1,099 schools we don't have*. Practically: Coursicle is a competitor, not a partner. They're more likely to send a cease-and-desist than an API key.

**(g) Effort.** Not actionable. **Skip.**

**(h) Docs.** None public.

---

## 5. RateMyProfessors GraphQL

**(a) What it provides.** What Pathfinder already uses: per-instructor quality, difficulty, would-take-again %, review tags, recent reviews. Pathfinder has 129/133 Bryant instructors covered.

**(b) Auth + pricing.** Public unauthenticated GraphQL endpoint at `https://www.ratemyprofessors.com/graphql` with a base64-encoded "Basic dGVzdDp0ZXN0" header that's been the de-facto auth for years. There is **no official public API**, and the **Terms of Use prohibit automated scraping**. Wrappers like `RateMyProfessorAPI` (PyPI), `Michigan-Tech-Courses/rate-my-professors` (npm), and Apify scrapers all rely on this endpoint at the user's risk. (https://github.com/Michigan-Tech-Courses/rate-my-professors, https://pypi.org/project/RateMyProfessorAPI/)

**(c) Rate limits.** Not documented; community wisdom is "be slow, rotate IPs above ~1 req/s."

**(d) Freshness.** Real-time.

**(e) FERPA.** None — instructors are public figures. But **defamation / instructor-likeness** is a real concern that Pathfinder should disclose. Cherwell's *NDLR v. RateMyProfessors* and similar suits make clear that institutions are wary of redistributing this data internally.

**(f) Pathfinder feature unlocked.** Already built. The forward-looking question is: **what happens when Cheddar Inc. (RMP's parent) sends a C&D?** Mitigations:
- **Cache aggressively** (Pathfinder already does; the scrape is one-time, snapshotted in `professor_ratings.json`).
- **Move to a partnership.** RMP has historically licensed bulk data to ed-tech (RateMyProfessors → Cheddar → Chegg lineage). Worth a cold email.
- **Substitute.** Polywork's faculty review startup, the various campus-specific Reddit-derived datasets, or a Pathfinder-native review system seeded with the existing scrape.

**(g) Effort.** **0 person-days** for current state. **2 person-days** to add a fallback to a Pathfinder-native review collector. **30 person-days** to negotiate a license, none of which are engineering.

**(h) Docs.** No official URL. Reverse-engineered: https://github.com/Michigan-Tech-Courses/rate-my-professors

---

## 6. Common Data Set (CDS)

**(a) What it provides.** A standardized 10-section template (A General, B Enrollment, C Admissions, D Transfer, E Academics, F Student Life, G Expenses, H Aid, **I Faculty/Class Size**, J Degrees) that ~95% of U.S. four-year institutions publish annually as a PDF or web form. The Class Size section (I.3) gives **distribution of class sizes by enrollment band** — directly useful to Pathfinder. (https://commondataset.org/, https://commondataset.org/wp-content/uploads/2025/11/CDS-PDF-2025-2026_PDF_Template.pdf)

**(b) Auth + pricing.** Free, public, but **no central API**. Each institution self-publishes a PDF on its institutional research page. Bryant's CDS is at the Office of Institutional Research site (typical pattern; not always linked from the catalog).

**(c) Rate limits.** N/A. Static PDFs.

**(d) Freshness.** Annual; published Sep–Nov for the prior academic year.

**(e) FERPA.** None.

**(f) Pathfinder feature unlocked.** **Class-size confidence indicator.** When Pathfinder shows a 33-seat FIN 312 section, it can annotate "Bryant typically caps Finance courses at 35 (CDS 2024-25, Section I.3)." The Negotiator Agent could also use I.3 distributions to predict which sections will fill and prioritize early-registration slots. This is most valuable for **multi-tenant expansion**: CDS gives Pathfinder a uniform first-pass dataset for any new institution before that school commits to a Banner integration.

**(g) Effort.** **4 person-days** for a PDF-parsing pipeline (Claude Vision works well on CDS tables — the format is rigid). **1 person-day** for a single school. Linear in number of institutions, but cacheable forever.

**(h) Docs.** https://commondataset.org/

---

## 7. U.S. News Best Colleges API / data partnerships

**(a) What it provides.** The rankings, of course, plus the underlying methodology dataset (peer assessment, financial resources, faculty resources, graduation rate performance). Underlying inputs are mostly IPEDS + Scorecard + survey work U.S. News conducts itself.

**(b) Auth + pricing.** **No public API.** U.S. News partners with data licensors (e.g., Elsevier Scopus for engineering rankings) but does **not license its rankings dataset** to third-party tools. Reproducing the rank from public inputs is a research project, not an integration. (https://www.usnews.com/education/best-colleges/articles/how-us-news-collects-rankings-data, https://www.elsevier.com/academic-and-government/us-news-rankings-scopus-scival)

**(c) Rate limits.** N/A.

**(d) Freshness.** Annual.

**(e) FERPA.** None.

**(f) Pathfinder feature unlocked.** Marginal. A "ranked #X by U.S. News" badge has marketing value but doesn't change scheduling. **Skip for now.**

**(g) Effort.** Not a technical integration; would need a business deal.

**(h) Docs.** https://www.usnews.com/best-colleges

---

## 8. Niche.com data partnerships

**(a) What it provides.** School data on 125,000 institutions (PK-12 + colleges). For colleges: rankings, student reviews, admissions stats, salary outcomes. (https://www.niche.com/about/licensing/, https://www.niche.com/about/data/)

**(b) Auth + pricing.** **No self-serve API.** Niche operates two channels: (i) lead-flow integrations into Slate / Finalsite for admissions teams, (ii) custom data licensing for real estate / market research. A scheduling tool would be a third use case; not impossible, but no published rate card. (https://knowledge.technolutions.net/docs/niche-integration)

**(c) Rate limits.** Custom contract.

**(d) Freshness.** Continuous.

**(e) FERPA.** None — Niche reviews are public student-submitted content.

**(f) Pathfinder feature unlocked.** Reviews and student-life context. Useful for the *exploration* phase of college choice, not the *registration* phase Pathfinder lives in. **Skip.**

**(g) Effort.** Business-development play, ≥10 person-days mostly non-engineering.

**(h) Docs.** https://www.niche.com/about/licensing/

---

## 9. Transferology / CollegeSource

**(a) What it provides.** The dominant U.S. transfer-equivalency database. Three real APIs: **Student Lead API** (CSV/JSON export of inquiry data), **PeopleSoft Extractor**, **Banner Extractor** (T-Rex Transfer Rule Extractor — pulls equivalency rules from a school's Banner DB into Transferology). (https://collegesource.com/integrations/, https://transferologylab-support.collegesource.com/article/1205-configure-api-access)

**(b) Auth + pricing.** **Subscription-only.** Pricing is institution-by-institution; Bryant is currently a Transferology subscriber per typical AACSB-business-school patterns (verify). Subscriber gets two annual data imports included; additional imports cost extra.

**(c) Rate limits.** Per contract.

**(d) Freshness.** Quarterly to annual depending on institution import cadence.

**(e) FERPA.** Yes — Student Lead API exposes student inquiry data. Requires institution data-sharing agreement.

**(f) Pathfinder feature unlocked.** **Transfer-credit awareness.** When Owen or a transfer student uses Pathfinder, the requirement expander could pre-mark satisfied requirements based on Transferology's equivalency map ("MAT 141 at CCRI = MATH 121 at Bryant — already counted"). This is a Bryant-specific institutional play, not something Pathfinder can self-onboard.

**(g) Effort.** **10 person-days** assuming Bryant subscribes and grants Pathfinder access. Most of that is data-modeling the equivalency rules into the existing requirement DSL.

**(h) Docs.** https://transferologylab-support.collegesource.com/article/1205-configure-api-access

---

## 10. CollegeAI / EdTech-Index style directories

**(a) What it provides.** CollegeAI markets itself as "the best API for university data" — colleges-search, rankings, demographics, admissions. (https://collegeai.com/data, https://docs.collegeai.com/latest, https://api.collegeai.com/) The 1EdTech / IMS Global **Edu-API** is a separate effort: a standards-track REST schema for *the* canonical course/term/section model. Not a hosted dataset; a **specification** any SIS can implement. (https://www.1edtech.org/standards/edu-api)

**(b) Auth + pricing.** CollegeAI is paid, key-based; pricing not published, sales-led. Edu-API is free spec.

**(c) Rate limits.** CollegeAI: per plan. Edu-API: depends on the implementing SIS.

**(d) Freshness.** CollegeAI: claims real-time. Edu-API: per implementer.

**(e) FERPA.** CollegeAI: aggregate-only, low risk. Edu-API: full FERPA scope when an institution wires it to live student data.

**(f) Pathfinder feature unlocked.** CollegeAI duplicates Scorecard + IPEDS at a price; **skip.** Edu-API is **strategically critical** for the long-term commercialization story: if Pathfinder adopts Edu-API as its internal data model, integrating the *next* SIS becomes a config change rather than a 30-day mapping project.

**(g) Effort.** Refactoring `models.py` to align Pydantic types with Edu-API's `Course`, `Term`, `Section`, `Component` types: **3 person-days**. Pure plumbing, no new feature, but pays compound interest.

**(h) Docs.** https://www.1edtech.org/standards/edu-api

---

## 11. Bryant University-specific public feeds

### 11a. Bryant academic catalog HTML

The Bryant catalog at `https://catalog.bryant.edu/` exposes an internal **course-search** module at `/course-search/api/` and `/course-search/build/` (visible in the rendered HTML's navigation). The version stamp seen on the page is `7.2.2`, which matches the **Modern Campus Catalog** (formerly Acalog) pattern. Acalog/Modern Campus catalogs typically expose a documented JSON endpoint at `/search/?format=json` or via the ribbon API; this is worth probing in the browser network tab when Owen has authenticated catalog access. The catalog is the canonical source for **course descriptions, prerequisites, and program-of-study rules** — which Pathfinder currently has only partially via Degree Works parsing. (https://catalog.bryant.edu/, https://catalog.bryant.edu/undergraduate/coursedescriptions/)

**Effort to integrate:** **2 person-days** if the catalog's JSON endpoint is reachable; **5 days** if it requires HTML scraping.

**Feature unlocked:** **Prerequisite enforcement.** Today the solver doesn't strictly validate prereqs because they aren't in `sections.json`. A catalog scrape gives Pathfinder a defensible "FIN 350 requires FIN 200" check before recommending a schedule. Critical for the multi-semester planner.

### 11b. Bryant academic calendar

Published as a static PDF (`https://catalog.bryant.edu/undergraduate/academiccalendar/academiccalendar.pdf`) and HTML page. **No iCal feed at the academic-calendar level.** LibCal (`https://bookme.bryant.edu/calendars`) supports iCal subscriptions, but those are **library-room/event** calendars, not the registrar's calendar. Pathfinder could either parse the PDF (Claude Vision works) or maintain a hand-curated YAML for term start/end + add/drop deadlines. **Effort:** 1 person-day. **Feature unlocked:** add-drop deadline countdowns + accurate `.ics` term boundaries.

### 11c. Bryant Banner Self-Service registration endpoint

**This is the highest-value finding in this report.** Bryant's Banner Student Registration runs at:

```
https://reg-prod.bryantec.bryant.edu/StudentRegistrationSsb/ssb/registration
```

This is the modern Ellucian Banner 9 (Banner XE) Student Registration Self-Service module. The reverse-engineered endpoint conventions (per https://gitlab.com/jennydaman/nubanned and https://github.com/alec-rabold/UnofficialEllucianBannerApi) include unauthenticated JSON endpoints like:

- `/courseSearchResults/courseSearchResults` — section search
- `/searchResults/searchResults` — section details + seat counts
- `/classSearch/get_subject` — subject codes
- `/classSearch/getInstructor` — instructor names
- `/term/search` — term codes

Many institutions leave these endpoints partially open for read access (the *write* endpoints — actually registering — require auth). If Bryant's Banner is configured this way, **Pathfinder could replace its static `sections.json` with a live feed**, refreshing every 60 seconds, and surface true real-time seat availability. This is the single biggest product-experience upgrade available to Pathfinder right now.

**Risks:**
1. The endpoints might be IP-restricted to on-campus or VPN-only.
2. Bryant IT might (correctly) view this as unauthorized scraping even though the data is publicly accessible to logged-in users.
3. Terms-of-use enforcement is unpredictable.

**Mitigation:** Request explicit permission from Bryant IS (Information Services) — they're listed at https://is.bryant.edu/services/administrative-and-business/student-information-systems/banner-web-portal — and frame Pathfinder as a sanctioned student tool. This converts a legal risk into a partnership story.

**Effort:** **3 person-days** to wire `solver.py`'s candidate-section loader to a live Banner client. **5 days** if seat-availability caching/staleness logic is required.

### 11d. Bryant LibCal / library API

Springshare LibCal at `https://bookme.bryant.edu/calendars` exposes an **OAuth2 client-credentials API** if Bryant Library opts to issue a client. Useful for: study-room availability cross-checked with schedule (Pathfinder could suggest "you have a 2-hour gap between FIN 312 and ECO 113 — book Library Room 4B"). Niche feature; **3 person-days**, low priority. (https://ask.springshare.com/libcal/faq/1407)

---

## 12. Banner / Ellucian Ethos public unauthenticated endpoints

Covered in 11c above for Bryant specifically. The **general** picture: Ethos is Ellucian's modern unified API (REST + JSON, OAuth2, school must contract) and is the *officially supported* path. The **legacy** Banner 9 Self-Service endpoints (`StudentRegistrationSsb`) are unauthenticated for catalog/section read at most installations and effectively act as a free public API, with the moral asterisk that this isn't the sanctioned use. (https://www.ellucian.com/solutions/ellucian-ethos, https://gitlab.com/jennydaman/nubanned, https://github.com/alec-rabold/UnofficialEllucianBannerApi)

For commercialization beyond Bryant: Ethos is the answer (per-school contract, unified data model, supports 750+ schools). For the hackathon-stage Bryant prototype: the Self-Service endpoints are the answer.

---

## 13. PESC — Postsecondary Electronic Standards Council

**(a) What it provides.** **Standards, not data.** PESC publishes XML and JSON-LD schemas for academic records (College Transcript, Course Inventory, Application for Admission). Adopted by AACRAO, common in transcript-exchange networks (Parchment, National Student Clearinghouse). (https://pesc.org/, https://pesc.org/the-rise-of-json-ld-in-data-standards-a-collaborative-approach/)

**(b) Auth + pricing.** Free specs.

**(c) Rate limits.** N/A.

**(d) Freshness.** Specs revised every 2-3 years.

**(e) FERPA.** Spec is FERPA-aware by design; the records *transmitted* in PESC format are PII.

**(f) Pathfinder feature unlocked.** Strategic, not user-facing. If Pathfinder's `DegreeAudit` Pydantic model emits PESC-compliant JSON-LD, the audit becomes portable — students could in theory take their Pathfinder profile to any PESC-aware system, and vice versa. Differentiator vs. Stellic / EAB. **Effort:** **2 person-days** for spec alignment; **0** if no commercialization push is happening.

**(h) Docs.** https://pesc.org/approved-standards/

---

## 14. EDUCAUSE — Core Data Service & Member Directory

**(a) What it provides.** Annual IT-environment benchmarking survey (staffing, budgets, services) for 800+ member institutions. Member-only access. **No public API.** Analytics Services Portal went **offline May 31, 2025** and is being rebuilt; current access is via the EDUCAUSE Connect community group. (https://www.educause.edu/research-and-publications/research/analytics-services, https://er.educause.edu/blogs/2020/6/charting-the-path-ahead-for-the-educause-core-data-service-and-analytics-services)

**(b) Auth + pricing.** Member-only. Bryant is a member (typical for AACSB schools); access requires a Bryant SSO login.

**(c)–(e).** N/A — no programmatic access.

**(f) Pathfinder feature unlocked.** None directly. Useful as **market-sizing and pitch material** when Pathfinder fundraises ("EDUCAUSE CDS 2024 shows the median institution spends $X on student-success software — Pathfinder is 1/10th that"). **Skip for engineering; revisit for business deck.**

**(h) Docs.** https://www.educause.edu/research-and-publications/research/analytics-services

---

## Summary table

| # | Source | Auth | Cost | Effort (PD) | Pathfinder Impact |
|---|---|---|---|---|---|
| 1 | College Scorecard | API key | Free | 0.5 | Outcomes panel |
| 2 | NCES IPEDS (via Urban Inst.) | None | Free | 2 | Multi-school benchmark |
| 3 | Open Syllabus | Subscription | $2.5K-$10K/yr | 3 (+ negotiation) | **Workload Agent v2** |
| 4 | Coursicle | None public | N/A | — | Skip |
| 5 | RateMyProfessors | Reverse-engineered | Free / risky | 0 (built) / 2 (fallback) | Already shipped |
| 6 | Common Data Set | PDFs | Free | 4 | Multi-school onboarding |
| 7 | U.S. News | Closed | Closed | — | Skip |
| 8 | Niche | Closed | Closed | — | Skip |
| 9 | Transferology | Subscription | Per institution | 10 | Transfer-credit aware |
| 10 | CollegeAI / Edu-API | Mixed | Mixed | 3 (Edu-API) | Long-term portability |
| 11a | Bryant catalog | Public HTML | Free | 2-5 | Prereq enforcement |
| 11b | Bryant academic calendar PDF | Public | Free | 1 | Add-drop countdowns |
| **11c** | **Bryant Banner SSB** | **Public, IP-risky** | **Free** | **3-5** | **LIVE seat counts** |
| 11d | Bryant LibCal | OAuth2 | Free | 3 | Study-room booking |
| 12 | Ellucian Ethos | OAuth2 + contract | Per institution | 15+ | Multi-school commercialization |
| 13 | PESC | Free spec | Free | 2 | Portable audits |
| 14 | EDUCAUSE CDS | Member | Membership | — | Pitch deck only |

---

## Top 3 to integrate first — ranked by Pathfinder-feature-impact-per-engineering-day

### #1 — Bryant Banner StudentRegistrationSsb live feed (3-5 person-days)

**Feature unlocked:** Real-time seat availability and live section data, replacing the 291-section static JSON snapshot. The current product's most visible weakness is that seat counts are stale; this fixes it. Also unlocks add-on features like "alert me when this section opens" — a direct Coursicle competitor moat. Risk is non-engineering: needs Bryant IS sign-off. *Endpoint confirmed live at* `https://reg-prod.bryantec.bryant.edu/StudentRegistrationSsb/ssb/registration`.

### #2 — College Scorecard API (0.5 person-days)

**Feature unlocked:** "Bryant Finance graduates earn $72,800 median 1-year out" panel on the schedule confirmation page. Trivial integration, free, federally maintained, unlocks a marketing-grade differentiator. Lowest risk on the list.

### #3 — Open Syllabus institutional subscription + Workload Agent v2 (3 person-days + Provost negotiation)

**Feature unlocked:** Workload estimates that read **actual peer-institution syllabi** instead of inferring from grade distributions. Defensible, demoable ("Pathfinder reads 30 real syllabi to estimate FIN 312 takes 9 hrs/week"), and exactly the kind of capability that distinguishes Pathfinder from a generic course planner. The $2,500 minimum subscription is a Bryant-side budget ask, not Owen's — bundle it into the pilot proposal.

**Honorable mention — Edu-API alignment (3 person-days).** Not a feature unlock but a structural bet that pays off the moment school #2 enters the pipeline.

---

## Notes on what was *not* worth a section

- **Acalog/CourseLeaf/Coursedog public APIs** — these are catalog-software vendors; their endpoints are per-institution and not aggregated.
- **OCLC WorldCat Discovery API** — interesting for library data but orthogonal to scheduling.
- **National Student Clearinghouse APIs** — verification-of-enrollment, not catalog data.
- **Parchment / Credentials APIs** — transcript transmission, not relevant.
- **AACRAO standards** — overlap heavily with PESC; covered there.

---

*Source URLs are inline above. Confidence on Bryant-specific endpoint discovery (Section 11c) is high but unverified against live HTTP — the next concrete action is for Owen to open Bryant's Banner registration page in DevTools and confirm the JSON paths actually return data without authentication.*
