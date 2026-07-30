# I4 — Browser Extension / Bookmarklet / Userscript / Share-Target PWA

> Research subagent for the BryantPathfinder input-method swarm.
> Question: can the student parse their Degree Works audit *in their own browser*, so the audit text never leaves their machine in raw form, and only structured (or even minimized) data hits Pathfinder's API?
>
> **Recommendation in one line:** ship a **bookmarklet** as the v1 in-browser ingestion path, with a **Manifest V3 Chrome extension** as the v2 polished install once Pathfinder has a real domain and a public Privacy Policy. Skip the userscript path entirely. Treat the **Web Share Target PWA** as a *complement* for the mobile-PDF flow, not a replacement.

---

## 1. Why this matters: the FERPA story

Today's flow uploads a Degree Works screenshot to FastAPI, which base64-encodes it and forwards it to Anthropic's Vision API. The image embeds the student's full legal name, Bryant ID number, cumulative GPA, advisor name, and every grade they've ever received. That image is then transmitted to a third-party LLM provider. Even with a Zero-Data-Retention agreement, the audit content still leaves the student's machine in unredacted form, traverses Pathfinder's backend, and hits a non-school subprocessor.

Every in-browser parsing path in this document is materially better on FERPA grounds because the audit DOM is parsed *inside the student's authenticated session* and the only thing transmitted to Pathfinder is structured JSON: a list of unmet requirement codes, a target-credits value, and (optionally) the student's intended major. Names, IDs, GPAs, and grade history are stripped at the source. That is the difference between "we send your audit screenshot to Anthropic" and "we never see your audit." For a school's General Counsel that is not a marginal improvement, it is a categorical one.

---

## 2. Browser-extension fundamentals (Manifest V3)

### MV3 is the only option going forward

Chrome's Manifest V2 phase-out moved from pre-stable channels in June 2024 (Chrome 127) into stable in October 2024, with the Chrome Web Store removing remaining MV2 listings by June 2025. Enterprise policy (`ExtensionManifestV2Availability`) was the last grandfathering escape, and that expired mid-2025. Any extension Pathfinder ships in 2026 must be Manifest V3. ([Chrome MV2 deprecation timeline](https://developer.chrome.com/docs/extensions/develop/migrate/mv2-deprecation-timeline), [Chromium Blog: Manifest V2 phase-out begins](https://blog.chromium.org/2024/05/manifest-v2-phase-out-begins.html))

### Permissions model

The two relevant primitives are `activeTab` and `host_permissions`. ([Declare permissions — Chrome for Developers](https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions))

- **`activeTab`** grants temporary host access *only* when the user explicitly invokes the extension (clicks the toolbar icon, hits a configured shortcut, or selects a context-menu item). The grant lives for the current tab navigation. There is no install-time host warning. This is the lowest-friction permission model and the right default for Pathfinder.
- **`host_permissions: ["https://degreeworks.bryant.edu/*"]`** grants persistent access to specified hosts. This shows the install-time scary "This extension can read and change your data on degreeworks.bryant.edu" prompt. Required only if Pathfinder needs to scrape on every visit without a user click — which it does not.

Pathfinder's extension should request `activeTab` plus `scripting` plus nothing else. The student is on the audit page, clicks the Pathfinder toolbar icon, the content script runs once, scrapes the DOM, POSTs to Pathfinder, done. No persistent monitoring. No background listeners on the Bryant domain. This is the version of the install prompt most likely to be approved by a campus IT-security review.

### Content scripts vs. service workers

Manifest V3 replaces the long-lived background page with an event-driven **service worker** that is suspended when idle. ([Content scripts — Chrome for Developers](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts)) Pathfinder's split:

- **Content script** (`scrape.js`) — runs in the Bryant page context. Reads the rendered Degree Works DOM, normalizes the audit into the same `DegreeAudit` Pydantic shape the FastAPI backend already expects, and posts a message to the service worker.
- **Service worker** (`sw.js`) — receives the structured JSON from the content script, and does the cross-origin `fetch` to `https://api.pathfinder.app/api/parse-audit-from-extension`. The Bryant page's CSP cannot interfere with a fetch made from the extension's own context, which is the whole reason to relay through the worker rather than `fetch` directly from the content script.

### Distribution

| Store | Fee | Review time | Notes |
|---|---|---|---|
| Chrome Web Store | $5 one-time developer fee | 1–3 business days for simple extensions; longer for sensitive permissions | One fee covers all extensions you publish under that account ([Register your developer account](https://developer.chrome.com/docs/webstore/register)) |
| Firefox Add-ons (AMO) | Free | Hours to days; auto-signed for many submissions | Mozilla's MV3 timeline diverges — Firefox still allows MV2 alongside MV3 |
| Microsoft Edge Add-ons | Free | 1–7 days | Edge accepts Chrome MV3 packages with minor manifest tweaks |

**Realistic time-to-ship for Pathfinder's extension:** 1–2 days of engineering for the manifest, content script, and service-worker plumbing; another half-day for the store listing (icons in 5 sizes, screenshots, a privacy policy URL, justification for each permission). Plus the 1–3 day Chrome review queue. Total wall-clock from first commit to "available in the store": about a week, conservatively.

---

## 3. The bookmarklet path

A bookmarklet is a single `javascript:`-URL bookmark the student drags to their bookmarks bar. When clicked on the Degree Works page, it executes against the page DOM. ([Bookmarklet — Wikipedia](https://en.wikipedia.org/wiki/Bookmarklet))

**Pros**

- **Zero install friction.** No store account, no review queue, no $5 fee, no IT-security approval. Owen pushes a one-line update by editing a snippet on the Pathfinder site.
- **Works on every browser.** Chrome, Edge, Firefox, Safari, Brave, Arc.
- **No persistent permissions.** The script runs only when the student clicks. There is no install-time scary prompt. Privacy posture is excellent because there is literally nothing installed.
- **Trivially auditable.** A 30-line script is something a curious student or campus IT reviewer can read in five minutes. An extension package is an opaque ZIP.

**Cons**

- **CSP can block it.** Modern Content Security Policy headers can prevent bookmarklets from running. CSP 1.0 originally recommended exempting user-installed bookmarklets, but CSP 1.1 weakened "should" to "may," and major browsers now generally enforce CSP against bookmarklets. Sites like GitHub, Twitter, and MDN demonstrably block them. ([Bookmarklets affected by CSP — bugzilla.mozilla.org](https://bugzilla.mozilla.org/show_bug.cgi?id=866522), [Bookmarklets are Dead — Instapaper engineering](https://medium.com/making-instapaper/bookmarklets-are-dead-d470d4bbb626), [SOCRadar: CSP Bypass via Bookmarklets](https://socradar.io/csp-bypass-unveiled-the-hidden-threat-of-bookmarklets/))

  *This is the empirical question that decides v1.* If `degreeworks.bryant.edu` ships a strict `Content-Security-Policy` header that blocks `unsafe-inline` and external `connect-src`, the bookmarklet is dead and we go straight to the extension. If the header is lax (which is common for older Ellucian responsive-dashboard deployments), the bookmarklet works. **Action item before committing:** open Degree Works in DevTools, look at the response headers on the audit page, and read off the `Content-Security-Policy` and `connect-src` directives.

- **UX is rough.** Students must drag a button to the bookmarks bar — a maneuver many students under 22 have literally never performed. Some browsers hide the bookmarks bar by default. Mobile Safari and mobile Chrome do not support bookmarklet execution from the bookmarks bar at all. So bookmarklets are a desktop-only path.

- **Discoverability.** A bookmark is invisible until invoked. There is no toolbar icon advertising "Pathfinder is ready."

### Minimum-viable bookmarklet skeleton

```javascript
javascript:(async () => {
  try {
    const root = document.querySelector('[data-test="audit-block"]')
              || document.querySelector('.audit, #auditTable, main');
    if (!root) throw new Error('Audit not found — open the Degree Works audit view first.');

    const requirements = [...root.querySelectorAll(
      '[data-test="requirement-row"], .requirement-row, tr.req'
    )]
      .filter(r => /Still needed|Not Started|Incomplete/i.test(r.textContent))
      .map(r => (r.textContent || '').replace(/\s+/g, ' ').trim());

    const major = (document.querySelector('[data-test="major"], .student-major')
                   ?.textContent || '').trim();

    const r = await fetch('https://api.pathfinder.app/api/parse-audit-from-browser', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source: 'bookmarklet', major, requirements })
    });
    if (!r.ok) throw new Error('Pathfinder API ' + r.status);
    const { redirect } = await r.json();
    window.open(redirect, '_blank');
  } catch (e) {
    alert('Pathfinder: ' + e.message);
  }
})();
```

This is intentionally tiny. The selectors are placeholders — they must be confirmed against the live Bryant Degree Works DOM (see §5). The shipped bookmarklet would be minified to a single line, URL-encoded, and wrapped in `javascript:` for the `href` attribute of the install button on Pathfinder's homepage.

### Student install flow (4 steps)

1. On `pathfinder.app/install`, the student sees a button labeled **"Drag this to your bookmarks bar"**.
2. They drag it. (One-time action.)
3. They open `degreeworks.bryant.edu` and load their audit.
4. They click the **Pathfinder** bookmark. The page parses, POSTs, and a new tab opens at `pathfinder.app/preferences` with their requirements pre-populated.

---

## 4. The userscript path (Tampermonkey / Violentmonkey / Greasemonkey)

A userscript is a JavaScript file managed by a userscript-manager extension. The manager handles match patterns, auto-injection, and updates. ([Violentmonkey](https://violentmonkey.github.io/), [Greasy Fork](https://greasyfork.org/en))

**Honest assessment:** this is the wrong path for Pathfinder. The audience is Bryant *undergraduates*, the median of whom has never installed a browser extension at all, much less a meta-extension that loads scripts from a third-party developer URL. The pre-requisite "first install Tampermonkey, then add this script" is a two-step climb where the bookmarklet is one step and the Pathfinder extension is one step. Userscripts are great for the small power-user slice of any audience; they are *terrible* for non-technical students. The only scenario where a userscript makes sense is if Pathfinder targets a specific niche — say, computer-science students at multiple campuses — and wants to ship one script that auto-runs across `*.degreeworks.*` domains. That is a v3 concern, not a v1 concern.

---

## 5. What to scrape: the Bryant Degree Works DOM

I could not directly probe `degreeworks.bryant.edu` from this research environment — the host blocks unauthenticated requests outside the campus network, which is itself a useful data point: only an authenticated student session can see the audit, which is the security property we want.

What is publicly knowable:

- Bryant runs **Ellucian Degree Works**, specifically the **Responsive Dashboard** (the modern card-based UI that replaced the older Java-applet "Classic Dashboard" around 2018–2019). ([Ellucian Degree Works — product page](https://www.ellucian.com/solutions/ellucian-degree-works), [Rowan University — Responsive Dashboard manual](https://sites.rowan.edu/registrar/_docs/degreeworks_responsive-dashboard_manualfinal.pdf), [ECU — Responsive Dashboard upgrade](https://registrar.ecu.edu/wp-content/pv-uploads/sites/166/2018/01/Degree-Works-Responsive-Dashboard-Upgrade.pdf))
- The Responsive Dashboard is a single-page application that hits an internal API (often documented as `DwApiGuide` from Ellucian — surfaced on Utah State's ServiceNow). It renders the audit client-side from JSON, which is good news for scraping: the data is already in the DOM as structured rows.
- The likely audit URL is `https://degreeworks.bryant.edu/responsiveDashboard/worksheets/WEB31` or similar — the Banner-and-DegreeWorks convention is `/responsiveDashboard/` followed by the worksheet template ID.
- Useful selectors to look for on first inspection (these are common across Ellucian deployments but should be confirmed):
  - `mat-card[data-test="block"]` — Material Design card wrapping each requirement block (Major, Concentration, General Education).
  - `.requirement` rows with `.status` children whose text is `Still Needed`, `Complete`, `In-Progress`, `Not Started`.
  - `.choice` and `.advice` elements — the natural-language requirement text ("Choose one of FIN 370, FIN 371, FIN 380").
  - `.studentInfoHeader` or `[data-test="student-name"]` — the PII to *avoid* scraping.

The bookmarklet/extension only needs to read `.requirement.status="Still Needed"` rows and the embedded course wildcard text. Names, IDs, GPAs, and historical grades are intentionally *not* collected. This is the FERPA story in code: the data minimization is mechanical, not promised.

The accompanying `DwApiGuide` document confirms a JSON API behind the dashboard. ([DwApiGuide on USU ServiceNow](https://usu.service-now.com/sys_attachment.do?sys_id=c14216c7b80ca100496e01a3fbc299e6)) A sufficiently sophisticated content script could call the same authenticated XHR endpoint the SPA uses — bypassing DOM parsing entirely — using the student's existing session cookies. That is more robust to UI redesigns than DOM scraping. But it is also more legally exposed: scraping the rendered page is "automating what the student would do manually," whereas calling an undocumented JSON API is "interacting with a non-public Bryant system." For v1, stick to DOM scraping.

---

## 6. Auth flow and PII handling

Because the script runs in the authenticated browser context, the student's Bryant SSO cookies are already present. The script does not see them, does not transmit them, does not store them. The browser's same-origin policy keeps the cookies attached only to `degreeworks.bryant.edu` requests, and the cross-origin POST to `pathfinder.app` carries no Bryant credentials whatsoever.

Pathfinder's `/api/parse-audit-from-browser` endpoint receives:

```json
{
  "source": "bookmarklet",
  "major": "Finance",
  "requirements": [
    "Still needed: 1 class in FIN 4@",
    "Still needed: FIN 310",
    "Still needed: 1 class in LCS 1@ or LCC 2@"
  ]
}
```

That is the entire payload. No name, no Bryant ID, no GPA, no grade history. The Pydantic model on the FastAPI side rejects any field outside this allowlist; even if a future scraper accidentally captures more, the server discards it. **This is a meaningful, demonstrable data-minimization control that General Counsel can verify by reading the schema.**

Anthropic still gets called for the explanation step in §6 of the existing pipeline, but the data Anthropic sees is now `["FIN 4XX", "FIN 310", "LCS 1XX or LCC 2XX"]`, not "Owen Ash, ID 123456789, GPA 3.74, has completed FIN 201 with a B+, …". That is a categorical FERPA improvement.

---

## 7. Companion mode for Banner Self-Service

Bryant's section catalog comes from Banner SSB (`bannerprod.bryant.edu/StudentRegistrationSsb` is the conventional URL). Once Pathfinder has produced three schedules, the student goes to Banner and pastes CRNs into the registration cart. Today this is a manual copy-paste loop.

A natural v2 extension feature: when the content script detects it is on the Banner SSB registration page, it injects a **"Send my cart back to Pathfinder for conflict-check"** button. The script reads the CRNs the student has added, posts them to Pathfinder, and Pathfinder returns "Yes, this matches your saved schedule" or "Wait — CRN 12345 just dropped to 0 seats; here is the closest alternative." This is a meaningful upgrade because Banner's cart does not check against Degree Works requirements — it only checks Banner-internal prereqs and time conflicts. Pathfinder closes that loop.

This is a strong post-pilot feature, not a v1 demo feature. List it on the roadmap for the General Counsel meeting; do not ship it until the bookmarklet path is in 50 students' hands.

---

## 8. Web Share Target PWA — the mobile drop-in

The Web Share Target API lets an installed PWA register itself as a destination in the OS share sheet, alongside Mail, Messages, and Drive. ([share_target — MDN](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest/Reference/share_target), [W3C Web Share Target spec](https://w3c.github.io/web-share-target/)) On Android Chrome, a student can long-press the Degree Works PDF (which Bryant's Degree Works exports natively), tap **Share**, and pick **Pathfinder**. The PDF is uploaded directly to `pathfinder.app/api/parse-audit-pdf`, and the student lands on the preferences page.

**Support reality:**
- **Android Chrome:** supported. Requires the PWA to be installed first. ([Web Share API on Can I Use](https://caniuse.com/web-share))
- **iOS Safari:** **not supported.** Apple has not implemented Web Share Target despite years of bug-tracker activity. ([WebKit bug 194593](https://bugs.webkit.org/show_bug.cgi?id=194593)) iOS users can still install Pathfinder as a home-screen PWA, but the share-sheet route is closed; they would have to switch to "Open the PDF in Pathfinder via the in-app file picker" instead.
- **Desktop Chrome / Edge:** partial support; varies.

Bryant has a roughly 50/50 iPhone/Android student split, biased toward iPhone. So Web Share Target is a *complement* — it is the most elegant flow for the Android half and irrelevant for the iPhone half. Treat it as a v2.5 feature, after the desktop bookmarklet ships.

---

## 9. Privacy and FERPA upside, summarized

The single sentence Owen should be ready to say in front of campus IT or General Counsel:

> "When a student installs the Pathfinder browser extension, their audit text is parsed locally in their browser, and the only data that leaves their machine is a short list of unmet requirement codes — no names, no IDs, no GPAs, no grades. We can show you the source, and we can show you the network log."

This is a much stronger answer than "we use a SOC 2 vendor for OCR." It removes the audit's PII from the wire entirely. Combined with a school-official FERPA agreement, this is the configuration most likely to clear vendor security review at a second institution.

---

## 10. Honest cons (all paths)

- **Install friction.** Even a one-click bookmarklet drag is a step that a non-trivial fraction of students will not complete. Conversion will be lower than "upload screenshot." Owen should A/B test this on the Bryant pilot.
- **Single-machine.** A bookmarklet on the student's laptop does not help when they are on the library iMac or their roommate's Chromebook. Screenshot upload remains the universal fallback.
- **DOM brittleness.** Ellucian ships Degree Works updates that move CSS classes around. The selectors in §5 will break, sometimes silently. Pathfinder must (a) version the bookmarklet, (b) ship a "report a problem" button on the install page, and (c) have a one-tester smoke check against `degreeworks.bryant.edu` after every Ellucian release.
- **Trust ask.** "Install this Chrome extension I built" is a high-trust ask from a sophomore to fellow sophomores. The bookmarklet is much easier to vouch for ("here are the 30 lines, read them"); the extension is harder ("trust me, I'll publish the source on GitHub"). The MV3 store-review process partially compensates for this, but does not eliminate it.
- **Cross-browser testing burden.** Bookmarklets must be smoke-tested across Chrome, Safari, Firefox, Edge, Brave, and Arc. Extensions need separate review-and-submit cycles for Chrome Web Store, Firefox AMO, and Edge Add-ons. That is real ongoing maintenance.
- **No Safari iOS path.** Mobile iOS Safari does not run bookmarklets from the bookmarks bar in the same way as desktop, does not support extensions in the same model, and does not implement Web Share Target. The mobile-iPhone student will continue to rely on the screenshot-upload path until Apple changes its mind.

---

## 11. Recommendation

| Path | Recommendation | Reason |
|---|---|---|
| **Bookmarklet** | **Ship as v1.** | Zero install fee, zero review queue, lowest trust ask. Easiest to demo to General Counsel as "look, you can read every line." If CSP on `degreeworks.bryant.edu` blocks it, fall back to extension immediately. |
| **Manifest V3 Chrome extension** | Ship as v2 (week 2 of pilot). | Solves the CSP risk. Toolbar icon is more discoverable. $5 fee is trivial. Use `activeTab` only — no host_permissions, no install-time scary prompt. |
| **Userscript (Tampermonkey)** | **Skip.** | Wrong audience. Too many install steps. Maintain only if a power-user multi-school audience emerges. |
| **Web Share Target PWA** | Ship as v2.5 for Android. | Beautiful UX for Android-PDF flow. Useless on iOS. Worth ~1 day of engineering. |
| **Screenshot upload (today)** | Keep as the universal fallback. | Library iMacs, roommate Chromebooks, iPhone Safari. The lowest-friction worst-privacy option must remain available. |

The right end-state is **all four paths visible on the same homepage**, with the bookmarklet as the recommended default for desktop students and the screenshot upload as the always-available fallback. The page's copy should be honest: "The bookmarklet keeps your audit in your browser. The screenshot path uploads it to our servers. Pick what you're comfortable with."

That is a sentence a 19-year-old can make a real consent decision about, and it is also the sentence that wins the General Counsel meeting.

---

## Sources

- [Manifest V2 support timeline — Chrome for Developers](https://developer.chrome.com/docs/extensions/develop/migrate/mv2-deprecation-timeline)
- [Chromium Blog: Manifest V2 phase-out begins (May 2024)](https://blog.chromium.org/2024/05/manifest-v2-phase-out-begins.html)
- [Declare permissions — Chrome for Developers](https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions)
- [Content scripts — Chrome for Developers](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts)
- [chrome.scripting API reference](https://developer.chrome.com/docs/extensions/reference/api/scripting)
- [Manifest file format — Chrome for Developers](https://developer.chrome.com/docs/extensions/reference/manifest)
- [Register your developer account — Chrome for Developers](https://developer.chrome.com/docs/webstore/register)
- [Chromium Blog: Chrome Web Store registration fee (2020)](https://blog.chromium.org/2020/03/new-developer-dashboard-and.html)
- [Bookmarklet — Wikipedia](https://en.wikipedia.org/wiki/Bookmarklet)
- [Bookmarklets affected by CSP — bugzilla.mozilla.org #866522](https://bugzilla.mozilla.org/show_bug.cgi?id=866522)
- [Bookmarklets are Dead — Instapaper engineering on Medium](https://medium.com/making-instapaper/bookmarklets-are-dead-d470d4bbb626)
- [SOCRadar: CSP Bypass via Bookmarklets](https://socradar.io/csp-bypass-unveiled-the-hidden-threat-of-bookmarklets/)
- [Content Security Policy — MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CSP)
- [Violentmonkey — open-source userscript manager](https://violentmonkey.github.io/)
- [Greasy Fork — userscript repository](https://greasyfork.org/en)
- [share_target — MDN PWA manifest reference](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest/Reference/share_target)
- [Web Share Target API — W3C Editor's Draft](https://w3c.github.io/web-share-target/)
- [Web Share API support — Can I Use](https://caniuse.com/web-share)
- [WebKit bug 194593: Add support for Web Share Target API](https://bugs.webkit.org/show_bug.cgi?id=194593)
- [PWA on iOS — current status and limitations 2025 (Brainhub)](https://brainhub.eu/library/pwa-on-ios)
- [Ellucian Degree Works — product page](https://www.ellucian.com/solutions/ellucian-degree-works)
- [Rowan University — Degree Works Responsive Dashboard manual](https://sites.rowan.edu/registrar/_docs/degreeworks_responsive-dashboard_manualfinal.pdf)
- [ECU — Responsive Dashboard upgrade documentation](https://registrar.ecu.edu/wp-content/pv-uploads/sites/166/2018/01/Degree-Works-Responsive-Dashboard-Upgrade.pdf)
- [DwApiGuide v4.1.3 — Utah State ServiceNow attachment](https://usu.service-now.com/sys_attachment.do?sys_id=c14216c7b80ca100496e01a3fbc299e6)
- [Coursedog — Ellucian Degree Works integration docs](https://coursedog.freshdesk.com/support/solutions/articles/48001210598-ellucian-degreeworks-integration)
