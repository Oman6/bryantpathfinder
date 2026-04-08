# Feature 01 -- Degree Audit Parsing

Pathfinder's first pipeline stage: take a Degree Works audit screenshot and turn it into a structured `DegreeAudit` object that the rest of the system can reason about.

---

## What It Does

A student uploads a screenshot (PNG, JPEG, or PDF) of their Degree Works audit page from Bryant University's student portal. Pathfinder sends the image to Claude Vision, which reads every requirement on the page and classifies each one as completed, in-progress, or outstanding. The outstanding requirements are further classified by rule type -- `specific_course`, `choose_one_of`, `wildcard`, or `course_with_lab` -- so the downstream requirement expander and constraint solver know exactly how to find candidate sections.

The output is a `DegreeAudit` Pydantic model containing student metadata (name, ID, major, expected graduation, credit counts), a list of completed courses with grades and terms, a list of in-progress courses, and a list of outstanding requirements with their rule types and candidate course lists.

---

## Where the Code Lives

| File | Role |
|------|------|
| `backend/scripts/parse_degree_audit.py` | Offline script that parses Owen Ash's raw audit text into `data/fixtures/audit_owen.json`. Used during initial data preparation, not at runtime. |
| `backend/app/claude_client.py` | Runtime Vision parsing. The `parse_audit_vision()` function accepts a base64-encoded image, calls Claude with `VISION_AUDIT_PROMPT`, and returns a validated `DegreeAudit`. |
| `backend/app/prompts.py` | Contains `VISION_AUDIT_PROMPT` -- the system prompt that instructs Claude how to read a Degree Works screenshot and classify requirements. |
| `backend/app/models.py` | Defines `DegreeAudit`, `CompletedRequirement`, and `OutstandingRequirement` Pydantic models. These are the source of truth for the audit schema. |
| `data/fixtures/audit_owen.json` | Pre-parsed fixture for Owen Ash's audit. Used as the "Use sample audit" fallback on the homepage and for testing without a live Claude API call. |

---

## How It Connects to the System

```
                     +-----------------------+
                     |  Student uploads       |
                     |  Degree Works          |
                     |  screenshot            |
                     +----------+------------+
                                |
                                v
                     +----------+------------+
                     |  POST /api/parse-audit |
                     |  claude_client.py      |
                     |  parse_audit_vision()  |
                     +----------+------------+
                                |
                                v
                     +----------+------------+
                     |  DegreeAudit object    |
                     |  (Pydantic validated)  |
                     +----------+------------+
                                |
               +----------------+----------------+
               |                                 |
               v                                 v
    +----------+----------+        +-------------+----------+
    |  Frontend stores     |        |  Sent to               |
    |  audit in Zustand    |        |  /api/generate-        |
    |  for preferences     |        |  schedules with        |
    |  page display        |        |  SchedulePreferences   |
    +----------------------+        +------------------------+
```

The `DegreeAudit` object flows forward through the entire pipeline. The preferences page reads `outstanding_requirements` to show the student which requirements they can schedule. The solver receives the audit as part of the `GenerateSchedulesRequest` and uses it to determine which sections to search for.

---

## Two Parsing Paths

**Live path (Vision):** Student uploads a real screenshot. The frontend base64-encodes the image and POSTs it to `/api/parse-audit`. Claude Vision reads the image and returns structured JSON. This is the primary path for production use.

**Fixture path (fallback):** Student clicks "Use sample audit" on the homepage. The frontend loads `audit_owen.json` directly -- no Claude API call, no network dependency. This is the safe path for the hackathon demo and the path used in all solver tests.

Both paths produce the same `DegreeAudit` schema. The rest of the pipeline does not know or care which path generated the audit.

---

## Key Numbers

- Owen Ash's audit contains **6 completed**, **9 in-progress**, and **16 outstanding** requirements
- The 16 outstanding requirements span three categories: general_education (4), business_core (6), and major (6)
- The four rule types appear in Owen's audit: 8 specific_course, 2 choose_one_of, 2 wildcard, 1 course_with_lab
- Claude Vision parsing takes approximately 3-5 seconds per call
- The retry-on-malformed-JSON logic allows up to 2 attempts before failing

---

## Owen Ash's Outstanding Requirements at a Glance

These 16 requirements are what Pathfinder needs to schedule. They span all four rule types and three degree categories.

| ID | Requirement | Rule Type | Category |
|----|------------|-----------|----------|
| `gen_201` | Intercultural Communication | specific_course | general_education |
| `lcs_course` | Literary and Cultural Studies | choose_one_of (20 options) | general_education |
| `science_lab` | Science and Lab Requirement | course_with_lab (10 pairs) | general_education |
| `gen_390_capstone` | General Education Capstone | specific_course | general_education |
| `acg_203` | Prin. of Financial Accounting | specific_course | business_core |
| `acg_204` | Prin. of Managerial Accounting | specific_course | business_core |
| `bus_400` | Business Policy | specific_course | business_core |
| `isa_201` | Intro to Info Tech and Analytics | specific_course | business_core |
| `lgls_211` | Legal Environment of Business | specific_course | business_core |
| `mkt_201` | Foundations of Marketing Mgmt | specific_course | business_core |
| `fin_310` | Intermediate Corporate Finance | specific_course | major |
| `fin_312` | Investments | specific_course | major |
| `fin_315` | Financial Inst. and Markets | specific_course | major |
| `fin_elective` | Financial Electives | choose_one_of (5 options) | major |
| `fin_400_level` | 400 Level Finance | wildcard (FIN 4XX) | major |
| `fin_general_elective` | Finance Electives | wildcard (FIN XXX) | major |

---

## Related Documentation

- `docs/adr/0002-claude-vision-for-degree-audit.md` -- Why Claude Vision instead of OCR or manual entry
- `docs/features/01-degree-audit-parsing/1-align.md` -- The problem this feature solves
- `docs/features/01-degree-audit-parsing/2-construct.md` -- Schema and contract details
- `docs/features/01-degree-audit-parsing/3-execute.md` -- Step-by-step runtime walkthrough
