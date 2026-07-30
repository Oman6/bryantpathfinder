# 05 — Hybrid and Accessibility Input Methods

> Subagent **I5** — BryantPathfinder input-method swarm. This brief evaluates alternative and accessible onboarding paths that complement the current "upload screenshot / paste text" flow. The bottom line, up front: the visual requirement picker (covered by sibling agents) should remain primary. The two secondaries worth investing in are **(1) an advisor-shared link** with a pre-filled requirement set, and **(2) a deeply accessible version of the existing upload zone**. Voice, OCR-on-device, email forwarding, PWA share targets, and QR codes are interesting but are skip / defer for the pre-pilot release.

---

## 1. Voice input — interesting demo, weak ROI

The freshman-walking-back-from-advising scenario is real but narrow. The student is outdoors, on cellular, often distracted, and trying to recall requirements they were just told. A voice channel can absorb this, but it duplicates what the visual major template (sibling agent I3's "ticket-and-untick the requirements" flow) already does in two taps.

**Web Speech API (`SpeechRecognition`).** Built into Chromium and Safari. Free. Caveat: Chrome streams audio to Google's servers; only `SpeechSynthesis` works fully offline. Per `caniuse`, the API is partially supported on Chrome 25–145 and Safari 14.1–26.2; **Firefox does not support it at all**, and the cross-browser score is roughly 50/100. Latency is acceptable for free dictation but not for conversational turn-taking. ([MDN — Using the Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API/Using_the_Web_Speech_API), [caniuse — Speech Recognition](https://caniuse.com/speech-recognition))

**Hosted streaming STT.** AssemblyAI Universal-3 Pro reports P50 ~150 ms / P90 ~240 ms after voice-activity detection at $0.0025/min (~$0.15/hr) base. Deepgram Nova-3 is sub-300 ms at $0.0077/min (~$0.46/hr). OpenAI Realtime sits at 300–500 ms at $0.0077/min. ([AssemblyAI — Best APIs 2026](https://www.assemblyai.com/blog/best-api-models-for-real-time-speech-recognition-and-transcription), [Deepgram — Best STT APIs 2026](https://deepgram.com/learn/best-speech-to-text-apis-2026))

**Reality check for Pathfinder.** A 90-second dictation costs <$0.01. That's not the problem. The problems are: (a) the student must still confirm a structured requirement list afterwards, so voice only replaces the "select your major" step, which is two clicks; (b) Bryant's library and study spaces are quiet — students will not speak out loud to pick courses; (c) accuracy on terms like "FIN 4XX" and "LCS-7" is poor without a domain-tuned vocabulary.

**Verdict: skip for pilot.** Re-evaluate only if the visual picker user-tests poorly. If it ships later, route through Web Speech API first (zero infra) and fall back to AssemblyAI streaming for Firefox/Edge users — total integration ~2 days.

---

## 2. Mobile camera OCR — already solved by Claude Vision

The current Vision call (Claude Sonnet 4.5) measured ~95% accurate on Owen's audit (per `00-product-baseline.md`). The four alternatives:

- **Apple Live Text** — iOS 15+, free, on-device, no API key. Cannot be invoked programmatically from a webpage; the user long-presses an image to copy text. Quality on dense text matches or beats Google's on-device OCR. ([Fritz — Comparing Apple's and Google's on-device OCR](https://heartbeat.fritz.ai/comparing-apples-and-google-s-on-device-ocr-technologies-fc5c7becf9f0))
- **Google ML Kit Text Recognition** — Android-native, free, on-device. ML Kit "outclassed Tesseract on many predictions" (per the Fritz benchmark) and was perfect on 316 images where Tesseract failed entirely. Web access requires a wrapper app. ([Fritz — ML Kit Text Recognition iOS vs Android](https://fritz.ai/comparing-ml-kits-text-recognition-api-on-android-ios/))
- **Tesseract.js** — Pure JavaScript, runs in-browser, works everywhere but is the slowest and least accurate of the four. On Bryant grade-distribution PDFs (small condensed text, multiple columns), Tesseract regularly drops course codes. Cold-start of the WASM model is 8–15 seconds on mid-range Android. ([IntuitionLabs — Modern non-LLM OCR engines](https://intuitionlabs.ai/articles/non-llm-ocr-technologies))
- **Cloud OCR (Google Document AI, AWS Textract, Mathpix)** — 98%+ accuracy on clean text but adds another vendor, another bill, and another data-privacy review. Google Cloud Vision OCR hits 98% accuracy on standard benchmarks. ([AIMultiple — OCR accuracy](https://aimultiple.com/ocr-accuracy))

**Quality difference vs. Claude Vision.** Claude is doing more than OCR — it is *interpreting* the audit (matching "Still Needed: 1 Class in FIN 4XX" to a structured requirement object). On-device OCR returns a flat string blob that Pathfinder would still need to send to Claude (or a regex parser) for semantic extraction. The double-hop adds latency and a failure mode without removing the LLM dependency.

**Verdict: skip.** Claude Vision is the right primitive. Mobile users should screenshot, then upload — same as desktop. The one thing worth adding is iOS-native HEIC support; Pathfinder currently rejects HEIC because the FastAPI image cap is set on the base64 payload. Convert HEIC → JPEG client-side before upload (`canvas.toBlob`).

---

## 3. Advisor-shared link — the highest-ROI secondary channel

This is the strongest commercialization-aligned input method. The Bryant Office of Advising already meets one-on-one with every student. If the advisor sees Pathfinder *first*, they generate a token, hand the URL to the student, and onboarding collapses from "screenshot → upload → confirm 16 requirements" to "open link → see 3 schedules."

**Mechanics.** Advisor logs in to a thin advisor-portal route (`/advisor`). Selects a student (or pastes the audit text once). Server creates a single-use token (UUID v4, 24-hour TTL) keyed to a JSON blob of the parsed audit. Returns `pathfinder.app/start?token=...`. Token is consumed on first GET; thereafter the audit lives in browser-side Zustand only.

**Why it wins for Pathfinder specifically:**
- **Trust.** The advisor is the source of truth. There is no Vision parse to validate.
- **No screenshot.** Removes the messy step that produced 5% of the parse errors.
- **Demo-friendly.** A 30-second demo: "advisor clicks button, student opens link, schedules appear."
- **Compliance fit.** Aligns with the FERPA "school official" framing — Bryant staff initiated the data flow.
- **Effort:** ~1 day to ship. One Pydantic model (`OnboardingToken`), one route (`POST /api/advisor/share`, `GET /api/onboarding/{token}`), in-memory dict with TTL eviction. No database needed for the pilot.

**Tradeoff.** Requires an advisor to know about Pathfinder — implies the sales motion is bottom-up to the advising office, not top-down to the registrar. That matches Owen's actual access at Bryant.

**Verdict: build for pilot.** This is the single most-leveraged input method given the founder's existing relationships.

---

## 4. QR code pattern — almost-free addition to (3)

Once advisor-shared links exist, QR is a render-time addition. Server returns the URL plus a `<canvas>` QR using the `qrcode` npm package. Advisor prints the next-semester plan handout with the QR in the corner. Student scans on the way out.

EDUCAUSE and Faculty Focus both report QR onboarding adoption is rising in higher ed — common uses are office-door office-hours codes and orientation-packet links. ([EDUCAUSE — 8 Ways to Use QR Codes in Higher Education](https://er.educause.edu/articles/2022/8/8-ways-to-use-qr-codes-in-higher-education-classrooms), [Faculty Focus — QR Codes for Student Engagement](https://www.facultyfocus.com/articles/effective-teaching-strategies/qr-codes-for-quick-student-engagement/))

**Effort:** ~2 hours, on top of (3). Add `qrcode` to the advisor portal, render alongside the URL.

**Verdict: ship as a side-effect of (3).** Zero marginal cost. Useful for the lowest-tech advisors who would rather print than email.

---

## 5. Email forwarding — defer

`student forwards advisor's email → parse@pathfinder.app → SES/Postmark webhook → Claude extracts → reply with confirm-link`.

**Cost.** Postmark inbound is $15/mo for 10K emails combined I/O, attachments capped at 10 MB per message and 35 MB total. AWS SES inbound is $0.10/1K plus S3 storage — cheaper but requires self-management of reputation and S3 plumbing. ([Postmark — Inbound webhook](https://postmarkapp.com/developer/webhooks/inbound-webhook), [Postmark — Inbound Email Pricing](https://postmarkapp.com/inbound-email))

**Pros.** Fully channel-agnostic. Works on locked-down student devices.

**Cons.**
- Async UX. Student forwards, then waits, then opens a reply, then clicks a link. That's 3 round-trips vs. one click for the advisor link.
- Spoofing risk. Anyone can forge a "From: advisor@bryant.edu" email. Need DKIM+SPF verification, which is doable but adds a day.
- The email content is unpredictable. Advisors don't write structured plans — they write "Take FIN 310 next, then 320 in spring." Now Claude is parsing two formats: Degree Works exports *and* free-text emails. Two failure surfaces.
- Adds a vendor and a recurring bill before there's revenue.

**Verdict: defer until 2+ pilot schools are paying.** The advisor-link covers 90% of the value at zero infra cost.

---

## 6. PWA + Web Share Target — defer until installs exist

The Web Share Target API lets an installed PWA appear in the iOS/Android share sheet so a student can share a screenshot directly into Pathfinder without a file picker. Manifest-side: declare `share_target` with `method: "POST"`, `enctype: "multipart/form-data"`, and a files parameter accepting `image/*` and `application/pdf`. ([MDN — share_target Manifest Reference](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest/Reference/share_target), [W3C — Web Share Target](https://w3c.github.io/web-share-target/))

**Constraint.** The PWA must be installed first. Android/Chrome supports this fully; iOS Safari support is partial and unreliable for files. ([MDN — Share data between apps](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/How_to/Share_data_between_apps))

**Reality.** Pathfinder is a once-or-twice-per-semester tool. Students will not install a PWA for that frequency. The share-sheet path is cute but the installation prerequisite kills it. Revisit only if usage becomes monthly (the multi-semester planner is the closest existing feature; if students return to revise their plan, then PWA install becomes plausible).

**Verdict: skip.** Add a `manifest.json` with the right metadata so the option exists, but do not invest in the share-target POST handler until PWA-install metrics justify it. Total cost of adding the manifest: 30 minutes.

---

## 7. Accessibility — under-invested, easy to fix

The baseline claims WCAG AA contrast and keyboard navigation. That is a partial answer. The current "Paste text / Upload image" tabset and dropzone need a structured pass.

### 7.1 Screen reader — what NVDA/VoiceOver/JAWS hears today

The `Tabs` from shadcn/ui render as `role="tablist"` with `role="tab"` children — that part is fine. The drop zone, however, is a `<div>` with `onDrop` handlers. NVDA reads it as a "group" with the dropzone label, and the actual `<input type="file">` is visually hidden but focusable. That works but is not announced clearly. **Fixes:**

- Add `aria-label="Upload Degree Works screenshot"` to the input.
- Add `aria-describedby` pointing at a paragraph that says "PNG, JPG, or PDF, up to 10 MB. Drop a file here or press Enter to choose one."
- Add a visible "Browse files" button (currently only the dropzone text is clickable). This also satisfies WCAG 2.5.7 (see below).

### 7.2 Keyboard — focus management

- The dropzone must be reachable in tab order. Currently the hidden `<input>` is — verify it's not `tabindex="-1"`.
- After a successful upload, focus must move to the parsed-requirements list so screen reader users don't get stranded.
- The "Use sample audit" button must have a visible focus ring meeting 2px / 3:1 contrast (WCAG 2.4.11/2.4.12).

### 7.3 WCAG 2.5.7 Dragging Movements (Level AA, new in WCAG 2.2)

"All functionality that uses dragging movements for operation can be achieved by a single pointer without dragging, unless dragging is essential." The native `<input type="file">` is exempt — but Pathfinder's dropzone is a custom-built component. **Mitigation:** the existing "Browse files" button is the single-pointer alternative; just ensure it's visible, not just an invisible overlay. ([TestParty — WCAG 2.5.7 Dragging Movements 2025 Guide](https://testparty.ai/blog/wcag-2-5-7-dragging-movements-2025-guide), [AccessiCart — WCAG 2.2 SC 2.5.7](https://accessicart.com/wcag-2-2-aa-sc-2-5-7-dragging-movements/))

### 7.4 Low vision / motor / cognitive

- **Low vision.** The warm-cream `#FAFAF7` on `#1A1A1A` is 17:1 — well over AA's 4.5:1 and AAA's 7:1. Verify the gold `#B8985A` on cream meets 4.5:1 for button text (it does for large text only — keep CTAs at ≥18px or 14px bold).
- **Font scaling.** Test 200% zoom and 400% zoom (WCAG 1.4.4 / 1.4.10). The asymmetric editorial layout collapses ungracefully at 400% if the left-hand serif headline isn't allowed to wrap.
- **Motor.** WCAG 2.5.5 (target size, AAA) and 2.5.8 (target size minimum, AA, 24×24 CSS pixels) — pill buttons must be ≥24px tall in interactive area. The current `py-2` Tailwind class produces 32px, which clears the bar.
- **Cognitive load.** The 16-requirement list on the preferences page is overwhelming on mobile. Group by area (Major / Core / General Ed) with `<details>` disclosure widgets. Progressive disclosure is the WCAG-aligned pattern. ([Filestack — HTML File Upload Accessibility](https://blog.filestack.com/html-file-upload-accessibility/))

**Effort:** ~1 day total — about 80% of which is verification (axe-core, Lighthouse, manual NVDA pass), 20% is the focus-management fix and the disclosure widget.

**Verdict: build for pilot.** This is the single most under-invested area. Higher ed institutions have hard accessibility procurement requirements; without an explicit pass, any pilot at a second school will be blocked at IT review.

---

## 8. Multi-modal hybrid — the synthesis

The strongest user flow combines (3) the advisor-link primary, with two graceful fallbacks:

1. **Advisor link.** Student arrives at `/start?token=...`. Audit pre-loaded. Skip directly to preferences.
2. **No token? Visual picker.** "I'm a sophomore Finance major" → major template loads → student ticks/unticks specific requirements. (This is sibling agent I3's territory, not mine.) The major template is a static JSON keyed off Bryant's catalog. No Vision call. Sub-second.
3. **Power user? Upload.** The current Vision-screenshot path stays for transfer students, double majors, and edge cases the visual picker can't represent.

A small "tell us in your own words" textarea on the preferences page can absorb the natural-language preferences ("no 8 a.m.s, please") that the structured controls miss. Claude already handles the free-text preference field.

This is the Pareto-optimal layout: each channel is the best path for its user segment. **Voice, OCR-on-device, email forwarding, and PWA share targets are not.**

---

## 9. Ranked recommendation

| # | Method | Verdict | Effort | Why |
|---|---|---|---|---|
| 1 | Visual major-template picker (sibling I3) | **Primary — ship** | (out of scope) | Lowest friction for ~80% of students |
| 2 | Advisor-shared link + QR | **Secondary — ship** | 1 day | Highest trust, pilot-aligned, FERPA-clean |
| 3 | Existing screenshot + paste fallback (already built) | **Secondary — keep, accessibility-harden** | 1 day | Necessary for transfers, edge cases |
| 4 | WCAG 2.2 AA accessibility pass | **Cross-cutting — ship** | 1 day | Procurement gate at any second institution |
| 5 | PWA `manifest.json` (no share target handler yet) | **Stub — ship** | 30 min | Lets future install metrics inform investment |
| 6 | Voice input | Skip | 2 days | Duplicates picker, environment-hostile |
| 7 | Mobile on-device OCR | Skip | 1 week | Claude Vision already covers this |
| 8 | Email forwarding inbox | Defer | 1 week + $15/mo | Async UX, parsing-surface explosion, vendor |
| 9 | Web Share Target full handler | Defer | 2 days | Requires PWA install — frequency is wrong |

**Composition for the pilot:** **visual picker (primary) + advisor link (secondary) + accessibility-hardened upload fallback (tertiary).** Skip everything else until pilot data justifies it.

---

## Sources

- [MDN — Using the Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API/Using_the_Web_Speech_API)
- [caniuse — Speech Recognition API](https://caniuse.com/speech-recognition)
- [AssemblyAI — Best APIs and models for real-time STT 2026](https://www.assemblyai.com/blog/best-api-models-for-real-time-speech-recognition-and-transcription)
- [Deepgram — Best Speech-to-Text APIs 2026](https://deepgram.com/learn/best-speech-to-text-apis-2026)
- [Fritz — Comparing Apple's and Google's on-device OCR](https://heartbeat.fritz.ai/comparing-apples-and-google-s-on-device-ocr-technologies-fc5c7becf9f0)
- [Fritz — Firebase ML Kit Text Recognition iOS vs Android](https://fritz.ai/comparing-ml-kits-text-recognition-api-on-android-ios/)
- [IntuitionLabs — Modern non-LLM OCR engines](https://intuitionlabs.ai/articles/non-llm-ocr-technologies)
- [AIMultiple — OCR accuracy benchmarks](https://aimultiple.com/ocr-accuracy)
- [MDN — share_target manifest reference](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest/Reference/share_target)
- [W3C — Web Share Target](https://w3c.github.io/web-share-target/)
- [MDN — Share data between apps (PWA)](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/How_to/Share_data_between_apps)
- [Postmark — Inbound webhook docs](https://postmarkapp.com/developer/webhooks/inbound-webhook)
- [Postmark — Inbound email pricing](https://postmarkapp.com/inbound-email)
- [TestParty — WCAG 2.5.7 Dragging Movements 2025 guide](https://testparty.ai/blog/wcag-2-5-7-dragging-movements-2025-guide)
- [AccessiCart — WCAG 2.2 SC 2.5.7](https://accessicart.com/wcag-2-2-aa-sc-2-5-7-dragging-movements/)
- [Filestack — HTML file upload accessibility with WCAG and ARIA](https://blog.filestack.com/html-file-upload-accessibility/)
- [EDUCAUSE — 8 Ways to Use QR Codes in Higher Education Classrooms](https://er.educause.edu/articles/2022/8/8-ways-to-use-qr-codes-in-higher-education-classrooms)
- [Faculty Focus — QR Codes for Quick Student Engagement](https://www.facultyfocus.com/articles/effective-teaching-strategies/qr-codes-for-quick-student-engagement/)
- [BryantPathfinder product baseline (00-product-baseline.md)](../commercialization/00-product-baseline.md)
