# Feature 04 — Preference Capture: Execute

> HOW does preference capture work from the student's perspective, end to end?

---

## The User Flow

The preferences page is step 2 of the three-page flow: Upload (homepage) -> Preferences -> Schedules. The student arrives here after their Degree Works audit has been parsed.

```
Homepage                 Preferences              Schedules
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ Upload audit or  │    │ Select courses   │    │ Three ranked     │
│ use sample       │───>│ Set constraints  │───>│ schedule cards   │
│                  │    │ Add free text    │    │ with explanations│
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

---

## Step-by-Step Walkthrough

### Step 1: Page loads with outstanding requirements

When the preferences page mounts, it reads the parsed `DegreeAudit` from the Zustand store. The outstanding requirements are displayed as a list of toggleable items. Each item shows:

- The requirement name (e.g., "Intermediate Corporate Finance")
- The course code(s) (e.g., `FIN 310`)
- The credit value (e.g., 3.0)
- The category (e.g., "major")

For Owen's audit, 16 outstanding requirements are shown:

| Requirement | Course(s) | Credits | Category |
|---|---|---|---|
| Intercultural Communication | GEN 201 | 3 | general_education |
| Literary and Cultural Studies | LCS 200-290, COM 230 | 3 | general_education |
| Science and Lab Requirement | SCI 251+L251, etc. | 4 | general_education |
| General Education Capstone | GEN 390 | 3 | general_education |
| Prin. of Financial Accounting | ACG 203 | 3 | business_core |
| Prin. of Managerial Accounting | ACG 204 | 3 | business_core |
| Business Policy | BUS 400 | 3 | business_core |
| Intro to Info Tech and Analytics | ISA 201 | 3 | business_core |
| Legal Environment of Business | LGLS 211 | 3 | business_core |
| Foundations of Marketing Mgmt | MKT 201 | 3 | business_core |
| Intermediate Corporate Finance | FIN 310 | 3 | major |
| Investments | FIN 312 | 3 | major |
| Financial Inst. and Markets | FIN 315 | 3 | major |
| Financial Electives | FIN 370/371/380/465/466 | 3 | major |
| 400 Level Finance | FIN 4XX | 3 | major |
| Finance Electives | FIN XXX | 3 | major |

All toggles start in the OFF position. A running credit counter at the top shows "0 / 15 credits selected."

---

### Step 2: Student toggles requirements on/off

Owen clicks on the requirements he wants to schedule this semester. As each is toggled on, the credit counter updates.

**Owen's selections:**

| Toggle | Requirement | Credits | Running total |
|--------|-------------|---------|---------------|
| ON | `fin_310` — Intermediate Corporate Finance | 3 | 3 |
| ON | `gen_201` — Intercultural Communication | 3 | 6 |
| ON | `acg_203` — Prin. of Financial Accounting | 3 | 9 |
| ON | `isa_201` — Intro to Info Tech and Analytics | 3 | 12 |
| ON | `mkt_201` — Foundations of Marketing Mgmt | 3 | 15 |

The credit counter now shows "15 / 15 credits selected" — exactly at the default target. The Zustand store updates:

```json
{
  "selected_requirement_ids": ["fin_310", "gen_201", "acg_203", "isa_201", "mkt_201"]
}
```

If Owen toggles on a sixth requirement, the counter would show "18 / 15 credits selected." The UI shows a warning that the schedule exceeds the target, but does not prevent submission. The solver will find combinations near the target credit count.

---

### Step 3: Student sets blocked days

Below the requirement list, a row of five day buttons: **M T W R F**. Each button toggles a day on/off. Active (blocked) buttons are visually distinct — outlined with the Bryant gold accent.

Owen clicks **F** to block Friday.

```json
{
  "blocked_days": ["F"]
}
```

The UI updates to show a note: "Sections meeting on Friday will be excluded from all generated schedules."

**What this means for the solver:** When the solver calls `filter_candidates_by_preferences()` for each requirement's candidate pool, every section with a Friday meeting is removed. For FIN 310, if Section A meets T/F, it would be excluded. Only sections meeting on non-Friday days survive.

---

### Step 4: Student sets time window preferences

Two optional fields: "No earlier than" and "No later than." Each is a dropdown or time picker in HH:MM format.

Owen does not set a lower bound (he accepts early morning classes) but also does not set an upper bound:

```json
{
  "no_earlier_than": null,
  "no_later_than": null
}
```

If Owen had set `no_earlier_than: "10:00"`, the solver would exclude any section whose first meeting starts before 10:00. Bryant's earliest time block is 08:00-09:15, so this would remove all 8am sections from every candidate pool.

If Owen had set both `no_earlier_than: "10:00"` and `no_later_than: "15:00"`, only sections starting at or after 10:00 and ending at or before 15:00 would survive. This is a tight window and might reduce candidate pools enough that the solver finds fewer valid combinations.

---

### Step 5: Student enters instructor preferences (optional)

Two text inputs: "Preferred instructors" and "Instructors to avoid." Each accepts comma-separated names.

Owen types "Kumar" in the preferred instructors field:

```json
{
  "preferred_instructors": ["Kumar"],
  "avoided_instructors": []
}
```

The solver will give +5 score to any schedule containing a section taught by an instructor whose name contains "Kumar" (case-insensitive). In Owen's candidate pool, FIN 310 Sections A and B are taught by "Kumar, Sonal" — both would match.

---

### Step 6: Student types free-text preferences

A text area at the bottom of the form for anything that does not fit the structured fields.

Owen types: "I want to start the finance concentration"

```json
{
  "free_text": "I want to start the finance concentration"
}
```

The solver will not read this. Claude will read it when:
1. Writing the 2-sentence explanation paragraph for each schedule.
2. Performing the final ranking of the three candidate schedules.

If Schedule A includes FIN 310 (starting the concentration) and Schedule B does not, Claude's ranking will favor Schedule A and mention the finance concentration in its explanation.

---

### Step 7: Submit

Owen clicks the "Generate my schedules" CTA (pill-shaped button with trailing arrow). The frontend constructs a `GenerateSchedulesRequest` containing the full `DegreeAudit` from the Zustand store and the `SchedulePreferences` assembled from the form. The preferences portion:

```json
{
  "target_credits": 15,
  "blocked_days": ["F"],
  "no_earlier_than": null,
  "no_later_than": null,
  "preferred_instructors": ["Kumar"],
  "avoided_instructors": [],
  "free_text": "I want to start the finance concentration",
  "selected_requirement_ids": ["fin_310", "gen_201", "acg_203", "isa_201", "mkt_201"]
}
```

This is sent as `POST /api/generate-schedules`. The frontend navigates to the `/schedules` page and shows a loading state while the backend processes.

---

## What Happens on the Backend

### Expansion phase

The solver filters to the 5 selected requirements and expands each:

| Requirement | Candidates (before preference filter) |
|---|---|
| `fin_310` | 3 sections (A, B, C) |
| `gen_201` | 12 sections (B through M) |
| `acg_203` | 13 sections (A through M) |
| `isa_201` | 9 sections (A through K) |
| `mkt_201` | 6 sections (A through H) |

### Preference filtering phase

`filter_candidates_by_preferences()` runs on each pool with `blocked_days: ["F"]`:

- FIN 310: Any section meeting on Friday is removed. If Section A meets T/F, it is dropped. Sections meeting only on M/W/R/T survive.
- GEN 201: Same filter applied. Sections with Friday meetings removed.
- ACG 203, ISA 201, MKT 201: Same.

The exact surviving counts depend on each section's meeting days. A section meeting MWF loses Friday; a section meeting TR keeps all its days but has no Friday meeting to begin with.

### Combination and scoring phase

The solver takes `itertools.product` of the filtered pools. For each combination:

1. Check total credits are within 3 of target (15). Five 3-credit courses = 15, which is exactly on target. All combinations pass.
2. Check pairwise time conflicts. Any overlapping meetings eliminate the combination.
3. Score valid combinations:
   - Credit match: 15 vs 15 target = +10
   - Instructor: +5 for each Kumar section (FIN 310 A or B)
   - Seat availability: +1 per section with >50% seats open
   - Category balance: +3 per distinct category (major, general_education, business_core = 3 categories = +9)

### Result

The top 3 scoring combinations are returned as `ScheduleOption` objects. Claude writes explanation paragraphs and performs the final ranking. The schedules page renders three cards.

---

## Worked Example: Over-Constrained Preferences

What if Owen blocks both Wednesday and Friday, sets `no_earlier_than: "11:00"`, and avoids "Beausejour"? The hard constraints stack: blocking W and F removes all MWF and WF sections; the 11:00 floor removes all 8:00, 9:35, and 10:00 block sections. Together, these might reduce ACG 203 from 13 candidates to 3 or 4. If any single requirement's pool hits zero, the solver returns an empty list and the API responds with a 422 suggesting the student loosen constraints.

---

## Worked Example: No Preferences

With all defaults (empty `blocked_days`, null time windows, no instructor preferences), the solver skips preference filtering entirely. All expanded candidates survive. The combination space is maximal: 3 x 12 x 13 x 9 x 6 = 25,272 combinations. The solver hits its 10,000-combination safety cap and returns the best 3 found within that cap. Scoring uses only credit match, seat availability, and category balance.

---

## State Management

The preferences page uses the Zustand store defined in `frontend/lib/store.ts`. The store holds:

- The parsed `DegreeAudit` (set by the homepage after upload/sample)
- The `SchedulePreferences` (set incrementally as the student interacts with the preferences page)
- The generated `ScheduleOption[]` (set by the schedules page after the API response)

The preferences are not persisted anywhere. If the student refreshes the page, they start over. This is a deliberate hackathon simplification — a production version would persist preferences in Supabase per student session.

---

## Edge Cases

**Student selects zero requirements.** The solver falls back to using all 16 outstanding requirements. The combination space explodes and the 10,000-cap is hit quickly. The returned schedules may not be meaningful.

**Student selects requirements totaling 4 credits.** The solver's credit range check (`abs(total - target) > 3`) rejects most combinations when `target_credits = 15` and the actual total is 4. Zero valid schedules are returned. The student should adjust their target or select more requirements.

**Student types instructor name with wrong capitalization.** Substring matching is case-insensitive. "kumar", "KUMAR", and "Kumar" all match "Kumar, Sonal."

**Student blocks all five days.** Every section in the catalog is excluded. Zero candidates for every requirement. Zero schedules returned.

---

## References

- `frontend/app/preferences/page.tsx` — the preferences UI
- `frontend/lib/store.ts` — Zustand state management
- `backend/app/models.py` — `SchedulePreferences`, `GenerateSchedulesRequest`
- `backend/app/solver.py` — `filter_candidates_by_preferences()`, `score_combination()`, `solve()`
- `docs/api.md` — `/api/generate-schedules` request/response documentation
- `CLAUDE.md` — demo path steps 3-5
