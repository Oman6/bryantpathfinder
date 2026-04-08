# Feature 02 -- Banner Catalog Ingestion

## 1-Align: Why This Feature Exists

---

### The Problem

Pathfinder's constraint solver needs to know what courses Bryant University is offering in Fall 2026 -- not just course codes and titles, but the precise meeting days, times, instructor assignments, and seat availability for every section. Without this data, the solver has nothing to search through. The degree audit tells Pathfinder what the student needs; the catalog tells Pathfinder what is available.

Banner Self-Service is the authoritative source for Bryant's course catalog. Students access it through a web interface to search for courses, view section details, and register during the registration window. The interface shows all the information Pathfinder needs: CRN, subject, course number, section letter, title, instructor, meeting days and times, seat counts, and waitlist status.

But Banner Self-Service does not expose a student-accessible API. There is no REST endpoint a student project can call to get structured section data. The Ellucian Ethos APIs exist for institutional integrations, but they require administrative credentials that a student hackathon project does not have access to. Scraping the Banner web interface would violate acceptable use policies and would be fragile against UI changes.

The solution for the hackathon build: manually extract the raw text data from Banner's search results and parse it into structured JSON with a Python script.

---

### The Data Source

The raw data was extracted from Banner Self-Service's "Look Up Classes" feature for the Fall 2026 term, filtered to the subject areas relevant to Owen Ash's B.S.B.A. in Finance degree. The full Bryant catalog for Fall 2026 contains approximately 784 sections across all departments. Pathfinder uses a 291-section subset covering the 17 subjects that appear on Owen's degree audit or are closely related:

- **Finance (FIN):** 45 sections -- Owen's concentration
- **Accounting (ACG):** 42 sections -- business core
- **Economics (ECO):** 28 sections -- prerequisite track
- **General Education (GEN):** 28 sections -- university requirements
- **Science (SCI):** 26 sections -- lab requirement
- **Management (MGT):** 19 sections -- business core
- **History (HIS):** 16 sections -- gen ed distribution
- **Sociology/Anthropology (SOAN):** 14 sections -- gen ed elective
- **Literary/Cultural Studies (LCS):** 12 sections -- gen ed requirement
- **Mathematics (MATH):** 10 sections -- prerequisite track
- **Marketing (MKT):** 10 sections -- business core
- **Information Systems (ISA):** 9 sections -- business core
- **Legal Studies (LGLS):** 8 sections -- business core
- **Business (BUS):** 6 sections -- capstone and core
- **Communication (COM):** 6 sections -- gen ed option
- **Political Science (POLS):** 6 sections -- gen ed distribution
- **Psychology (PSY):** 6 sections -- gen ed distribution

This subset was chosen to include every course that could appear in the requirement expander's output for a Finance major's audit, plus enough breadth in the gen ed subjects to give the solver meaningful choices.

---

### Why Static JSON

The architectural decision to use a static JSON file instead of a database is documented in detail in `docs/adr/0001-static-json-vs-database.md`. The key points:

**The data is frozen.** The Fall 2026 catalog was published in Spring 2026 and is not changing during the hackathon weekend. Seat counts are a snapshot from April 7, 2026. Building a live data pipeline to refresh data that will not change is architecture theater.

**Infrastructure time is build time lost.** Setting up Supabase, defining a schema, writing a seed script, configuring connection strings, and handling connection errors would consume 45-60 minutes of a one-day build. That is time not spent on the solver, the UI, or the demo.

**Zero failure surface.** With static JSON loaded at startup, the data layer cannot fail at runtime. No network calls, no connection timeouts, no query errors, no replica lag. The solver either finds sections or it does not -- and if it does not, the problem is in the student's preferences, not in the infrastructure.

**The JSON file is the schema.** Anyone reviewing the repository can open `data/sections.json` and see the exact data the solver works with. No ORM translation layer, no migration history to trace, no database console to connect to.

**The production path is clear.** When Pathfinder evolves past the hackathon, `sections.json` would be replaced by a Supabase Postgres table with indexes on `subject`, `course_code`, and `term`, refreshed nightly from Banner Ethos. The solver and expander would not need to change -- they receive `list[Section]` regardless of where the data came from.

---

### Why Not OCR the Banner Web Pages

An alternative approach would be to screenshot Banner Self-Service search results and use Claude Vision to parse them, similar to the degree audit parsing path. This was rejected for three reasons:

1. **Volume.** Parsing one audit screenshot is a single API call. Parsing 291 sections from dozens of search result pages would require dozens of calls, each costing tokens and adding latency. The raw text extraction was faster and cheaper.

2. **Precision.** Course registration data demands exact precision -- a CRN of "1045" cannot be read as "1046", a seat count of "18 of 30" cannot be read as "18 of 31". Text extraction from the Banner DOM preserves this precision. Vision parsing introduces a small but nonzero error rate that is unacceptable for registration data.

3. **Repeatability.** The text dump can be re-parsed any number of times with identical results. Vision parsing might produce slightly different JSON on different runs due to model nondeterminism, even at temperature 0.

---

### What Success Looks Like

The Banner ingestion feature succeeds when:

- `data/sections.json` contains exactly 291 valid section objects
- Every section has a CRN, course code, title, section letter, and credit count
- Meeting days use the M/T/W/R/F encoding (Thursday is R, not T or Th)
- Meeting times are in HH:MM 24-hour format
- Async sections have `is_async: true` and `meetings: []`
- FULL sections have `is_full: true` and `seats_open: 0`
- The subject distribution matches the expected counts (FIN: 45, ACG: 42, etc.)
- The parser script runs idempotently -- running it twice produces identical output

---

### Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Raw text has formatting inconsistencies | Medium | Parser uses regex with flexible whitespace matching. Manual spot-checks on output. |
| Section count does not match expected 291 | Low | Script asserts `len(sections) == 291` and exits with error if count is wrong. |
| Time format edge cases (midnight, noon) | Low | `parse_time_12_to_24()` handles 12:00 PM (noon stays 12:00) and 12:00 AM (becomes 00:00). |
| Async sections have sentinel times | Expected | Parser detects "00:00 AM" in the time field and sets `is_async=true`, `meetings=[]`. |
| Instructor listed as "TBA" | Expected | Parser converts "TBA" to `null` in the instructor field. |
| Catalog changes after snapshot | N/A for hackathon | Data is frozen at April 7. Production would sync nightly. |

---

### Alignment with the Core Insight

Banner ingestion is a pure Python operation -- no Claude involvement. The data is structured (key:value text blocks) and the parsing rules are deterministic. There is no perception or language understanding needed. A regex can parse "Monday,Thursday" into `["M", "R"]` more reliably than any language model.

This is the other side of Pathfinder's design philosophy. Claude handles the messy, unstructured Degree Works screenshot. Python handles the structured, precise catalog data. Each tool stays in its lane.
