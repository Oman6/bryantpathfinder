# 01 — Buyer & Procurement Map for BryantPathfinder

> Companion to `00-product-baseline.md`. The product is a single-school prototype today. This document answers: when BryantPathfinder tries to sell its second installation, who are the eight people on the other side of the table, who actually signs the contract, and where should Owen aim his first five cold emails.

---

## 1. The Higher-Ed Buying Committee

A course-planning / advising tool that ingests Degree Works data and sends FERPA-protected content to a third-party LLM hits the seams of academic affairs, IT, student services, and legal at the same time. There is no single buyer. Below is each role's actual incentive structure, drawn from public job descriptions, EDUCAUSE materials, and recent procurement disclosures.

### 1a. Provost / Chief Academic Officer

The Provost owns the academic mission and almost always controls the discretionary budget that pays for student-success software. They are the ultimate "yes" — but rarely the originator of a deal.

- **KPIs:** Six-year graduation rate, first-to-second-year retention, DFW (D/F/Withdraw) rates in gateway courses, time-to-degree, faculty satisfaction with curricular tools, accreditation standing.
- **Says yes when:** A tool measurably moves retention or time-to-degree, faculty governance has signed off, and the cost is inside an existing line item (no new ask to the President or Board).
- **Says no when:** The tool conflicts with faculty advising prerogatives, duplicates EAB / Stellic / Ellucian Degree Works that the institution already pays for, or requires curriculum changes.
- **Title variance:**
  - **R1:** "Provost and Executive Vice President for Academic Affairs." Multiple Vice Provosts under them (Vice Provost for Undergraduate Education, Vice Provost for Student Success). The Provost rarely takes a sales meeting until very late.
  - **Regional comprehensive (CSU/SUNY):** Provost or "Provost and Vice President for Academic Affairs." More accessible; one Vice Provost layer.
  - **Community college:** "Vice Chancellor for Academic and Student Affairs" or "Chief Academic Officer." Often a single person doing the work of three R1 vice provosts.
  - **Small liberal arts (Bryant, Babson, Bentley):** "Provost and Chief Academic Officer" — at Bryant this is Dr. Rupendra Paliwal ([news.bryant.edu](https://news.bryant.edu/bryant-university-president-ross-gittell-phd-appoints-rupendra-paliwal-phd-provost-and-chief)). Single layer between Provost and the academic deans.

### 1b. Registrar

The Registrar is the operational owner of the SIS (Banner / Workday Student / PeopleSoft) and the gatekeeper for any tool that reads from or writes to course/section/registration records. They are usually neither champion nor blocker — they are a *necessary co-signer*.

- **KPIs:** On-time registration completion rate, error rate in degree audits, FERPA breach count (ideally zero), time-to-resolution for record corrections, classroom utilization, grading-cycle close ([aacrao.org](https://www.aacrao.org/resources/newsletters-blogs/aacrao-connect/article/3-ways-to-optimize-your-course-schedule-with-actionable-analytics)).
- **Says yes when:** The tool is read-only on official records, is FERPA-defensible (preferably under the "school official" exception), and reduces walk-in traffic to their office during registration windows.
- **Says no when:** The tool tries to write CRNs back into Banner, presents itself to students as authoritative on graduation requirements, or makes them the support escalation point for vendor outages.
- **Title variance:** "University Registrar" (R1, comprehensive, liberal arts), "Director of Enrollment Services" or "Dean of Enrollment Management" (community college, where the Registrar function is folded in). The AACRAO 2025 program ([aacrao.org](https://www.aacrao.org/events-training/meetings/annual-meeting/annual-meeting-2025)) confirms registrars are now actively interested in AI for transfer advising and course articulation.

### 1c. Dean of Undergraduate Studies / Dean of Students

At larger schools this is the Dean of Undergraduate Education. At smaller schools it collapses into the Dean of Students or Vice President for Student Affairs.

- **KPIs:** First-year persistence, advising-load ratios, complaints to the Ombuds about advising errors, students-per-advisor, "stuck student" cohort size (those who can't graduate because of a missed prerequisite).
- **Says yes when:** Advisors get more time for high-touch conversations because the tool absorbs routine "what should I take next semester" questions. They love the EAB/Navigate framing of "advisor-augmenting, not advisor-replacing."
- **Says no when:** Faculty advisors feel surveilled, or when the tool generates schedules that contradict program-specific advice.
- **Title variance:** "Dean of Undergraduate Education" (R1), "Dean of Undergraduate Studies" or "AVP for Student Success" (regional comprehensive), "Vice President for Student Affairs" (community college), "Dean of the College" or "Dean of Students" (liberal arts). At Michigan LSA this role's adjacent title is "Assistant Dean for Undergraduate Education and Student Academic Affairs," held by Perry Fittrer ([lsa.umich.edu](https://lsa.umich.edu/lsa/faculty-staff/office-of-the-dean/dean-s-office-directory/undergraduate-education-staff/perry-fittrer--ph-d-.html)).

### 1d. CIO / CTO / VP for IT

The CIO owns the integration burden and the security review. For an AI tool that ingests audit data, the CIO is the second-most important person in the room after the Provost.

- **KPIs:** Uptime of core systems (SIS, LMS, SSO), security-incident count, HECVAT review backlog, integration-debt remediation, AI-policy compliance rate ([usdla.org](https://usdla.org/blog/navigating-ai-adoption-in-higher-education-a-cios-guide/)).
- **Says yes when:** Vendor has a completed HECVAT (Lite minimum, Full preferred), supports SAML/Shibboleth SSO, signs the institution's data-protection addendum, and operates as a "school official" under FERPA ([educause.edu](https://www.educause.edu/higher-education-community-vendor-assessment-toolkit)).
- **Says no when:** Vendor sends data to an LLM provider without a signed BAA-equivalent / DPA, has no SOC 2, or proposes integration that requires a custom Banner connector the IT team has to build and maintain.
- **Title variance:**
  - **R1:** "Vice President for Information Technology and CIO" (e.g., Lev Gonick, Enterprise CIO at ASU — [linkedin.com/in/levgonick](https://www.linkedin.com/in/levgonick); [campustechnology.com](https://campustechnology.com/articles/2024/04/30/inside-arizona-state-universitys-openai-partnership.aspx)).
  - **Regional comprehensive:** "Associate Vice Chancellor for IT" or "CIO."
  - **Community college:** "Vice Chancellor and CIO" — at Maricopa this is Dr. Jess Evans, who oversees the largest community college system in the U.S. ([maricopa.edu](https://www.maricopa.edu/about/leadership/chief-information-officer)).
  - **Small liberal arts:** "Director of IT" or "CIO" reporting to the CFO; far less specialized AI/security review staff. HECVAT reviews are often outsourced to a regional consortium.

### 1e. Director of Academic Advising / VP of Student Success

This is the person whose team's daily workflow the product would change. They are the most likely *internal champion* for BryantPathfinder.

- **KPIs:** Advising appointments completed, average wait time for advising, advising-related student satisfaction, "advising touches" per at-risk student, registration-period stress metrics ([eab.com](https://eab.com/resources/blog/student-success-blog/what-are-students-asking-university-chatbots/)).
- **Says yes when:** They can see the tool reduces transactional questions ("what fulfills my Lit-Hum requirement?") so advisors can spend more time on developmental advising. The Maryville "Max" chatbot — 6,000+ questions/month resolved — is the reference story.
- **Says no when:** They sense the vendor is pitching "replace advisors" or when their faculty advising committee will resist on principle.
- **Title variance:** "Vice Provost for Student Success" (R1), "AVP for Student Success" or "Dean of Student Success" (regional), "Vice President for Student Affairs and Enrollment Management" (community college), "Director of Academic Advising" or "Dean of the College" (liberal arts).

### 1f. Director of Institutional Research

Often overlooked. The IR director defines the metrics by which the pilot will be judged, and they are the ones who will produce the "did this tool actually help?" memo at renewal time.

- **KPIs:** Survey response rates, IPEDS reporting accuracy, model fit on retention prediction, board-report turnaround.
- **Says yes when:** The tool exposes structured outcome data (schedules generated, requirements satisfied, students who registered after using the tool). They want a CSV export, not a dashboard.
- **Says no when:** The vendor refuses to share aggregate usage analytics, or wraps everything in a proprietary dashboard with no export.
- **Title variance:** "AVP for Institutional Effectiveness" (R1, regional), "Director of Institutional Research" (community college, liberal arts).

### 1g. General Counsel / Privacy Officer (FERPA gatekeeper)

The single hardest gate for BryantPathfinder in its current architecture. The audit content is FERPA-protected education records and is currently sent to Anthropic's API for parsing and explanation.

- **KPIs:** Zero FERPA incidents, contract turnaround time (often a complaint metric), insurance-claim count.
- **Says yes when:** Vendor signs a Data Protection Addendum incorporating the FERPA "school official" language, agrees to Anthropic-style sub-processor disclosure, has SOC 2 Type II, and accepts notification-of-breach within 72 hours ([concentric.ai](https://concentric.ai/maintain-ferpa-compliance-with-concentric-ai/); [bwf.com](https://www.bwf.com/navigating-responsible-ai-a-look-through-ferpa-and-hipaa-compliance/)).
- **Says no when:** The model provider's terms reserve the right to train on customer data, or when the vendor cannot describe data flow, retention, and deletion.
- **Title variance:** "General Counsel" + separate "Chief Privacy Officer" (R1), "General Counsel" doubling as Privacy Officer (regional, liberal arts), "College Attorney" (community college, often outside counsel).

### 1h. Faculty Senate / Curriculum Committee

Faculty governance is rarely a *purchaser* but is frequently a *vetoer*. A tool that touches degree requirements is curriculum-adjacent and faculty senates have well-documented authority over curriculum and instructional technology adoption ([senate.psu.edu](https://senate.psu.edu/curriculum/introduction-to-guide-to-curricular-procedures/); [csusb.edu](https://www.csusb.edu/faculty-senate/committees/university-curriculum-committee)).

- **KPIs:** Shared-governance compliance, faculty workload protection, academic-freedom protection.
- **Says yes when:** They've been consulted before procurement, the tool is positioned as "supporting faculty advisors" not "replacing them," and an opt-in pilot is offered.
- **Says no when:** They learn about the deal from the student newspaper. This will kill renewal even if procurement signed.

---

## 2. Procurement Mechanics — Who Actually Signs

Across every U.S. university, the **legal contracting party is the Board of Trustees**, and signature authority is delegated downward in writing. Three patterns emerge from public policies:

- **Stanford** delegates by dollar threshold and contract type, with the President holding broad authority and specific delegations to the Provost, deans, and procurement officers ([adminguide.stanford.edu](https://adminguide.stanford.edu/chapters/guiding-policies-and-principles/signature-and-financial-approval-authority/signature-and)).
- **NYU** requires written delegation by title, never by named individual, and binds the institution only via authorized signers ([nyu.edu](https://www.nyu.edu/about/policies-guidelines-compliance/policies-and-guidelines/signature-authority-policy.html)).
- **University of Alabama** sets explicit Board thresholds — technology acquisitions over **$750,000** require Board of Trustees approval; consulting/professional-services contracts over **$250,000** require Board approval regardless of process ([procurement.ua.edu](https://procurement.ua.edu/board-of-trustees-approval-threshold-changes/)).

**Practical pattern for a SaaS deal in the $20K–$150K/year range** (which is where BryantPathfinder will live in any realistic year-one pilot):

1. **Sponsor budgets it** — typically the Vice Provost for Student Success or the CIO, out of an existing line.
2. **Procurement office** issues a PO once two competing quotes (or a sole-source justification) are on file.
3. **CIO/Privacy Officer** must sign off on the HECVAT review and Data Protection Addendum.
4. **General Counsel** approves contract language.
5. **Authorized signer** (commonly the CFO, VP for Finance, or a delegated Director of Procurement) executes the SaaS agreement. The Provost almost never signs the actual paper.
6. **Board notification** is a line item on a quarterly contracts report; **Board approval** is not required below the institution's threshold (commonly $250K–$1M depending on type and institution).

The procurement office runs the *mechanics* (PO, vendor onboarding, insurance certificates, W-9). The *decision* is made in academic affairs, by the sponsor with CIO/GC sign-off. A vendor who only sells to procurement loses; a vendor who sells the academic sponsor and lets the sponsor pull procurement along wins.

---

## 3. Buying-Committee Variance by Institution Type

| Dimension | R1 (Michigan, ASU) | Regional Comprehensive (CSU/SUNY) | Community College (Maricopa, Valencia) | Small Liberal Arts (Bryant, Babson, Bentley) |
|---|---|---|---|---|
| Decision cycle | 9–18 months | 6–12 months | 3–9 months | 3–6 months |
| Required sign-offs | Provost + CIO + CISO + GC + Privacy Officer + Faculty Senate | Provost + CIO + GC | Vice Chancellor for Academic Affairs + CIO + College Attorney | Provost + CIO + GC (often one person wears two hats) |
| Board threshold | $500K–$1M+ | $250K–$500K | $100K–$250K (system board) | $100K–$250K |
| Likely sponsor | Vice Provost Student Success | AVP Student Success | Chief Student Services Officer | Dean of Students or Director of Advising |
| HECVAT depth | Full (180+ questions) | Full or Lite | Lite, often via consortium | Lite, sometimes waived for <$50K deals |
| AI policy maturity | Highest (ASU/UMich have published AI policies) | Medium (CSU just rolled out system-wide AI access — [edsource.org](https://edsource.org/2025/cal-state-unveils-artificial-intelligence-tools-for-students/726205)) | Variable; often follows a state mandate | Lowest; most likely to say "we'll figure it out" |
| Faculty senate veto risk | High | Medium | Low | Medium-high (small senates, loud voices) |
| Already owns EAB/Stellic? | Almost always | Often | Sometimes | Rarely |

The R1 path is slowest and most lucrative. The community college path is the fastest path to a paid contract. The liberal arts path is the fastest path to *a contract* but the smallest dollar value.

---

## 4. Five Named, Verified Initial Conversations

Each name below is verified against a current .edu page or LinkedIn profile that confirms the role.

1. **Dr. Lev Gonick — Enterprise CIO, Arizona State University.** Public champion of ASU's OpenAI partnership and on record about scaling AI use cases across student-facing services ([campustechnology.com](https://campustechnology.com/articles/2024/04/30/inside-arizona-state-universitys-openai-partnership.aspx); [linkedin.com/in/levgonick](https://www.linkedin.com/in/levgonick)). Why useful: ASU is the most-quoted reference in the AI-in-higher-ed press, and Gonick *teaches* peer CIOs how to think about AI procurement. Even a 20-minute conversation produces transferable signal.
2. **Dr. Elizabeth Reilley — Executive Director, AI Acceleration, Arizona State University.** Leads ASU's 15-person team building AI products for the student experience ([tech.asu.edu](https://tech.asu.edu/features/ASU-launches-AI-acceleration); [search.asu.edu](https://search.asu.edu/profile/3742704)). Why useful: she is the operator-level counterpart to Gonick and the person who actually evaluates incoming AI tools. She is on conference panels weekly and her inbox is open.
3. **Dr. Jess Evans — Vice Chancellor and CIO, Maricopa Community Colleges.** CIO of the nation's largest community college system; appointed to the National Applied AI Consortium leadership team in 2025 ([maricopa.edu](https://www.maricopa.edu/about/leadership/chief-information-officer); [arizonadigitalfreepress.com](https://arizonadigitalfreepress.com/maricopa-community-colleges-cio-dr-jess-evans-joins-national-ai-business-industry-leadership-team/)). Why useful: community college students disproportionately suffer from registration friction, Maricopa has 10 colleges, and a single deal there is effectively ten installations. Evans has explicitly stated she wants to move "beyond AI-washing to responsible innovation" — exactly Pathfinder's positioning.
4. **Perry Fittrer — Assistant Dean for Undergraduate Education and Student Academic Affairs, U-M College of LSA.** Built and shipped Maizey, a Michigan-only AI advising assistant on top of UM-GPT, for ~19,000 LSA students ([lsa.umich.edu](https://lsa.umich.edu/lsa/faculty-staff/office-of-the-dean/dean-s-office-directory/undergraduate-education-staff/perry-fittrer--ph-d-.html); [michigan.it.umich.edu](https://michigan.it.umich.edu/news/2024/03/26/meet-the-newest-advisor-at-the-newnan-academic-advising-center-maizey/)). Why useful: he has already done what BryantPathfinder is doing, in-house, and will have strong opinions about what worked and what didn't. He is also the rare administrator who understands the build-vs-buy question with real engineering scars.
5. **Dr. Rupendra Paliwal — Provost and Chief Academic Officer, Bryant University.** ([news.bryant.edu](https://news.bryant.edu/bryant-university-president-ross-gittell-phd-appoints-rupendra-paliwal-phd-provost-and-chief)). Why useful: Owen has access to him. Paliwal is the only person on this list who can authorize a sanctioned Bryant pilot — which is the prerequisite for every external conversation. Without a Bryant case study, the other four conversations stall at "interesting demo, come back when you have a reference."

---

## 5. "Land Here First" — Owen's First Five Cold Outreach Targets

Owen has zero warm network outside Bryant. Paid pilots from cold outreach by a sophomore are unrealistic in year one. The right goal for the first five emails is **conversational signal** — "would you take a 20-minute call about how you'd evaluate this if it landed in your procurement queue?" — not a sale.

1. **Dr. Rupendra Paliwal (Bryant Provost)** — first, immediately, before any external outreach: a sanctioned Bryant pilot is the only credibility Owen can buy with one email, and he can hand-deliver this one.
2. **Perry Fittrer (Michigan LSA)** — has already built the in-house version and will engage with a peer-builder framing rather than a vendor framing; his feedback is the highest-quality external signal Owen can get.
3. **Dr. Elizabeth Reilley (ASU AI Acceleration)** — operator-level, evaluates dozens of AI vendors monthly, and her stated mission of "amplifying human creativity" maps directly onto Pathfinder's deterministic-solver-plus-Claude split.
4. **Dr. Jess Evans (Maricopa CIO)** — the highest-leverage single contract in U.S. higher ed for an advising tool, and the institution most likely to move on a 90-day timeline because community college boards approve technology at lower thresholds and registration friction is most acute there.
5. **A Vice Provost for Student Success at one CSU campus that already uses CSU's new AI infrastructure** — e.g., San José State or Fresno State, where the system-level AI rollout ([edsource.org](https://edsource.org/2025/cal-state-unveils-artificial-intelligence-tools-for-students/726205)) means campus-level evaluators are already procurement-ready and looking for use cases that justify the system spend.

The recommendation: Owen sends email #1 (Paliwal) this week, runs the Bryant pilot through fall, and only after that pilot has a registered-students-using-it number does he send the four external emails. Sending #2–#5 before #1 produces "interesting, send us a reference" replies that he cannot answer. With a Bryant pilot number — even N=50 students — those same emails convert to calls.

---

## Sources

- [Oregon State University Contract Signature Authority](https://policy.oregonstate.edu/UPSM/03-001_contract_signature_authority)
- [Stanford Signature and Financial Approval Authority](https://adminguide.stanford.edu/chapters/guiding-policies-and-principles/signature-and-financial-approval-authority/signature-and)
- [NYU Signature Authority Policy](https://www.nyu.edu/about/policies-guidelines-compliance/policies-and-guidelines/signature-authority-policy.html)
- [University of Alabama Board Thresholds](https://procurement.ua.edu/board-of-trustees-approval-threshold-changes/)
- [EDUCAUSE HECVAT Toolkit](https://www.educause.edu/higher-education-community-vendor-assessment-toolkit)
- [AACRAO 2025 Annual Meeting](https://www.aacrao.org/events-training/meetings/annual-meeting/annual-meeting-2025)
- [AACRAO on AI scheduling analytics](https://www.aacrao.org/resources/newsletters-blogs/aacrao-connect/article/3-ways-to-optimize-your-course-schedule-with-actionable-analytics)
- [EAB on what students ask university chatbots](https://eab.com/resources/blog/student-success-blog/what-are-students-asking-university-chatbots/)
- [Inside ASU's OpenAI partnership (Campus Technology)](https://campustechnology.com/articles/2024/04/30/inside-arizona-state-universitys-openai-partnership.aspx)
- [Lev Gonick, ASU LinkedIn](https://www.linkedin.com/in/levgonick)
- [Elizabeth Reilley, ASU profile](https://search.asu.edu/profile/3742704)
- [ASU AI Acceleration team](https://tech.asu.edu/features/ASU-launches-AI-acceleration)
- [Jess Evans, Maricopa CIO](https://www.maricopa.edu/about/leadership/chief-information-officer)
- [Maricopa CIO joins national AI leadership team](https://arizonadigitalfreepress.com/maricopa-community-colleges-cio-dr-jess-evans-joins-national-ai-business-industry-leadership-team/)
- [Perry Fittrer, U-M LSA](https://lsa.umich.edu/lsa/faculty-staff/office-of-the-dean/dean-s-office-directory/undergraduate-education-staff/perry-fittrer--ph-d-.html)
- [Maizey AI advisor at Michigan LSA](https://michigan.it.umich.edu/news/2024/03/26/meet-the-newest-advisor-at-the-newnan-academic-advising-center-maizey/)
- [Bryant Provost Rupendra Paliwal appointment](https://news.bryant.edu/bryant-university-president-ross-gittell-phd-appoints-rupendra-paliwal-phd-provost-and-chief)
- [Bryant Registrar office directory](https://info.bryant.edu/registrar)
- [Cal State AI tools rollout (EdSource)](https://edsource.org/2025/cal-state-unveils-artificial-intelligence-tools-for-students/726205)
- [Penn State Faculty Senate curriculum procedures](https://senate.psu.edu/curriculum/introduction-to-guide-to-curricular-procedures/)
- [CSUSB University Curriculum Committee](https://www.csusb.edu/faculty-senate/committees/university-curriculum-committee)
- [USDLA on CIOs and AI adoption](https://usdla.org/blog/navigating-ai-adoption-in-higher-education-a-cios-guide/)
- [BWF on FERPA / HIPAA and responsible AI](https://www.bwf.com/navigating-responsible-ai-a-look-through-ferpa-and-hipaa-compliance/)
- [Concentric AI on FERPA compliance](https://concentric.ai/maintain-ferpa-compliance-with-concentric-ai/)
- [Tambellini Group 2023 Student Success Solutions](https://www.thetambellinigroup.com/research/2023-student-success-best-of-breed-solutions/)
- [Adelphi switches to Stellic](https://www.adelphi.edu/it-services/stellic/)
