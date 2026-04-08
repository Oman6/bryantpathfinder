# 07 Calendar UI — Align

> WHY does Pathfinder render schedules as weekly calendar grids?

---

## The mental model

Every college student thinks about their schedule as a weekly grid. Monday through Friday, morning through evening, with colored blocks representing classes. This is the universal mental model for class schedules — it is how every university's registration system displays them, how students sketch them on paper during advising, and how they describe them to friends ("I have a three-hour gap on Tuesdays").

A list of five courses with their days and times is data. A weekly calendar grid is understanding. The visual form immediately answers the questions students actually ask:

- **"Do I have gaps?"** Visible as empty space between blocks on a given day.
- **"When do I start?"** The topmost block on any day.
- **"When am I done?"** The bottommost block on any day.
- **"Which days are free?"** Columns with no blocks.
- **"Is this schedule crammed or spread out?"** The overall density of the grid.
- **"Do I have back-to-back classes?"** Adjacent blocks with no gap.

None of these questions can be answered at a glance from a text list. All of them can be answered in under two seconds from a calendar grid.

## Why three cards

Pathfinder generates three schedule options, not one. The multi-option design serves two purposes:

### 1. It surfaces trade-offs

Owen's preferences include Fridays off and a preference for Professor Kumar. But both Kumar sections of FIN 310 meet on Tuesdays and Fridays. A single "optimal" schedule would hide this trade-off — it would either silently drop Kumar or silently include Friday classes. Three options let the student see the trade-off explicitly:

- Schedule 1: Fridays off, TBA instructor for FIN 310
- Schedule 2: Kumar for FIN 310, but meets on Fridays
- Schedule 3: A different arrangement with different trade-offs

### 2. It builds trust

A tool that returns one answer feels like a black box. A tool that returns three ranked options with explanations feels like a knowledgeable advisor presenting choices. The student retains agency — they are choosing, not being told.

## Why not a list or table

Several alternative presentation formats were considered and rejected.

### Plain text list

```
1. FIN 310 sec C — MR 15:55-17:10 — TBA
2. GEN 201 sec D — MR 11:10-12:25 — Zammarelli
3. ACG 203 sec I — MR 09:35-10:50 — Beausejour
4. ISA 201 sec H — MR 12:45-14:00 — Chaudhury
5. MKT 201 sec A — W 08:00-10:40 — Bell-Lombardo
```

This is how Banner Self-Service shows the schedule. It is functional but requires mental effort to visualize the weekly layout. The student has to parse day abbreviations, convert 24-hour times, and mentally reconstruct the grid. This is the experience Pathfinder exists to replace.

### Sortable table

A table with columns for course, instructor, days, time, and seats is useful for comparing individual sections but does not show the schedule as a whole. The student sees five rows, not a week.

### Daily timeline (vertical)

A single vertical timeline for one day at a time (like Google Calendar's day view) would require clicking through five tabs. The weekly view shows everything at once.

## The editorial treatment

The schedule cards follow the editorial minimalism design direction documented in ADR 0005 (`docs/adr/0005-editorial-minimalism-design.md`). Key decisions:

### Double-bezel cards

Each ScheduleCard uses the double-bezel architecture: an outer shell with a hairline border and background tint containing an inner core with its own background and a mathematically smaller border radius. This creates physical depth without drop shadows.

### Staggered reveal

The three cards animate in with a rhythmic stagger: the first card appears, then the second 100ms later, then the third 100ms after that. This cascade draws the eye through the options in rank order and creates a sense of considered presentation rather than everything appearing at once.

### Monospace course codes

Course codes like `FIN 310` and CRNs like `1047` are rendered in Geist Mono. This gives structured data its own visual register — it reads as "this is information, not decoration." The monospace treatment is applied consistently across the entire application: course codes on the calendar blocks, CRNs in the registration dialog, and requirement IDs on the preferences page.

### Warm background

The calendar grid sits on the `#FAFAF7` warm cream background, not pure white. The course blocks use tinted variations of the same warm palette. This is a deliberate departure from the pure-white grid that most scheduling tools use, and it is one of the visual details that makes Pathfinder feel considered rather than default.

## What the grid communicates that the explanation does not

Claude's two-sentence explanation is good at summarizing: "This gives you Tuesdays and Fridays off" or "nothing starts before 9:35." But the explanation cannot convey schedule shape — the visual density of a Monday versus a Wednesday, the size of a gap between classes, the feel of a 2.5-hour Wednesday marketing block compared to a 1:15 MR class.

The calendar grid and the text explanation are complementary. The grid shows the shape. The explanation tells the story. Together they give the student everything they need to choose.

## References

- `docs/adr/0005-editorial-minimalism-design.md` — the design direction
- `frontend/components/WeeklyCalendar.tsx` — the calendar grid component
- `frontend/components/ScheduleCard.tsx` — the card wrapper
- `frontend/components/CourseBlock.tsx` — the individual course block
- [2-construct.md](2-construct.md) — component architecture and positioning math
- [3-execute.md](3-execute.md) — data flow from API to rendered cards
