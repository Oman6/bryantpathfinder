# Feature 01 -- Degree Audit Parsing

## 2-Construct: What We Are Building

---

### The DegreeAudit Schema

The `DegreeAudit` model is defined in `backend/app/models.py` and is the single source of truth for the shape of a parsed audit. Every field is typed. No optional fields except where the data genuinely may not exist.

```python
class DegreeAudit(BaseModel):
    student_id: str
    name: str
    major: str
    expected_graduation: str
    credits_earned_or_inprogress: int
    credits_required: int
    completed_requirements: list[CompletedRequirement]
    in_progress_requirements: list[CompletedRequirement]
    outstanding_requirements: list[OutstandingRequirement]
```

**Field-by-field breakdown:**

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `student_id` | `str` | `"001118725"` | Banner student ID, zero-padded |
| `name` | `str` | `"Owen Ash"` | First Last format |
| `major` | `str` | `"Finance"` | Primary concentration |
| `expected_graduation` | `str` | `"May 2029"` | Month + year |
| `credits_earned_or_inprogress` | `int` | `42` | Sum of completed + registered credits |
| `credits_required` | `int` | `120` | Total for degree completion |
| `completed_requirements` | `list[CompletedRequirement]` | 6 items for Owen | Courses with final grades |
| `in_progress_requirements` | `list[CompletedRequirement]` | 9 items for Owen | Currently registered courses |
| `outstanding_requirements` | `list[OutstandingRequirement]` | 16 items for Owen | What Pathfinder schedules |

---

### CompletedRequirement

Used for both completed and in-progress courses. The distinction is the `grade` field: completed courses have letter grades ("A", "B"), while in-progress courses have "REG" (registered).

```python
class CompletedRequirement(BaseModel):
    requirement: str    # "Statistics I"
    course: str         # "MATH 201"
    grade: str          # "A" (completed) or "REG" (in-progress)
    credits: float      # 3.0
    term: str           # "Fall 2025"
```

---

### OutstandingRequirement

The core model for Pathfinder's scheduling logic. Each outstanding requirement describes what the student still needs and how the system should find sections to satisfy it.

```python
class OutstandingRequirement(BaseModel):
    id: str
    requirement: str
    rule_type: Literal["specific_course", "choose_one_of", "wildcard", "course_with_lab"]
    options: list[str] = Field(default_factory=list)
    pattern: str | None = None
    pairs: list[list[str]] | None = None
    credits_needed: float
    category: Literal["general_education", "business_core", "major", "elective", "minor"]
```

**The `id` field** is a stable snake_case identifier generated from the course code or requirement name. It must be deterministic -- the same requirement in the same audit always gets the same ID. Examples: `fin_310`, `lcs_course`, `science_lab`, `fin_400_level`. The solver uses these IDs to track which requirements each generated schedule satisfies.

**The `category` field** determines the color coding on the frontend calendar and affects the solver's category balance scoring. The five possible values cover Bryant's degree structure: general education (university-wide requirements), business core (required for all business majors), major (concentration-specific), elective (free electives), and minor (minor program requirements).

---

### The Four Rule Types

Each rule type tells the requirement expander (`backend/app/requirement_expander.py`) how to find candidate sections in the catalog.

#### 1. specific_course

The student must take exactly one specific course. The `options` list has exactly one entry. The expander searches `sections.json` for all sections where `course_code` matches the option.

```json
{
  "id": "fin_310",
  "requirement": "Intermediate Corporate Finance",
  "rule_type": "specific_course",
  "options": ["FIN 310"],
  "pattern": null,
  "pairs": null,
  "credits_needed": 3.0,
  "category": "major"
}
```

**Degree Works source text:** "Still needed: 1 Class in FIN 310"

**Expansion result:** 3 sections (FIN 310 A/B with Kumar, FIN 310 C with TBA)

#### 2. choose_one_of

The student must take one course from a list of options. The `options` list has multiple entries. The expander searches for all sections matching any course code in the list.

```json
{
  "id": "fin_elective",
  "requirement": "Financial Electives",
  "rule_type": "choose_one_of",
  "options": ["FIN 370", "FIN 371", "FIN 380", "FIN 465", "FIN 466"],
  "pattern": null,
  "pairs": null,
  "credits_needed": 3.0,
  "category": "major"
}
```

**Degree Works source text:** "Still needed: 1 Class in FIN 370 or 371 or 380 or 465 or 466"

**Critical parsing detail:** The "or" numbers inherit the subject prefix from the first course. "FIN 370 or 371 or 380" means "FIN 370 or FIN 371 or FIN 380", not three different subjects. The VISION_AUDIT_PROMPT includes a worked example showing this propagation.

**Expansion result:** 9 candidate sections across FIN 370 (4), FIN 380 (2), FIN 465 (2), FIN 466 (1).

#### 3. wildcard

The student must take a course matching a pattern. The `options` list is empty. The `pattern` field contains the matching rule in `SUBJECT LEVEL` format, where `XX` represents any digits.

```json
{
  "id": "fin_400_level",
  "requirement": "400 Level Finance",
  "rule_type": "wildcard",
  "options": [],
  "pattern": "FIN 4XX",
  "pairs": null,
  "credits_needed": 3.0,
  "category": "major"
}
```

**Degree Works source text:** "Still needed: 1 Class in @ 4@ with attribute = FIN"

**Pattern format:** The `@` symbols in Degree Works are translated to `X` in Pathfinder's pattern format. `4XX` means any course number starting with 4 (400-level). `XXX` means any course number for that subject.

**Expansion logic:** The expander walks every section in the catalog, filters by `subject == "FIN"`, and checks whether `course_number` starts with "4". Returns sections for FIN 412, FIN 414, FIN 458, FIN 460, FIN 465, FIN 466, and FIN 475.

#### 4. course_with_lab

The student must register for both a lecture and its paired lab section. The `options` list is empty. The `pairs` field contains a list of valid [lecture_code, lab_code] pairs.

```json
{
  "id": "science_lab",
  "requirement": "Science and Lab Requirement",
  "rule_type": "course_with_lab",
  "options": [],
  "pattern": null,
  "pairs": [
    ["SCI 251", "SCI L251"],
    ["SCI 262", "SCI L262"],
    ["SCI 264", "SCI L264"],
    ["SCI 265", "SCI L265"],
    ["SCI 269", "SCI L269"],
    ["SCI 351", "SCI L351"],
    ["SCI 352", "SCI L352"],
    ["SCI 355", "SCI L355"],
    ["SCI 356", "SCI L356"],
    ["SCI 371", "SCI L371"]
  ],
  "credits_needed": 4.0,
  "category": "general_education"
}
```

**Degree Works source text:** "2 Classes in SCI 251 and L251" (repeated for each pair)

**Expansion logic:** The expander generates all (lecture, lab) tuples for each valid pair. If SCI 251 has 2 lecture sections and SCI L251 has 3 lab sections, that pair produces 6 tuples. The solver must pick one complete tuple -- it cannot schedule the lecture without the lab.

---

### The VISION_AUDIT_PROMPT

Defined in `backend/app/prompts.py` as a module-level constant. The prompt is approximately 140 lines and has four sections:

1. **Role and task description.** Tells Claude it is looking at a Degree Works screenshot and must extract every requirement.

2. **Output schema.** The exact JSON structure matching `DegreeAudit`, shown as a JSON example with field descriptions.

3. **Rule type classification.** Four worked examples, one per rule type, showing the Degree Works source text and the expected JSON output. This is the most important section -- without these examples, Claude would not know how to classify "FIN 370 or 371 or 380" as `choose_one_of` with the subject prefix propagated.

4. **Category assignment rules.** Maps Degree Works section headers to category values: "GENERAL EDUCATION" becomes `general_education`, "FINANCE CONCENTRATION" becomes `major`, etc.

5. **Important rules.** Six constraints: only include visible requirements, extract actual grades for completed courses, use "REG" for in-progress, generate stable snake_case IDs, return only JSON (no markdown fences), and skip informational requirements like GPA minimums.

Temperature is set to `0` in the API call to maximize determinism.

---

### Input/Output Contracts

#### POST /api/parse-audit

**Request body** (`ParseAuditRequest`):

```json
{
  "image_base64": "iVBORw0KGgoAAAANSuhEUgAA..."
}
```

The `image_base64` field is the raw base64 encoding of the image file (PNG, JPEG) or PDF. No data URL prefix -- just the base64 string. The media type is inferred on the backend (defaulting to `image/png`).

**Success response** (200): A full `DegreeAudit` JSON object.

**Error responses:**
- `422`: Claude returned malformed JSON after 2 attempts. Response body includes the parse error.
- `400`: The uploaded file is not a supported image or PDF format.
- `500`: Anthropic API authentication error (missing or invalid API key).
- `429`: Anthropic API rate limit exceeded.

#### Fixture loading (frontend-only path)

No API call. The frontend fetches `audit_owen.json` from the static data directory and loads it directly into the Zustand store as a `DegreeAudit` object. The TypeScript types in `frontend/lib/types.ts` mirror the Pydantic models exactly.

---

### Component Boundaries

```
+-------------------+     +-------------------+     +-------------------+
|  Frontend         |     |  API Layer        |     |  Claude Client    |
|                   |     |                   |     |                   |
|  UploadZone.tsx   +---->+  POST /api/       +---->+  parse_audit_     |
|  or "Use sample"  |     |  parse-audit      |     |  vision()         |
|                   |     |                   |     |                   |
|  Stores result    +<----+  Returns          +<----+  Returns          |
|  in Zustand       |     |  DegreeAudit      |     |  DegreeAudit      |
+-------------------+     +-------------------+     +-------------------+
```

- The **frontend** owns image encoding and the decision of whether to use live parsing or the fixture
- The **API layer** owns request validation and error handling
- The **Claude client** owns the Anthropic SDK call, the retry logic, and Pydantic validation of the response
- The **prompt** owns the domain knowledge about Degree Works formatting and rule type classification

No component reaches into another's responsibility. The Claude client does not know about HTTP status codes. The API layer does not know about the Anthropic SDK. The frontend does not know which model Claude uses.
