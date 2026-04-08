# ADR 0002 — Claude Vision for Degree Audit Parsing

**Status:** Accepted
**Date:** 2026-04-08
**Deciders:** Owen Ash

---

## Context

The first step in the Pathfinder user flow is getting the student's degree audit into the system. Bryant uses Ellucian Degree Works, which presents audits as web pages inside the authenticated `dw-prod.bryantec.bryant.edu` portal. The audit contains dozens of "requirement blocks" — things like "Intermediate Corporate Finance" mapping to "1 Class in FIN 310" or "Financial Electives" mapping to "1 Class in FIN 370 or 371 or 380 or 465 or 466." The wildcard syntax (`@ 4@ with attribute = FIN`) makes manual transcription error-prone.

Pathfinder needs to get this data out of Degree Works and into a structured `DegreeAudit` object the solver can act on. The question is *how*.

The obvious answers all have problems. Scraping the Degree Works page requires authentication, which means either asking students for their Bryant credentials (a non-starter for a hackathon and probably a FERPA violation for production) or integrating with Bryant's SSO (a weeks-long project). The official Banner Ethos API covers course catalog data but does not expose degree audit rules in a queryable form — degree audits live in Degree Works, not Banner, and the two systems federate through nightly batch jobs. Asking students to manually type their outstanding requirements into a form would work but it kills the demo — the "wow" moment of Pathfinder is that the student never has to transcribe anything.

The remaining option is OCR or vision-based parsing: the student takes a screenshot of their Degree Works audit page, uploads it, and the system extracts the structured data from the image.

---

## Decision

Pathfinder uses Claude Vision (via the Anthropic API, model `claude-sonnet-4-5`) to parse Degree Works audit screenshots. The student uploads an image or PDF through the homepage upload zone. The backend base64-encodes the file, calls Claude with a prompt specifically tuned for Degree Works structure, and receives a strict JSON response matching the `DegreeAudit` Pydantic model.

The prompt includes two worked examples — one for a `specific_course` rule ("1 Class in FIN 310") and one for a `choose_one_of` rule ("1 Class in FIN 370 or 371 or 380 or 465 or 466") — so Claude has concrete templates for the Degree Works DSL. Temperature is set to 0 for deterministic parsing. The response is validated against the Pydantic schema before being returned to the frontend. One retry is attempted on malformed JSON; further failures return a clean error to the user.

---

## Consequences

### Positive

- **Zero IT integration.** Pathfinder works for any Bryant student today without asking Bryant IT to enable anything, provision API keys, or approve an OAuth app. The student controls their own data — they upload the screenshot themselves.
- **Works beyond Bryant.** Because Claude Vision is parsing visual structure rather than calling a Bryant-specific API, the same parser works on any Degree Works-using university with minor prompt adjustments. This is the long-term story for Pathfinder — 1,600+ universities use Degree Works, all of them with the same visual format.
- **The demo is a magic moment.** Drop in a screenshot, three seconds later a structured list of outstanding requirements appears on screen. Judges have all seen Degree Works before and immediately understand what just happened.
- **Handles the Degree Works DSL natively.** Claude can interpret `FIN 370 or 371 or 380`, `@ 4@ with attribute = FIN`, and `2 Classes in SCI 251 and L251` in a single parsing pass. A regex-based parser would need custom rules for each DSL construct and would break on the next Degree Works UI update.
- **Resilient to layout changes.** When Bryant updates Degree Works to a new template next year, Claude Vision still parses it correctly because it's reading structure semantically, not pattern-matching on HTML classes.

### Negative

- **Costs money per parse.** Each audit parse is one Claude Vision API call, roughly $0.02 at current pricing. For a hackathon demo this is trivial. At 10,000 students parsing audits monthly it becomes a line item. Mitigated by caching parsed audits by screenshot hash.
- **Latency is not zero.** A Vision call takes 2-4 seconds wall-clock. The demo is fast enough that this feels snappy, but students expect sub-second responses from web apps. The preferences page loading state covers most of this.
- **Hallucination risk.** Claude can theoretically invent a requirement that isn't in the audit. In testing against Owen's real audit this has not happened, but the risk is non-zero. Mitigated by showing the parsed requirements on the preferences page with checkboxes so the student can unselect anything wrong before generating schedules.
- **Authentication footprint on Claude.** The Anthropic API key lives on the backend. A production deployment needs proper secret management (not `.env` in git) and rate limiting to prevent abuse.
- **Requires the student to take a screenshot.** One step of friction. Future versions should support PDF export from Degree Works directly (which Degree Works does support).

### What failure looks like

If Vision parsing fails during the demo, Pathfinder falls back to a pre-loaded sample audit (`data/fixtures/audit_owen.json`) accessed via a "Use sample audit" button on the homepage. This is a deliberate architectural decision: the demo must not be single-pointed on a Claude API call that has a 1% chance of timing out or returning garbage. The fallback path is documented in `CLAUDE.md` under "Demo Path — What Has to Work."

---

## Alternatives Considered

**Traditional OCR (Tesseract) plus regex parsing.** Rejected because Degree Works audits contain structured information — hierarchies, rule operators, course options — that survives visual layout but doesn't survive flat OCR. Tesseract would give us a wall of text; the regex rules to recover structure from that text would be brittle, university-specific, and longer than the Vision prompt.

**Scraping the Degree Works HTML.** Rejected because the page is behind Bryant SSO. Automating the authenticated session would require handling Bryant credentials, which is both unethical for a hackathon and non-viable for production (FERPA concerns, credential storage requirements, session management). A headless browser approach would also be significantly slower and more fragile than Vision.

**Banner Ethos API integration.** Rejected because Ethos does not expose Degree Works audit rules. It exposes course catalog data (which Pathfinder does use via the static JSON) and student enrollment data, but not the degree plan structure. Ellucian sells that through a separate product.

**Asking students to manually enter their outstanding requirements.** Rejected because it kills the core demo moment. The whole point of Pathfinder is that the student doesn't have to transcribe anything. If we're asking them to type "I need FIN 310, GEN 201, a 400-level finance elective, and a gen ed capstone" into a form, we've built a glorified course filter, not a scheduling assistant.

**GPT-4V or Gemini Vision instead of Claude.** Not evaluated. This is a Claude hackathon. Claude Vision is the right tool for the building context regardless of benchmark comparisons.
