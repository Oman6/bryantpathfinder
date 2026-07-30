# 06 — AI & Search Augmentation

> Subagent A6 brief for the BryantPathfinder API swarm. Inputs: `00-product-baseline.md`. Question: beyond Anthropic Claude alone, which AI / search / embeddings / voice services would meaningfully improve Pathfinder, and where is the ROI? Currency = USD, prices verified April 2026.

---

## 0. Where Claude is doing the work today

Pathfinder already calls Claude Sonnet 4.5 (`claude-sonnet-4-5`) for three things: Vision-based audit parsing, the schedule-explanation paragraph, and the natural-language preferences pass that feeds the negotiator agent. Sonnet 4.5 is priced at **$3 / 1M input** and **$15 / 1M output** tokens, with a 200K-token context window and image input support ([Claude Sonnet 4.5 pricing — pricepertoken.com](https://pricepertoken.com/pricing-page/model/anthropic-claude-sonnet-4.5); [Claude API pricing — platform.claude.com](https://platform.claude.com/docs/en/about-claude/pricing)).

Claude Haiku 4.5 (~$1 / $5 per 1M tokens) is also imported but unused in the hot path. Three of Anthropic's own production features are *not* yet exploited: prompt caching, the Message Batches API, and tool use. Each of these is a near-zero-engineering, high-impact lever before Pathfinder reaches for a third-party vendor.

---

## 1. Anthropic-native features Pathfinder is leaving on the table

### 1.1 Prompt caching (highest ROI, lowest engineering cost)

Anthropic's prompt caching prices cache *writes* at 1.25× the base input rate (5-minute TTL) or 2× (1-hour TTL), and cache *reads* at **10% of the base input rate** ([Prompt caching docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching); [Anthropic API pricing 2026 — finout.io](https://www.finout.io/blog/anthropic-api-pricing)).

Pathfinder's explanation prompt and ranking prompt both pass the same static block: a system prompt plus the relevant subset of the 291-section catalog plus professor ratings. Concretely, on a Generate-Schedules run today, three Claude calls each re-tokenize the same ~6K-token preamble. With caching:

- 6,000 input tokens × $3 / 1M = **$0.018 per call** today (× 3 calls = $0.054 per generate).
- Cached: $0.018 × 1.25 once on the first write, then $0.018 × 0.10 = **$0.0018 per cached read** for the next two calls (and any further calls within 5 min).
- A 50-student-pilot day with 4 generates per student = 200 generates = 600 Claude-touched calls. Today that's ~$10.80/day in tokens; with caching it's ~$1.20/day on the static block. **About a 90% drop on the cached portion**, which matches the case study circulating in the community ([Lightfoot, Medium — $720→$72](https://medium.com/@labeveryday/prompt-caching-is-a-must-how-i-went-from-spending-720-to-72-monthly-on-api-costs-3086f3635d63)).

**Watch-out:** in early 2026 the *default* TTL silently regressed from 60 minutes to 5 minutes ([dev.to write-up](https://dev.to/whoffagents/claude-prompt-caching-in-2026-the-5-minute-ttl-change-thats-costing-you-money-4363)). For Pathfinder this is fine because the three calls in a single generate happen in parallel inside a 2-second window. For overnight batch re-rankings, request the 1-hour TTL explicitly.

**Engineering effort:** ~half a day. Add `cache_control: { type: "ephemeral" }` to the system block in `claude_client.py`. Zero new vendor.

### 1.2 Message Batches API (nightly re-ranking workloads)

The Batches API is **a flat 50% off both input and output tokens** with up to a 24-hour SLA, stackable with prompt caching ([Batch processing docs](https://platform.claude.com/docs/en/build-with-claude/batch-processing); [finout.io 2026 guide](https://www.finout.io/blog/anthropic-api-pricing)). Useless for the synchronous generate-schedules endpoint, but valuable for two future features:

- Nightly "what changed?" re-rankings as Banner sections open/close.
- Multi-semester planner pre-computes for every active student.

At the 50-student pilot scale, this turns a $30/month nightly job into a $15/month one. Engineering effort: ~1 day to refactor the multi-semester agent to write JSONL batch jobs.

### 1.3 Tool use / function calling

Today the solver runs once, deterministically, before Claude is consulted. With tool use, the **negotiator agent** could run in a Claude-driven loop: Claude proposes a relaxation ("drop no-Friday"), calls `solver.solve(audit, relaxed_prefs)` as a tool, sees the candidate count, and iterates until feasibility. This is a more honest implementation of the negotiator than the current "try a few hard-coded relaxations" heuristic. Engineering effort: ~2 days. No new vendor cost beyond the extra Claude calls (which prompt caching covers).

### 1.4 Files API and Computer Use — defer

The **Files API** is interesting only if Pathfinder accepts syllabus PDFs (not on the demo path). **Computer Use** for "auto-register the student in Banner" is technically possible but flagged as a usage-policy risk: Anthropic explicitly calls out scaled abuse and account compromise as elevated-harm areas ([Anthropic Usage Policy update](https://www.anthropic.com/news/usage-policy-update)). Worse, automating Banner clicks almost certainly violates Bryant's Acceptable Use Policy and Ellucian's terms. **Recommendation: do not ship Computer Use against Banner.** Output CRNs as copyable text (current behavior) and revisit only if a Bryant Registrar's office sponsors the pilot in writing.

---

## 2. Web search APIs — for grounding professor and course data

The headline use case: a student asks "is Prof X tough?" and RMP missed them. Pathfinder fans out to a fresh web search, summarizes via Claude, and surfaces the result. Six contenders:

| Provider | Cost / 1K queries | Latency | Notable |
|---|---|---|---|
| **Tavily** | $0 (1K/mo free), then $0.008/credit pay-as-you-go ([tavily.com pricing](https://www.tavily.com/pricing); [docs](https://docs.tavily.com/documentation/api-credits)) | ~1–2 s | LangChain default; AI-optimized result shapes |
| **Brave Search** | $5 / 1K Search; $4 / 1K Answers + tokens ([api-dashboard pricing](https://api-dashboard.search.brave.com/documentation/pricing); [implicator coverage of free-tier removal](https://www.implicator.ai/brave-drops-free-search-api-tier-puts-all-developers-on-metered-billing/)) | 200–400 ms | Independent index, no Google dependency |
| **Exa** | $3 / 1K searches; $7 / 1K with content + 10 results ([exa.ai/pricing](https://exa.ai/pricing); [changelog](https://exa.ai/docs/changelog/pricing-update)) | 400–800 ms | Embeddings-native; best for semantic intent |
| **Perplexity Sonar** | $1 / 1M tokens (Sonar Large) + $5–14 / 1K request fee ([Perplexity docs](https://docs.perplexity.ai/docs/getting-started/pricing); [aipricing.guru](https://www.aipricing.guru/perplexity-pricing/)) | 2–4 s | Built-in answer synthesis |
| **Serper** | $0.30 / 1K ($50/mo for 50K) ([serper.dev](https://serper.dev/)) | ~300 ms | Cheapest Google SERP scraper |
| **SerpAPI** | $15 / 1K dev tier; $5 / 1K at volume ([serpapi.com/pricing](https://serpapi.com/pricing)) | ~500 ms | Most mature legal posture |

**Recommendation:** start with **Tavily** for the agent-grounding path (1K/mo free covers the entire Bryant pilot) and **Serper** as a fallback for raw-Google needs. Skip Brave (no free tier as of Feb 2026) and Perplexity Sonar (the per-request fee plus 2–4 s latency blows the demo's 2-second budget). Exa becomes attractive only if Pathfinder builds the "find courses similar to FIN 310" feature — at which point its embeddings-native semantic search beats keyword search by a wide margin ([buildmvpfast 2026 search comparison](https://www.buildmvpfast.com/api-costs/ai-search)).

**FERPA posture:** none of these are zero-data-retention by default. The query "Prof X reviews" is not student PII, so the FERPA exposure is low. Do not pass audit content (which contains the student's name and ID) to a third-party search vendor.

---

## 3. Cross-checking / vendor-redundancy LLMs

The Claude Vision audit-parse path occasionally fails or hallucinates. A second-opinion check before accepting the parse is cheap insurance.

- **OpenAI GPT-4.1** with structured outputs: $2 / $8 per 1M, 1M-token context, native JSON-schema enforcement ([OpenAI pricing](https://developers.openai.com/api/docs/pricing); [pecollective 2026](https://pecollective.com/tools/openai-api-pricing/)). Slightly cheaper than Sonnet 4.5 on input. Run as a parallel call; if the two parses disagree on requirement count or course codes, fail closed and prompt the user.
- **Google Gemini 2.5 Pro**: $1.25 / $10 per 1M (under 200K context), multimodal, 1M-token window ([Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)). Cheapest of the three flagships for vision input.
- **Mistral / Cohere Command** as commodity fallbacks — useful only if Anthropic outage tolerance becomes a procurement requirement.

**Recommendation:** add **GPT-4.1** as a structured-output cross-check on the audit-parse path only. Gate it behind `ENABLE_VISION_CROSSCHECK` env flag so the demo can stay single-vendor when convenient. Engineering effort: ~1 day. Cost: <$0.01 per audit parse, paid only on the ingest path (low volume).

---

## 4. Embeddings + vector search

Use cases that justify embeddings in Pathfinder:

1. **"Find a class like FIN 310 but easier"** — semantic similarity over course descriptions weighted by historical workload + grade-distribution data.
2. **"Professors with similar teaching styles"** — review-tag clustering across the 110 instructors with RMP tag data.
3. **Free-text preference parsing fallback** — if a student writes "I want a chill quant class on Tuesdays," embed against course descriptions for shortlist before the solver runs.

### 4.1 Embedding model choice

| Model | Cost / 1M tokens | Dim | Notable |
|---|---|---|---|
| **OpenAI text-embedding-3-small** | $0.02 ([helicone calculator](https://www.helicone.ai/llm-cost/provider/openai/model/text-embedding-3-small)) | 1536 | Cheapest reputable option |
| **OpenAI text-embedding-3-large** | $0.13 ([embeddingcost.com](https://embeddingcost.com/openai)) | 3072 (truncatable to 256) | Best OpenAI quality; truncation keeps 95% quality at 12× less storage |
| **Voyage 3.5 / 3-large** | $0.06–$0.18 ([Voyage pricing](https://docs.voyageai.com/docs/pricing)) | 1024 / 1536 | Anthropic-recommended; first 200M tokens free per account |
| **Cohere embed-v3** | $0.10 / 1M ([Cohere pricing](https://cohere.com/pricing)) | 1024 | Strong multilingual |

**Recommendation:** **Voyage 3.5** for production-grade quality, with the 200M-token free tier covering Pathfinder's entire embedded corpus several times over. The 291 sections × ~200 tokens each ≈ 58K tokens to embed once; even with full RMP review text it's <2M tokens total. Voyage is *the* embedding model Anthropic publicly recommends, and shipping with it telegraphs "this team knows the stack."

### 4.2 Vector DB — does Pathfinder need one?

**Short answer: no, not at pilot scale.** With ~291 sections + ~133 professor profiles + a few thousand RMP review snippets, the entire corpus is on the order of 10K vectors at 1024 dimensions ≈ 40 MB. Brute-force cosine similarity over 10K vectors in NumPy completes in <50 ms on commodity hardware.

When Pathfinder eventually adds Postgres (per ADR 0001 the Static-JSON-vs-DB transition is planned for multi-tenant), **`pgvector` is the right answer** through ~50–100M vectors with HNSW indexing ([encore.dev pgvector vs Pinecone](https://encore.dev/articles/pgvector-vs-pinecone); [Tiger Data choosing-a-vector-DB guide](https://www.tigerdata.com/blog/how-to-choose-a-vector-database)). At 1M vectors pgvector hits 95%+ recall in 5–20 ms, which is competitive with Pinecone or Turbopuffer ([Medium benchmark — Coders Stop](https://medium.com/@coders.stop/pgvector-vs-pinecone-vs-weaviate-in-2026-i-actually-ran-them-all-at-scale-here-are-the-numbers-c27d6dba91fb)).

Move to **Turbopuffer** ($64/mo minimum, ~$9 per 1M reads/writes) only when Pathfinder is multi-tenant across 50+ schools and total vector count crosses ~50M. Skip Pinecone unless an enterprise customer demands its SOC-2 posture; the per-vector economics are uncompetitive at small scale.

### 4.3 Reranking

**Cohere Rerank** at $2 / 1K searches ([Cohere pricing](https://cohere.com/pricing)) is the cheapest quality-improver in RAG. For Pathfinder's "find a similar class" feature, the flow is: embedding-shortlist top 20 → Cohere Rerank → top 5 → Claude explains. **Voyage Rerank** is an alternative if standardizing on the Voyage stack.

---

## 5. Specialized AI services

### 5.1 OCR alternatives to Claude Vision (audit-parse cost cutting)

Claude Vision charges full Sonnet 4.5 input rates on each audit parse (~3K image tokens × $3/1M = $0.009 per parse). **Mathpix** at **$0.002 per image request** ([Mathpix pricing](https://mathpix.com/pricing/api)) is ~4.5× cheaper but produces raw text/LaTeX, not structured Degree Works objects. **Google Document AI** and **AWS Textract** are similar.

**Recommendation:** **do not switch.** The audit-parse path is low-volume (one call per student per session) and the structural understanding Vision provides is the load-bearing capability. The parsing logic — "extract requirement codes and rule types from a noisy screenshot" — is exactly what Claude is good at and what raw OCR is bad at. Cost-cutting here saves pennies and risks the demo. Revisit only if audit ingestion ever becomes a hot loop (it shouldn't).

### 5.2 Wolfram Alpha

Marginal at best for Pathfinder. The solver already handles credit math deterministically; "what's my GPA after this semester" is two lines of arithmetic. Skip.

### 5.3 Voice — accessibility win, not core demo

**Cartesia Sonic** at ~$0.05 / 1K characters and 40–90 ms time-to-first-audio is the right pick over **ElevenLabs** ($0.06 / 1K, 75 ms latency on Flash v2.5) for read-schedule-aloud or audio explanation features ([cartesia.ai pricing](https://cartesia.ai/vs/cartesia-vs-openai-tts); [ElevenLabs vs Cartesia comparison](https://elevenlabs.io/blog/elevenlabs-vs-cartesia)). **Deepgram** or **AssemblyAI** for the "transcribe my advisor meeting" feature, but that's a separate product surface and shouldn't compete with the core demo. Defer all voice work until post-pilot.

---

## 6. FERPA / data-residency posture per vendor

Audit content includes student name + ID + GPA (FERPA-protected educational records). Treat them as PII when choosing vendors:

| Vendor | ZDR / DPA available? | FERPA posture |
|---|---|---|
| Anthropic (Claude API) | Yes — ZDR for approved enterprise customers; commercial-terms accounts not used for training ([ZDR docs](https://platform.claude.com/docs/en/build-with-claude/api-and-data-retention); [Privacy Center](https://privacy.claude.com/en/articles/8956058-i-have-a-zero-data-retention-agreement-with-anthropic-what-products-does-it-apply-to)) | Workable as school official under FERPA with DPA + ZDR |
| OpenAI | ZDR for enterprise; standard API has 30-day retention | Same posture as Anthropic for Education tier |
| Google Vertex (Gemini) | Per Vertex policy, configurable | Workable; Bryant is a Workspace school |
| Voyage AI | DPA on request | Embeddings of public course text — low PII risk |
| Tavily / Serper / Brave | No ZDR; logs queries | Pass *queries only*, never audit content |
| Perplexity | Standard retention | Skip for FERPA-protected paths |

**Architectural rule:** the audit content stays inside Anthropic + (optionally) one cross-check vendor with a DPA. Search vendors only see derivative queries like "Bryant FIN 310 instructor reviews," never the audit itself. This matches the privacy story in `00-product-baseline.md` and is a defensible posture for a Bryant pilot.

---

## 7. Top three picks ranked by impact-per-engineering-day

1. **Prompt caching the catalog block.** ~0.5 engineer-days. ~90% cost reduction on the cached portion of every generate call. Zero new vendor. Zero policy risk. **This is the single highest-ROI item in the entire commercialization research.**
2. **Voyage 3.5 embeddings + brute-force NumPy similarity.** ~1 engineer-day. Unlocks the "what's a class like FIN 310 but easier" feature and the free-text preference fallback. 200M-token free tier covers the entire pilot. No vector DB needed yet.
3. **GPT-4.1 structured-output cross-check on audit parse.** ~1 engineer-day. Cuts the "Vision returned garbage" demo failure mode roughly in half by requiring two flagship models to agree before accepting the parse. Trivial cost (<$0.01 per audit). Adds vendor redundancy as a procurement-readiness signal.

**Bonus #4:** Tavily for the professor-grounding feature when RMP misses someone — free at pilot scale, ~0.5 engineer-days.

---

## 8. Vector-DB recommendation (explicit)

**Through pilot scale (≤5 institutions, ≤10M vectors): use Postgres + pgvector with HNSW indexing.** It hits 95%+ recall in 5–20 ms at 1M vectors, keeps relational and vector data co-located (so a "courses similar to X" query can join section metadata in one trip), and avoids a second piece of managed infrastructure. ADR 0001 already plans the Postgres migration; pgvector adds a single `CREATE EXTENSION` line.

**Move to Turbopuffer** when multi-tenant scale crosses ~50M total vectors or when object-storage economics (cold tiers) start to matter. **Skip Pinecone** unless a specific enterprise procurement demands it — the per-vector cost at small scale is uncompetitive and the lock-in is real.

---

## 9. Prompt-caching cost-reduction estimate (explicit)

Claude charges 10% of input rate on cache *read* (and 1.25× on the 5-min-TTL cache *write*). For Pathfinder's three-call generate flow over a static ~6K-token catalog/system block:

- Today: 3 calls × 6K tokens × $3/1M = **$0.054 per generate** on cached-eligible content alone.
- Cached: 1 write at $0.0225 + 2 reads at $0.0018 each = **$0.0261 per generate** — a **52% drop on the *first* generate**, and a **94% drop on every subsequent generate within the TTL window** ($0.0036 vs $0.054).

At a 50-student × 4-generates-per-day pilot, that's roughly $10.80/day → ~$1.20/day. At a 5,000-student steady-state across multiple schools, it's the difference between $1,080/day and $120/day in Claude tokens — about $350K/year saved on the cached path alone. **This is the #1 lever in this brief.**

---

## Sources

- [Claude API pricing — platform.claude.com](https://platform.claude.com/docs/en/about-claude/pricing)
- [Prompt caching docs — Claude API](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [Batch processing docs — Claude API](https://platform.claude.com/docs/en/build-with-claude/batch-processing)
- [Anthropic API Pricing 2026 — finout.io](https://www.finout.io/blog/anthropic-api-pricing)
- [Claude Sonnet 4.5 pricing — pricepertoken.com](https://pricepertoken.com/pricing-page/model/anthropic-claude-sonnet-4.5)
- [Cache TTL regression write-up — dev.to](https://dev.to/whoffagents/claude-prompt-caching-in-2026-the-5-minute-ttl-change-thats-costing-you-money-4363)
- [Prompt caching case study — Lightfoot, Medium](https://medium.com/@labeveryday/prompt-caching-is-a-must-how-i-went-from-spending-720-to-72-monthly-on-api-costs-3086f3635d63)
- [Anthropic ZDR & data retention — Claude API docs](https://platform.claude.com/docs/en/build-with-claude/api-and-data-retention)
- [Anthropic Privacy Center — ZDR coverage](https://privacy.claude.com/en/articles/8956058-i-have-a-zero-data-retention-agreement-with-anthropic-what-products-does-it-apply-to)
- [Anthropic Usage Policy update](https://www.anthropic.com/news/usage-policy-update)
- [Tavily pricing](https://www.tavily.com/pricing)
- [Tavily API credits docs](https://docs.tavily.com/documentation/api-credits)
- [Brave Search API pricing](https://api-dashboard.search.brave.com/documentation/pricing)
- [Brave free-tier removal — implicator.ai](https://www.implicator.ai/brave-drops-free-search-api-tier-puts-all-developers-on-metered-billing/)
- [Exa pricing](https://exa.ai/pricing)
- [Exa pricing changelog](https://exa.ai/docs/changelog/pricing-update)
- [Perplexity Sonar pricing — docs.perplexity.ai](https://docs.perplexity.ai/docs/getting-started/pricing)
- [Perplexity Sonar pricing — aipricing.guru](https://www.aipricing.guru/perplexity-pricing/)
- [Serper](https://serper.dev/)
- [SerpAPI pricing](https://serpapi.com/pricing)
- [Search API price comparison — buildmvpfast](https://www.buildmvpfast.com/api-costs/ai-search)
- [OpenAI API pricing](https://developers.openai.com/api/docs/pricing)
- [OpenAI 2026 pricing — pecollective](https://pecollective.com/tools/openai-api-pricing/)
- [OpenAI text-embedding-3-large — embeddingcost.com](https://embeddingcost.com/openai)
- [OpenAI text-embedding-3-small — helicone](https://www.helicone.ai/llm-cost/provider/openai/model/text-embedding-3-small)
- [Voyage AI pricing docs](https://docs.voyageai.com/docs/pricing)
- [Cohere pricing](https://cohere.com/pricing)
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Mathpix Convert API pricing](https://mathpix.com/pricing/api)
- [Cartesia vs OpenAI TTS](https://cartesia.ai/vs/cartesia-vs-openai-tts)
- [ElevenLabs vs Cartesia comparison](https://elevenlabs.io/blog/elevenlabs-vs-cartesia)
- [pgvector vs Pinecone — encore.dev](https://encore.dev/articles/pgvector-vs-pinecone)
- [Vector DB benchmark 2026 — Coders Stop, Medium](https://medium.com/@coders.stop/pgvector-vs-pinecone-vs-weaviate-in-2026-i-actually-ran-them-all-at-scale-here-are-the-numbers-c27d6dba91fb)
- [Choosing a vector DB — Tiger Data](https://www.tigerdata.com/blog/how-to-choose-a-vector-database)
