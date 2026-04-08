# Feature 07 — Calendar UI

The frontend renders the solver's output as weekly calendar grids. Each of the three schedules is displayed on its own card with a visual layout that shows exactly when every class meets during the week.

## Stack

- **Next.js 15** — App Router with server components where possible
- **Tailwind CSS** — Utility-first styling with custom design tokens
- **shadcn/ui** — Component primitives (dialogs, buttons) restyled to match the editorial minimalism aesthetic
- **Zustand** — Client-side state management for audit data, preferences, and generated schedules
- **Geist / Instrument Serif / Geist Mono** — The typographic system (see ADR 0005)

## Three pages

| Route | Purpose |
|---|---|
| `/` | Homepage with the Degree Works upload zone. Student uploads a screenshot, Claude Vision parses it. |
| `/preferences` | Captures target credits, blocked days, time windows, instructor preferences, and requirement selection. |
| `/schedules` | Renders the three generated schedules as ScheduleCards with weekly calendar grids. |

## Key components

| Component | Role |
|---|---|
| `WeeklyCalendar.tsx` | 5-column grid (Mon-Fri), rows at 30-min intervals from 8:00 AM to 9:00 PM. Each section is rendered as a `CourseBlock` positioned absolutely within the grid. |
| `CourseBlock.tsx` | A colored block representing one section on the calendar. Displays course code (monospace), instructor last name, and room. Height is proportional to class duration. |
| `ScheduleCard.tsx` | A double-bezel card containing the WeeklyCalendar plus metadata: total credits, days off, earliest/latest class, and Claude's two-sentence explanation. |
| `UploadZone.tsx` | Drag-and-drop zone on the homepage for the Degree Works screenshot. |
| `EyebrowTag.tsx` | Uppercase pill tag above headlines (e.g., "RANK #1"). |
| `PillButton.tsx` | Primary CTA with button-in-button trailing arrow. |

## Design direction

Editorial minimalism with a warm monochrome palette. Background `#FAFAF7`, text `#1A1A1A`, accent `#B8985A`. Instrument Serif for headings, Geist for body, Geist Mono for course codes and CRNs. See ADR 0005 (`docs/adr/0005-editorial-minimalism-design.md`).

## AIE documentation

- [1-align.md](1-align.md) — Why a visual calendar grid is the right UI for schedule display
- [2-construct.md](2-construct.md) — Component architecture, positioning logic, and design tokens
- [3-execute.md](3-execute.md) — Data flow from API response to rendered cards
