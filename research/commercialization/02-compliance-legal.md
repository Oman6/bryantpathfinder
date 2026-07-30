# 02 — Compliance & Legal Teardown

> Subagent: Compliance & Legal. Audience: the synthesis agent and the founder.
> Question: what is the actual regulatory and contractual landscape BryantPathfinder has to satisfy before any sanctioned campus pilot, a paid second-school pilot, or an R1 contract?
> Bottom line up front: BryantPathfinder, as architected today, is non-compliant with FERPA's school-official exception in any institutional deployment, fails the threshold security-review gate at virtually every U.S. university (no HECVAT, no SOC 2, no SSO, no audit log), and is materially under-prepared for state-level student-privacy statutes in Illinois, New York, Texas, California, Colorado, Virginia, and Connecticut. None of these are unfixable; all of them are blocking.

---

## 1. FERPA — The Load-Bearing Federal Law

### 1.1 What FERPA actually says about education records

FERPA's statutory hook is **20 U.S.C. §1232g** and its implementing regulations live at **34 CFR Part 99**. Two definitions are decisive for BryantPathfinder.

**"Education records"** are defined at 34 CFR §99.3 as records that are "(1) Directly related to a student; and (2) Maintained by an educational agency or institution or by a party acting for the agency or institution," with narrow carve-outs for sole-possession records, law-enforcement-unit records, employment records, treatment records, and post-attendance records (https://www.law.cornell.edu/cfr/text/34/99.3).

**"Personally identifiable information" (PII)** in §99.3 is broad. It includes the student's name, the names of family members, addresses, "a personal identifier, such as the student's social security number, student number, or biometric record," indirect identifiers like date of birth, and — critically — "other information that, alone or in combination, is linked or linkable to a specific student that would allow a reasonable person in the school community … to identify the student with reasonable certainty" (https://www.law.cornell.edu/cfr/text/34/99.3).

Apply that to BryantPathfinder.

- A **Degree Works screenshot** plainly contains the student's name, Bryant student ID (a "personal identifier"), GPA, completed and unmet requirements, and frequently a date of birth or DOB-equivalent. It is unambiguously an education record containing PII.
- A **parsed `DegreeAudit` JSON** with `student_name`, `student_id`, `gpa`, and `outstanding_requirements` is also an education record. It is "directly related to a student" and is now "maintained by a party acting for the agency or institution" (BryantPathfinder/Anthropic) the moment a school sanctions Pathfinder.
- An **unmet-requirements list with no name attached** is still PII if combined with anything else (an IP, an email domain, a session cookie) that would let a reasonable Bryant employee identify the student. The product baseline confirms the audit object includes the student name and GPA, so this hypothetical is moot — Pathfinder is processing PII, not de-identified data.

There is no FERPA exception for "small dataset," "AI parsing only," or "the student uploaded it themselves." Once an institution sanctions the tool, the records flowing through it are education records.

### 1.2 The school-official exception and how SaaS vendors fit through it

FERPA prohibits disclosure of PII from education records without prior written consent (§99.30) unless one of the §99.31 exceptions applies. The exception every edtech vendor lives or dies on is **§99.31(a)(1)(i)(B)** — the "school official with legitimate educational interests" exception extended to outside parties.

Per Cornell LII's regulatory text, an outside party (contractor, consultant, volunteer, vendor) qualifies as a school official only if it:

1. **"Performs an institutional service or function for which the agency or institution would otherwise use employees"**;
2. **"Is under the direct control of the agency or institution with respect to the use and maintenance of education records"**; and
3. **"Is subject to the requirements of §99.33(a) governing the use and redisclosure of personally identifiable information"** (https://www.law.cornell.edu/cfr/text/34/99.31).

Section 99.33(a) further requires that recipients use the information "only for the purposes for which the disclosure was made" and not redisclose without consent (https://www.law.cornell.edu/cfr/text/34/99.33).

Three concrete redlines for BryantPathfinder follow:

- **"Direct control" is a contract.** ED's Student Privacy Policy Office (formerly PTAC) has consistently interpreted "direct control" as requiring a written agreement that limits use, prohibits secondary use, and gives the institution practical authority over the vendor's handling of records (https://studentprivacy.ed.gov/faq/what-ferpa). A click-through ToS is not enough.
- **Sub-processors are governed by flow-down.** Anthropic, as a downstream processor, must be contractually bound by Pathfinder to the same use-and-redisclosure limits the school imposes on Pathfinder. If Pathfinder's standard Anthropic API terms permit Anthropic to use prompt content for any purpose other than serving the school, Pathfinder is out of compliance the moment a school sanctions the tool.
- **"Functional substitution" is the test.** Course-scheduling advisement is a function Bryant currently performs through advisors. Pathfinder substitutes for that function. So long as a school official agreement exists, the §99.31(a)(1)(i)(B) exception is structurally available — but Pathfinder has to be invited in by an institutional decision, not bolted on student-by-student.

### 1.3 What a school-official agreement (data-sharing agreement) must contain

The contractual minimum, drawn from §99.31, §99.33, and ED's published guidance for vendors (https://studentprivacy.ed.gov/training/online-training-modules):

- Purpose limitation: scheduling and degree-progress assistance only.
- No secondary use: no model training, no advertising, no analytics resale, no redisclosure to third parties without the institution's prior written consent.
- Sub-processor disclosure with flow-down obligations identical to the prime contract (this means Pathfinder must contractually bind Anthropic).
- Data-minimization commitments: Pathfinder receives only what is necessary for the function (no SSN, no disability accommodations, no Title IV financial-aid detail beyond what's needed).
- Retention and deletion: defined retention windows, deletion on request, deletion on contract termination.
- Security minimums: encryption in transit and at rest, access controls, audit logging, breach-notification timelines.
- Audit and inspection rights for the institution.
- FERPA-specific clauses: explicit school-official designation, §99.33(a) acknowledgment, "directly related to a student" language.

### 1.4 Directory information vs. non-directory PII

Under §99.37, institutions may designate certain information as "directory information" disclosable without consent. The §99.3 definition of directory information includes name, address, email, photo, major, enrollment status, dates of attendance, and degrees received — **but explicitly excludes Social Security numbers and student ID numbers** (https://www.law.cornell.edu/cfr/text/34/99.3).

Pathfinder's audit object contains the student ID and GPA. **Neither qualifies as directory information.** GPA in particular is non-directory PII at every institution that has been challenged on the point. So the directory-information exception is not a shortcut Pathfinder can use to skip §99.31 contracting.

### 1.5 When written consent from the student is required

§99.30 requires "signed and dated written consent" prior to disclosure unless an exception applies. For a sanctioned campus deployment, the school-official exception applies and per-student written consent is **not required** — the institutional consent suffices. For an unsanctioned, student-direct deployment (the current Pathfinder posture: the student personally uploads their own audit), the legal theory is different: the student is the eligible-student rights-holder and is choosing to disclose their own record to a third party. That is permissible at the *student's* election but does **not** create a school-official relationship, and **does not allow Pathfinder to call itself FERPA-compliant in any institutional sense**.

### 1.6 The 2024 FERPA NPRM

ED announced in fall 2024 its intention to propose amendments to 34 CFR Part 99, with an NPRM targeted for January 2026. The agenda includes clarifying the definition of education record, updating provisions governing nonconsensual disclosure of PII, and improving FERPA enforcement procedures (https://er.educause.edu/articles/2025/12/spring-2025-regulatory-agenda-highlights). The FTC has explicitly held back COPPA edtech amendments to avoid conflict with the FERPA NPRM (https://iapp.org/news/a/ftc-finalizes-coppa-rule-amendments). For Pathfinder this means: expect the school-official exception to be *tightened*, not loosened, in 2026. Architect to the strict reading.

### 1.7 The Anthropic disclosure problem in plain terms

Today, every audit text Pathfinder parses is sent to the Anthropic API. The product baseline confirms "audit content (which includes the student name and GPA) is sent to Anthropic for parsing and explanation." Under FERPA, that is a disclosure of PII from an education record to a third party. It is permissible only if Anthropic, by contract, satisfies the §99.31(a)(1)(i)(B) school-official conditions — direct control, function-substitution, no secondary use, §99.33(a) flow-down. Anthropic's standard commercial terms do not currently designate Anthropic as a school official under any specific institution's policies; Pathfinder must execute a Zero-Data-Retention (ZDR) addendum and a written processor-flow-down agreement before any sanctioned deployment can ride on top of Anthropic.

---

## 2. State-Level Laws

### 2.1 Illinois — SOPPA and BIPA (the misnamed "SCOPE Act")

Illinois's controlling student-privacy statute is the **Student Online Personal Protection Act (SOPPA)**, 105 ILCS 85, signed in its current form on August 23, 2019, effective July 1, 2021 (https://www.stateregstoday.com/family/privacy/student-data-privacy-laws-in-illinois). SOPPA is K-12-focused but its vendor-contract framework is widely cited at the postsecondary level. Vendors must:

- Execute written agreements with each district/institution.
- Refrain from selling data, targeted advertising, or building advertising profiles.
- Delete data on request.
- Notify of breaches as soon as aware.
- Be publicly listed on the institution's website.

Illinois's **Biometric Information Privacy Act (BIPA)**, 740 ILCS 14, applies if Pathfinder ever ingests biometrics. Pathfinder, as currently architected, processes screenshots and text — no fingerprints, retinal scans, voiceprints, or face geometry. **BIPA does not currently bite Pathfinder.** This must remain true: any future feature that adds voice notes, webcam-based verification, or face-based SSO drags Pathfinder into BIPA's notice-and-consent and 5-year private-right-of-action regime.

(There is no statute literally called "Illinois SCOPE Act"; the question likely intends California's SB 1047 or California's SOPIPA-equivalent, addressed below.)

### 2.2 California — SB 1047, CCPA/CPRA, SOPIPA, AB 2273

California's student-online-privacy statute is the **Student Online Personal Information Protection Act (SOPIPA)**, Bus. & Prof. Code §§22584–22585. Like SOPPA, it forbids targeted advertising and the sale of student PII by edtech operators. The **CCPA/CPRA** (Cal. Civ. Code §1798.100 et seq.) layers on top, treating identifiable student data as personal information subject to access, deletion, and opt-out-of-sale rights — though FERPA-covered data is partly carved out where FERPA preempts. Pathfinder must still respond to CCPA verifiable consumer requests for any non-FERPA-covered processing.

The much-debated **SB 1047** (Safe and Secure Innovation for Frontier Artificial Intelligence Models Act) was vetoed in September 2024, but its successor framework — California's **AB 2013** (training-data transparency, effective Jan 1, 2026) and the **California AI Transparency Act** — imposes disclosure obligations for AI systems. Pathfinder, as a downstream user of a foundation model, has limited primary obligations but inherits Anthropic's disclosures.

### 2.3 New York SHIELD Act

The **NY SHIELD Act** (General Business Law §899-bb) extends to any business holding "private information" of New York residents, including students at NY institutions. It mandates "reasonable" administrative, technical, and physical safeguards and was amended in December 2024 to require breach notification within 30 days, with expanded protected information taking effect March 21, 2025 (https://ag.ny.gov/resources/organizations/data-breach-reporting/shield-act). For Pathfinder this means: a written information-security program, encryption, access control, vendor-flowdown, and breach-response runbook are statutory minimums for any NY student touched.

### 2.4 Texas DIR — procurement gate for state schools

Texas state institutions (UT system, Texas A&M system, etc.) procure cloud services through the **Texas Department of Information Resources (DIR)** cooperative contracts (https://dir.texas.gov/). DIR-listed vendors must complete a **Texas Risk and Authorization Management Program (TX-RAMP)** assessment for cloud services that store, process, or transmit state data. For Pathfinder, TX-RAMP Level 1 (low-impact data) or Level 2 (moderate-impact, which includes PII) certification — modeled on FedRAMP — is the procurement floor for any Texas public university contract. **No TX-RAMP, no Texas state-school sale.**

### 2.5 Sectoral state student-privacy and consumer-privacy laws

- **Colorado Privacy Act (CPA)**, C.R.S. §6-1-1301 et seq., effective July 1, 2023. Treats students as consumers; requires DPIAs for high-risk processing including profiling that produces "legal or similarly significant effects" — course-scheduling that affects graduation timing arguably qualifies.
- **Virginia Consumer Data Protection Act (VCDPA)**, Va. Code §59.1-575 et seq., effective Jan 1, 2023. DPIA requirement for profiling. FERPA-covered data partly exempt where FERPA controls.
- **Connecticut Data Privacy Act (CTDPA)**, Conn. Gen. Stat. §42-515 et seq., effective July 1, 2023. Same DPIA framework. Connecticut also has a separate **student data privacy law (Public Act 16-189)** with strict vendor contract requirements.

The pattern is universal: written data-sharing agreement, purpose limitation, no targeted ads, deletion on request, breach notice. Pathfinder needs one master template that satisfies the union of these.

---

## 3. AI-Specific Frameworks

### 3.1 NIST AI Risk Management Framework

**NIST AI RMF 1.0** (NIST.AI.100-1, published January 26, 2023) and the **Generative AI Profile** (NIST-AI-600-1, published July 26, 2024) define the four core functions: **Govern, Map, Measure, Manage** (https://www.nist.gov/itl/ai-risk-management-framework). The framework is voluntary but is becoming the de facto standard universities cite when evaluating AI vendors. Pathfinder should produce, at minimum:

- A Govern artifact: AI governance policy, role assignments, escalation paths.
- A Map artifact: documented system context, data flows, intended uses, foreseeable misuses.
- A Measure artifact: validation methodology for the Vision parser (accuracy, false-positive rate on hallucinated requirements), the explanation generator (factuality, prompt-injection resistance), and the solver (correctness proof — the fact that the solver cannot return a time-conflicted schedule, per ADR-0003, is a Measure artifact).
- A Manage artifact: incident response, model-update cadence, retraining/rollback policy.

The Generative AI Profile adds 12 GAI-specific risks. Most relevant to Pathfinder: confabulation (hallucinated requirements), data privacy (audit content sent to Anthropic), information integrity (wrong CRN suggested → student misregisters), and value chain/component integration risks (Anthropic dependency).

### 3.2 U.S. Department of Education AI guidance

The foundational document is **"Artificial Intelligence and the Future of Teaching and Learning: Insights and Recommendations,"** Office of Educational Technology, May 2023 (https://www.ed.gov/sites/ed/files/documents/ai-report/ai-report.pdf). Two principles bear directly on Pathfinder:

- **"Humans in the loop."** ED's framing rejects AI as a replacement for educators; the human (advisor, faculty, registrar) must remain the central decision-maker (https://www.k12dive.com/news/Education-department-AI-schools-guidance/651409/). Pathfinder's architecture aligns with this — it suggests schedules; the student or advisor makes the registration decision — but that posture must be explicit in product documentation and contract language.
- **Data minimization for AI.** ED notes that AI requires data going beyond conventional roster/gradebook records and that "data privacy and security" is the central safety argument for vendor systems. Pathfinder must be able to articulate, per institution, exactly what data flows where and for how long.

ED followed up in October 2024 with **"Designing for Education with Artificial Intelligence: An Essential Guide for Developers"** (https://www.ed.gov/ai/), which functions as a vendor-facing checklist. Pathfinder should self-assess against it before any procurement conversation.

### 3.3 Accreditor positions on AI in advising

- **MSCHE** (Middle States Commission on Higher Education) approved a new **Use of Artificial Intelligence Policy and Procedures** in 2025 (https://www.msche.org/2025/07/02/new-use-of-artificial-intelligence-accreditation-policy-and-procedures/). Bryant University is MSCHE-accredited; Pathfinder must align with the framework.
- **C-RAC** (Council of Regional Accrediting Commissions, comprising MSCHE, NECHE, SACSCOC, HLC, NWCCU, WSCUC) released a joint statement on AI in October 2025 (https://www.msche.org/2025/10/06/c-rac-releases-statement-on-the-use-of-artificial-intelligence-ai/). For pilots in any region, the statement is the unified accreditor position.
- **NECHE** (New England Commission of Higher Education) has not issued a separate AI-in-advising standard but treats it under existing Standard Six (Teaching, Learning, and Scholarship) and Standard Eight (Educational Effectiveness). The 2024 application guide is the operative document (https://www.neche.org/wp-content/uploads/2024/07/2024-Guide-for-currently-accredited-institutions-updated-with-Data-Dashboards.pdf).
- **SACSCOC, WSCUC, HLC** have similar institutional-effectiveness-based postures; specific advising-AI policy is not yet published as of April 2026.

The accreditor angle matters because a misfire (Pathfinder hallucinates a requirement, a student misses graduation, Bryant's MSCHE review picks it up) is a vector for institutional reputational and accreditation risk that procurement officers will price into the deal.

### 3.4 EU AI Act

**Regulation (EU) 2024/1689** (the EU AI Act) entered into force August 1, 2024, with full applicability August 2, 2026 (https://artificialintelligenceact.eu/high-level-summary/). Annex III, point 3 designates the following education-related AI systems as **high-risk**:

- (a) Determining access, admission, or assignment to educational/vocational institutions.
- (b) Evaluating learning outcomes, including outcomes used to steer the learning process.
- (c) Assessing the appropriate level of education an individual will receive.
- (d) Monitoring and detecting prohibited behavior of students during tests.

Pathfinder is on the boundary of (b) and (c). A scheduling tool that recommends one course over another, particularly one that interacts with graduation-progress decisions, plausibly "steers the learning process." The conservative reading is **high-risk**, which triggers risk management, data governance, technical documentation, transparency, human oversight, accuracy/robustness/cybersecurity, and post-market monitoring obligations under Articles 9-15. For any institution with EU students or operations (Bryant has none, but a future customer may), Pathfinder needs an EU AI Act conformity assessment readiness package.

---

## 4. Data Residency & Sub-Processor Concerns

### 4.1 Anthropic's published compliance posture

Anthropic publishes the following (https://privacy.claude.com/en/articles/10015870-what-certifications-has-anthropic-obtained):

- **SOC 2 Type I and Type II** (Trust Services Criteria: Security, Availability, Confidentiality).
- **ISO/IEC 27001:2022** (Information Security Management).
- **ISO/IEC 42001:2023** (AI Management Systems — Anthropic was an early adopter).
- **HIPAA-ready** with Business Associate Agreement available on request.
- **Zero-Data-Retention (ZDR)** addendum available for enterprise customers, applying to first-party APIs and the Anthropic-key-using products (https://privacy.claude.com/en/articles/8956058-i-have-a-zero-data-retention-agreement-with-anthropic-what-products-does-it-apply-to). Default API retention is 7 days for abuse-monitoring inputs (reduced from 30); ZDR drops this to nothing persisted post-session.
- A SOC 3 summary is publicly downloadable from the Anthropic Trust Portal; the SOC 2 detailed report is available under NDA.

What Anthropic does **not** publish: a formal FERPA attestation. ED does not certify vendors and there is no federal "FERPA seal." The right way to read Anthropic's posture for Pathfinder's purposes: SOC 2 Type II + ISO 27001 + ZDR + a contractual flow-down clause is the maximum practical FERPA-readiness Anthropic can provide. The remaining FERPA accountability sits with Pathfinder.

### 4.2 Data residency

Anthropic API regions are limited. For schools with statutory in-state or in-country data-residency requirements (Texas DIR for state-funded data, EU GDPR for EU residents, Canadian PIPEDA for Canadian institutions), Pathfinder's ability to meet residency is **gated by Anthropic's region availability**. As of April 2026, Anthropic offers AWS Bedrock and Google Vertex deployment options in more regions than the first-party API; for any institution requiring strict residency, Pathfinder will likely need to deploy through Bedrock-in-region rather than through the first-party API.

### 4.3 GDPR if EU students are touched

GDPR Article 28 (processor obligations), Article 30 (records of processing), Article 35 (DPIA), and the Schrems II framework for cross-border transfers all apply if any EU student's audit is processed. Pathfinder needs Standard Contractual Clauses with Anthropic, a DPIA, and an EU representative for any EU-touching deployment.

---

## 5. Vendor Security Expectations

### 5.1 HECVAT — the dominant higher-ed vendor assessment

**HECVAT** (Higher Education Community Vendor Assessment Toolkit) is published by EDUCAUSE in collaboration with REN-ISAC and Internet2 (https://www.ren-isac.net/hecvat/index.html). The current release is **HECVAT 4** (with point releases through **HECVAT 4.1.5** as of early 2026), launched in January 2025 (https://er.educause.edu/articles/2024/10/coming-in-january-hecvat-4). HECVAT 4 consolidated the prior **Full**, **Lite**, and **On-Premise** variants into a single questionnaire with conditional logic, and added dedicated **AI** and **privacy** sections — directly relevant to Pathfinder.

The variants in current use:

- **HECVAT 4 (consolidated)** — the new full-spectrum questionnaire; conditional logic substitutes for the old Lite/Full split.
- **HECVAT On-Premise (legacy)** — retained for self-hosted deployments.
- **HECVAT Triage** — short risk-screening tool used by procurement to decide whether a Full review is needed.

Typical timeline for a small vendor to complete HECVAT 4 cold: **80-160 hours of internal effort over 4-12 weeks**, longer if the vendor lacks a SOC 2. Many universities will not begin a procurement conversation without a current HECVAT on file at the **Cloud Broker Index (CBI)** maintained by REN-ISAC.

Pathfinder has **no HECVAT submitted**. This is the single most actionable near-term gap.

### 5.2 SOC 2 Type II

Most R1 universities require a current SOC 2 Type II report (or an equivalent independent attestation) for any vendor handling student PII. Type II covers operating effectiveness over a multi-month observation window; Type I is a point-in-time design assessment.

Cost and timeline for a small SaaS startup, current 2025-2026 figures (https://www.vanta.com/collection/soc-2/soc-2-audit-cost, https://trycomp.ai/soc-2-cost-breakdown):

- Audit fees: $12,000-$50,000 for Type II; $10,000-$25,000 from mid-tier specialized firms.
- Readiness/consulting: $5,000-$25,000.
- Compliance automation tooling (Vanta, Drata, Secureframe): $8,000-$30,000/year.
- Internal staff effort: 100-300+ hours.
- Total realistic budget for a first SOC 2 Type II: **$40,000-$90,000** all-in over 6-12 months (pre-audit readiness 3-6 months + 3-12 month observation window).

Short-cut path: SOC 2 Type I in ~3 months for ~$15k-$25k as an interim artifact while Type II accrues. Several universities will accept Type I + "Type II in flight" for a pilot.

### 5.3 VPAT / Section 508 / WCAG

The **Voluntary Product Accessibility Template (VPAT)** is published by the Information Technology Industry Council (ITI) and produces an **Accessibility Conformance Report (ACR)** measured against Section 508 (U.S.), EN 301 549 (EU), and WCAG (https://www.itic.org/policy/accessibility/vpat). Under the **DOJ ADA Title II final rule** (April 2024), public colleges and universities must ensure all digital tools — including third-party vendors — conform to **WCAG 2.1 Level AA** by April 24, 2026 (large entities) or April 24, 2027 (smaller entities). Many state universities have "mini-508" laws that have already required vendor VPATs for years (https://accessibe.com/blog/knowledgebase/how-higher-education-institutions-evaluate-vendors).

Pathfinder claims WCAG AA compliance via manual contrast and keyboard checks. That is a reasonable starting point but is not a VPAT/ACR. A formal third-party accessibility audit and ACR drafting cost **$5,000-$15,000** and take 2-4 weeks.

### 5.4 Cybersecurity insurance minimums

Higher-ed risk-management offices typically require **$5,000,000 per-occurrence cyber and tech-E&O coverage** for any vendor with access to sensitive university data, with the institution named as additional insured. Cornell's published vendor requirement is "not less than $5,000,000 for each wrongful act" (https://www.risk.cornell.edu/vendor-provider-main-page/cyber-and-technology/). University of Nevada Reno requires the same $5M floor for technology contracts under $1M (https://www.unr.edu/bcn-nshe/risk/contracts/technology-contracts). Higher contracts trigger higher limits.

A first cyber liability policy for a pre-revenue SaaS startup typically runs **$1,500-$5,000/year** at $1M limits and $5,000-$15,000/year at $5M limits. Pathfinder, operating without an entity, has zero coverage today.

### 5.5 Penetration testing

Most HECVAT-equivalent reviews ask for a recent (≤12 months) third-party penetration test. Cost: **$8,000-$25,000** for a SaaS web app of Pathfinder's scope; timeline 2-4 weeks plus remediation.

---

## 6. Concrete Pre-Pilot Checklist

Numbered, ordered by urgency. Each item is labeled with what it blocks:

**[P]** = blocks **Bryant pilot** (sanctioned, opt-in, no money).
**[N]** = blocks **non-Bryant paid pilot** (single second institution).
**[R]** = blocks **R1 paid contract** (recurring revenue, multi-tenant).

| # | Action | Blocks | Effort | Cost |
|---|---|---|---|---|
| 1 | Form a corporate entity (Delaware C-corp or LLC) and execute founder IP assignment. Pathfinder cannot enter contracts as Owen-personally for institutional data. | P, N, R | 2 wk | $500-$2k |
| 2 | Draft a one-page **Bryant data-sharing memorandum** with Bryant's General Counsel and Registrar, designating Pathfinder a §99.31(a)(1)(i)(B) school official. Include purpose limitation, no-secondary-use, deletion-on-request, sub-processor flow-down. | P, N, R | 4-8 wk | legal $2k-$8k |
| 3 | Execute an **Anthropic Zero-Data-Retention addendum** and ensure the contract includes FERPA-equivalent flow-down language. | P, N, R | 2-6 wk | included w/ enterprise plan |
| 4 | Publish a **privacy notice** for students (purpose, data collected, retention, deletion request mechanism, contact). Required by SOPPA-style statutes and GDPR; signaled best practice everywhere else. | P, N, R | 1 wk | self |
| 5 | Implement **audit logging** of every audit ingest, every Claude call, and every CRN export. Required by FERPA §99.32 (recordkeeping for disclosures) and SOC 2. | P, N, R | 2-3 wk | self |
| 6 | Implement a **retention/deletion policy**: 90-day default retention, deletion on student request, automatic purge on session end. | P, N, R | 1 wk | self |
| 7 | Write the **NIST AI RMF Map artifact** documenting data flows, intended use, foreseeable misuse, and the deterministic-solver guarantee. | P, N, R | 1-2 wk | self |
| 8 | Stand up **Bryant SSO** (Shibboleth/SAML or Azure AD) before the pilot population exceeds 5 students. The current "anyone can paste an audit" model is itself a privacy issue. | P, N, R | 4-6 wk | self |
| 9 | **Cyber liability + tech E&O policy**, $1M minimum for Bryant, $5M before any non-Bryant institution. | (P at $1M), N, R at $5M | 1-2 wk | $1.5k-$5k/yr at $1M, $5k-$15k/yr at $5M |
| 10 | **HECVAT 4 questionnaire** completed and submitted to the REN-ISAC Cloud Broker Index. | N, R | 6-12 wk | self ($5k-$15k if outsourced) |
| 11 | **SOC 2 Type I** as an interim artifact while Type II accrues. | N, R | 3-4 mo | $15k-$30k |
| 12 | **Third-party penetration test** with remediation. | N, R | 4-6 wk | $8k-$25k |
| 13 | **VPAT / ACR** drafted against WCAG 2.1 AA (the ADA Title II floor by April 2026). | N, R | 2-4 wk | $5k-$15k |
| 14 | **SOC 2 Type II** (12-month observation, then audit). | R | 12-15 mo total | $40k-$90k all-in |
| 15 | **TX-RAMP Level 2** if pursuing Texas state schools; **StateRAMP** if pursuing other state-funded institutions. | R (state-school subset) | 6-12 mo | $30k-$80k |
| 16 | **Multi-tenant tenancy isolation** with per-institution catalog, auth scope, and audit log segregation. (Architectural — not strictly a compliance artifact, but every HECVAT will fail without it for an R1.) | R | 2-3 mo | self |
| 17 | **EU AI Act conformity assessment readiness package** (technical documentation per Article 11, risk management per Article 9, transparency per Article 13) if any EU student is in scope. | R (EU subset) | 2-4 mo | legal $10k-$30k |
| 18 | **DPIA** for Colorado, Virginia, Connecticut students — single template covering profiling under all three statutes. | R | 2 wk | legal $2k-$5k |
| 19 | **Sub-processor disclosure page** publicly listing Anthropic, AWS/GCP, any analytics or email vendors, with links to each sub-processor's compliance artifacts. | N, R | 1 wk | self |
| 20 | **Incident-response runbook** with the 30-day NY SHIELD breach-notification clock and per-state notification deltas. | N, R | 1-2 wk | self |

### 6.1 What blocks the **Bryant pilot** specifically (items #1-#9)

The Bryant pilot is the cheap path. The founder is a Bryant student, the data is intra-institution, the school's General Counsel can negotiate a §99.31 designation in a single meeting, no money changes hands, and the population is opt-in. The realistic blocker set is items 1-9. Total cash: ~$5k-$15k. Total elapsed time: ~8-12 weeks.

The non-obvious gating item is **#2 (the Bryant data-sharing memo)**. Without the memo, Pathfinder is a third-party tool that students happen to upload their own audits into. With the memo, Pathfinder is a sanctioned school-official vendor, which both unlocks legitimate institutional access (rosters, real Banner integration) and makes Bryant the responsible party for the §99.31 designation.

### 6.2 What blocks a **non-Bryant paid pilot** (items #1-#13)

A second institution is qualitatively different. They have no relationship to Owen. They will demand the HECVAT, they will demand a SOC 2 (Type I minimum, Type II strongly preferred), they will demand cyber insurance at the $5M floor, they will demand a VPAT, and they will demand an MSA + DPA + FERPA addendum that has been blessed by their general counsel. Total cash for items 10-13 alone: ~$30k-$70k. Total elapsed time on top of the Bryant pilot: ~6-9 months.

### 6.3 What blocks an **R1 paid contract** (all items)

R1 universities have mature procurement offices, often with a privacy review board, a security review board, and an accessibility review board operating in series. The full checklist is the floor. Add: indemnification clauses with carve-outs for IP and privacy, a published Service Level Agreement, board-level data governance, and (for any state-school subset) the relevant state authorization (TX-RAMP, StateRAMP, etc.). Total cash to clear all gates: **~$100k-$200k** in year-one external spend, plus 15-25% of one full-time engineer's time for ongoing compliance operations.

---

## 7. The Three Findings the Synthesis Agent Should Carry Forward

1. **Today, Pathfinder is non-compliant with FERPA in any institutional sense.** Audit content goes to Anthropic without a school-official agreement, without §99.33 flow-down, without ZDR, and without an audit log. The fix is contractual, not architectural — but it has to happen before the first sanctioned student touches the system.
2. **The HECVAT/SOC 2/VPAT/cyber-insurance bundle is the threshold gate at every U.S. university outside Bryant.** None of the four are individually exotic; together they are a 6-12 month, $50k-$100k expedition that no solo founder will complete part-time. This is the single biggest commercialization rate-limiter.
3. **The 2024 FERPA NPRM and the EU AI Act both raise the floor in 2026.** Pathfinder should architect to the *strict* reading — function-substitution-only use, ZDR, full Article 9-15 EU AI Act readiness for any future EU exposure — rather than the permissive reading. Retrofitting compliance after a customer signs is harder and more expensive than designing for it on day one.

---

*Sources cited inline. Primary regulatory sources (ecfr.gov, law.cornell.edu, ed.gov, nist.gov, msche.org, ren-isac.net, educause.edu) prioritized over secondary commentary.*
