# 07 — Bryant + Campus-Life Data Feeds

> Subagent **A7** — research swarm output. Question: which Bryant-specific data feeds and campus-life APIs could turn BryantPathfinder from a once-per-semester scheduling tool into a daily-open student app?
>
> Method: probe `bryant.edu` and adjacent vendor domains for each surface (calendar, athletics, dining, library, clubs, transit, parking, residence, health, bookstore, tutoring, alerts, social), identify the underlying SaaS platform, and look up that platform's public API or feed format. Where Bryant exposes nothing directly, fall back to (a) the vendor's documented API, or (b) a scraping plan with effort estimate.

Today: **2026-04-25**. The current product is local-only, single-fixture, Fall-2026 catalog (291 sections), no database. Every integration below has to live behind the FastAPI backend as a small JSON cache plus a refresh job — no per-student credentials, no PHI, no FERPA-touching data on the daily-app side.

---

## TL;DR — top 3 to integrate first

| Rank | Feed | Why it's the highest leverage | Effort |
|---|---|---|---|
| **1** | **Bryant academic calendar** (drop/add, withdraw, finals, breaks) | Pinned to every schedule. Powers the highest-value notification ("drop deadline is Oct 25") and is impossible to over-claim. Bryant publishes only HTML + PDF — we scrape once per semester into static JSON. | **Low** — one Python parser, 16 known dates per year, manual re-run each May/December. |
| **2** | **Krupp Library hours + study room availability** via Springshare LibCal | Daily-relevant. The library publishes hours through a public Google Calendar and runs `bookme.bryant.edu` (LibCal). Both are scrapeable today; LibCal also has a documented REST API if Bryant grants a key. Lets us answer "where can I study between FIN 310 and ECO 114?" | **Low–Medium** — Google Calendar iCal parse is 50 lines; LibCal API is gated by an API key request to the library. |
| **3** | **Bryant Bulldogs athletics schedule** (SIDEARM Sports) | Cultural stickiness, low-stakes, never blocks a student's actual workflow but consistently surfaces "your schedule clashes with the URI hockey game." SIDEARM exposes per-sport iCal subscribe + RSS on every team page. | **Low** — subscribe URLs follow a pattern; one cron a week. |

These three together give Pathfinder a recurring reason to be opened **every weekday** without touching FERPA, PHI, payment, or auth boundaries.

---

## 1. Bryant academic calendar

**Source:** `https://catalog.bryant.edu/undergraduate/academiccalendar/` and the PDF mirror at `https://catalog.bryant.edu/undergraduate/academiccalendar/academiccalendar.pdf`.

**Format:** HTML table + PDF. **No iCal feed.** No RSS. The page links a PDF and that's it.

**Verified key dates (Fall 2025 / Spring 2026, scraped 2026-04-25):**
- Fall 2025: classes begin Sep 2, add ends Sep 8, drop ends Sep 15, last "W" Nov 11, finals Dec 13–19.
- Spring 2026: classes begin Jan 20, add ends Jan 26, drop ends Feb 2, last "W" Apr 7, spring break Mar 16–22, finals May 6–12.

**Auth:** None.
**Pricing:** Free.
**Integration plan:** One-time `parse_academic_calendar.py` script that reads the HTML, emits `data/academic_calendar.json`. Re-run each May (when fall dates publish) and December (spring). 16 dates per year. The whole thing is a fixture in practice.

**Pathfinder features unlocked:**
- "Drop deadline for your fall schedule is **Sep 15** — pinned reminder."
- "Last day to withdraw with W: **Apr 7**."
- "Final for FIN 310 falls in finals window May 6–12. Confirm date in Banner once published."
- "Spring break Mar 16–22 — schedule has no class meetings that week."

**Source URLs:**
- https://catalog.bryant.edu/undergraduate/academiccalendar/
- https://catalog.bryant.edu/graduate/academiccalendars/
- https://info.bryant.edu/registrar

**Honest assessment:** No proper API ever, but the data is small and cold. Static JSON refreshed twice a year is the right answer; do not overbuild.

---

## 2. Bryant athletics — bryantbulldogs.com (SIDEARM Sports)

**Vendor:** **SIDEARM Sports** (acquired by LEARFIELD; powers ~95% of NCAA D-I athletic sites). Bryant relaunched on the new SIDEARM platform in **June 2024** and shipped a SIDEARM-powered mobile app in **Feb 2025**.

**Source:** `https://bryantbulldogs.com/calendar` (composite) + per-sport pages e.g. `https://bryantbulldogs.com/sports/mens-basketball/schedule/2025-26`.

**Format:** SIDEARM team schedule pages expose a calendar widget with **Download (iOS/Win), Import, Google Calendar, RSS Feed, Excel/Text** options on every sport. The composite-calendar page on Bryant's deployment did not expose a top-level subscribe link in the HTML I fetched, but the per-sport schedule pages do (this is documented behavior of the SIDEARM template). The URL pattern is well known: `https://bryantbulldogs.com/calendar.ashx/calendar.ics?sport_id=X` and `schedule.aspx?path=...&template=ical`.

**Auth:** None — public pages.
**Pricing:** Free at the consumption end. SIDEARM does not publish a developer API; the only sanctioned read path is iCal/RSS scrape per sport.
**Effort:** 1 hour to enumerate all 22 varsity sports, store the iCal URL list, and run a daily fetch. Parse with `icalendar` (Python). Cache games as `data/athletics.json`. 

**Pathfinder features unlocked:**
- "Your Tuesday 6pm class ends 30 minutes before tipoff — **Bryant vs URI men's basketball is at 7pm in the Chace Center**."
- Pinned "next home game" widget on the schedules page.
- Conflict warnings when a student selects an evening lab section that overlaps multiple home games.
- Filtering: "show me schedules where I'm free for **football Saturdays**."

**Source URLs:**
- https://bryantbulldogs.com/calendar
- https://bryantbulldogs.com/news/2024/6/6/general-welcome-to-the-new-bryantbulldogs-com.aspx
- https://bryantbulldogs.com/news/2025/2/24/general-bryant-launches-new-mobile-app-powered-by-sidearm-sports.aspx
- https://playbook.sidearmsports.com/quick-hits/new-composite-calendar/

**Honest assessment:** This is the easy win. Athletics produces ~150 home/away events per year across all sports, and the iCal feed is rock-solid because SIDEARM standardized it. Note the on-campus vs travel distinction — only home games are walking-distance from class.

---

## 3. Bryant dining — Sodexo (`bryantdining.sodexomyway.com`)

**Vendor:** **Sodexo**, confirmed via `bryantdining.sodexomyway.com`. Locations: Salmanson Dining Hall ("Salmo"), Corey E. Levine '80 Dining Commons (BELC), Nick's Place, Bulldog Bytes Café, Café a la Cart, Gulski Dining.

**Format:** Sodexo is **migrating off `sodexomyway.com` and the "So Happy" app** to **Nutrislice** as the menu/digital-signage platform. Search results specifically called this transition out: "Sodexo is retiring SodexoMyWay and the So Happy app, replacing them with breakfast and lunch menus on NutriSlice." Bryant's `bryantdining.sodexomyway.com` site failed my fetch (`ECONNREFUSED`) on 2026-04-25 — that may be transient or it may be the cutover.

**Auth:** Sodexo's MyWay menus are unauthenticated HTML; Nutrislice exposes a JSON-ish endpoint per district that the official mobile app uses, e.g., `https://<district>.nutrislice.com/menu/api/weeks/school/<school>/menu-type/<type>/<yyyy>/<mm>/<dd>/`. There's no documented public API, but the endpoint is widely scraped (the Devpost project "f00d" did exactly this).

**Pricing:** Free at consumption.
**Effort:** **Medium**. Two paths:
1. Stay on `bryantdining.sodexomyway.com` — scrape menu HTML per location per day. Brittle; will break when Bryant migrates to Nutrislice.
2. Wait for the Nutrislice cutover and pull JSON. Cleaner, but unknown timing.

**Pathfinder features unlocked:**
- "**Salmo lunch is a 7-minute walk from Smithfield Hall** — you have 15 minutes between FIN 310 and ECO 114."
- "Today's hot entrée at Salmo: \[item\]. Walk-time-aware suggestion."
- Allergen + dietary filters (Sodexo data has these fields when present in the source feed).

**Source URLs:**
- https://bryantdining.sodexomyway.com/
- https://info.bryant.edu/dining
- https://www.bryant.edu/undergraduate/campus-life/residential-life/dining
- https://nutrislice.com/solutions/higher-ed/

**Honest assessment:** Highest emotional resonance ("what's for dinner") but most-likely-to-break feed in the stack. Don't ship until the Nutrislice migration is complete or get a vendor commitment via Bryant Dining Services. Wire-frame the UI now; integrate later.

---

## 4. Krupp Library — Springshare LibCal

**Vendor:** **Springshare** — three confirmed surfaces:
- `bookme.bryant.edu` — LibCal (room reservations, equipment booking: Bloomberg terminals, 3D printers, sewing, Cricut, exhibits).
- `bryant.libguides.com` — LibGuides (research guides + database links).
- `library.bryant.edu` exposes hours via a **public Google Calendar** (`circdesk@bryant.edu`), embedded directly. This is unusual: most LibCal-using libraries surface hours through `bookme.<school>.edu/hours`, but Bryant has chosen a Google Calendar embed. **Both can be scraped.**

**Format:**
- Google Calendar iCal: `https://calendar.google.com/calendar/ical/circdesk%40bryant.edu/public/basic.ics` — verified pattern (the embed src in the page references `circdesk@bryant.edu` as the calendar ID).
- LibCal Hours API: `https://api3.libcal.com/api_hours_today.php?iid=<bryant_iid>&lid=<location_id>&format=json` (institution ID required; lookup via `Admin → Hours → Widgets`).
- LibCal REST API 1.1 — full programmatic access to hours, spaces, bookings; **requires API key issued by Bryant's library admin**.

**Auth:** Google Calendar iCal is fully public. LibCal `api_hours_today.php` is public if iid is known. LibCal REST 1.1 needs OAuth-style client credentials issued by the library.
**Pricing:** Free. LibCal is already paid for by the library.
**Effort:** Low for the iCal scrape (an hour). Medium for the LibCal REST API (one polite email to `bryill@bryant.edu`, one OAuth token rotation cron).

**Pathfinder features unlocked:**
- "**Krupp is open until 1:30 AM tonight** — your CIS 350 paper is due tomorrow."
- "Bello 103 group room (4 seats) is open from 6–8 pm — book it."
- "Your last class ends at 3:00 PM, walk over to the library for a 3:30 study slot."
- During finals week: "Library hours just changed — open until 2 AM through May 12."
- Bloomberg terminal availability — directly relevant for Finance majors (Owen's audience).

**Source URLs:**
- https://library.bryant.edu/
- https://bookme.bryant.edu/
- https://bookme.bryant.edu/reserve/library
- https://ask.springshare.com/libcal/faq/1407
- https://www.apis4librarians.com/libcal/todays-hours
- https://github.com/BGSU-LITS/libcal

**Honest assessment:** This is the second-best integration after the academic calendar because it's **actually daily**. Students walk into the library, look up a free room, walk out — that's a Pathfinder push notification waiting to happen. The Bloomberg terminal angle is uniquely valuable to the Finance audience that Bryant is built for.

---

## 5. Bryant Engaged — Anthology / Campus Labs Engage

**Vendor:** **Anthology Engage** (formerly Campus Labs). Bryant's deployment is `engaged.bryant.edu`. Powers ~100+ student organizations and event RSVPs.

**Format:** **Documented JSON REST API** (the API surface is well-known among the Engage developer community). Endpoints include `/events`, `/organizations`, `/communities`, `/eventattendance`, `/eventrsvps`, `/organizationmembers`, `/organizationpositionholders`. Two versions live (v2, v3 — use v3).

**Auth:** API keys are issued **only to the institution itself** ("APIs documented are made available exclusively to licensed Anthology member campuses, third-party or public use of this API is prohibited without the consent of Anthology, and campus developers who wish to access the API must be pre-approved by Anthology"). Bryant Information Services would have to issue Owen a key.

**Pricing:** Free if Bryant grants the key; Bryant already pays the Engage license.
**Effort:** High **socially**, low **technically**. Need a sponsor inside Bryant IS or Student Activities. Once the key is issued, integration is a couple hours.

**Pathfinder features unlocked:**
- "Your **Bulldog Buddies** club meets Mondays at 7pm — already added to your calendar."
- Conflict-aware club discovery: "show me clubs that meet on days you don't have evening class."
- RSVP'd events stitched into the weekly grid alongside courses.

**Source URLs:**
- https://engaged.bryant.edu/
- https://engaged.bryant.edu/organizations
- https://engaged.bryant.edu/events
- https://docs.api.campuslabs.com/
- https://help.anthology.com/engage/en/using-the-engage-api.html
- https://engagesupport.campuslabs.com/hc/en-us/articles/360027628671-Using-the-Engage-API

**Honest assessment:** Highest unlock per integration (binds Pathfinder to the campus social graph) but gated by a relationship, not technology. This is the integration to ask for **after** Pathfinder is sanctioned for the Bryant pilot — a reason to stay in conversation with IS, not a pre-pilot prerequisite.

---

## 6. events.bryant.edu — Localist

**Vendor:** **Localist** (now Concept3D). Confirmed via `localist-images.azureedge.net` URLs in the page source. The events calendar already exposes Google Calendar / iCal / Outlook / RSS subscribe options directly in its UI.

**Format:** Localist's **public read-only API** lives at `https://events.bryant.edu/api/2/events`, returns JSON. Up to 100 results per page, up to 370-day window per query. No auth required.

**Auth:** None for read.
**Pricing:** Free.
**Effort:** Trivial. One cron, one parser. The API has well-documented filters (department, group, tag).

**Pathfinder features unlocked:**
- Campus-wide events alongside personal schedule (career fair, guest speaker, finance industry panel — directly relevant to Owen's pitch).
- Filter to events on campus during a specific class break.
- "Department of Finance is hosting Bloomberg Workshop tomorrow at 5pm in BELC 110 — you're free."

**Source URLs:**
- https://events.bryant.edu/
- https://developer.localist.com/doc/api
- https://www.localist.com/event-calendar-api

**Honest assessment:** Easy to ship; lower stickiness than dining or athletics because the volume is bursty (career fair week vs. quiet week). Nice-to-have, not a top-3.

---

## 7. Bryant shuttle — "MBT app" + web tracker

**Format:** Bryant runs the Bulldog Express Shuttle on three lines (Gold, Black, Purple) with stops at the RIPTA bus shelter, Townhouse Entrance, BELC, and Tupper Campus. The official tracking surface is the **MBT app** (Master Boston Transit / Make Better Transit — vendor branding ambiguous; not TransLoc, not Passio Go) plus a web browser tracker.

**Auth/API:** Not publicly documented. No iCal, no GTFS that I could find. RIPTA (the Smithfield public bus) does publish GTFS and GTFS-Realtime: `https://www.ripta.com/gtfs/`.

**Pricing:** N/A.
**Effort:** **High** — would require sniffing the MBT mobile app or a partnership conversation. Not worth it for a hackathon-stage product.

**Pathfinder features that *would* be unlocked:**
- "Your next class is at BELC — Gold Line is 4 minutes out at the Townhouse stop."
- Bus-aware walk-time warnings.

**Honest assessment:** **Skip for now.** Building-to-building walk times are already in `data/walk_times.json` (manual). Real-time shuttle tracking is a year-2 polish feature, not a stickiness driver.

**Source URLs:**
- https://info.bryant.edu/transportation
- https://www.ripta.com/gtfs/

---

## 8. Bryant parking — T2 Systems

**Vendor:** T2 Systems. Bryant uses `armsportal.bryant.edu` for online permit registration. T2 advertises real-time lot inventory in its enterprise product, but Bryant has not exposed a public lot-occupancy API. No scraping target with stable structure.

**Effort:** Skip. There is no value-aligned feature for a scheduling app — Pathfinder is not parking software.

**Source URLs:**
- https://armsportal.bryant.edu/
- https://is.bryant.edu/services/administrative-and-business/parking-and-transportation
- https://www.t2systems.com/higher-education/

---

## 9. Bookstore — Follett (`bkstr.com/bryantstore`)

**Vendor:** **Follett**, branded as `bkstr.com/bryantstore`. Textbook lookup is gated through Banner Self-Service ("Bryant Bookstore On-line Textbook Ordering") for authenticated students. Follett does not publish a public textbook-by-CRN API for third-party developers.

**Auth:** Student SSO into Banner.
**Effort:** **High** — would require Banner write/read on behalf of student, which is not in scope for the daily app.
**Workaround:** Scrape the public `bkstr.com/bryantstore` course materials lookup form, which accepts term/department/course/section publicly and returns the books and prices. This is brittle but doable; ToS gray area.

**Pathfinder features unlocked:**
- "Textbooks for your schedule total **$487 used** — buy them by August 20 to get free shipping."
- Total-cost-of-schedule sticker, alongside walk-time and predicted-GPA stickers.

**Source URLs:**
- https://www.bkstr.com/bryantstore/shop/textbooks-and-course-materials
- https://info.bryant.edu/university-bookstore
- https://facultyguide.bryant.edu/bryant-bookstore/bryant-bookstore/
- https://follett.com/campus-solutions/course-material-programs/

**Honest assessment:** High demo-value, medium technical-effort, real ToS risk. Defer until after pilot sanction — at which point Bryant Bookstore could be asked to provide a feed directly.

---

## 10. ACE tutoring — manual scheduling

**Status:** Bryant ACE (Academic Center for Excellence) offers tutoring by phone or in-person appointment. **No Penji, no Knack, no TutorOcean** in the search results. Scheduling is non-digital. No integration target.

**Pathfinder feature** that would be valuable but is not buildable today: "you got a C+ in MATH 201 — book a tutor for next week." Without an API, this is just a hyperlink.

**Source URLs:**
- https://info.bryant.edu/academic-center-excellence-ace
- https://studenthandbook.bryant.edu/academic-resources

---

## 11. Health Services / counseling

**Status:** PHI/FERPA hot zone. Bryant uses standard appointment systems internally. Even if an API existed, **Pathfinder should not touch health data** until SOC 2 + BAA + counsel sign-off (see baseline doc, section "What it would take to make BryantPathfinder a real campus product"). Hard skip.

---

## 12. Emergency alerts — Rave Mobile Safety

**Vendor:** **Rave Mobile Safety** (Rave Alert + Rave Guardian app). Bryant uses Rave for SMS/voice/email notifications.

**Auth/API:** Rave **does not expose a public consumer API** for receiving alerts — alerts are pushed to enrolled phones only, by design. Consuming them in Pathfinder would mean either (a) an SMS gateway that students forward to (clunky and creepy) or (b) a sanctioned push from Bryant DPS, which doesn't exist.

**Effort:** Hard skip. The right call is to not duplicate this.

**Source URLs:**
- https://is.bryant.edu/services/communication-and-collaboration/mobile-services/mobile-companion-apps/rave-guardian-safety-app
- https://is.bryant.edu/services/communication-and-collaboration/emergency-notification/emergency-alerts

---

## 13. Social — Reddit, Discord, Instagram

**Status:** No major active subreddit (`r/BryantUniversity` exists per the karlding college-subreddits list but is small). No semi-official Discord with a known invite. Bryant runs Instagram `@bryantuniversity` and Threads. Social integration is not differentiating for a scheduling tool — skip.

**Source URLs:**
- https://www.threads.com/@bryantuniversity
- https://github.com/karlding/college-subreddits

---

## Stickiness ladder

How each integration moves Pathfinder up the daily-open ladder:

| Tier | Open frequency | Integration that gets it there |
|---|---|---|
| **Once per semester** (today) | August + January | Status quo: schedule generation only. |
| **Once per month** | Drop deadline, withdraw deadline, finals week reminder | **Academic calendar** (#1) — gets you to monthly with one weekend's work. |
| **Once per week** | "What's open at the library this weekend?" "Home football Saturday." | **LibCal hours + study rooms** (#4) and **Athletics** (#2). |
| **Once per day** | "Salmo lunch in 8 minutes." "Bloomberg terminal free at 2 PM." "Engaged event you RSVP'd is in BELC 110 in 30 minutes." | **Dining** (#3) + **Bloomberg/study room real-time** (#4 deeper) + **Engaged** (#5). Daily-open requires at least two of these three. |
| **Multiple times per day** | Embedded in the morning routine | All of the above + push notifications + a calendar widget. Year 2 product. |

**The honest cliff:** Pathfinder's current product is a one-time tool. Tier-2 (monthly) is achievable in **a single afternoon of work** by adding the academic calendar JSON and pinning a "next deadline" widget on the schedule view. That alone changes the product narrative from "scheduling tool" to "schedule companion" — useful for the pilot pitch.

Tier-3 (weekly) needs **library hours + athletics**, both of which are public-feed integrations doable in a weekend.

Tier-4 (daily) needs **dining + Engaged**, both of which require either a vendor-cooperation conversation (Sodexo/Nutrislice cutover) or an institution-issued API key (Anthology Engage). Those are sales moves, not engineering moves.

---

## Honest verdict on which scrapers are worth building

| Feed | Build a scraper? | Why |
|---|---|---|
| Academic calendar (HTML) | **Yes** | Tiny, stable, twice-a-year refresh. |
| Athletics iCal (SIDEARM) | **Yes** | Vendor-supported subscribe URLs; rock solid. |
| Library hours (Google Calendar iCal) | **Yes** | Bryant publishes it publicly; the URL is the API. |
| Library rooms (LibCal) | **Yes if you can get an API key**; otherwise scrape `bookme.bryant.edu` reserve pages cautiously. |
| Dining menus (Sodexo HTML / Nutrislice JSON) | **Wait** | Vendor migration in progress; ship a placeholder UI. |
| Engaged events (Anthology) | **No, ask for the key** | Scraping is explicitly prohibited by ToS. Worth the email. |
| events.bryant.edu (Localist) | **Yes** | Official public read API. Free win. |
| Shuttle (MBT app) | **No** | No documented endpoint, low feature value. |
| Parking (T2) | **No** | No public surface. |
| Follett textbooks | **Maybe** | Public form is scrapeable, ToS is gray. Defer until pilot is sanctioned. |
| ACE tutoring | **No** | No digital surface to integrate with. |
| Health Services | **No** | PHI boundary. |
| Rave alerts | **No** | Push-only, by design. |
| Social (Reddit/Discord) | **No** | No differentiator. |

---

## Recommended sequencing

1. **This weekend (4 hours).** Ship `data/academic_calendar.json` from the catalog page parse. Pin the next deadline on the schedules page. Pathfinder is now a monthly tool.
2. **Next weekend (8 hours).** Subscribe to the SIDEARM iCal feeds for all 22 varsity sports, store in `data/athletics.json`, refresh nightly. Add "home games during your free blocks" to the schedule card. Pathfinder is now a weekly tool for sports fans.
3. **Following week (8 hours).** Parse Krupp Library's `circdesk@bryant.edu` Google Calendar iCal into `data/library_hours.json`. Add a "library is open until X" sticker to the schedules page. Now Pathfinder is a weekly tool for everyone.
4. **Pilot conversation with Bryant IS.** Request: (a) Anthology Engage v3 API key, (b) a sanctioned Sodexo/Nutrislice menu URL or a heads-up on the cutover date, (c) an introduction to the library's LibCal admin for a REST API key. **None of these are technical asks** — they're relationship asks, and they only make sense once the academic-calendar + athletics + library-hours version is shipped to demonstrate good faith.

---

## Source list (for traceability)

- https://catalog.bryant.edu/undergraduate/academiccalendar/
- https://catalog.bryant.edu/undergraduate/academiccalendar/academiccalendar.pdf
- https://catalog.bryant.edu/graduate/academiccalendars/
- https://info.bryant.edu/registrar
- https://bryantbulldogs.com/
- https://bryantbulldogs.com/calendar
- https://bryantbulldogs.com/news/2024/6/6/general-welcome-to-the-new-bryantbulldogs-com.aspx
- https://bryantbulldogs.com/news/2025/2/24/general-bryant-launches-new-mobile-app-powered-by-sidearm-sports.aspx
- https://playbook.sidearmsports.com/quick-hits/new-composite-calendar/
- https://bryantdining.sodexomyway.com/
- https://info.bryant.edu/dining
- https://www.bryant.edu/undergraduate/campus-life/residential-life/dining
- https://nutrislice.com/solutions/higher-ed/
- https://library.bryant.edu/
- https://bookme.bryant.edu/
- https://bookme.bryant.edu/reserve/library
- https://bryant.libguides.com/
- https://ask.springshare.com/libcal/faq/1407
- https://www.apis4librarians.com/libcal/todays-hours
- https://github.com/BGSU-LITS/libcal
- https://engaged.bryant.edu/
- https://engaged.bryant.edu/organizations
- https://engaged.bryant.edu/events
- https://docs.api.campuslabs.com/
- https://help.anthology.com/engage/en/using-the-engage-api.html
- https://engagesupport.campuslabs.com/hc/en-us/articles/360027628671-Using-the-Engage-API
- https://events.bryant.edu/
- https://developer.localist.com/doc/api
- https://www.localist.com/event-calendar-api
- https://info.bryant.edu/transportation
- https://www.ripta.com/gtfs/
- https://armsportal.bryant.edu/
- https://is.bryant.edu/services/administrative-and-business/parking-and-transportation
- https://www.t2systems.com/higher-education/
- https://www.bkstr.com/bryantstore/shop/textbooks-and-course-materials
- https://info.bryant.edu/university-bookstore
- https://facultyguide.bryant.edu/bryant-bookstore/bryant-bookstore/
- https://follett.com/campus-solutions/course-material-programs/
- https://info.bryant.edu/academic-center-excellence-ace
- https://studenthandbook.bryant.edu/academic-resources
- https://is.bryant.edu/services/communication-and-collaboration/mobile-services/mobile-companion-apps/rave-guardian-safety-app
- https://is.bryant.edu/services/communication-and-collaboration/emergency-notification/emergency-alerts
- https://www.threads.com/@bryantuniversity
- https://github.com/karlding/college-subreddits
