# 05 Constraint Solver — Execute

> HOW does the solver run? A worked example with Owen's real data.

---

## Setup

Owen is a sophomore Finance major at Bryant University. He has 42 credits earned or in progress and needs to register for Fall 2026. His degree audit (`data/fixtures/audit_owen.json`) lists 16 outstanding requirements. For this semester, he selects 5:

| Requirement ID | Course | Category | Credits |
|---|---|---|---|
| `fin_310` | FIN 310 (Intermediate Corporate Finance) | major | 3.0 |
| `gen_201` | GEN 201 (Intercultural Communication) | general_education | 3.0 |
| `acg_203` | ACG 203 (Prin. of Financial Accounting) | business_core | 3.0 |
| `isa_201` | ISA 201 (Intro to Information Tech and Analytics) | business_core | 3.0 |
| `mkt_201` | MKT 201 (Foundations of Marketing Management) | business_core | 3.0 |

His preferences:

```json
{
  "target_credits": 15,
  "blocked_days": ["F"],
  "no_earlier_than": null,
  "no_later_than": null,
  "preferred_instructors": ["Kumar"],
  "avoided_instructors": [],
  "selected_requirement_ids": ["fin_310", "gen_201", "acg_203", "isa_201", "mkt_201"]
}
```

---

## Step 1: Expand each requirement into candidate sections

The solver calls `expand_requirement()` for each of Owen's 5 selected requirements. All 5 are `specific_course` type, so expansion is straightforward: find all sections in `data/sections.json` whose `course_code` matches. Full sections and async sections are excluded.

### FIN 310 — 3 sections

| CRN | Section | Instructor | Days | Time | Seats |
|---|---|---|---|---|---|
| 1045 | A | Kumar, Sonal | TF | 12:45-14:00 | 18/30 |
| 1046 | B | Kumar, Sonal | TF | 09:35-10:50 | 16/30 |
| 1047 | C | TBA | MR | 15:55-17:10 | 22/30 |

### GEN 201 — 12 sections

| CRN | Section | Instructor | Days | Time | Seats |
|---|---|---|---|---|---|
| 1686 | B | Robins, Mary | TF | 09:35-10:50 | 17/30 |
| 1687 | C | Pearce, Kevin | MR | 09:35-10:50 | 20/30 |
| 1688 | D | Zammarelli, Thomas | MR | 11:10-12:25 | 18/30 |
| 1689 | E | Gallo, Mary Ann | MR | 12:45-14:00 | 19/30 |
| 1690 | F | Kanemoto, Emi | TF | 14:20-15:35 | 18/30 |
| 1691 | G | Kanemoto, Emi | TF | 12:45-14:00 | 17/30 |
| 1692 | H | Zdravkovic, Cindy | TF | 08:00-09:15 | 17/30 |
| 1693 | I | Zammarelli, Thomas | MR | 09:35-10:50 | 17/30 |
| 1694 | J | Williams, Zhongyuan | MR | 14:20-15:35 | 22/30 |
| 1695 | K | Williams, Zhongyuan | MR | 15:55-17:10 | 20/30 |
| 1696 | L | Williams, Zhongyuan | MR | 09:35-10:50 | 19/30 |
| 1697 | M | Zdravkovic, Cindy | TF | 09:35-10:50 | 17/30 |

### ACG 203 — 13 sections

| CRN | Section | Instructor | Days | Time | Seats |
|---|---|---|---|---|---|
| 1212 | A | TBA | T | 18:30-21:10 | 23/30 |
| 1213 | B | Diaz, Carlos | M | 18:30-21:10 | 22/30 |
| 1214 | C | Hughes, Nia | W | 18:30-21:10 | 16/30 |
| 1215 | D | Leandres, Angelina | TF | 08:00-09:15 | 20/30 |
| 1216 | E | Hughes, Nia | T | 18:30-21:10 | 18/30 |
| 1217 | F | Terranova, Natalie | M | 18:30-21:10 | 30/30 |
| 1218 | G | Beausejour, David | MR | 11:10-12:25 | 18/30 |
| 1219 | H | Beausejour, David | MR | 14:20-15:35 | 22/30 |
| 1220 | I | Beausejour, David | MR | 09:35-10:50 | 22/30 |
| 1221 | J | Precourt, Elena | MR | 11:10-12:25 | 21/30 |
| 1222 | K | Precourt, Elena | MR | 14:20-15:35 | 25/30 |
| 1223 | L | Andre, Christina | W | 11:10-13:50 | 26/30 |
| 1224 | M | Andre, Christina | R | 18:30-21:10 | 30/30 |

### ISA 201 — 9 sections

| CRN | Section | Instructor | Days | Time | Seats |
|---|---|---|---|---|---|
| 1140 | A | Ryan, Riazat | MR | 09:35-10:50 | 14/30 |
| 1141 | B | Prichard, Janet | TF | 09:35-10:50 | 21/30 |
| 1142 | C | Varin, Francis | TF | 14:20-15:35 | 19/30 |
| 1143 | D | TBA | R | 18:30-21:10 | 30/30 |
| 1144 | E | Varin, Francis | TF | 08:00-09:15 | 22/30 |
| 1145 | F | Varin, Francis | TF | 12:45-14:00 | 21/30 |
| 1147 | H | Chaudhury, Abhijit | MR | 12:45-14:00 | 24/30 |
| 1148 | I | Sousa, Kenneth | MR | 11:10-12:25 | 22/30 |
| 1150 | K | Chaudhury, Abhijit | MR | 14:20-15:35 | 26/30 |

### MKT 201 — 6 sections

| CRN | Section | Instructor | Days | Time | Seats |
|---|---|---|---|---|---|
| 1093 | A | Bell-Lombardo, Hannah | W | 08:00-10:40 | 27/30 |
| 1094 | B | Gulidanan, Donna | W | 18:30-21:10 | 24/30 |
| 1095 | C | Jayaraman, Jay | TF | 14:20-15:35 | 26/30 |
| 1096 | D | Jayaraman, Jay | TF | 12:45-14:00 | 20/30 |
| 1097 | E | Lenz, Michael | W | 11:10-13:50 | 21/30 |
| 1100 | H | Pasha, Mehreen | MR | 17:30-18:45 | 18/30 |

---

## Step 2: Filter by Friday block

Owen has `blocked_days=["F"]`. Every section that meets on Friday is removed.

**Sections removed:**

- FIN 310 sec A (TF 12:45-14:00) — meets Friday
- FIN 310 sec B (TF 09:35-10:50) — meets Friday
- GEN 201 sec B, F, G, H, M (all TF) — meet Friday
- ACG 203 sec D (TF 08:00-09:15) — meets Friday
- ISA 201 sec B, C, E, F (all TF) — meet Friday
- MKT 201 sec C, D (TF) — meet Friday

**Sections remaining after Friday filter:**

| Requirement | Remaining | Section letters |
|---|---|---|
| FIN 310 | 1 section | C (MR 15:55-17:10) |
| GEN 201 | 7 sections | C, D, E, I, J, K, L |
| ACG 203 | 11 sections | A, B, C, E, F, G, H, I, J, K, L, M |
| ISA 201 | 5 sections | A, D, H, I, K |
| MKT 201 | 4 sections | A, B, E, H |

Note: FIN 310 drops to a single section. Both Kumar sections are on TF and were filtered out. Only the TBA section on MR survives. Owen will not get Kumar with Fridays off — this is a real trade-off the solver surfaces.

---

## Step 3: Generate combinations

The solver computes the product:

```
1 (FIN 310) x 7 (GEN 201) x 11 (ACG 203) x 5 (ISA 201) x 4 (MKT 201) = 1,540 combinations
```

This is well under the `MAX_COMBINATIONS = 10,000` safety cap, so all 1,540 are evaluated.

The solver logs:

```
solver.search_space: requirements=5, pool_sizes=[1, 7, 11, 5, 4], total_combinations=1540
```

---

## Step 4: Check conflicts

For each of the 1,540 combinations, the solver checks every pair of sections for time conflicts.

With 5 sections per combination, there are `C(5,2) = 10` pairwise checks per combination.

### Example: a conflict

Consider the combination:
- FIN 310 sec C: **MR 15:55-17:10**
- GEN 201 sec K: **MR 15:55-17:10**
- ACG 203 sec I: MR 09:35-10:50
- ISA 201 sec H: MR 12:45-14:00
- MKT 201 sec A: W 08:00-10:40

The solver checks FIN 310 sec C vs GEN 201 sec K:

```
shared_days = {M, R} & {M, R} = {M, R}  -- shared days exist
a_start = to_minutes("15:55") = 955
a_end   = to_minutes("17:10") = 1030
b_start = to_minutes("15:55") = 955
b_end   = to_minutes("17:10") = 1030

955 < 1030 AND 955 < 1030 --> True --> CONFLICT
```

This combination is discarded immediately. The solver does not check the remaining 8 pairs.

### Example: no conflict (back-to-back)

Consider:
- ACG 203 sec I: MR **09:35-10:50**
- ISA 201 sec I: MR **11:10-12:25**

```
shared_days = {M, R} & {M, R} = {M, R}  -- shared days exist
a_start = to_minutes("09:35") = 575
a_end   = to_minutes("10:50") = 650
b_start = to_minutes("11:10") = 670
b_end   = to_minutes("12:25") = 745

575 < 745 = True
670 < 650 = False --> NOT a conflict
```

These sections are back-to-back with a 20-minute gap (10:50 to 11:10). The half-open interval rule correctly identifies them as non-conflicting.

### Example: adjacent at exact boundary

If two sections ended and started at exactly the same time (e.g., one ending at 10:50, another starting at 10:50):

```
a_end = 650, b_start = 650
650 < 650 = False --> NOT a conflict
```

The half-open interval rule means `[09:35, 10:50)` and `[10:50, 12:25)` do not overlap. This is correct for Bryant's schedule.

---

## Step 5: Score the valid combinations

Suppose one valid combination is:

| Section | Course | Instructor | Days | Time | Seats | Credits |
|---|---|---|---|---|---|---|
| FIN 310 sec C | FIN 310 | TBA | MR | 15:55-17:10 | 22/30 | 3 |
| GEN 201 sec D | GEN 201 | Zammarelli, Thomas | MR | 11:10-12:25 | 18/30 | 3 |
| ACG 203 sec I | ACG 203 | Beausejour, David | MR | 09:35-10:50 | 22/30 | 3 |
| ISA 201 sec H | ISA 201 | Chaudhury, Abhijit | MR | 12:45-14:00 | 24/30 | 3 |
| MKT 201 sec A | MKT 201 | Bell-Lombardo, Hannah | W | 08:00-10:40 | 27/30 | 3 |

**Scoring breakdown:**

### 1. Credit match

```
total_credits = 3 + 3 + 3 + 3 + 3 = 15
credit_diff = |15 - 15| = 0
0 <= 1 --> score += 10.0
```

### 2. Instructor preferences

Owen listed `preferred_instructors=["Kumar"]`. None of these sections are taught by Kumar (the Kumar sections were filtered out by the Friday block). No avoided instructors.

```
No matches --> score += 0.0
```

### 3. Seat availability

Check each section for >50% open:
- FIN 310 sec C: 22/30 = 73% > 50% --> +1
- GEN 201 sec D: 18/30 = 60% > 50% --> +1
- ACG 203 sec I: 22/30 = 73% > 50% --> +1
- ISA 201 sec H: 24/30 = 80% > 50% --> +1
- MKT 201 sec A: 27/30 = 90% > 50% --> +1

```
score += 5.0
```

### 4. Category balance

Requirements covered:
- `fin_310` -> category `major`
- `gen_201` -> category `general_education`
- `acg_203` -> category `business_core`
- `isa_201` -> category `business_core`
- `mkt_201` -> category `business_core`

Distinct categories: {major, general_education, business_core} = 3

```
score += 3 * 3.0 = 9.0
```

### Total score

```
10.0 + 0.0 + 5.0 + 9.0 = 24.0
```

### Metadata

```python
active_days = {M, R, W}   # MR from four sections, W from MKT 201
days_off = [T, F]          # Tuesday and Friday are free
earliest_class = "08:00"   # MKT 201 sec A starts at 8:00 on Wednesday
latest_class = "17:10"     # FIN 310 sec C ends at 17:10 on MR
```

---

## Step 6: Return top 3

After evaluating all 1,540 combinations, the solver:

1. Sorts valid combinations by score (descending).
2. Deduplicates by CRN set — if two combinations have the exact same set of CRNs, only the first is kept.
3. Takes the top 3.
4. Wraps each in a `ScheduleOption` with `rank=1`, `rank=2`, `rank=3`.

The solver logs:

```
solver.completed: combinations_evaluated=1540, valid_combinations=47, returned=3, duration_ms=280
```

Of the 1,540 total combinations, 47 passed the conflict check and credit range filter. The top 3 distinct schedules are returned to the caller.

---

## What happens next

The 3 `ScheduleOption` objects are passed to the Claude layer (`backend/app/claude_client.py`), which:

1. Calls `explain_schedule()` for each — generating a two-sentence paragraph.
2. Calls `rank_schedules()` once with all three — Claude may reorder the solver's ranking based on qualitative factors.
3. Returns the final 3 options with explanations and updated ranks.

See [Feature 06 — Schedule Ranking](../06-schedule-ranking/readme.md) for that flow.

---

## Performance notes

- **1,540 combinations, ~280ms.** The solver is CPU-bound and single-threaded. For Owen's inputs this is fast enough that the total `/api/generate-schedules` response time is dominated by the Claude API calls, not the solver.
- **The safety cap rarely triggers.** With 5 requirements and typical section counts (3-12 per requirement), the product space stays well under 10,000. The cap would trigger with 6+ requirements each having 5+ sections, which is unusual for a single semester.
- **No caching.** The solver re-runs from scratch on every request. For a hackathon build with no persistent storage, this is the right choice. A production version could cache expansion results since the catalog does not change within a registration period.
