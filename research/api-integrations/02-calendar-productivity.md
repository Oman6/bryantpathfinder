# 02 — Calendar & Productivity API Integrations

> Research subagent **A2**. Scope: APIs that BryantPathfinder could push generated schedules INTO so the student never has to download an `.ics` file. The current flow ends with an RFC 5545 `.ics` download (Google / Apple / Outlook). Goal: skip the download step, with re-sync that doesn't duplicate, real-time updates when a section is swapped, and a defensible posture on FERPA.

---

## TL;DR — Top three picks

1. **Microsoft Graph / Outlook Calendar API** — Bryant runs Microsoft 365 / Exchange as the primary collaboration platform per Bryant IS ([is.bryant.edu](https://is.bryant.edu/services/communication-and-collaboration/collaboration/office-365)). Every `@bryant.edu` mailbox already has an Outlook calendar. This is the highest-leverage integration for the Bryant pilot. Unlocks a "Push to my Bryant Outlook" one-click button. Native idempotency via `transactionId`. Real-time PATCH on swap.
2. **Google Calendar API** — Bryant also provisions Google Workspace alongside Microsoft for students. Plus, transfer students, summer-bridge applicants, and any second-institution rollout will skew Google. Unlocks "Push to Google Calendar" with the largest install base for non-Bryant pilots. Idempotency requires a client-managed `iCalUID` strategy.
3. **Subscribed iCal feed (`webcal://pathfinder.bryant.edu/u/<token>.ics`)** — A signed, per-student feed URL the student adds *once*. The schedule auto-propagates on every solver re-run because the calendar client polls. This is the lowest-engineering-effort, highest-coverage option (works on Apple / iCloud, Outlook desktop, Google, Fantastical, Notion, Todoist via Calendar feeds, even a shared family calendar). The cost is **refresh latency**: Google polls every 12–24 hours, Outlook 3–24 hours, with no publisher-side push ([Lauren Stephen, *Subscribe to an iCalendar feed in Google Calendar*](https://lauren-c-stephen.medium.com/subscribe-to-an-icalendar-feed-in-google-calendar-and-solve-update-issues-79b4e84b3c64), [OneCal](https://www.onecal.io/blog/how-to-get-an-ics-url-for-your-calendar)).

**Recommendation:** Ship the subscribed iCal feed first (1 day of work, no OAuth, no scopes, no security review). Layer Microsoft Graph on top for Bryant ("Push now" button on schedule confirmation, refresh ≤2s). Layer Google Calendar for non-Bryant pilots. The feed becomes the universal fallback for Apple, Notion, Todoist, and anyone who refuses to OAuth.

---

## 1. Google Calendar API

**Docs:** https://developers.google.com/workspace/calendar/api/v3/reference

**Auth flow.** OAuth 2.0 via Google Identity. To create or modify events, the request needs the `https://www.googleapis.com/auth/calendar` scope or the narrower `https://www.googleapis.com/auth/calendar.events` scope. Both are classified by Google as **restricted** scopes ([Google scopes](https://developers.google.com/workspace/calendar/api/auth)). That matters for Pathfinder: any production OAuth client requesting either scope must pass a third-party security assessment (currently Bishop Fox, Leviathan, NCC Group, KirkpatrickPrice are CASA-authorized) — annual fee in the $5K–$15K range, plus a privacy-policy review by Google Trust & Safety. The Bryant Workspace tenant could install Pathfinder as a domain-wide internal app to bypass external verification, but only for `@bryant.edu` accounts.

**Free tier limits.** API usage is free. Quota is 1,000,000 queries/day per project as a default ceiling, with per-minute and per-user buckets ([Google quota guide](https://developers.google.com/workspace/calendar/api/guides/quota), [Elfsight summary](https://elfsight.com/blog/how-to-use-google-calendar-api-v3-cost-limits-examples/)). For Pathfinder's volume (one student × ~5 events × occasional re-runs) this is a non-issue.

**Write capability.** `events.insert` (POST), `events.patch` (partial), `events.update` (PUT), `events.delete`. For multi-day weekly classes, use RFC 5545 `RRULE` strings (`RRULE:FREQ=WEEKLY;BYDAY=MO,WE,TH;UNTIL=20261218T235959Z`) — Google natively expands recurrences.

**Idempotency.** This is the gotcha. `events.insert` is **not idempotent**: a retried POST creates a duplicate event ([Hex Docs / google_api_calendar](https://hexdocs.pm/google_api_calendar/GoogleApi.Calendar.V3.Model.Event.html)). The right pattern for Pathfinder is:
1. Generate a deterministic `iCalUID` per Pathfinder section, e.g. `pathfinder-{audit_hash}-{crn}@bryantpathfinder.com`.
2. On first push, call `events.import` with that `iCalUID` (the `import` method *requires* `iCalUID` and is the recommended path for cross-system events).
3. On re-sync, call `events.list` with `iCalUID=<...>` to find the existing event id, then `events.patch`/`update` if changed, or insert if missing. Pure key-based reconciliation.

**FERPA / data residency.** A schedule written into a student's *personal* Google Calendar carries the student's enrollment information (course codes, room numbers, instructor names) — that's PII from an education record under FERPA's broad definition. The school-official exception only covers data flowing to vendors *under direct institutional control*; once the data lands in a personally-owned Google account, it's the student's own disclosure of their own record (FERPA permits this under written consent / the eligible-student waiver). For the Bryant Workspace path, the data stays inside Bryant's tenant — cleaner. Sources: [studentprivacy.ed.gov vendor FAQ](https://studentprivacy.ed.gov/sites/default/files/resource_document/file/Vendor%20FAQ.pdf).

**Integration effort.** ~2 days. Pathfinder's backend already speaks Pydantic-typed JSON; the Google Python SDK is a few hundred lines.

---

## 2. Microsoft Graph / Outlook Calendar API

**Docs:** https://learn.microsoft.com/en-us/graph/api/resources/calendar-overview

**Bryant context.** Bryant Information Services lists Outlook + Exchange as the primary email/calendar service for all faculty, staff, and students ([is.bryant.edu](https://is.bryant.edu/services/communication-and-collaboration/collaboration/office-365)). Every `@bryant.edu` student already has a working Outlook calendar provisioned. **This is the single highest-leverage integration for the Bryant pilot.**

**Auth flow.** OAuth 2.0 via Microsoft Entra ID (formerly Azure AD). Pathfinder registers as a multi-tenant application in the Microsoft identity platform, requesting `Calendars.ReadWrite` (delegated). For application-level access (server pushes to multiple students without each student consenting), use `Calendars.ReadWrite` (application) — but that requires the tenant admin to grant consent for the whole organization ([Microsoft Graph permissions](https://learn.microsoft.com/en-us/graph/permissions-reference), [graphpermissions.merill.net/permission/Calendars.ReadWrite](https://graphpermissions.merill.net/permission/Calendars.ReadWrite)). Tenant admins can further restrict the app to a subset of mailboxes via Application Access Policy.

**Free tier limits.** No per-call cost. Throttling is per-app-per-mailbox (10,000 requests / 10 min default) and well above any Pathfinder usage. The bigger constraint is consent screen friction: students see "Pathfinder wants to read and write your calendar." That copy survives because Microsoft does not let third parties customize the consent dialog.

**Write capability.** `POST /me/events` to create, `PATCH /me/events/{id}` to update, `DELETE /me/events/{id}` to remove. Recurrence is supported via the `recurrence` object on the event payload ([Microsoft Create Event](https://learn.microsoft.com/en-us/graph/api/calendar-post-events?view=graph-rest-1.0)).

**Idempotency.** Microsoft Graph supports a first-class **`transactionId`** field on event creation ([same doc](https://learn.microsoft.com/en-us/graph/api/calendar-post-events?view=graph-rest-1.0)). Pathfinder sets `transactionId` to a deterministic string like `pf-{audit_hash}-{crn}-{semester}`; Microsoft guarantees that retries with the same `transactionId` won't create duplicates. **Microsoft Graph has the cleanest idempotency story of any calendar API in this report.** Caveat: `transactionId` is set-once at creation and cannot be modified on PATCH ([Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/1530652/microsoft-graph-api-subscriptions-missing-events-d)). To re-sync, Pathfinder still needs to store the Graph event id in its backend or re-list events filtered by `transactionId` (filter is supported on the `events` collection).

**FERPA.** Bryant-issued mailboxes live inside Bryant's M365 tenant. Microsoft signs an academic Data Processing Addendum that covers FERPA. From a regulatory standpoint, pushing into Bryant Outlook is *the* lowest-risk choice — the data never leaves Bryant's contractually-controlled tenant.

**Integration effort.** ~2 days. MSAL Python is mature; the Pathfinder OAuth callback can reuse the same redirect URI as Google.

---

## 3. Apple Calendar / iCloud (CalDAV)

**Docs:** https://developer.apple.com/documentation/devicemanagement/caldav

iCloud does not expose OAuth. The only programmatic path is **CalDAV with Basic Auth + an app-specific password** the user generates in their Apple ID settings ([OneCal](https://www.onecal.io/blog/how-to-integrate-icloud-calendar-api-into-your-app), [Aurinko](https://www.aurinko.io/blog/caldav-apple-calendar-integration/)). For consumer apps this is a non-starter — students will not generate an app-specific password to add 5 weekly classes.

Additional limitations:
- No webhooks / no push notifications. Pathfinder cannot subscribe to changes ([OneCal, ibid.](https://www.onecal.io/blog/how-to-integrate-icloud-calendar-api-into-your-app)).
- No PATCH semantics: any update is a full PUT replacement.
- Apple's CalDAV implementation has documented gotchas — not every standard method behaves per spec.

**Recommendation:** **Do not build an iCloud OAuth-style integration.** Instead, give Apple users the subscribed iCal feed URL. iOS, macOS, watchOS Calendar all natively support `webcal://` subscriptions — the student opens the URL once, taps "Subscribe," and the schedule is on their lock screen. This is materially better UX than CalDAV would ever be.

---

## 4. CalDAV (generic standard)

CalDAV (RFC 4791) is supported by Fastmail, mailbox.org, Nextcloud, ownCloud, Posteo, Zoho, and (with caveats) iCloud. There is no central OAuth. Each provider hands the user a server URL + username + password.

For Pathfinder, supporting CalDAV directly is overscope — the addressable userbase among undergraduates is near zero. The subscribed iCal feed covers every CalDAV client transparently, since CalDAV servers can subscribe to external `webcal` URLs.

---

## 5. Notion API

**Docs:** https://developers.notion.com/

**Auth.** OAuth 2.0 (public integrations) or internal integration token. Each user must explicitly add the Pathfinder integration to a parent page or database — Notion's permission model is page-scoped, not workspace-scoped.

**Free tier.** API access is free across all Notion plan tiers; rate limit is **3 requests / second average** with HTTP 429 on overage ([Notion request limits](https://developers.notion.com/reference/request-limits)). Free workspaces with multiple members hit a 1,000-block ceiling that students may bump into for a busy semester.

**Write capability.** `POST /v1/pages` creates a page (a row, in database terms). `PATCH /v1/pages/{id}` updates properties.

**Use case for Pathfinder.** Schedule-as-database: create a Notion database "Spring 2026 Schedule" with columns (Course, CRN, Instructor, Days, Time, Room, Workload est., Professor rating). One row per section. This is genuinely useful for the Notion-native student cohort (a real, growing slice). It is **not** a calendar replacement — Notion's calendar view is weak and doesn't surface on a phone lock screen.

**Idempotency.** Pathfinder must store Notion page ids in its backend keyed by `(audit_hash, crn)` to update on re-sync. There is no server-side dedup primitive.

**FERPA.** Same posture as Google Calendar — data lands in the student's personal workspace; consent is the student's.

**Effort.** ~1 day. Lower priority than Google/Microsoft for the demo, higher leverage as a "wow" feature for a sophomore audience.

---

## 6. Todoist API

**Docs:** https://developer.todoist.com/rest/v2/

**Auth.** OAuth 2.0 (public apps) or personal API token. Bearer tokens.

**Free tier.** API itself is free. **Rate limit: 1,000 requests / 15 min per token** ([Todoist developer docs](https://developer.todoist.com/rest/v2/)).

**Write capability.** `POST /tasks` to create a task with `due_string`, `due_datetime`, `project_id`. Pathfinder can create one project "Bryant Spring 2026" with one task per assignment / exam — but Pathfinder doesn't currently know assignments (only meeting times).

**Use case.** Limited — Pathfinder is a *schedule* tool, and Todoist is a *task* tool. A real integration would require a syllabus parser feeding due dates into Todoist. That's a future feature, not a launch feature. Skip for v1.

**Idempotency.** No server-side dedup; client must track task ids.

---

## 7. Reclaim.ai

**Docs:** https://help.reclaim.ai/, [API reference](https://www.apirefs.com/apps/reclaim-ai)

**Auth.** OAuth 2.0. **Rate limit: 100 req/min on free plan.**

**Use case.** Reclaim auto-blocks study/focus time *around* fixed events. The pitch: Pathfinder pushes the 5 class blocks into Google Calendar; Reclaim then auto-schedules study time, gym, and group projects in the gaps. The student never manually time-blocks again. This is a genuine productivity multiplier and a credible "premium tier" upsell for Pathfinder.

**Caveat.** The Reclaim public API is partner-gated. Make/Zapier integrations exist; direct API access requires contacting Reclaim. Confirm with their BD team before quoting the integration to a customer.

**Priority.** v2 feature, premium positioning. Not for the Bryant pilot.

---

## 8. Motion (usemotion.com)

**Docs:** https://docs.usemotion.com/

**Auth.** API key (header `X-API-Key`), generated under Settings. **No OAuth flow** — meaning each student would have to paste an API key into Pathfinder, which is dreadful UX.

**Use case.** Same shape as Reclaim — auto-prioritize coursework around classes. Motion's task scheduler is more aggressive than Reclaim's.

**Priority.** Skip for v1. Revisit only if Motion ships OAuth.

---

## 9. Cal.com / Calendly

**Docs:** https://cal.com/docs/api-reference/v2/introduction

**Auth.** Cal.com offers OAuth 2.0 with a managed-user model where Pathfinder can provision per-student bookable resources ([Cal.com OAuth](https://cal.com/docs/api-reference/v2/introduction)). Calendly's API is similar but more locked down at the free tier.

**Use case for Pathfinder.** Outbound, not inbound. If Pathfinder books **advisor / professor office-hours meetings** on the student's behalf during empty class blocks, Cal.com is the pipe. Bryant advising could publish Cal.com event types; Pathfinder reads professor RMP data + course load and suggests "Your Tuesday afternoon is free — book office hours with your CFA advisor." This is a credible feature for the multi-semester planner.

**Priority.** v2 feature. Strong story for the institutional sale (advising-office adoption).

---

## 10. Linear

**Docs:** https://linear.app/developers

**Auth.** OAuth 2.0. Workspace-level OAuth apps get up to **200,000 complexity points/hr per user** ([Linear rate limiting](https://linear.app/developers/rate-limiting)).

**Use case.** Long shot. CS-major students who run their personal life out of Linear could ingest weekly classes as recurring Linear issues. Niche. Skip for v1.

---

## 11. Apple Wallet pass API (PassKit)

**Docs:** https://developer.apple.com/documentation/walletpasses/

**Requirements.** Apple Developer Program enrollment ($99/yr) + a Pass Type ID Certificate signing each `.pkpass` ([Apple Wallet Get Started](https://developer.apple.com/wallet/get-started/), [PassKit](https://developer.apple.com/documentation/passkit)). A pass is a signed ZIP containing JSON + images.

**Use case for Pathfinder.** Generic-style pass with the student's weekly schedule on the back, current-class notification on the front. The pass can have a **web service URL** for push updates — Pathfinder POSTs to Apple's push endpoint when a section is swapped, and the pass auto-refreshes on the lock screen. **This is genuinely novel for a student-scheduling product.** The "Schedule on your lock screen" feature is a marketing moment.

**Effort.** ~3–4 days (Pass Type ID, certificate, signing pipeline, web service for push updates).

**Priority.** v2 differentiator. Excellent demo screenshot for the website.

---

## 12. Native iOS Shortcuts / App Intents

**Docs:** https://developer.apple.com/documentation/sirikit, [App Intents](https://developer.apple.com/documentation/appintents) (iOS 16+)

**Use case.** Pathfinder has no native iOS app today (it's a Next.js web app). However, the **Shortcuts app's "Add New Event" share-sheet action** ([Apple Support](https://support.apple.com/guide/shortcuts/share-actions-apdaf74d75a5/ios)) lets a user one-tap an `.ics` file into Calendar. The current `.ics` download path already lights this up implicitly — a student who taps the downloaded `.ics` on iOS gets a "Add to Calendar" sheet with no extra build work from Pathfinder.

**Native App Intents** (iOS 16+) would let Pathfinder declare an intent like "Add my schedule to Calendar" that surfaces in Spotlight, Siri, and Shortcuts — but that requires a native iOS app. Out of scope until Pathfinder has an iOS app.

**Priority.** Ship the iOS app later; in the meantime the share-sheet works for free off the existing `.ics`.

---

## Push (OAuth-write) vs Pull (subscribed iCal feed)

This is the architectural call. Both are useful; they answer different questions.

| Dimension | OAuth write (Google/Graph) | Subscribed iCal feed |
|---|---|---|
| Engineering effort | 2 days per provider | < 1 day total |
| Update latency on swap | Instant via PATCH | 3–24h Google, 3–24h Outlook ([source](https://lauren-c-stephen.medium.com/subscribe-to-an-icalendar-feed-in-google-calendar-and-solve-update-issues-79b4e84b3c64)) |
| User consent friction | OAuth screen, scope grant, possible enterprise admin block | Single tap on `webcal://` link |
| Coverage | Provider-specific | Anything that supports RFC 5545 (universal) |
| Idempotency | Client must implement (Google) or `transactionId` (Graph) | Server-trivial — feed always reflects current state |
| FERPA exposure | Data crosses to a third-party tenant under user consent | Same exposure (the URL is the data) but easier to revoke (rotate token) |
| Real-time on swap | Yes (PATCH within seconds) | No (poll cycle) |
| Works offline / on Apple Watch | Yes (after initial sync) | Yes (after initial poll) |
| Failure mode | OAuth token expiry, scope changes, app verification | Token leak — anyone with URL sees schedule |

**Verdict.** The subscribed iCal feed is the right *first* surface because it's universal and zero-friction. Pathfinder already produces RFC 5545 — exposing it as `GET /api/feed/<token>.ics` with a per-student rotating bearer-in-URL token is a 4-hour ticket. The push-via-OAuth path is the right *second* surface specifically because the feed's update latency (up to 24h) is unacceptable when a student swaps a section the night before registration. So:

> **Pathfinder should ship both, with the iCal feed as the default ("Subscribe in Calendar" pill button) and OAuth-write as the upsell ("Push instantly to Outlook")** — gated behind the Bryant SSO when ready.

---

## Idempotency cheat sheet

| API | Mechanism | Pathfinder pattern |
|---|---|---|
| Google Calendar | `iCalUID` (set at insert/import; query via `events.list?iCalUID=`) | Deterministic UID `pf-{audit_hash}-{crn}@bryantpathfinder.com` |
| Microsoft Graph | `transactionId` (set-once at create) | Same deterministic string in `transactionId` |
| Notion | None (no native dedup) | Backend store `(audit_hash, crn) → page_id` |
| Todoist | None | Backend store task ids |
| iCloud (CalDAV) | `UID` in iCalendar payload | Deterministic UID |
| Subscribed iCal feed | N/A — feed is the source of truth | Just regenerate |

For Pathfinder, the **`audit_hash + crn + semester`** triple is the right idempotency key everywhere. It survives section swaps (different CRN → different event) and audit re-parses (different hash → migrate, don't update).

---

## Real-time updates on section swap

The schedules page lets a student pin sections and swap individuals. Calendar must reflect this immediately.

- **Google:** `events.patch(eventId, body={start, end, recurrence})` — instant.
- **Graph:** `PATCH /me/events/{id}` — instant. PATCH supports partial bodies.
- **Notion:** `PATCH /v1/pages/{id}` — instant.
- **iCal feed:** server-side trivial (regenerate on next solver run). Client refresh delay is the cost.

Pathfinder's existing solver finishes in ~300ms. Adding a calendar PATCH on swap costs another ~200ms round-trip. The user-perceived "swap and see it on your calendar" loop is < 1 second on Google or Graph — comfortably below the threshold of feeling laggy.

---

## Recommended build order

1. **Subscribed iCal feed** (1 day). Per-student signed URL. Universal coverage. Zero OAuth.
2. **Microsoft Graph** OAuth-write (2 days). The Bryant-pilot money-shot. `transactionId`-based idempotency, instant PATCH on swap.
3. **Google Calendar** OAuth-write (2 days). Required for any non-Bryant pilot. `iCalUID`-based idempotency.
4. **Notion** database push (1 day). Marketing differentiator with the Notion-native cohort.
5. **Apple Wallet pass** (3–4 days, v2). Lock-screen schedule. Demo gold.
6. **Reclaim.ai** (v2 premium tier). Auto-blocks study time around classes.
7. **Cal.com** (v2 institutional). Books advisor office hours in empty class blocks.

Skip: iCloud CalDAV, Motion (no OAuth), Todoist (no syllabus data yet), Linear (niche), generic CalDAV (covered by feed).

---

## Open questions for the synthesis agent

- **Bryant Microsoft tenant ID.** Confirm with Bryant IT whether they will grant tenant-admin consent for a Pathfinder Entra ID app, or whether each student must individually OAuth. Tenant-admin consent removes per-student friction but requires a security review (probably HECVAT-Lite).
- **Workspace audit.** Bryant says Google Workspace is also available. If this is a real Workspace for Education tenant, push-to-Google is also Bryant-tenant-internal and FERPA-clean. If it's just personal Gmail accounts that students happen to have, push-to-Google is a personal-disclosure path.
- **Per-student token rotation cadence** for the iCal feed. Suggest 90 days with one-click rotate from the Pathfinder dashboard.

---

## Sources

- [Google Calendar API auth scopes](https://developers.google.com/workspace/calendar/api/auth)
- [Google Calendar API quota](https://developers.google.com/workspace/calendar/api/guides/quota)
- [Google Calendar API events reference](https://developers.google.com/workspace/calendar/api/v3/reference/events)
- [GoogleApi.Calendar.V3.Model.Event (iCalUID semantics)](https://hexdocs.pm/google_api_calendar/GoogleApi.Calendar.V3.Model.Event.html)
- [Microsoft Graph create event](https://learn.microsoft.com/en-us/graph/api/calendar-post-events?view=graph-rest-1.0)
- [Microsoft Graph update event (PATCH)](https://learn.microsoft.com/en-us/graph/api/event-update?view=graph-rest-1.0)
- [Microsoft Graph permissions reference](https://learn.microsoft.com/en-us/graph/permissions-reference)
- [Calendars.ReadWrite scope](https://graphpermissions.merill.net/permission/Calendars.ReadWrite)
- [Bryant University Office 365](https://is.bryant.edu/services/communication-and-collaboration/collaboration/office-365)
- [Bryant University Information Services](https://is.bryant.edu/services/all-services)
- [Bryant Account / IAM](https://is.bryant.edu/services/security/identity-and-access-management/bryant-account)
- [iCloud Calendar API integration limitations (OneCal)](https://www.onecal.io/blog/how-to-integrate-icloud-calendar-api-into-your-app)
- [Aurinko CalDAV / Apple Calendar guide](https://www.aurinko.io/blog/caldav-apple-calendar-integration/)
- [Apple CalDAV device management documentation](https://developer.apple.com/documentation/devicemanagement/caldav)
- [Notion API request limits](https://developers.notion.com/reference/request-limits)
- [Notion pricing 2026](https://www.notion.com/pricing)
- [Todoist REST API v2](https://developer.todoist.com/rest/v2/)
- [Reclaim.ai integrations](https://reclaim.ai/integrations)
- [Reclaim.ai API reference (apirefs.com)](https://www.apirefs.com/apps/reclaim-ai)
- [Motion API docs](https://docs.usemotion.com/)
- [Motion API getting started](https://docs.usemotion.com/cookbooks/getting-started/)
- [Cal.com API v2 introduction](https://cal.com/docs/api-reference/v2/introduction)
- [Linear rate limiting](https://linear.app/developers/rate-limiting)
- [Linear developers](https://linear.app/developers)
- [Apple PassKit documentation](https://developer.apple.com/documentation/passkit)
- [Apple Wallet developer overview](https://developer.apple.com/wallet/)
- [Apple Wallet getting started](https://developer.apple.com/wallet/get-started/)
- [Apple App Intents framework](https://developer.apple.com/documentation/appintents)
- [Apple SiriKit / Siri Shortcuts](https://developer.apple.com/documentation/sirikit)
- [Apple Shortcuts share actions](https://support.apple.com/guide/shortcuts/share-actions-apdaf74d75a5/ios)
- [Subscribe to iCalendar feed in Google Calendar (Lauren Stephen)](https://lauren-c-stephen.medium.com/subscribe-to-an-icalendar-feed-in-google-calendar-and-solve-update-issues-79b4e84b3c64)
- [How to get an .ics URL (OneCal)](https://www.onecal.io/blog/how-to-get-an-ics-url-for-your-calendar)
- [Microsoft Graph subscriptions / idempotency Q&A](https://learn.microsoft.com/en-us/answers/questions/1530652/microsoft-graph-api-subscriptions-missing-events-d)
- [FERPA vendor FAQ (studentprivacy.ed.gov)](https://studentprivacy.ed.gov/sites/default/files/resource_document/file/Vendor%20FAQ.pdf)
- [FERPA exceptions (Public Interest Privacy Center)](https://publicinterestprivacy.org/ferpa-exceptions/)
