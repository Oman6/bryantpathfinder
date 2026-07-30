# 02 — Conversational Input (Multi-Turn Chat)

**Question:** Should Pathfinder add a chat-based input path where students describe their requirements in natural language, and Claude extracts a structured `OutstandingRequirement[]` via tool use?

**Sources:**
- Anthropic Tool Use docs: https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview
- Anthropic Pricing docs: https://platform.claude.com/docs/en/about-claude/pricing
- Anthropic Prompt Caching docs: https://platform.claude.com/docs/en/build-with-claude/prompt-caching

---

## 1. Sample dialog

A realistic three-turn exchange between Pathfinder and a Bryant sophomore. The system prompt loads the Bryant catalog summary and the `OutstandingRequirement` schema; the assistant has one client-side tool, `submit_requirements`, which terminates the conversation by handing structured data to the FastAPI solver.

**Turn 1 — Student:**
> "I'm a finance sophomore, I still need FIN 310, a science with lab, and an LCS course."

**Turn 1 — Claude (text, no tool call yet):**
> "Got it — Financial Management (FIN 310, 3 cr) is locked in. For your science-with-lab, Bryant lets you choose any SCI course tagged with a lab section — for example BIO 111, CHEM 110, or ENV 250. Do you have a preference, or should I leave it open so the solver finds the best fit? And by 'LCS' do you mean the Literary & Cultural Studies general-ed bucket (LCS 100-level), or a specific course like LCS 280?"

**Turn 2 — Student:**
> "Open on the science. LCS — anything 200-level is fine, I just need the credit."

**Turn 2 — Claude (clarifying once more):**
> "Quick check: target 15 credits this term, and any preference on no-Friday or no-8am? I'll fold those into the search."

**Turn 3 — Student:**
> "15 credits, no Fridays."

**Turn 3 — Claude (calls the tool):**

```json
{
  "type": "tool_use",
  "id": "toolu_01R4q...",
  "name": "submit_requirements",
  "input": {
    "outstanding": [
      {"code": "FIN 310", "credits": 3, "rule_type": "exact"},
      {"code": "SCI_LAB", "credits": 4, "rule_type": "category", "category": "science_with_lab"},
      {"code": "LCS 2XX", "credits": 3, "rule_type": "wildcard", "pattern": "LCS 2"}
    ],
    "target_credits": 15,
    "preferences": {"no_friday": true}
  }
}
```

**Tool schema** (registered in `claude_client.py`, per Anthropic's `input_schema` format — a JSON Schema object passed in the `tools` array on the Messages API; Claude returns a `tool_use` content block with `stop_reason: "tool_use"` when it decides it has enough information):

```python
SUBMIT_REQUIREMENTS_TOOL = {
    "name": "submit_requirements",
    "description": "Submit the student's outstanding degree requirements once "
                   "all are confirmed. Call only after the student has named "
                   "every requirement and confirmed credit target.",
    "input_schema": {
        "type": "object",
        "properties": {
            "outstanding": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "credits": {"type": "integer"},
                        "rule_type": {
                            "type": "string",
                            "enum": ["exact", "wildcard", "category"]
                        },
                        "pattern": {"type": "string"},
                        "category": {"type": "string"}
                    },
                    "required": ["code", "credits", "rule_type"]
                }
            },
            "target_credits": {"type": "integer"},
            "preferences": {"type": "object"}
        },
        "required": ["outstanding", "target_credits"]
    }
}
```

---

## 2. Why chat beats paste/upload

**Three concrete advantages:**

1. **Lower friction for an unsure student.** A first-semester sophomore who has never opened Degree Works often does not know the difference between "LCS bucket" and a specific course code. Paste-text and screenshot upload both presuppose the student already has a structured list. Chat lets them start from "I think I need a science?" and get there.
2. **Asks clarifying questions in-flow.** Tool use lets Claude defer the `submit_requirements` call until it has every required field. Per Anthropic's tool-use docs, when a required parameter is missing, Claude (especially with explicit prompting) asks for it instead of guessing. The Vision parser, by contrast, has one shot and silently hallucinates on ambiguous text.
3. **Mobile-friendly.** The current Vision path requires a clean Degree Works screenshot — which Bryant's portal does not render well on iOS Safari. A chat input is just a textbox and works identically on phone and desktop. Half of demo-day visitors will pull out their phones.

**One concrete disadvantage:**

- **`rule_type` hallucination.** When a student says "any 200-level FIN," Claude may emit `pattern: "FIN 2*"`, `pattern: "FIN 2"`, or `pattern: "^FIN\\s2\\d{2}$"` — three different wildcards Pathfinder's `requirement_expander.py` reads differently. The solver then either silently filters too few sections (FIN 305 missing) or too many (FIN 4XX leaks in). The paste path forces the student to write the canonical token themselves; chat introduces a translation layer that can quietly fail.

---

## 3. Hybrid: chat + confirmation step

After Claude calls `submit_requirements`, do not run the solver yet. Render a confirmation card listing every extracted requirement as an editable checkbox row:

> **I think you need these — confirm or fix:**
> - [x] FIN 310 — Financial Management (3 cr) [exact match]
> - [x] Science w/ lab — any SCI course tagged `lab` (4 cr)
> - [x] LCS 2XX — any 200-level LCS (3 cr) [wildcard]
> - **Target:** 15 credits • **No Fridays:** yes
> [ Generate schedules → ]

Each row shows the `rule_type` in plain English ("exact match" / "any 200-level LCS"), plus an inline pencil icon to swap a wildcard for a specific course. This adds one click but eliminates the failure mode in §2: if Claude mis-extracts `LCS 2XX` as `LCS 200` (exact), the student catches it before 291 sections get filtered to one. It also gives the student agency — important for a school audience that has never trusted a black-box scheduler before. The card uses Pathfinder's existing double-bezel card pattern, so no new design work.

---

## 4. Cost / latency at pilot scale

**Assumptions** for a 50-student pilot, one schedule-generation session per student per semester (~one term):

- Model: `claude-sonnet-4-5` — base input $3 / MTok, cache read $0.30 / MTok, output $15 / MTok (per Anthropic pricing docs).
- Per session: 3 turns. Each turn sends the same ~1,500-token system prompt (tool schema 313 tokens + Bryant catalog summary + few-shot examples) plus the rolling conversation (~200 tokens new per turn).
- Output: ~150 tokens per turn (Claude's reply or the tool call).

**Math with prompt caching enabled** (the static 1,500-token prefix is cached on turn 1 and read on turns 2–3):

| Item | Tokens | Rate | Cost |
|---|---|---|---|
| Turn 1 cache write (1.25× base) | 1,500 | $3.75 / MTok | $0.0056 |
| Turn 1 fresh input | 100 | $3 / MTok | $0.0003 |
| Turns 2–3 cache reads (2 × 1,500) | 3,000 | $0.30 / MTok | $0.0009 |
| Turns 2–3 fresh input (2 × 200) | 400 | $3 / MTok | $0.0012 |
| Output (3 × 150) | 450 | $15 / MTok | $0.0068 |
| **Per-session total** | | | **~$0.0148** |

**50 students × $0.015 = ~$0.74 per pilot semester.** Round to **$1/month** including retry overhead. Negligible — a rounding error against the existing Vision spend.

**Latency:** Sonnet 4.5 typically returns a 150-token response in 2–3 s on a 1,500-token cached prefix; the 5-minute cache TTL covers a normal conversation, so turns 2 and 3 are noticeably faster than turn 1. End-to-end, three turns ≈ 7–9 s of model time, plus user typing — comparable to the Vision path's 4–5 s single-shot.

---

## 5. Recommendation

**Ship chat as a secondary input alongside the existing paste/upload paths, gated behind a "Talk it through" button on the homepage — not as the primary.** The hybrid confirmation step from §3 is mandatory; without it the `rule_type` hallucination risk is unacceptable for a demo where one wrong wildcard means a blank schedules page. Cost is trivial, mobile UX is a real win, and three input paths give the demo more recoverable failure modes — but the demo's hero flow remains "Use sample audit → preferences → generate," which must not change.
