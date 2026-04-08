# 07 Calendar UI — Execute

> HOW does the data flow from the API response to the rendered schedule cards?

---

## The full data flow

```
POST /api/generate-schedules
         │
         ▼
  API returns GenerateSchedulesResponse
  (3 ScheduleOption objects with explanations and ranks)
         │
         ▼
  Zustand store receives and stores schedules
         │
         ▼
  /schedules page reads from store
         │
         ▼
  Maps each ScheduleOption to a ScheduleCard
         │
         ▼
  Each ScheduleCard renders a WeeklyCalendar
         │
         ▼
  WeeklyCalendar positions CourseBlocks on the grid
         │
         ▼
  Student sees three visual schedules with explanations
```

---

## Step 1: API response arrives

The frontend calls `POST /api/generate-schedules` with the parsed audit and student preferences. The response is a JSON object:

```json
{
  "schedules": [
    {
      "rank": 1,
      "sections": [
        {
          "crn": "1047",
          "course_code": "FIN 310",
          "title": "Intermediate Corporate Finance",
          "section": "C",
          "instructor": null,
          "meetings": [{"days": ["M", "R"], "start": "15:55", "end": "17:10"}],
          "credits": 3.0,
          "seats_open": 22,
          "seats_total": 30
        },
        {
          "crn": "1688",
          "course_code": "GEN 201",
          "title": "Intercultural Communication",
          "section": "D",
          "instructor": "Zammarelli, Thomas",
          "meetings": [{"days": ["M", "R"], "start": "11:10", "end": "12:25"}],
          "credits": 3.0,
          "seats_open": 18,
          "seats_total": 30
        },
        {
          "crn": "1220",
          "course_code": "ACG 203",
          "title": "Prin. of Financial Accounting",
          "section": "I",
          "instructor": "Beausejour, David",
          "meetings": [{"days": ["M", "R"], "start": "09:35", "end": "10:50"}],
          "credits": 3.0,
          "seats_open": 22,
          "seats_total": 30
        },
        {
          "crn": "1147",
          "course_code": "ISA 201",
          "title": "Intro to Information Tech and Analytics",
          "section": "H",
          "instructor": "Chaudhury, Abhijit",
          "meetings": [{"days": ["M", "R"], "start": "12:45", "end": "14:00"}],
          "credits": 3.0,
          "seats_open": 24,
          "seats_total": 30
        },
        {
          "crn": "1093",
          "course_code": "MKT 201",
          "title": "Foundations of Marketing Management",
          "section": "A",
          "instructor": "Bell-Lombardo, Hannah",
          "meetings": [{"days": ["W"], "start": "08:00", "end": "10:40"}],
          "credits": 3.0,
          "seats_open": 27,
          "seats_total": 30
        }
      ],
      "requirements_satisfied": ["fin_310", "gen_201", "acg_203", "isa_201", "mkt_201"],
      "total_credits": 15,
      "days_off": ["T", "F"],
      "earliest_class": "08:00",
      "latest_class": "17:10",
      "score": 24.0,
      "explanation": "This puts all four of your MR classes back-to-back from Beausejour at 9:35 through Chaudhury at 14:00, with Zammarelli for GEN 201 in between, leaving you Tuesdays and Fridays completely free. Bell-Lombardo's Wednesday morning MKT 201 is the only non-MR class, and all five sections have plenty of seats."
    }
  ],
  "solver_stats": {
    "combinations_evaluated": 1540,
    "valid_combinations": 47,
    "duration_ms": 280
  }
}
```

---

## Step 2: Zustand store receives the response

The `frontend/lib/store.ts` Zustand store holds the application state across pages. When the API response arrives, the store is updated:

```typescript
// Simplified store shape
interface PathfinderStore {
  audit: DegreeAudit | null;
  preferences: SchedulePreferences;
  schedules: ScheduleOption[];
  solverStats: SolverStats | null;
  isLoading: boolean;

  setAudit: (audit: DegreeAudit) => void;
  setPreferences: (prefs: SchedulePreferences) => void;
  setSchedules: (schedules: ScheduleOption[], stats: SolverStats) => void;
}
```

After `setSchedules()` is called, the store holds three `ScheduleOption` objects sorted by rank. The router navigates to `/schedules`.

---

## Step 3: /schedules page maps options to cards

The `/schedules` page (`frontend/app/schedules/page.tsx`) reads the schedules from the Zustand store and maps each one to a `ScheduleCard` component:

```tsx
export default function SchedulesPage() {
  const { schedules, solverStats } = usePathfinderStore();

  return (
    <main className="min-h-screen bg-[#FAFAF7] py-24 px-8">
      <h1 className="font-display text-5xl text-[#1A1A1A] mb-16">
        Your schedules
      </h1>

      <div className="flex flex-col gap-8">
        {schedules.map((schedule, index) => (
          <ScheduleCard
            key={schedule.rank}
            schedule={schedule}
            index={index}
          />
        ))}
      </div>
    </main>
  );
}
```

The three cards are laid out vertically with `gap-8` between them. Each card receives its `index` (0, 1, 2) for stagger animation.

---

## Step 4: ScheduleCard renders WeeklyCalendar

Each `ScheduleCard` wraps the schedule's sections in a `WeeklyCalendar`, along with metadata and the explanation.

The card renders in this order:

1. **EyebrowTag** — "RANK #1" / "RANK #2" / "RANK #3" using `schedule.rank`
2. **WeeklyCalendar** — the visual grid with all `schedule.sections`
3. **Metadata row** — three items displayed inline:
   - Total credits: `schedule.total_credits` (e.g., "15 credits")
   - Days off: `schedule.days_off.join(", ")` (e.g., "Days off: T, F")
   - Time range: `schedule.earliest_class` to `schedule.latest_class` (e.g., "8:00 AM - 5:10 PM")
4. **Explanation** — `schedule.explanation` rendered as a paragraph in Geist, secondary text color
5. **PillButton** — "Use this schedule" CTA that opens the CRN dialog

---

## Step 5: WeeklyCalendar positions each CourseBlock

For each section in the schedule, the WeeklyCalendar iterates over the section's meetings. For each meeting, it iterates over the meeting's days. For each day, it creates a CourseBlock with computed position.

### Positioning logic

```typescript
const GRID_START_MINUTES = 480;  // 08:00
const PX_PER_MINUTE = 1.2;

function positionBlock(meeting: Meeting, day: string) {
  const column = { M: 0, T: 1, W: 2, R: 3, F: 4 }[day];
  const startMin = toMinutes(meeting.start);
  const endMin = toMinutes(meeting.end);

  return {
    column,
    top: (startMin - GRID_START_MINUTES) * PX_PER_MINUTE,
    height: (endMin - startMin) * PX_PER_MINUTE,
  };
}
```

### Worked example: Owen's Schedule A

The calendar processes 5 sections with a total of 6 meeting-day pairs (4 sections on MR = 8 blocks, 1 section on W = 1 block, total 9 CourseBlocks):

| Section | Day | Column | Start (min) | Top (px) | Duration (min) | Height (px) |
|---|---|---|---|---|---|---|
| ACG 203 sec I | M | 0 | 575 | 114.0 | 75 | 90.0 |
| ACG 203 sec I | R | 3 | 575 | 114.0 | 75 | 90.0 |
| GEN 201 sec D | M | 0 | 670 | 228.0 | 75 | 90.0 |
| GEN 201 sec D | R | 3 | 670 | 228.0 | 75 | 90.0 |
| ISA 201 sec H | M | 0 | 765 | 342.0 | 75 | 90.0 |
| ISA 201 sec H | R | 3 | 765 | 342.0 | 75 | 90.0 |
| FIN 310 sec C | M | 0 | 955 | 570.0 | 75 | 90.0 |
| FIN 310 sec C | R | 3 | 955 | 570.0 | 75 | 90.0 |
| MKT 201 sec A | W | 2 | 480 | 0.0 | 160 | 192.0 |

The result: columns 0 (Mon) and 3 (Thu) have four stacked blocks with gaps between them. Column 2 (Wed) has one tall block at the top. Columns 1 (Tue) and 4 (Fri) are empty — visually confirming Owen's days off.

---

## Step 6: "Use this schedule" flow

When the student clicks the PillButton on a ScheduleCard:

1. A shadcn/ui `Dialog` opens with a centered modal.
2. The dialog header says "Register for these CRNs".
3. The body lists each section's CRN, course code, and section letter in a monospace grid:

```
CRN    Course     Section
─────────────────────────
1047   FIN 310    C
1688   GEN 201    D
1220   ACG 203    I
1147   ISA 201    H
1093   MKT 201    A
```

4. A "Copy CRNs" button copies the CRN values (`1047 1688 1220 1147 1093`) to the clipboard using the Clipboard API.
5. Instructional text below says: "Paste these into Banner Self-Service to register."

The student can then open Banner in another tab and register with the exact CRNs. The entire Pathfinder flow — from uploading a Degree Works screenshot to having CRNs ready to register — is completed.

---

## Staggered reveal animation

The three ScheduleCards animate in with a cascade effect when the page loads:

```tsx
<div
  className={cn(
    "transform transition-all duration-[800ms]",
    "translate-y-16 blur-md opacity-0",
    isVisible && "translate-y-0 blur-0 opacity-100",
    index === 0 && "delay-100",
    index === 1 && "delay-200",
    index === 2 && "delay-300",
  )}
>
  <ScheduleCard schedule={schedule} index={index} />
</div>
```

The animation sequence:
1. **100ms** — Card 1 (Rank #1) begins fading in from below with blur
2. **200ms** — Card 2 (Rank #2) begins its entrance
3. **300ms** — Card 3 (Rank #3) begins its entrance
4. **900ms** — Card 1 finishes its 800ms transition
5. **1000ms** — Card 2 finishes
6. **1100ms** — Card 3 finishes

The easing is `cubic-bezier(0.32, 0.72, 0, 1)` — an asymmetric ease-out that feels physical. The blur resolution (going from `blur-md` to `blur-0`) adds a depth-of-field effect that makes the entrance feel like a camera focusing.

This is the one deliberately kinetic moment in the app. The rest of the interface is static and typographically driven. The stagger on the schedules page is the payoff — the moment the student sees their options materialize.

---

## Responsive behavior

The calendar grid is designed for desktop-first (the primary use case is students on laptops during advising or registration). On narrow screens:

- The grid columns compress proportionally.
- CourseBlock text truncates to course code only (instructor and room are hidden below a breakpoint).
- The metadata row stacks vertically instead of inline.
- The stagger animation is preserved — it works equally well on mobile.

The minimum usable width is approximately 768px (iPad portrait). Below that, the calendar becomes too compressed to read. A future mobile version would use a daily view instead of the weekly grid.

---

## State management detail

The Zustand store persists across page navigations within the same session. The flow is:

1. `/` — Student uploads audit. Store receives `DegreeAudit`.
2. `/preferences` — Student sets preferences. Store receives `SchedulePreferences`.
3. `/schedules` — Page reads `schedules` from store. If empty (e.g., direct navigation), the page shows a redirect prompt to start from `/`.

No data is persisted to localStorage or a database in the hackathon build. Refreshing the page on `/schedules` clears the store and the student must start over. This is acceptable for a demo; a production build would persist to Supabase.

---

## Performance

- **Rendering 3 cards with 5 sections each** = 15 sections total, producing approximately 20-25 CourseBlock components. React handles this trivially — no virtualization needed.
- **Animation** — CSS transitions only, no JavaScript animation library. The browser's compositor handles the transforms.
- **Font loading** — Instrument Serif, Geist, and Geist Mono are loaded via `next/font/google`, which inlines font files at build time. No FOUT (flash of unstyled text) on the schedules page.
