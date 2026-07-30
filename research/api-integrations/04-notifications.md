# 04 — Notifications & Messaging APIs

> Research subagent A4. Scope: pick the right API stack for BryantPathfinder to wake students up at the moments that matter — registration windows opening, pinned sections losing seats, advisor feedback landing on a draft schedule, a fresh batch of generated schedules ready to review. Today the product has zero notification surface. Everything below is greenfield.

---

## 1. Why notifications matter for Pathfinder specifically

The Pathfinder workflow has a hard temporal edge that the current product completely ignores: **registration is a clock-driven event.** A student who generated three perfect schedules in October and never came back will lose their pinned FIN 310 section the moment a classmate registers two minutes earlier. The product baseline (`research/commercialization/00-product-baseline.md`) confirms there is no database, no persistent user, no auth, no async eventing — so notifications are not just a feature, they are also the architectural forcing function that pushes Pathfinder from a single-session schedule generator to a stateful campus tool.

Four canonical alerts emerge from the product's job-to-be-done:

| # | Trigger | Latency budget | Channel intuition |
|---|---|---|---|
| A | Pinned section seats just dropped to <3 | 30–120 s | SMS (or push if installed PWA) |
| B | Registration window opens in 24 h | 1 h | Email |
| C | Advisor commented on draft schedule | 5–15 min | Email + in-app |
| D | New schedules generated, review here | minutes | Email (and in-app if open) |

Anything that misses budget A is worthless — by the time the email is read 20 minutes later, the seat is gone. Anything that hits A but spams the student into muting the channel kills B and D. So channel selection is not a checklist exercise; it is a tradeoff between latency, deliverability, regulatory drag, and signal-to-noise.

---

## 2. Email APIs — comparative table for transactional sends

All numbers as of April 2026. Pricing assumed at the **50K sends/month** target the prompt asked about; that volume corresponds roughly to ~5,000 active Bryant pilot users averaging 10 transactional emails each per month (verification, daily digests, registration-window blasts, advisor pings).

| Vendor | Free tier | 50K/mo cost | Deliverability reputation | EDU notes |
|---|---|---|---|---|
| **Resend** | 3,000/mo, 100/day | **$20/mo (Pro)** | Strong; Postmark-class infra under the hood; DKIM/SPF/DMARC + custom tracking domains | DevX leader. React Email components ship in-tree. ([Resend pricing](https://resend.com/pricing), [Nuntly 2026](https://nuntly.com/resend-pricing)) |
| **Postmark** | 100/mo dev plan, no expiry | $15/mo Basic (10K) → $87/mo for 50K (overage $1.30–$1.80/1K) | **Best-in-class** — 98.5–98.7% inbox placement in independent tests, separate streams for transactional vs broadcast | The "if deliverability matters, Postmark is king" pick. ([Postmark pricing](https://postmarkapp.com/pricing), [Hackceleration 2026](https://hackceleration.com/postmark-review/)) |
| **SendGrid (Twilio)** | None as of late 2025 | **$19.95/mo Essentials 50K** | Solid but commoditized; shared-IP risk on Essentials, no dedicated IP until Pro $89.95 | Incumbent. Heavy historical use → some EDU spam filters auto-reputation it. ([SendGrid pricing](https://sendgrid.com/en-us/pricing), [Sender review](https://www.sender.net/reviews/sendgrid/pricing/)) |
| **Mailgun** | 100/day | $35/mo Foundation, $90/mo Scale | Good after warmup; includes one dedicated IP at Foundation+ | Sinch-acquired; users report 20–40% price hikes since 2021. ([Mailgun pricing](https://www.mailgun.com/pricing/)) |
| **Loops.so** | 4,000 sends, 1K contacts | $49/mo entry, **transactional unlimited** included | Marketing+transactional+sequences in one tool; deliverability competent but not Postmark-tier | Useful if Pathfinder ever runs onboarding email *sequences* (4-week registration drip). ([Loops pricing](https://loops.so/pricing), [transactional now free](https://loops.so/updates/transactional-email-is-now-free)) |
| **AWS SES** | 3,000/mo first 12 months (legacy accounts) | **$5/mo** ($0.10 per 1K × 50K) + $0.07/1K Virtual Deliverability Manager | Cheapest by an order of magnitude; deliverability requires hand-tuning (warmup, DKIM, dedicated IP $24.95/mo) | The right answer if you have an SRE; the wrong answer at hackathon-team scale. ([AWS SES pricing](https://aws.amazon.com/ses/pricing/), [Costbench 2026](https://blog.campaignhq.co/amazon-ses-pricing/)) |

### EDU-domain (.edu / @bryant.edu) deliverability notes

None of the vendors have a documented "EDU mode." `@bryant.edu` is a Microsoft 365 / Exchange Online tenant (typical for Bryant given they are an AACSB business school running standard MS infra), so inbox placement comes down to: SPF aligned, DKIM signed by the sending domain, DMARC at `p=none` minimum, and a warm sender reputation. Resend, Postmark, and SES all support all three out of the box. The risk is **shared-IP pools getting tarred by another sender's bad behavior** — this is why Postmark's separate broadcast/transactional streams matter, and why a dedicated IP becomes worth it once Pathfinder ships to a second institution. ([Resend deliverability tips](https://resend.com/blog/top-10-email-deliverability-tips), [FERPA & electronic comms FAQ](https://lcuniversity.edu/wp-content/uploads/2020/05/ferpa-faqs.pdf))

**Pick at pilot scale: Resend.** $20/mo, React Email components compose cleanly with the existing Next.js 15 + Tailwind + shadcn frontend, and DX is the dominant cost at the founder's solo-builder scale. **Pick at scale (3+ institutions):** migrate to Postmark for the deliverability ceiling, or AWS SES if Pathfinder ever has dedicated infra staff.

---

## 3. SMS APIs — and the A2P 10DLC tax

Use case A ("pinned seat just dropped to 2") is the only one that genuinely demands SMS — a push notification to a non-installed PWA can't reach an iPhone in a pocket, and email is too slow.

| Vendor | Per-segment US | Phone number | 10DLC brand | 10DLC campaign | Notes |
|---|---|---|---|---|---|
| **Twilio** | $0.0083 + carrier surcharges $0.0035–0.005 | $1.15/mo | $4.50 (Sole Proprietor) – $44 (Standard, with Fast Track) one-time | $1.50–$10/mo per campaign | Industry default; documentation, ecosystem, status page all best-in-class. ([Twilio A2P 10DLC fees](https://help.twilio.com/articles/1260803965530-What-pricing-and-fees-are-associated-with-the-A2P-10DLC-service-)) |
| **Telnyx** | $0.004 | varies | passes 10DLC fees through at cost; no markup | same TCR fees | ~52% cheaper per segment; free incoming SMS; free 24/7 support (Twilio charges $1,500/mo minimum). ([Telnyx vs Twilio](https://telnyx.com/resources/telnyx-vs-twilio-sms), [Telnyx 10DLC](https://support.telnyx.com/en/articles/5634625-10dlc-fees-and-charges)) |
| **MessageBird (Bird)** | comparable to Twilio | varies | required | required | Stronger in EU; less relevant for a Rhode Island pilot. |
| **Plivo** | $0.0055 | $0.80/mo | required | required | Twilio-compatible API; good cost middle ground. ([Plivo comparison](https://www.plivo.com/blog/telnyx-vs-twilio/)) |
| **AWS End User Messaging** | similar to Twilio after carrier fees | $1/mo | required | required | Worth it only if already deep in AWS. |

### The A2P 10DLC reality check (READ THIS)

In the US, **every** A2P (application-to-person) SMS sender is required by the major carriers to register a "brand" with The Campaign Registry (TCR) and submit each "campaign" (use case) for vetting. The fees are nominal but the **timeline is the gate**:

- **Sole Proprietor brand**: $4 one-time, ~2–3 business days. Required if Owen registers as an individual (no EIN). Throughput is hard-capped at low-volume tier (~3,000 messages/day across all carriers, with T-Mobile capping individual brands far lower).
- **Standard Brand**: $44 one-time (incl. $3 Fast Track), needs a US EIN. **Campaign vetting: 10–15 business days currently per Twilio docs; budget 4 weeks total accounting for resubmissions.**
- **Per-campaign monthly fee**: $1.50–$11/mo recurring, applied even to rejected campaigns until cancelled.

([Twilio Standard onboarding](https://www.twilio.com/docs/messaging/compliance/a2p-10dlc/direct-standard-onboarding), [HighLevel sole prop guide](https://help.gohighlevel.com/support/solutions/articles/155000000340-a2p-sole-proprietor-brand-registration-for-10dlc), [notificationapi 10DLC dev guide](https://www.notificationapi.com/blog/a2p-10dlc-registration-the-complete-developer-s-guide-2025))

Translation for Pathfinder: **SMS for the Bryant fall pilot is a 4-week procurement project with a US-EIN dependency**, which means Owen first has to incorporate (LLC ~$150 in RI, plus EIN free from IRS), then register as a Standard Brand or accept Sole-Proprietor throughput limits that may not survive a registration-day burst (50 students × 3 alerts in 5 minutes = throttle). The ~$50 brand+campaign fee is trivial; the calendar weeks are not.

**Recommendation: skip SMS for the Bryant pilot.** Use push + email + in-app. Add SMS only for the second institution, when there's an LLC, a paid pilot, and a justification beyond "it would be cool." If SMS is non-negotiable, **Telnyx over Twilio** — same compliance gate, half the per-segment cost, free inbound, and meaningfully better support at startup scale.

---

## 4. Push notifications

| Service | Free tier | Cost | Best for |
|---|---|---|---|
| **Firebase Cloud Messaging (FCM)** | **Unlimited free** for messages themselves; only pay egress | $0 | Web push (Chrome/Edge/Firefox), Android. The default. ([Firebase pricing](https://firebase.google.com/pricing)) |
| **APNs** (Apple Push) | Free, requires Apple developer account ($99/yr) | $0 + $99/yr | iOS native — but Pathfinder has no native iOS app today |
| **OneSignal** | 10K web push subs + unlimited mobile push subs free; 10K emails free | $19/mo Growth + $0.004/web sub + $0.012/mobile MAU + $2/1K emails | Managed wrapper if you don't want to own the FCM/APNs token plumbing. ([OneSignal pricing](https://onesignal.com/pricing)) |
| **Knock** | 10K notifications/mo dev plan | $250/mo Starter (next tier up — big jump) | Multi-channel orchestration, not just push. ([Knock pricing](https://knock.app/pricing)) |
| **Novu** | Free open-source self-host; cloud $30/mo for 30K runs | $30–$250/mo cloud | Knock alternative; can self-host on existing FastAPI server. ([Novu pricing](https://novu.co/pricing/)) |

### Web push reality check on Apple platforms

iOS 16.4 (March 2023) added Web Push for PWAs, but **only when the site is installed to the home screen**. iOS 16.4+ outside the EU; Safari 18.4 added Declarative Web Push. Practically: **the reachable audience for web push on iPhone is 10–15x smaller than for native** because most users never tap "Add to Home Screen." For a hackathon-built web app targeting iPhone-heavy college students, that's a structural ceiling. Desktop Safari and all of Android/Chrome work fine. ([MagicBell PWA iOS guide](https://www.magicbell.com/blog/pwa-ios-limitations-safari-support-complete-guide), [Apple developer push docs](https://developer.apple.com/documentation/usernotifications/sending-web-push-notifications-in-web-apps-and-browsers))

**Pick: FCM directly.** Free, unlimited, no vendor markup, browser-standard Web Push protocol underneath. OneSignal is only worth it if Pathfinder wants a single dashboard for push+email+SMS analytics — and we get that from Knock/Novu instead, with better orchestration semantics.

---

## 5. Slack / Discord / Teams / Telegram — student-preferred channels

This is the most underestimated category for a student-facing product.

- **Discord webhooks** are the unsung hero. Bryant students self-organize in major-specific Discord servers (Finance, CS, Marketing). A single HTTP POST to a webhook URL drops a formatted message into a channel, no bot framework, no OAuth, no rate-limit tax for typical volumes, $0 forever. Use case: an opt-in "registration radar" channel where students can subscribe to public seat-drop alerts for popular sections. ([Discord webhook resource docs](https://discord.com/developers/docs/resources/webhook), [Hookdeck Discord webhooks](https://hookdeck.com/webhooks/platforms/how-to-get-started-with-discord-webhooks))
- **Slack API** is ~useless at Bryant — Bryant doesn't run a campus-wide Slack workspace. Skip unless a partner institution has one.
- **Microsoft Teams Graph API** matters because Bryant *does* run M365, and faculty/advisors live in Teams. Worth it for the *advisor* surface — "advisor commented on a student schedule" → Teams DM to the advisor — not for the student surface. Higher integration cost (Azure AD app registration, admin consent, Graph permissions).
- **Telegram** is rare in US college contexts; skip.

**Pick: Discord webhooks for student opt-in alerts (free, two-line implementation), Teams Graph for advisor pings (later).**

---

## 6. In-app notifications and orchestration

This is the layer the product is missing entirely. An advisor commenting on a draft schedule should see a feed item in the student's Pathfinder UI the next time they open it, not just an email.

| Option | Approach | Cost | Notes |
|---|---|---|---|
| **Knock** | Hosted SaaS; React `<NotificationFeed/>` + workflow engine routes to email/SMS/push/in-app from one trigger | Free 10K/mo, then $250/mo | Best DX of the orchestration platforms. Frontend ships production-ready React components matching shadcn aesthetic. ([Knock blog: top notification platforms](https://knock.app/blog/the-top-notification-infrastructure-platforms-for-developers)) |
| **Courier** | Hosted SaaS; visual template designer; broader provider list (50+) | Custom | Stronger for non-technical content authors; weaker DX than Knock. |
| **MagicBell** | Drop-in React/Vue notification bell + multi-channel | Free 100 MAU, usage-based | Best component library; pricing gets unpredictable. |
| **Novu** | Open-source self-host *or* cloud | Self-host free; cloud $30+/mo | Only one with a credible self-host story. Sits on the same FastAPI server. |
| **Customer.io** | Marketing-first, supports transactional | $$$ | Overkill for Pathfinder's volume; better for lifecycle marketing. |
| **In-house** | Build it on FastAPI + Next.js | Eng-time | The "real" cost is preference centers, batching, throttling, dedupe across channels — all the hard parts that orchestrators exist to solve. |

The orchestration platforms exist because writing the code path "user X gets an SMS *unless* they've opened the in-app feed in the last 15 minutes, in which case batch it into a daily email digest, and respect their quiet-hours preference" is genuinely hard. Pathfinder will need this exact logic by the time use case A (seat-drop alerts) ships, because spamming an SMS every time a seat fluctuates between 2 and 3 will get the sender muted.

**Pick at pilot: Novu self-host or just-in-time in-house.** Knock's $250 jump is brutal for a pre-revenue project, and the 10K free tier disappears the moment the pilot includes 200 students with daily digests (200 × 30 days = 6K monthly already, leaving no headroom for transactional).

**Pick at second institution: Knock.** The DX, the React components, and the preference-center primitive are worth $250/mo once there's a paid pilot to amortize against.

---

## 7. FERPA implications — when a notification is an education record

This shapes the architecture more than vendor pricing does. The Department of Education's guidance is explicit: **education records can exist in any medium including email, computer files, computer screen display, paper documents, printouts...** ([studentprivacy.ed.gov FAQ](https://studentprivacy.ed.gov/frequently-asked-questions), [NYSED FERPA FAQ](https://www.nysed.gov/data-privacy-security/frequently-asked-questions-about-data-privacy-and-security)). The JD Supra summary of Franczek's analysis is directly on point: emails and texts containing personally identifiable academic information about a specific student *are* education records, full stop. ([JDSupra: are emails, texts FERPA records](https://www.jdsupra.com/legalnews/are-emails-texts-tweets-and-other-dig-60950/))

What that means for each Pathfinder alert:

| Alert | Contains education record content? | FERPA-clean delivery |
|---|---|---|
| "Registration opens in 24h" | No (generic schedule reminder) | Any vendor |
| "Your pinned section FIN 310 with Kumar dropped to 3 seats" | **Yes** — names a specific course on a specific student's plan | Sender must be a "school official" or under direct school control with FERPA flow-through |
| "Advisor commented on your draft schedule" | **Yes** — links to a record containing GPA, audit, schedule | Same |
| "3 new schedules generated" with course list | **Yes** | Same |

The single FERPA-relevant FAQ from the federal guidance: schools may outsource to third parties **provided the third party performs an institutional service, is under direct control of the institution, and uses PII only for the purpose disclosed.** ([ED.gov vendor FAQ PDF](https://studentprivacy.ed.gov/sites/default/files/resource_document/file/Vendor%20FAQ.pdf))

Practical implications:

1. **Sign DPAs (Data Processing Agreements) with whichever email/SMS/push vendor you use.** Resend, Postmark, Twilio, Telnyx, OneSignal, Knock all offer DPAs as standard. Loops and Discord webhook may not — Discord especially is *not* a HIPAA/FERPA-safe channel for student-identifying info, which is fine for a public "FIN 310 dropped to 3 seats anonymized" channel but **never** for "Owen Ash's FIN 310 dropped to 3 seats."
2. **Strip PII from the alert payload, send the student to authenticated UI for details.** "A pinned section needs your attention. Open Pathfinder to see." No course code in the SMS body, no GPA in the email subject. This dodges 80% of the FERPA exposure surface.
3. **Get a written school-official designation from Bryant's registrar before the pilot.** Without it, Pathfinder is technically not under the school's direct control and can't claim the FERPA exception. This is a 2-page legal artifact, not a SOC 2 audit.
4. **SMS specifically is the highest-FERPA-risk channel** because LCU's published FERPA FAQ is unambiguous: *"If information to be transmitted is FERPA protected, text message should not be used."* ([LCU FERPA FAQ](https://lcuniversity.edu/wp-content/uploads/2020/05/ferpa-faqs.pdf)) This is one institution's interpretation, not a federal rule, but it is a directionally common position. The mitigation is the strip-PII pattern from #2 — the SMS says "Pathfinder alert: open the app" with no academic content in the message body.

---

## 8. Mapping each critical use case to a recommended API

| Use case | Latency | Channel | Recommended API | Rationale |
|---|---|---|---|---|
| **A. Pinned section seats <3** | 30–120s | Web push (primary) → email digest (fallback after 1h unread) | **FCM web push + Resend** routed via **Novu** | Web push is free, instant, FERPA-safe (subject line: "Action needed in Pathfinder", no course content). Email is the fallback channel. Skip SMS until Pathfinder has an LLC and 10DLC clearance. |
| **B. Registration window opens in 24h** | 1h | Email | **Resend** | Generic reminder, no FERPA content; warm cream HTML built with React Email matches the editorial-minimalism aesthetic. |
| **C. Advisor commented on draft schedule** | 5–15 min | Email + in-app feed | **Resend + Novu in-app inbox** | Two-channel; in-app feed loads when student opens Pathfinder; email backfills if dormant. Teams Graph DM optional for the advisor's side. |
| **D. New schedules generated** | minutes | Email + in-app | **Resend + Novu in-app inbox** | The "your schedules are ready" card is also the marketing surface — keep it owned, FERPA-safe content (count of schedules, not course names), and link to authenticated UI. |

---

## 9. Top 3 recommended stacks

### Stack 1 — Pilot (fall 2026, Bryant only). Recommended.

- **Resend** ($20/mo Pro, 50K emails) — transactional + React Email components
- **FCM web push** (free) — instant alerts to opted-in browsers, no PWA install required for Chrome/Edge/Firefox/Android
- **Novu cloud** ($30/mo, 30K runs) — orchestration, in-app inbox React component, preference center, multi-channel routing
- **Discord webhooks** (free) — opt-in public "seat radar" channels for popular sections
- **No SMS, no Slack, no Teams** — defer until Q1 2027

Total: ~$50/mo. Covers four canonical alerts cleanly. FERPA-defensible with DPAs from Resend + Novu. Builds the in-app inbox that Pathfinder is missing today.

### Stack 2 — Scale (3+ institutions, paid pilots).

- **Postmark** ($87/mo for 50K, climbing) — replace Resend when deliverability becomes a contractual SLA
- **FCM** + native iOS APNs (if a React Native app ships)
- **Knock** ($250/mo Starter) — replace Novu when the team has 5+ message templates, multi-tenant preference centers, and per-institution branding
- **Telnyx SMS** ($0.004/segment) once 10DLC Standard Brand is approved (~4 weeks lead time after LLC + EIN)
- **Microsoft Teams Graph** for advisor-side workflows in M365 institutions
- **Discord webhooks** retained for student community channels

Total: ~$400–600/mo at 5 institutions × 1,000 students. Deliverability ceiling is the differentiator.

### Stack 3 — Lean / cost-floor (if Pathfinder ever needs to subsidize 50K students at near-zero margin).

- **AWS SES** ($5/mo for 50K) — but requires SRE-grade DKIM/warmup/IP management
- **FCM web push** (free)
- **Novu self-hosted** on the existing FastAPI server (Docker, ~$0 marginal cost)
- **Discord webhooks** (free)
- **No SMS, no managed orchestrator**

Total: ~$5–15/mo. Right answer only if Pathfinder hires an ops engineer; wrong answer for solo-founder hackathon scale.

---

## 10. Opinion: is SMS worth the A2P 10DLC pain at pilot scale?

**No.** Not for the Bryant pilot, not for the second institution either unless the second institution is a paying customer who explicitly demands SMS as a contractual requirement.

The argument for SMS is use case A — seat-drop alerts that are genuinely time-critical. But three things blunt that argument at pilot scale:

1. **Web push covers 70% of the latency requirement** for free. A student with Pathfinder open in a Chrome tab — which is most of them, most of the day, on a college laptop — gets the alert in under 5 seconds.
2. **The students who would benefit most from SMS** (iPhone users in class, no laptop open) need a PWA install for web push to work, and SMS to a phone they're not allowed to look at during class. Either way, the alert isn't actionable for ~3 hours of the day.
3. **The 10DLC tax — 4 weeks of calendar time, US EIN dependency, throughput caps, per-campaign monthly fees, and FERPA-text-message guidance that pushes you to strip all useful content from the SMS body anyway** — is a disproportionate cost for a feature that buys you maybe 90 seconds of latency over web push.

The right call for the fall 2026 Bryant pilot: ship FCM web push + Resend email + Novu in-app, with Discord webhooks as a free public-channel bonus. Measure A's actual latency in production. Only add SMS in 2027 if data shows that students who only had email/push lost pinned sections at meaningfully higher rates than students who would have had SMS.

The discipline here — refusing to ship SMS until there's evidence of need — is exactly the deterministic-vs-LLM discipline ADR-0003 already established for the solver. Use the right tool for the latency tier, don't over-engineer the channel mix, and protect the demo path.

---

## Sources

- [Resend pricing](https://resend.com/pricing)
- [Resend deliverability tips](https://resend.com/blog/top-10-email-deliverability-tips)
- [Resend domain verification docs](https://resend.com/docs/dashboard/domains/introduction)
- [Nuntly Resend pricing 2026](https://nuntly.com/resend-pricing)
- [Postmark pricing](https://postmarkapp.com/pricing)
- [Postmark review 2026 (Hackceleration)](https://hackceleration.com/postmark-review/)
- [SendGrid pricing](https://sendgrid.com/en-us/pricing)
- [Sender SendGrid pricing 2026](https://www.sender.net/reviews/sendgrid/pricing/)
- [Mailgun pricing](https://www.mailgun.com/pricing/)
- [Loops pricing](https://loops.so/pricing)
- [Loops: transactional now free](https://loops.so/updates/transactional-email-is-now-free)
- [AWS SES pricing](https://aws.amazon.com/ses/pricing/)
- [AWS SES 2026 cost breakdown](https://blog.campaignhq.co/amazon-ses-pricing/)
- [Twilio A2P 10DLC fees](https://help.twilio.com/articles/1260803965530-What-pricing-and-fees-are-associated-with-the-A2P-10DLC-service-)
- [Twilio Direct Standard onboarding](https://www.twilio.com/docs/messaging/compliance/a2p-10dlc/direct-standard-onboarding)
- [Telnyx 10DLC fees](https://support.telnyx.com/en/articles/5634625-10dlc-fees-and-charges)
- [Telnyx vs Twilio SMS](https://telnyx.com/resources/telnyx-vs-twilio-sms)
- [Plivo: Telnyx vs Twilio comparison](https://www.plivo.com/blog/telnyx-vs-twilio/)
- [HighLevel A2P Sole Proprietor guide](https://help.gohighlevel.com/support/solutions/articles/155000000340-a2p-sole-proprietor-brand-registration-for-10dlc)
- [notificationapi.com 10DLC developer guide](https://www.notificationapi.com/blog/a2p-10dlc-registration-the-complete-developer-s-guide-2025)
- [Firebase pricing (FCM free)](https://firebase.google.com/pricing)
- [Apple developer: web push](https://developer.apple.com/documentation/usernotifications/sending-web-push-notifications-in-web-apps-and-browsers)
- [MagicBell PWA iOS Safari guide](https://www.magicbell.com/blog/pwa-ios-limitations-safari-support-complete-guide)
- [OneSignal pricing](https://onesignal.com/pricing)
- [Knock pricing](https://knock.app/pricing)
- [Knock: top notification infra platforms 2026](https://knock.app/blog/the-top-notification-infrastructure-platforms-for-developers)
- [Novu pricing](https://novu.co/pricing/)
- [Novu vs Knock vs Courier 2026](https://www.pkgpulse.com/blog/novu-vs-knock-vs-courier-notification-infrastructure-2026)
- [Discord webhook resource docs](https://discord.com/developers/docs/resources/webhook)
- [Hookdeck: getting started with Discord webhooks](https://hookdeck.com/webhooks/platforms/how-to-get-started-with-discord-webhooks)
- [US ED studentprivacy.ed.gov FERPA FAQ](https://studentprivacy.ed.gov/frequently-asked-questions)
- [US ED Vendor FAQ PDF (third-party FERPA)](https://studentprivacy.ed.gov/sites/default/files/resource_document/file/Vendor%20FAQ.pdf)
- [JDSupra: are emails, texts FERPA records (Franczek)](https://www.jdsupra.com/legalnews/are-emails-texts-tweets-and-other-dig-60950/)
- [LCU FERPA & electronic communication FAQ](https://lcuniversity.edu/wp-content/uploads/2020/05/ferpa-faqs.pdf)
- [NYSED data privacy FAQ](https://www.nysed.gov/data-privacy-security/frequently-asked-questions-about-data-privacy-and-security)
