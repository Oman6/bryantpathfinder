# 99 — Input-Method Roadmap

> Synthesis of files I1–I5. Frame: how should a Bryant student get their outstanding requirements INTO Pathfinder? Today there are two paths — paste text or upload a Degree Works screenshot — and both are clunky. This doc picks the next 2–3 to build, ranks the rest, and names the ones to skip.

---

## 1. Verdict

The current paste-text + upload-image pair is **not enough**. The paste path requires the student to already know the codes; the upload path costs ~$0.04 per parse, leaks the audit (with name, ID, GPA) to Anthropic, and breaks when Bryant ships a new Degree Works skin. The right replacement is a **three-way split**: a default visual picker for cold-start, a conversational fallback for "I don't know my codes yet," and an advisor-shared link for the 50-student fall pilot.

---

## 2. The Top 5 Input Methods, Ranked

Ranked by `(user-friction reduction × FERPA upside) ÷ engineering effort`. Bryant fall pilot is the scoring frame.

| # | Method | Friction | FERPA upside | Effort | Source |
|---|---|---|---|---|---|
| 1 | **Visual major-template picker** (synthetic audit built in Zustand from a Bryant-major template, reusing the existing `/preferences` page) | 3 taps to a usable schedule | None of the audit goes to Anthropic | **2 days** | I3 |
| 2 | **Advisor-shared link / QR code** (advisor pre-fills the requirements once, student opens `pathfinder.app/start?token=…`) | Zero student typing; pre-filled on open | Cleanest §99.31 school-official path | **1 day** | I5 |
| 3 | **Conversational chat as secondary input** (Claude tool-use extracting `OutstandingRequirement[]` from natural language, with a mandatory confirmation step) | One sentence to start | Low — chat content goes to Anthropic | **3 days** | I2 |
| 4 | **Bookmarklet / MV3 extension** scraping `degreeworks.bryant.edu` in the student's authenticated browser; only structured codes hit Pathfinder | One-time install; one click thereafter | **Categorical** — name/ID/GPA never leave the student's machine | **3 days bookmarklet · 8 days extension** | I4 |
| 5 | **Authenticated webview cookie-replay** to Banner SSB / Degree Works (Plaid / Coursicle pattern) | Native sign-in; full audit auto-pulled | Pathfinder server now in the FERPA blast radius — needs DPA before ship | **5–8 days summer · 15–25 days sanctioned** | I1 |

**Total to ship #1–3: 6 person-days.** That's the realistic summer scope. #4 and #5 are post-pilot.

---

## 3. The Three-Sprint Build Order

### Sprint 1 (Week 1–2): Visual picker becomes the default

1. **Build the Bryant Finance major template.** Hand-write `data/major_templates/finance.json` with the canonical 16 Finance requirements (FIN 310, FIN 4XX choose-one-of, the gen-ed slots, the science+lab pair, etc.). Reuse the same `OutstandingRequirement` schema as the audit parser — that's the lock per I3 §3.
2. **Ship the major-template picker as the new homepage primary.** "I'm a sophomore Finance major" → click → audit pre-loads → `/preferences` → schedule. Per I3 §11, three taps to a generated schedule.
3. **Demote paste-text + upload-image to a "Have an audit?" disclosure** below the picker. They keep working; they're just not the path of least resistance.
4. **Ship the empty-state copy from I3 §10:** "Tell us what you're studying. We'll handle the rest." Edit the existing `app/page.tsx` hero, don't rewrite it.

> **Demo line:** "A Bryant student now goes from homepage to schedule in three taps with zero typing."

### Sprint 2 (Week 3): Advisor-shared link

1. **Add `POST /api/advisor/share`** that takes a payload of `{ student_email, requirements: [...] }` and returns `{ token, share_url }`. Backend stores the pre-filled audit in a TTL keyed by token (in-memory or Supabase later — for the pilot, in-memory is fine).
2. **Add `/start?token=xxx` route** that fetches the pre-filled audit and routes the student straight to `/preferences`. No upload, no chat, no clicks beyond "Generate my schedules."
3. **Generate a QR code** alongside the link (use `qrcode-svg`, no external service) so the advisor can hand a printout to a low-tech student.
4. **No advisor-side UI yet for the pilot.** Owen builds the link via curl or a 5-line script while sitting next to the advisor. UI can come later.

> **Demo line:** "Advisor sends one link; student opens it; schedule generated; no Vision call, no FERPA exposure."

### Sprint 3 (Week 4): Conversational chat as a secondary input

1. **Add a third tab** to the existing UploadZone alongside paste and upload: "Chat with Pathfinder." Mandatory confirmation step at the end (I2 §3) — Claude proposes the structured requirements as checkbox cards; student edits if Claude got `rule_type` wrong.
2. **Use Anthropic tool-use** with a `submit_requirements` tool whose schema mirrors `OutstandingRequirement[]` (I2 §1). System prompt sets ~1500 tokens of catalog/Bryant context (cacheable — already wired).
3. **Cost:** ~$1/month at pilot scale per I2 §4. Latency 2–3s/turn after cache warm. Acceptable.

> **Demo line:** "Type one sentence about your major and Claude builds the requirement list."

---

## 4. The "Don't Build" List

| Method | Why it's tempting | Why it's wrong (now) | Source |
|---|---|---|---|
| **Voice / Web Speech / Realtime** | "Just say what you need" feels futuristic | Library / study-space environments are voice-hostile; duplicates two clicks of the picker for no FERPA win (I5) | I5 |
| **Mobile camera OCR / Apple Live Text / Tesseract.js** | Snap audit on the screen, no upload | Vision already does this — and adds semantic interpretation OCR can't. On-device OCR adds a hop without removing the LLM | I5 |
| **Email forwarding to `parse@pathfinder.app`** | Friction-free, "just forward it" | SES inbound + parse + token roundtrip is more code than a bookmarklet, with similar FERPA exposure | I5 |
| **Web Share Target full handler** | One-tap share-from-Files to Pathfinder | iOS Safari doesn't implement it (WebKit bug 194593, still open). Stub the manifest only | I4, I5 |
| **InCommon Shibboleth SP registration** | Real institutional auth | Requires Bryant IT sponsorship + 4–8 wks process. Sanctioned-pilot territory, not summer | I1 §3 |
| **Userscripts (Tampermonkey/Greasemonkey)** | Power users love them | Wrong audience — sophomores won't install Tampermonkey | I4 |
| **Authenticated webview cookie-replay** for paid pilot #2 | Pulls the full audit automatically | Pathfinder server enters the FERPA blast radius; brittle against Bryant's Duo MFA per I1 §4. Defer until sanctioned pilot has a DPA in place | I1 |

---

## 5. Empirical Checks That Block Some of These

Before committing to #4 (bookmarklet), one cheap test from I4 §4 must run first:

```bash
curl -sI https://degreeworks.bryant.edu | grep -i content-security-policy
```

If Bryant's Degree Works ships a strict CSP (likely `default-src 'self'`), the bookmarklet is dead — the inline script tag won't execute. In that case, fall through to a real MV3 extension or skip #4 entirely.

Same gate for #5 (webview cookie-replay): check whether `degreeworks.bryant.edu` enforces SameSite=Strict on its session cookie. If yes, embedding it in a webview won't carry the cookie cross-context.

These are 2-minute checks; do them before sprint planning.

---

## 6. Strategic Asks (Relationship, Not Code)

- **Bryant Office of Academic Advising** — pitch the advisor-link pattern as the FERPA-safe onboarding for 5 advisors and 50 students this fall. Single meeting; no contract needed at pilot scale (per I1 §5 / commercialization 02).
- **Bryant IT** — request to register Pathfinder as an InCommon Shibboleth SP for a Q1 2027 sanctioned-pilot upgrade. Long process; start the conversation now (I1 §3).
- **Ellucian Partner Network** — defer until paid customer #2 is signed (commercialization roadmap).

---

## 7. The Cost Reality Check

- **Bryant pilot, 50 students, fall 2026:** ~$1/month additional API cost (chat input, modest Claude usage). Visual picker and advisor-link are zero ongoing cost.
- **Bryant + 1 second school, ~600 students, spring 2027:** ~$10/month. Bookmarklet would also be cheap — it doesn't add Pathfinder-side compute.
- **5-school multi-tenant, ~5,000 students, fall 2027:** ~$80/month for chat input. Visual picker + advisor-link still negligible. Webview cookie-replay would dominate cost only if it triggers re-parses (Vision spend re-emerges, ~$0.04/parse × 5K students × 2x/yr = $400/yr).

The input layer is the cheapest part of the system at every scale.

---

## 8. The Single Highest-ROI Change

**Demote the paste/upload pair and ship the visual major-template picker as the homepage default.** Two engineering days. Cuts time-to-first-schedule from ~30 seconds (best case, working Vision) or "infinite" (when Vision fails or the student can't find their audit) to **three taps**. Zero ongoing cost. Zero FERPA exposure on the input side. Works on a phone. Works for a freshman who hasn't met with an advisor yet. Works for the demo Owen will give the Provost in two weeks.

The paste and upload paths stay live as power-user fallbacks behind a "Have a Degree Works audit?" disclosure. They don't get rebuilt; they just stop being the front door.
