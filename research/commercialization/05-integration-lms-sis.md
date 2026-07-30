# 05 — Integration: SIS / LMS / SSO

> Subagent 05 brief for the BryantPathfinder commercialization swarm. Scope: the technical integration surface BryantPathfinder must traverse to move from a Degree Works screenshot ingestion + manual CRN copy/paste workflow into something a campus IT shop will sanction, configure, and pay for.

---

## 0. Starting position

BryantPathfinder today has zero SIS read or write integration. Its inputs are (a) a Claude Vision parse of a Degree Works screenshot, (b) a static `sections.json` produced by a one-time scrape of Banner Self-Service. Its output is a list of CRNs the student manually pastes into Banner's "Add by CRN" form. There is no SSO. There is no LMS hookup. There is no production deployment. This is the floor.

The ceiling — what every adjacent commercial product (Stellic, Coursedog, EAB Navigate, Pathify, Civitas, Ellucian's own Student Planning) reaches for — is a bidirectional, authenticated, near-real-time relationship with the SIS, the degree-audit system, the LMS, and the campus IdP. Closing that gap is mostly engineering, partly vendor-relationship navigation, and entirely non-negotiable for institutional procurement.

---

## 1. SIS systems — read paths

### 1.1 Ellucian Banner (via Ethos Integration)

**Market share.** Banner is the dominant SIS in U.S. higher education. According to ListEdTech's January 2025 update, Ellucian Banner leads the North American SIS HigherEd market at roughly **24% market share**, with Tambellini Group's 2023 report describing Ellucian as the most widely used student system across two-year and four-year, public and private/not-for-profit institutions ([ListEdTech](https://www.listedtech.com/blog/north-american-sis-highered-market-share-january-2025-update/), [Ellucian press](https://www.ellucian.com/news/ellucian-recognized-market-leader-higher-education-student-system)). Bryant University runs Banner, which is why BryantPathfinder happens to work at all.

**Official API name.** Ethos Integration. Banner data is exposed through Ellucian's Ethos API gateway at `https://integrate.elluciancloud.com/api/...` rather than direct Banner DB connections. Resources are modeled as REST endpoints conforming to a unified data model: `academic-periods` (terms), `courses` (catalog), `sections` (offerings), `persons`, `student-academic-programs`, etc. Filtering uses a JSON `criteria` query parameter, e.g. `GET /api/sections?criteria={"academicPeriod":{"id":"..."},"course":{"id":"..."}}` ([Ellucian Ethos endpoint examples via Ad Astra](https://help.adastra.live/hc/en-us/articles/15295562799252-Ethos-Data-Access-Models-and-Endpoints), [ellucianEthos GitHub](https://github.com/ellucianEthos/postman-ethos-integration)).

**Authentication.** Ethos uses an API-key-to-JWT exchange. The integration registers an API key in the institution's Ethos tenant, calls `/auth` with that key, and receives a short-lived JWT bearer token; subsequent REST calls send `Authorization: Bearer <jwt>` ([Ellucian integration-bruno](https://github.com/ellucian-developer/integration-bruno), [integration-postman](https://github.com/ellucian-developer/integration-postman)). Scoping is done through Ethos "applications" — each application registration declares which resources it may read or write, and OAuth-style scopes are constrained to the catalog Ellucian publishes, not freeform ([Systech overview of Banner API security](https://systechus.com/secure-banner-apis-mtls-oauth-least-privilege/)).

**Data scope.** Course catalog, sections, academic terms, student demographics, enrollment, registration, holds, grades. For BryantPathfinder, the load-bearing endpoints are `courses`, `sections`, and `student-academic-programs` (to map a student to their declared major/minor for requirement filtering).

**Getting access.** Three gates: (1) the institution must license Ethos Integration (most Banner sites have it, but not all have it turned on), (2) a campus admin must register the third-party application in Ethos and provision an API key, (3) Ellucian's Partner Program (Ellucian Partner Network) is the formal route for ISVs who want to be listed in the Ellucian Solution Center marketplace and validated against Ellucian's reference data. Partner Network membership is gated on a paid agreement and a technical review; you can integrate without it (institution-by-institution) but you cannot be listed as an Ellucian-validated solution.

**Friction.** Ethos isn't free at the institution level — it's a separate license — and a non-trivial number of Banner sites either don't have it provisioned or don't have it on the latest release. The "Banner has Ethos" assumption fails roughly often enough that any commercial pitch needs a fallback (see §8).

### 1.2 Workday Student

**Official API.** Workday exposes both SOAP web services (the older, more feature-complete surface) and REST APIs through the Workday Web Services framework, accessible to authenticated tenants via `community.workday.com/api` documentation. The Workday Student domain has its own object model (Student, Course Definition, Course Section, Academic Period, Program of Study) ([Workday Community API portal](https://community.workday.com/api), [Workday REST directory](https://community.workday.com/sites/default/files/file-hosting/restapi/index.html)).

**Authentication.** OAuth 2.0 with refresh tokens for REST; for SOAP, ISU (Integration System User) credentials with WS-Security UsernameToken. Production integrations register an "Integration System" inside the tenant and are bound to a security group that controls object-level visibility ([Reco overview of Workday REST](https://www.reco.ai/hub/workday-rest-api-integration-security)).

**Friction.** Workday Student is the harder market to crack: every tenant is custom-configured, the data model varies institution-to-institution more than Banner's, and Workday gates partner-program access tightly. Newer R1s (Yale, USC, Cornell partial) have moved to Workday Student, but the ISV ecosystem is far thinner than Banner's.

### 1.3 Oracle PeopleSoft Campus Solutions / Oracle Cloud Student Experience

**Official API.** PeopleSoft Campus Solutions exposes web services through PeopleSoft Integration Broker, supporting both SOAP and REST; REST endpoints are configured through Service Operations and routed through Integration Broker ([Oracle: Understanding REST API Endpoints for PeopleSoft](https://docs.oracle.com/cd/F92336_01/fscm92pbr50/eng/fscm/eccf/UnderstandingRestApiEndpointsForPeoplesoft.html), [PeopleSoft Integration Broker docs](https://docs.oracle.com/cd/E25688_01/pt852pbr0/eng/psbooks/tibr/htm/tibr12.htm)).

**Authentication.** Out of the box: HTTP Basic, WS-Security UsernameToken, or SSL client certificates; OAuth 2.0 supported via Oracle Identity Manager or third-party gateway. There is no first-class developer portal in the way Ethos provides — every PeopleSoft site exposes its own PIA URL, its own service registry, and its own auth scheme depending on how the campus configured Integration Broker.

**Friction.** Each campus is essentially a custom integration. Oracle's Cloud Student Experience (the SaaS successor) is still a small footprint; most PeopleSoft Campus Solutions sites are on-prem or hybrid.

### 1.4 Ellucian Colleague (Web API or Ethos)

**Official APIs.** Two pathways: the Colleague Web API (a REST/JSON interface deployed on IIS that wraps the Colleague application via DMI Toolkit, supporting Colleague-native auth, CAS, or SAML) and Ellucian Ethos Integration (the same unified gateway as Banner, so the same endpoints surface Colleague data) ([Yuba CCD setup guide](https://yc.yccd.edu/wp-content/uploads/2018/03/Setting-Up-Colleague-Web-API.pdf), [Coursedog Colleague Ethos setup](https://coursedog.freshdesk.com/support/solutions/articles/48001252098-colleague-ethos-integration-extension-setup)).

**Authentication.** Web API: session-token-based (POST credentials → opaque token in `X-CustomCredentials`-style header). Ethos: same JWT flow as Banner.

**Friction.** Colleague sites tend to be smaller institutions (community colleges, small privates). Ethos coverage is improving but not universal. Direct DB integration is technically possible (and historically common) but not a path BryantPathfinder should pursue.

### 1.5 Jenzabar (JX, Jenzabar One, Unity Platform)

**Official API.** Jenzabar's Unity Platform is a per-institution iPaaS layer; the Campus Marketplace Public API (announced May 2024) exposes student, financial, course, and section data through a documented REST surface for ISVs ([Jenzabar press](https://jenzabar.com/blog/jenzabar-unveils-public-api-for-campus-marketplace), [BusinessWire](https://www.businesswire.com/news/home/20240508903173/en/Jenzabar-Unveils-Public-API-for-Campus-Marketplace-Designed-to-Enhance-Data-Analyses-Streamline-Operations-and-Improve-Reporting), [Jenzabar Unity Platform](https://jenzabar.com/product/unity-platform)).

**Authentication.** OAuth 2.0 client credentials per the Marketplace API.

**Friction.** Coursedog's Jenzabar integration documentation notes you commonly need both Unity Platform and direct read replicas to get full coverage, which means a Jenzabar pilot is a 2x integration at minimum.

### 1.6 Anthology Student (formerly CampusNexus Student)

**Official API.** Two API surfaces — the Query Model (read) and Command Model (write) — exposed as REST/OData with Swagger documentation per-tenant at `https://<tenant>.campusnexus.cloud/swagger/` ([Anthology developer index](https://docs.api.campuslabs.com/), [Anthology student-api-samples on GitHub](https://github.com/anthology-inc/student-api-samples), [Anthology dev docs](https://blackboard.github.io/), [Student Service Catalog](https://blackboard.github.io/rest-apis/student/servicecatalog/about-student-service-catalog)).

**Authentication.** OAuth 2.0 client credentials. From Anthology's docs: "an OAuth 2.0-based authorization token is required to make calls to the API. To get a token, your code must make a POST call to the authorization server with your access keys."

**Friction.** Anthology Student is "made available exclusively to licensed Anthology member campuses. Third-party or public use of Student APIs is prohibited without the consent of Anthology. Campus developers who wish to access the API must be pre-approved by Anthology" — so a partner-program agreement is a hard prerequisite, not just a nice-to-have.

---

## 2. Degree-audit systems

The audit data is the single most valuable input BryantPathfinder consumes. Today it's parsed from a screenshot. Direct ingestion changes everything about reliability.

### 2.1 Ellucian Degree Works (dominant, including Bryant)

**Bryant's stack.** Bryant publishes degree audits through Degree Works on top of Banner — this is what the demo screenshot is from. Any commercialization conversation at Bryant or a peer Banner+Degree-Works site goes through this product.

**API surface.** Degree Works exposes RESTful "DW services" (deployable as `degreeworks-services.war` and `StudentPlanner-war`) on Tomcat/Weblogic. The most relevant services for BryantPathfinder are:
- `ArticulateAuditService` — accepts a PESC-conformant `RequestDA` XML payload (validated against `RequestDA-1.5.xsd`) and returns the audit as either DegreeWorks XML or HTML.
- A `plans` GET endpoint returning JSON for student plans.
- Various transcript and goal CRUD endpoints.

See the unofficial `DwApiGuide` (DW 4.1.3) circulating publicly ([USU ServiceNow attachment](https://usu.service-now.com/sys_attachment.do?sys_id=c14216c7b80ca100496e01a3fbc299e6)) and the Coursedog integration article ([Coursedog DegreeWorks integration](https://coursedog.freshdesk.com/support/solutions/articles/48001210598-ellucian-degreeworks-integration), [product page](https://www.ellucian.com/solutions/ellucian-degree-works)).

**Authentication.** Typically institution-internal SAML/CAS with a service-account fallback; for ISVs, Ethos is the cleaner path because Degree Works data can also be surfaced through Ethos resources (`student-academic-programs`, `student-academic-program-progress` in newer releases). In practice most third parties either (a) get a service account and call DW REST directly through a campus VPN/reverse proxy, or (b) negotiate a nightly XML drop of audit results to SFTP.

**The cleanest read path** for BryantPathfinder is: student initiates → frontend calls our backend → backend calls DW `getAudit` (REST) with the student's Banner ID via a campus-issued service account → response is the structured audit XML, parsed deterministically. This eliminates the Vision step entirely, with all its hallucination risk.

### 2.2 Stellic

**Status.** Stellic is the modern degree-audit replacement at a growing number of R1s — Cornell, Carnegie Mellon, Indiana University all listed publicly ([Stellic](https://www.stellic.com), [CMU](https://www.cmu.edu/es/stellic/index.html), [Cornell IT](https://it.cornell.edu/degreeaudit), [IU](https://studentsuccess.iu.edu/stellic/index.html)).

**Integration.** Stellic itself integrates with the SIS via APIs and batch updates and has been moving toward real-time API delivery ([Stellic technology overview](https://www.stellic.com/resources/under-the-hood)). For BryantPathfinder the strategically interesting question is whether Stellic *exposes* a third-party API for an external scheduler to read the audit. As of April 2026 Stellic does not publish a public partner API; integration with Stellic likely requires a partnership conversation. Practically, at a Stellic campus BryantPathfinder either competes with Stellic Progress (their own scheduling/registration product, launched for Fall 2026 registration at IU per their press) or partners — and the partnership economics are unattractive given Stellic's overlapping roadmap.

### 2.3 u.achieve / CollegeSource

Legacy degree-audit at a long tail of campuses; integration is typically through CSV exports or vendor-specific XML. Lower priority for an MVI.

### 2.4 Banner Self-Service Degree Audit (CAPP / SSDA)

Older Banner audits without Degree Works. Read paths are even messier (often only HTML), and CAPP is end-of-life. Treat as not addressable.

---

## 3. LMS systems

### 3.1 Coverage and integration mechanics

| LMS | Higher-ed share (rough) | Primary integration surface |
|---|---|---|
| Canvas (Instructure) | Plurality at U.S. 4-year | LTI 1.3 + Canvas LMS REST API + Canvas Data 2 |
| Blackboard Learn Ultra (Anthology) | Significant install base | Anthology Learn REST APIs + LTI 1.3 |
| D2L Brightspace | Strong in mid-size publics | Valence REST API + LTI 1.3 |
| Moodle | Long tail / community colleges / global | Moodle Web Services + LTI 1.3 |

**Canvas (Instructure).** LTI 1.3 with LTI Advantage is the canonical path. A "Developer Key" registered by a campus admin stores the tool's OIDC issuer, JWKS URL, redirect URIs, and scopes; the tool launches via OIDC then calls LTI Advantage Services (Names and Roles Provisioning, Assignment and Grade Services, Deep Linking) using a client credentials grant scoped by the developer key ([Instructure Developer Keys](https://developerdocs.instructure.com/services/canvas/resources/developer_keys), [Manually configuring LTI Advantage tools](https://www.canvas.instructure.com/doc/api/file.lti_dev_key_config.html), [LTI launch overview](https://documentation.instructure.com/doc/api/file.lti_launch_overview.html)). Canvas Data 2 is a separate analytics-grade dataset (S3 / parquet), not relevant for a scheduling tool.

**Blackboard Learn Ultra.** Anthology publishes its REST APIs on the developer portal at `developer.blackboard.com` with OAuth 2.0; LTI 1.3 is the cross-LMS path.

**D2L Brightspace.** Valence (`docs.valence.desire2learn.com`) is REST/OAuth 2.0; tools register through D2L's "Manage Extensibility" admin tool to get OAuth 2.0 client credentials ([Valence reference](https://docs.valence.desire2learn.com/reference.html), [Valence about](https://docs.valence.desire2learn.com/about.html)).

**Moodle.** Web Services exposes a per-function REST/SOAP/XML-RPC surface gated by capability tokens; LTI 1.3 is also supported. Moodle integrations are LMS-instance-specific and notoriously variable.

**Standards-based shortcut.** LTI 1.3 / LTI Advantage works across all four. A single LTI 1.3 tool registration gives you launch + names-and-roles + (optional) grade passback in any IMS/1EdTech-certified LMS. For a scheduling tool with no grading concern, LTI launch + NRPS is enough.

### 3.2 What does an LMS integration *add* for BryantPathfinder?

This is worth interrogating because LMS integration is not free and may be a distraction.

Plausible value:
- **In-LMS launch.** "Plan next semester" tile inside Canvas → seamless launch into BryantPathfinder with the student already authenticated and identified (NRPS gives you the SIS person sourced ID). This solves the discovery problem more than any marketing channel.
- **Calendar sync.** Once a schedule is selected, push class meeting times to the Canvas calendar (already covered by `.ics` export today, marginally better natively).
- **Notifications.** Push "registration opens in 48 hours, your plan is locked" via the LMS notification system.
- **Advisor-facing roster push.** When a student finalizes a plan, deliver the CRN list to the assigned advisor via an LMS course tool (the "advising course" pattern is common).

Not valuable:
- Gradebook integration (BryantPathfinder doesn't grade anything).
- Course content delivery.
- Assignment workflows.

**Recommendation.** LMS integration is post-MVI, not part of MVI. The LMS adds discovery surface, not core function.

---

## 4. SSO

Non-negotiable. No campus IT will sanction a tool that asks students for new credentials, and no campus security review will allow a tool that doesn't authenticate against the institutional IdP.

### 4.1 The four paths in U.S. higher ed

**Shibboleth / SAML 2.0 via InCommon Federation.** Shibboleth IdP is the dominant academic IdP in the U.S., and InCommon is the federation operator that lets a Service Provider register metadata once and become trusted by ~1,000 member institutions automatically ([InCommon Shibboleth](https://incommon.org/software/shibboleth/), [Shibboleth at Columbia](https://www.cuit.columbia.edu/shibboleth), [SAML/Shibboleth at Harvard IAM](https://www.iam.harvard.edu/resources/saml-shibboleth-integration)). InCommon membership for an SP is currently in the low thousands of dollars per year and requires a sponsoring institution. *Joining InCommon is the single highest-leverage SSO move BryantPathfinder can make* — it converts each new campus deployment from a multi-week SAML metadata exchange into a one-day registration.

**Microsoft Entra ID (formerly Azure AD).** The IdP at most Microsoft 365 Education campuses. Supports both SAML 2.0 and OIDC. Many Shibboleth shops have moved to a hybrid Entra-as-IdP-with-Shibboleth-as-SAML-proxy pattern ([Microsoft architecture doc](https://learn.microsoft.com/en-us/entra/architecture/multilateral-federation-solution-two)).

**Google Workspace for Education.** OIDC primary, SAML available. Common at smaller and community colleges.

**Okta.** Common as a campus SSO replacement at private institutions; SAML 2.0 + OIDC. Has its own ISV partner registration but for SAML it's just another IdP.

### 4.2 Engineering effort to add SAML to a small SaaS

The SaaS-SSO industry consensus is that building production-grade multi-tenant SAML in-house is **12 to 16 weeks of focused engineering** ([Scalekit guide](https://www.scalekit.com/blog/saml-implementation-in-b2b-saas-apps-a-step-by-step-guide-for-developers), [Frontegg implementation guide](https://frontegg.com/blog/implementing-saml-authentication-in-enterprise-saas-applications), [Stack Overflow blog on SSO problems](https://stackoverflow.blog/2022/09/12/the-many-problems-with-implementing-single-sign-on/)) — covering protocol, metadata management, multi-tenant routing, certificate rotation, IdP-specific quirks, and admin UX.

For BryantPathfinder specifically, the realistic numbers are:
- **Single-tenant SAML against one IdP (e.g., just Bryant Shibboleth).** ~1–2 person-weeks using an off-the-shelf library (e.g., `python3-saml`, `pysaml2`, FastAPI OIDC adapter). This is enough for a Bryant pilot.
- **Multi-tenant SAML with per-institution metadata config.** ~6–10 person-weeks. This is what's needed for a second paid pilot.
- **InCommon-federated production SP.** ~8–12 person-weeks plus the InCommon membership/sponsorship process (~6–12 weeks elapsed for the membership itself).
- **Use a managed SSO provider** (WorkOS, Auth0/Okta Customer Identity, Scalekit, Stytch). Cuts engineering to ~1–2 weeks but adds $0.50–$5/MAU at higher-ed scale, which can wreck the unit economics. Worth doing for the first 2–3 customers, then re-evaluate.

**Recommendation.** Use WorkOS or equivalent for the first paid pilot to compress time-to-value. Plan to migrate to native multi-tenant SAML + InCommon membership once revenue justifies the engineering quarter.

---

## 5. Standards

**1EdTech (formerly IMS Global).** The standards body that owns LTI, OneRoster, and Caliper.

- **LTI 1.3 / LTI Advantage** — secure tool launch + NRPS + AGS. Use LTI 1.3, not LTI 1.1 (deprecated). LTI 1.3 is built on OIDC + JWS-signed messages + OAuth 2.0 client credentials for service calls.
- **OneRoster v1.1 / v1.2** — roster, gradebook, and resources data exchange between SIS and LMS, both REST (JSON) and CSV bindings. v1.2 splits into three independent services (Rostering, Gradebook, Resources) that can be implemented independently ([OneRoster v1.1 final spec](https://www.imsglobal.org/oneroster-v11-final-specification), [OneRoster CSV tables](https://www.imsglobal.org/oneroster-v11-final-csv-tables), [OneRoster intro](https://www.imsglobal.org/oneroster-11-introduction), [OneRoster + LTI Advantage](https://www.imsglobal.org/about/k12/oneroster-and-lti-advantage)). Heavily used in K-12; lighter footprint in higher ed but increasingly relevant.
- **Caliper Analytics** — learning analytics event stream. Not relevant for a scheduling tool.

**Ed-Fi data standard.** K–12 focused, not directly applicable to higher ed. Worth knowing because dual-enrollment programs and statewide data efforts cross both worlds, but no MVI value ([Ed-Fi Alliance](https://www.ed-fi.org/ed-fi-data-standard/)).

**IPEDS.** Federal Integrated Postsecondary Education Data System reporting — not an integration in the SIS sense. Useful only as a market-sizing data source.

**PESC (Postsecondary Electronic Standards Council).** XML schemas for transcripts, course catalogs, applications. Degree Works' `RequestDA` payload is PESC-conformant. Useful background, not a primary integration target.

---

## 6. Data freshness — push vs. pull

Banner section data is volatile during registration windows. Caps change as students drop and add. New sections get opened. Instructors get reassigned. CRNs occasionally get repurposed. During the 48-hour registration storm at most institutions, section state changes by the **minute**, not the hour.

For a SaaS that caches catalog data, this is the architecture-defining question.

**Pull (the easy path).** Nightly batch of `courses` + `sections` + `instructors` from Ethos, full-refresh into a tenant-scoped database. Works fine for plan-ahead use cases (the student is exploring next semester). Fails badly at registration time, when "FIN 310 has 3 seats left" displayed in BryantPathfinder might be -2 in Banner by the time the student clicks register.

**Pull more often.** Hourly or every-15-minutes pull of `sections` only (catalog rarely changes mid-term, but section seat counts do). Reasonable middle ground. Ethos can comfortably handle this from one tenant.

**Push (the right path long-term).** Ellucian Ethos supports change-event subscriptions — a webhook stream where Banner publishes a message every time a section is updated. The integration consumes events from a queue and patches its local cache. This is what production-grade ISVs (Coursedog, Stellic) use. Engineering complexity is meaningfully higher (idempotent consumer, replay handling, event-ordering guarantees, dead-letter queue), but it's the only architecture that supports "live seats remaining" during registration.

**Recommendation for MVI.** Hourly pull of sections + nightly pull of courses + per-request pull of student audit. Defer event-stream subscription until the third paid customer.

---

## 7. Minimum Viable Integration (MVI)

What's the *smallest* integration scope that wins a paid pilot at a Banner-using mid-sized university (~12,000 FTE)?

| Component | Read/write | Effort (person-weeks) | Notes |
|---|---|---|---|
| Banner Ethos: nightly catalog pull (`courses`, `sections`, `academic-periods`, `instructors`) | Read | 3–4 | Includes tenant config, retry/backoff, schema mapping into our `Section` model, error monitoring. Assumes Ethos is already provisioned. |
| Banner Ethos: hourly section pull during registration window | Read | 1 | Adds incremental update logic on top of nightly job. |
| Degree Works: per-student audit on demand via REST `getAudit` | Read | 4–5 | Includes service-account provisioning, structured XML parser, mapping into our `DegreeAudit` model, fallback to screenshot if DW endpoint unreachable. |
| SSO: SAML 2.0 single-tenant against campus Shibboleth IdP | Auth | 2 | Off-the-shelf library (`python3-saml`); SP metadata exchanged manually with campus IAM team. |
| Multi-tenancy primitives: per-institution config, data isolation, admin console for tenant onboarding | Infra | 4–6 | Required even for a "pilot." Database schema with `institution_id` discriminator, tenant-aware FastAPI middleware, secrets management per tenant. |
| Write-back: nothing — keep CRN copy/paste | — | 0 | Banner registration write-back is ~6–10 weeks on its own and is not required for a pilot. Defer. |
| HECVAT-Lite + minimal data-handling documentation | Compliance | 2 | Required by most campus security reviews before go-live. |
| **Total MVI** | | **~16–20 person-weeks** | One engineer, ~4–5 calendar months. |

**What the MVI buys.** A pilot-ready integration where Bryant (or peer Banner+Degree-Works campus) can onboard with: Shibboleth SSO, automatic catalog refresh, automatic audit ingestion, no manual screenshot. The student-facing UX is identical to today; the backend just stops guessing.

**What the MVI deliberately excludes.** Auto-registration write-back (next major scope), LMS integration (post-MVI value, not core), event-stream catalog updates (operational nicety, not product), Workday/PeopleSoft/Colleague support (each is its own MVI-equivalent project).

---

## 8. Failure modes

Things that will break integrations in the wild. Each is a real risk that has bitten real ISVs.

1. **Banner version skew.** A campus on Banner 9.20 vs 9.32 may have different Ethos endpoints available, different field semantics, or missing resources entirely. Always probe the tenant's Ethos resource catalog at provisioning time.
2. **Ethos not enabled.** Campus has Banner but not Ethos Integration — common at smaller institutions. Fallback: direct Banner Self-Service scrape (fragile, against TOS at some sites, but how BryantPathfinder works today) or campus-provided ODS/EDW read replica.
3. **Degree Works on a different release cadence than Banner.** DW gets upgraded semi-independently; the audit XML schema can change between releases, breaking parsers. Treat the DW response as semi-versioned and monitor schema drift.
4. **Service-account expiration.** Campus IT rotates service-account passwords on a 90/180/365-day cycle. Build expiration alerting before the third week of a pilot.
5. **Shibboleth attribute release.** A campus IdP must explicitly release attributes (eduPersonPrincipalName, eduPersonAffiliation, mail) to your SP. Default policies often release nothing useful. Document the attribute requirements clearly during onboarding.
6. **InCommon metadata churn.** Federation metadata refreshes can change SP/IdP entityIDs or certificates. Use a metadata aggregator that auto-refreshes (Shibboleth SP, mod_shib, or a SaaS-side equivalent).
7. **Test environments.** Many Banner sites only have `BANTEST` and `BANPROD`; there is no isolated dev tenant for an ISV to play in, so first-pilot integration is necessarily against production data with manufactured test users. Plan for read-only access first.
8. **Campus VPN / network gating.** DW REST endpoints are often only reachable from inside the campus network. Production SaaS needs either a campus-side reverse proxy (campus IT has to stand up) or a VPN tunnel agreement, which is its own compliance review.
9. **PII spillage.** Audit data contains student name, ID, GPA, and program. Sending this to Anthropic for parsing without a DPA in place is a FERPA red flag. The MVI must include a Business Associate / DPA path with Anthropic before any non-Bryant audit data is parsed by Claude.
10. **Stellic/EAB lock-in.** A campus with Stellic, EAB Navigate, or Ellucian Student Planning already deployed will not buy a redundant scheduler unless BryantPathfinder integrates with the incumbent rather than replacing it. Map the incumbent landscape before each sales conversation.
11. **API rate limits.** Ethos rate-limits per tenant (specifics not publicly documented, but in the hundreds of requests/minute range for typical tiers). A naive implementation that pulls every section individually rather than paging through `?limit=500` will hit limits within an hour.
12. **OneRoster mismatch.** OneRoster is K-12-shaped; mapping higher-ed terms ("academic period" with sub-terms, multiple meeting patterns per section, lab-vs-lecture sub-sections) into OneRoster's flatter model loses fidelity. Don't try to use OneRoster as a primary higher-ed SIS read path.

---

## 9. Bottom line

The integration moat in higher-ed SIS is not technical sophistication — Ethos REST + SAML is a known pattern. The moat is **the long tail of variation between deployments** (Banner 9.x release, Ethos provisioning state, DW release, Shibboleth attribute release, campus network topology) and **vendor-program friction** (Anthology requires pre-approval, Ellucian Partner Network is a paid tier, Workday gates everything tightly).

For BryantPathfinder, the cheapest credible commercialization path is:

1. **Stay Banner-only for the first year.** It's 24% market share and the demo home turf.
2. **Replace screenshot ingestion with Degree Works REST first**, before anything else. This is the single biggest reliability and demo-believability upgrade available.
3. **Add Ethos catalog pull second**, replacing the static `sections.json`.
4. **Use a managed SSO provider for SAML on pilot 1**, then move to native + InCommon when revenue covers the engineering quarter.
5. **Defer LMS, defer write-back, defer Workday/PeopleSoft/Colleague.** Each is a 1+ quarter project that doesn't change the demo and doesn't unlock the next pilot.

Total path-to-MVI engineering: ~16–20 person-weeks, gated by the campus-IT relationship velocity rather than the code itself. The code is the easy part.

---

## Sources

- [Ellucian: Banner / Colleague SaaS press release](https://www.prnewswire.com/news-releases/ellucian-leads-higher-educations-digital-transformation-with-banner-and-colleague-saas-302110130.html)
- [ListEdTech — North American SIS HigherEd Market Share, January 2025](https://www.listedtech.com/blog/north-american-sis-highered-market-share-january-2025-update/)
- [Ellucian — recognized as market leader for higher education student system](https://www.ellucian.com/news/ellucian-recognized-market-leader-higher-education-student-system)
- [Ellucian Ethos: integration-bruno (auth + JWT)](https://github.com/ellucian-developer/integration-bruno)
- [Ellucian Ethos: integration-postman](https://github.com/ellucian-developer/integration-postman)
- [Ellucian Ethos: integration-sdk-csharp](https://github.com/ellucian-developer/integration-sdk-csharp)
- [Ellucian Ethos: ellucianEthos postman collection](https://github.com/ellucianEthos/postman-ethos-integration)
- [Ad Astra — Ethos Data Access Models and Endpoints](https://help.adastra.live/hc/en-us/articles/15295562799252-Ethos-Data-Access-Models-and-Endpoints)
- [Tray.ai — Ellucian Ethos connector](https://docs.tray.ai/connectors/service/ellucian-ethos)
- [Systech — Securing Banner APIs with mTLS, OAuth & Least Privilege](https://systechus.com/secure-banner-apis-mtls-oauth-least-privilege/)
- [Ellucian Solutions — Degree Works](https://www.ellucian.com/solutions/ellucian-degree-works)
- [USU ServiceNow — DwApiGuide DW4.1.3](https://usu.service-now.com/sys_attachment.do?sys_id=c14216c7b80ca100496e01a3fbc299e6)
- [Coursedog — Ellucian DegreeWorks Integration](https://coursedog.freshdesk.com/support/solutions/articles/48001210598-ellucian-degreeworks-integration)
- [Coursedog — Colleague Ethos Integration & Extension Setup](https://coursedog.freshdesk.com/support/solutions/articles/48001252098-colleague-ethos-integration-extension-setup)
- [Yuba CCD — Setting Up Colleague Web API](https://yc.yccd.edu/wp-content/uploads/2018/03/Setting-Up-Colleague-Web-API.pdf)
- [Workday Community — API documentation portal](https://community.workday.com/api)
- [Workday — REST Services Directory](https://community.workday.com/sites/default/files/file-hosting/restapi/index.html)
- [Reco — Workday REST API integration & security](https://www.reco.ai/hub/workday-rest-api-integration-security)
- [Oracle — Understanding REST API Endpoints for PeopleSoft](https://docs.oracle.com/cd/F92336_01/fscm92pbr50/eng/fscm/eccf/UnderstandingRestApiEndpointsForPeoplesoft.html)
- [Oracle — PeopleSoft Integration Broker](https://docs.oracle.com/cd/E25688_01/pt852pbr0/eng/psbooks/tibr/htm/tibr12.htm)
- [Coursedog — Oracle PeopleSoft Campus Solutions integration](https://coursedog.freshdesk.com/support/solutions/articles/48001049005-oracle-peoplesoft-campus-solutions-integration)
- [Jenzabar — Unity Platform product page](https://jenzabar.com/product/unity-platform)
- [Jenzabar — public API for Campus Marketplace announcement (BusinessWire)](https://www.businesswire.com/news/home/20240508903173/en/Jenzabar-Unveils-Public-API-for-Campus-Marketplace-Designed-to-Enhance-Data-Analyses-Streamline-Operations-and-Improve-Reporting)
- [Jenzabar — blog on public API](https://jenzabar.com/blog/jenzabar-unveils-public-api-for-campus-marketplace)
- [Anthology — student-api-samples on GitHub](https://github.com/anthology-inc/student-api-samples)
- [Anthology — developer docs index](https://blackboard.github.io/)
- [Anthology — Student REST API service catalog](https://blackboard.github.io/rest-apis/student/servicecatalog/about-student-service-catalog)
- [Anthology — First Steps with Student REST API](https://blackboard.github.io/rest-apis/student/getting-started/student-first-steps)
- [Anthology — API documentation index (campuslabs)](https://docs.api.campuslabs.com/)
- [Stellic — homepage](https://www.stellic.com)
- [Stellic — Progress (degree planner / registration)](https://www.stellic.com/progress)
- [Stellic — Under the Hood (architecture)](https://www.stellic.com/resources/under-the-hood)
- [Carnegie Mellon — Stellic implementation](https://www.cmu.edu/es/stellic/index.html)
- [Cornell IT — Degree Audit (Stellic)](https://it.cornell.edu/degreeaudit)
- [Indiana University — Stellic implementation](https://studentsuccess.iu.edu/stellic/index.html)
- [Instructure — Developer Keys (Canvas LTI 1.3)](https://developerdocs.instructure.com/services/canvas/resources/developer_keys)
- [Instructure — External Tools introduction](https://developerdocs.instructure.com/services/canvas/external-tools/lti/file.tools_intro)
- [Instructure — Manually configuring LTI Advantage tools](https://www.canvas.instructure.com/doc/api/file.lti_dev_key_config.html)
- [Instructure — LTI launch overview](https://documentation.instructure.com/doc/api/file.lti_launch_overview.html)
- [D2L Brightspace — Valence reference](https://docs.valence.desire2learn.com/reference.html)
- [D2L Brightspace — Valence about](https://docs.valence.desire2learn.com/about.html)
- [Edlink — D2L Brightspace API overview](https://ed.link/community/what-can-i-do-with-the-brightspace-api/)
- [Edlink — Brightspace SSO implementation](https://ed.link/community/how-to-implement-sso-with-brightspace-d2l/)
- [InCommon — Shibboleth software](https://incommon.org/software/shibboleth/)
- [Columbia CUIT — Shibboleth/SAML integration](https://www.cuit.columbia.edu/shibboleth)
- [Harvard IAM — SAML/Shibboleth integration how-to](https://www.iam.harvard.edu/resources/saml-shibboleth-integration)
- [Microsoft Entra — multilateral federation with Shibboleth as SAML proxy](https://learn.microsoft.com/en-us/entra/architecture/multilateral-federation-solution-two)
- [Stack Overflow blog — The many problems with implementing SSO](https://stackoverflow.blog/2022/09/12/the-many-problems-with-implementing-single-sign-on/)
- [Scalekit — SAML implementation in B2B SaaS step-by-step](https://www.scalekit.com/blog/saml-implementation-in-b2b-saas-apps-a-step-by-step-guide-for-developers)
- [Frontegg — implementing SAML in enterprise SaaS](https://frontegg.com/blog/implementing-saml-authentication-in-enterprise-saas-applications)
- [EnterpriseReady — Single Sign-On guide](https://www.enterpriseready.io/features/single-sign-on/)
- [1EdTech — OneRoster v1.1 final specification](https://www.imsglobal.org/oneroster-v11-final-specification)
- [1EdTech — OneRoster v1.1 introduction](https://www.imsglobal.org/oneroster-11-introduction)
- [1EdTech — OneRoster v1.0 CSV tables](https://www.imsglobal.org/lis/imsOneRosterv1p0/imsOneRosterCSV-v1p0.html)
- [1EdTech — OneRoster + LTI Advantage](https://www.imsglobal.org/about/k12/oneroster-and-lti-advantage)
- [Ed-Fi Alliance — What is the Ed-Fi Data Standard?](https://www.ed-fi.org/ed-fi-data-standard/)
- [Ed-Fi docs — data standards reference](https://docs.ed-fi.org/reference/data-exchange/data-standard/)
