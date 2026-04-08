# 07 Calendar UI — Construct

> WHAT are the components, positioning logic, and design tokens?

---

## Component architecture

The schedule display is built from four nested components, each with a single responsibility.

### WeeklyCalendar.tsx

The core grid component. Renders a 5-column layout (Monday through Friday) with time rows at 30-minute intervals from 08:00 to 21:00 (8 AM to 9 PM).

**Structure:**

```
┌──────────────────────────────────────────────────────┐
│  Time │  Mon   │  Tue   │  Wed   │  Thu   │  Fri   │
│───────┼────────┼────────┼────────┼────────┼────────│
│  8:00 │        │        │ ██████ │        │        │
│  8:30 │        │        │ ██████ │        │        │
│  9:00 │ ██████ │        │ ██████ │ ██████ │        │
│  9:30 │ ██████ │        │        │ ██████ │        │
│ 10:00 │ ██████ │        │        │ ██████ │        │
│ 10:30 │ ██████ │        │        │ ██████ │        │
│  ...  │  ...   │  ...   │  ...   │  ...   │  ...   │
└──────────────────────────────────────────────────────┘
```

Each column is a `relative`-positioned container. CourseBlock components are positioned `absolute` within their column based on start time and duration.

**Props:**

| Prop | Type | Description |
|---|---|---|
| `sections` | `Section[]` | The sections to render on the grid |
| `startHour` | `number` | Grid start hour (default: 8) |
| `endHour` | `number` | Grid end hour (default: 21) |

**Day-to-column mapping:**

| Day code | Column index | Label |
|---|---|---|
| `M` | 0 | Mon |
| `T` | 1 | Tue |
| `W` | 2 | Wed |
| `R` | 3 | Thu |
| `F` | 4 | Fri |

### CourseBlock.tsx

A single colored block representing one section on one day. For multi-day sections (e.g., MR 09:35-10:50), the component is rendered once per day — the same section produces two CourseBlock instances, one in the Mon column and one in the Thu column.

**Visual contents (top to bottom):**

1. **Course code** — `FIN 310` in Geist Mono, semi-bold
2. **Instructor** — last name only (e.g., "Kumar") in Geist, regular weight
3. **Room** — building and room number if available, in Geist, secondary text color

**Sizing:**

The block's height is proportional to class duration. A 75-minute class (e.g., 09:35-10:50) is taller than a 50-minute class. A 160-minute class (e.g., MKT 201 W 08:00-10:40) is proportionally taller still.

**Color:**

Each course gets a distinct color from a muted palette. The colors are assigned by index in the sections array, cycling through a predefined set that maintains readability against the warm background. Colors are tinted, low-saturation variants — no bright primaries, no gradients.

### ScheduleCard.tsx

A double-bezel card wrapping the WeeklyCalendar and schedule metadata.

**Layout:**

```
┌─ Outer shell ──────────────────────────────────────────────┐
│  ┌─ Inner core ──────────────────────────────────────────┐ │
│  │  EyebrowTag: "RANK #1"                                │ │
│  │                                                        │ │
│  │  ┌─ WeeklyCalendar ────────────────────────────────┐  │ │
│  │  │                                                  │  │ │
│  │  │  (the calendar grid with CourseBlocks)           │  │ │
│  │  │                                                  │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  │                                                        │ │
│  │  Metadata row:                                         │ │
│  │  15 credits  |  Days off: T, F  |  9:35 AM - 5:10 PM │ │
│  │                                                        │ │
│  │  Explanation:                                          │ │
│  │  "This puts all four of your MR classes back-to-back  │ │
│  │   from Beausejour at 9:35 through Chaudhury at..."    │ │
│  │                                                        │ │
│  │  ┌─────────────────────────────────┐                   │ │
│  │  │  Use this schedule        →     │  PillButton       │ │
│  │  └─────────────────────────────────┘                   │ │
│  └────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

**Double-bezel architecture:**

- **Outer shell:** `border` with `border-[#E8E8E3]` (hairline), `bg-[#F5F5F0]` (slightly darker than page background), `rounded-2xl`
- **Inner core:** `bg-[#FAFAF7]` (matches page background), `rounded-xl` (mathematically smaller radius than outer shell)
- The gap between outer and inner creates a visible "frame" effect without drop shadows

**Props:**

| Prop | Type | Description |
|---|---|---|
| `schedule` | `ScheduleOption` | The full schedule object with sections, metadata, and explanation |
| `index` | `number` | 0, 1, or 2 — used for stagger delay |

### EyebrowTag.tsx

An uppercase pill tag that sits above the card headline. Displays the rank: "RANK #1", "RANK #2", "RANK #3".

**Styling:** Uppercase, letter-spaced, Geist Mono, small text, border with muted color. No background fill — just outline.

### PillButton.tsx

The primary CTA at the bottom of each card. "Use this schedule" with a button-in-button trailing arrow.

**Structure:**

```
┌──────────────────────────────────────┐
│  Use this schedule     ┌────┐       │
│                        │  → │       │
│                        └────┘       │
└──────────────────────────────────────┘
```

The outer pill is `bg-[#1A1A1A]` (near-black) with white text. The inner arrow circle is `bg-[#B8985A]` (accent gold) with a white arrow icon. On hover, the outer pill scales down slightly while the inner circle translates diagonally — a subtle industrial interaction.

---

## Positioning math

The WeeklyCalendar positions each CourseBlock using absolute positioning within a relative container.

### Constants

```typescript
const GRID_START_HOUR = 8;         // 08:00 = top of grid
const GRID_START_MINUTES = 480;    // 8 * 60
const PX_PER_MINUTE = 1.2;        // 1.2px per minute of time
```

### Position calculation

For a section meeting from `start` to `end` on day `D`:

```typescript
const column = dayIndex(D);        // M=0, T=1, W=2, R=3, F=4

const startMinutes = toMinutes(start);  // e.g., "09:35" -> 575
const endMinutes = toMinutes(end);      // e.g., "10:50" -> 650
const duration = endMinutes - startMinutes;  // 75 minutes

const top = (startMinutes - GRID_START_MINUTES) * PX_PER_MINUTE;
// (575 - 480) * 1.2 = 114px from grid top

const height = duration * PX_PER_MINUTE;
// 75 * 1.2 = 90px tall
```

### Examples with real sections

| Section | Start | Duration | Top (px) | Height (px) |
|---|---|---|---|---|
| ACG 203 sec I (MR 09:35-10:50) | 575 min | 75 min | 114.0 | 90.0 |
| GEN 201 sec D (MR 11:10-12:25) | 670 min | 75 min | 228.0 | 90.0 |
| ISA 201 sec H (MR 12:45-14:00) | 765 min | 75 min | 342.0 | 90.0 |
| FIN 310 sec C (MR 15:55-17:10) | 955 min | 75 min | 570.0 | 90.0 |
| MKT 201 sec A (W 08:00-10:40) | 480 min | 160 min | 0.0 | 192.0 |

Notice that the MKT 201 block (160 minutes, 192px) is more than twice the height of the standard 75-minute blocks (90px). This proportional sizing immediately communicates that Wednesday's class is a long session.

### Grid total height

The grid spans from 08:00 (480 min) to 21:00 (1260 min) = 780 minutes.

```
780 * 1.2 = 936px total grid height
```

Time labels appear at 30-minute intervals along the left edge, giving the student a precise visual reference for when each class starts and ends.

---

## Design tokens

The full token set, as implemented in `frontend/tailwind.config.ts`:

### Colors

| Token | Hex | Usage |
|---|---|---|
| `background` | `#FAFAF7` | Page background, inner card core |
| `foreground` | `#1A1A1A` | Primary text, PillButton background |
| `secondary` | `#787774` | Captions, metadata, time labels |
| `accent` | `#B8985A` | PillButton arrow, active states, rank #1 tag border |
| `border` | `#E8E8E3` | Card outer shell, grid lines, dividers |
| `card-shell` | `#F5F5F0` | Outer bezel fill |

### Typography

| Token | Font | Usage |
|---|---|---|
| `font-display` | Instrument Serif | Hero headlines, section titles |
| `font-body` | Geist | Body text, labels, metadata, explanations |
| `font-mono` | Geist Mono | Course codes, CRNs, EyebrowTag text |

### Spacing

| Context | Value | Notes |
|---|---|---|
| Section padding | `py-24` to `py-32` | Between major page sections |
| Card gap | `gap-8` | Between the three ScheduleCards |
| Inner card padding | `p-6` to `p-8` | Inside the inner core |
| Bezel width | `p-2` | Gap between outer shell and inner core |

### Motion

| Property | Value |
|---|---|
| Easing | `cubic-bezier(0.32, 0.72, 0, 1)` |
| Entry animation | `translate-y-16 blur-md opacity-0` to `translate-y-0 blur-0 opacity-100` |
| Entry duration | `800ms` |
| Stagger delay | `delay-100`, `delay-200`, `delay-300` |

---

## "Use this schedule" dialog

When the student clicks the PillButton, a shadcn/ui `Dialog` opens showing the CRNs for all sections in the schedule. The CRNs are displayed in a monospace list that the student can copy and paste into Banner Self-Service.

```
Register for these CRNs in Banner:

1047  FIN 310  sec C
1688  GEN 201  sec D
1220  ACG 203  sec I
1147  ISA 201  sec H
1093  MKT 201  sec A
```

The dialog includes a "Copy CRNs" button that copies just the CRN numbers (space-separated) to the clipboard.
