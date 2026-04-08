# Feature 02 -- Banner Catalog Ingestion

Pathfinder's data foundation: parse Bryant University's Fall 2026 course catalog from a raw Banner Self-Service text dump into structured, machine-readable JSON that the solver can search.

---

## What It Does

The Banner ingestion pipeline takes a raw text file extracted from Bryant's Banner Self-Service system -- containing every section offered in the Fall 2026 term for the Business Administration track -- and converts it into `data/sections.json`, a structured JSON array of 291 `Section` objects. Each section includes the CRN, course code, title, instructor, meeting days and times (normalized to 24-hour format with single-letter day codes), seat availability, waitlist counts, and enrollment status.

This is an offline, build-time operation. The parse script runs once during data preparation and produces the JSON file that the backend loads into memory at startup. There are no runtime Banner API calls.

---

## Where the Code Lives

| File | Role |
|------|------|
| `backend/scripts/parse_banner_dump.py` | The parser. Reads `data/raw/banner_fall2026_raw.txt`, splits on separator lines, parses each block into a `Section` dict, and writes `data/sections.json`. |
| `backend/app/models.py` | Defines the `Section` and `Meeting` Pydantic models that the rest of the system uses to represent sections at runtime. |
| `data/raw/banner_fall2026_raw.txt` | The raw input. A text dump from Banner Self-Service with one block per section, separated by lines of dashes. |
| `data/sections.json` | The output. A JSON array of 291 section objects, loaded by the FastAPI backend at startup. |

---

## How It Connects to the System

```
+----------------------------+
|  data/raw/                 |
|  banner_fall2026_raw.txt   |
|  (raw Banner text dump)    |
+------------+---------------+
             |
             v  python backend/scripts/parse_banner_dump.py
+------------+---------------+
|  data/sections.json        |
|  (291 structured sections) |
+------------+---------------+
             |
             v  loaded at FastAPI startup via lifespan
+------------+---------------+
|  app.state.sections        |
|  (in-memory list[Section]) |
+------------+---------------+
             |
     +-------+-------+
     |               |
     v               v
+----+----+    +-----+----------+
| Expander |    | Health check  |
| finds    |    | reports       |
| candidate|    | sections_     |
| sections |    | loaded: 291   |
+----------+    +---------------+
```

The sections data flows through the system as follows:
1. The raw file is parsed offline into `sections.json`
2. The FastAPI lifespan context manager loads `sections.json` into `app.state.sections` at startup
3. The requirement expander queries this in-memory list to find candidate sections for each outstanding requirement
4. The solver receives the candidate sections and searches for conflict-free combinations
5. The health endpoint reports the section count to confirm the data loaded correctly

---

## Key Numbers

- **291 total sections** across 17 subjects
- **45 FIN sections** (the largest subject, reflecting Owen's Finance concentration)
- **42 ACG sections** (Accounting -- closely related to the business core)
- **28 GEN sections** (General Education)
- **28 ECO sections** (Economics)
- **26 SCI sections** (Science, including labs)
- All sections are for the **Fall 2026** term
- Term dates: **2026-08-31** to **2026-12-18**
- Meeting times span **08:00** to **17:10** for in-person sections

---

## Design Decision: Static JSON over Database

The choice to use a static JSON file instead of a database is documented in `docs/adr/0001-static-json-vs-database.md`. The core reasoning: the Fall 2026 catalog is frozen for the hackathon, a database would add 45-60 minutes of infrastructure setup with no benefit to the demo, and the 291-section dataset fits comfortably in memory at approximately 150KB. The production path would use Supabase Postgres with nightly syncs from Banner Ethos.

---

## Subject Coverage

The 291 sections span 17 subjects. This table shows the count per subject and its relevance to Owen's degree.

| Subject | Count | Relevance |
|---------|-------|-----------|
| ACG | 42 | Business core (Financial and Managerial Accounting) |
| BUS | 6 | Business core (capstone BUS 400) and intro (BUS 100) |
| COM | 6 | Gen ed option (COM 230 satisfies LCS requirement) |
| ECO | 28 | Prerequisite track (ECO 113, ECO 114) |
| FIN | 45 | Finance concentration (FIN 310, 312, 315, electives) |
| GEN | 28 | General education (GEN 201, GEN 390 capstone) |
| HIS | 16 | Gen ed distribution |
| ISA | 9 | Business core (ISA 201) |
| LCS | 12 | Gen ed requirement (Literary and Cultural Studies) |
| LGLS | 8 | Business core (LGLS 211) |
| MATH | 10 | Prerequisite track (MATH 110, MATH 201) |
| MGT | 19 | Business core (MGT 200, MGT 201) |
| MKT | 10 | Business core (MKT 201) |
| POLS | 6 | Gen ed distribution |
| PSY | 6 | Gen ed distribution |
| SCI | 26 | Gen ed lab requirement (lecture + lab pairs) |
| SOAN | 14 | Gen ed distribution |

---

## Related Documentation

- `docs/adr/0001-static-json-vs-database.md` -- Why static JSON instead of a database
- `docs/features/02-banner-ingestion/1-align.md` -- Why this feature exists
- `docs/features/02-banner-ingestion/2-construct.md` -- The Section schema and parsing rules
- `docs/features/02-banner-ingestion/3-execute.md` -- Step-by-step parsing walkthrough
- `docs/features/03-requirement-expansion/` -- How sections.json is queried downstream
