# ADR 0005 — Editorial Minimalism as the Design Direction

**Status:** Accepted
**Date:** 2026-04-08
**Deciders:** Owen Ash

---

## Context

Pathfinder has one shot at making a first impression. When a judge opens the app for the first time, they form a trust judgment about the product in roughly two seconds — before reading any copy, before trying any feature, before understanding what the thing actually does. That trust judgment is almost entirely driven by visual design. A polished, intentional interface reads as "real product built by someone who knows what they're doing." A generic interface reads as "hackathon project built in a rush with whatever default template was available."

At an AI hackathon, the second category is the baseline. Most projects will ship with some combination of: Tailwind's default Inter font, Lucide icons, centered hero sections on pure white backgrounds, `shadow-lg` on every card, purple-to-blue gradients in the header, and Bootstrap-style three-column grids. Shadcn/ui's default aesthetic is fine but unremarkable, and without conscious design direction it converges on a look that's visually identical to half the projects in the room.

Pathfinder has a specific content profile that suggests a specific design response. It's a tool for academic planning. It deals with structured data (courses, professors, times, requirements). It's used by students making real decisions about their semesters. The aesthetic needs to read as *trustworthy* and *substantive*, not flashy or toy-like. It needs to feel like something a student would actually use for a real semester, not a hackathon demo.

That framing narrows the design space considerably. Glassmorphism, neon gradients, 3D hero animations, playful illustrations, and maximalist dashboards are all wrong for this content. What's right is something closer to editorial design — Linear's interface, Notion's restraint, a well-designed academic journal. Warm, monochromatic, typographically driven, confident in its use of whitespace, and boring in exactly the ways that read as serious.

---

## Decision

Pathfinder adopts an **editorial minimalism** aesthetic with a warm monochrome palette and one accent color. The direction is locked across all pages, components, and states. The core decisions:

### Color system

- **Background:** `#FAFAF7` — warm cream, explicitly not pure white. Pure white (`#FFFFFF`) reads as default and unintentional. `#FAFAF7` reads as chosen.
- **Primary text:** `#1A1A1A` — near-black with enough warmth to sit well on the cream background. Never pure black.
- **Secondary text:** `#787774` — muted gray for captions, metadata, and de-emphasized content.
- **Accent:** `#B8985A` — a Bryant-adjacent gold/bronze, used only for primary CTAs and active states. Every other color element is monochrome.

**Banned colors:** purple gradients, blue gradients, any bright saturated primary color for large surfaces, and in particular the "AI purple" (`#6366F1`-ish) that has become the instant tell of a ChatGPT-templated frontend.

### Typography

- **Display:** Instrument Serif for hero headlines and section titles. Serifs are unusual in SaaS interfaces and immediately signal editorial intent.
- **UI:** Geist for body text, labels, and interface elements. Clean geometric sans-serif with enough character to not feel like Inter.
- **Monospace:** Geist Mono for course codes (FIN 310), CRNs, and tabular data. The monospace treatment gives structured data its own visual register and reads as "this is information, not decoration."

**Banned fonts:** Inter, Roboto, Arial, Helvetica, Open Sans. Any font that ships as a browser default is banned for this project.

### Layout

- **Asymmetric splits.** Hero sections use a 50/50 split — massive editorial typography on the left, interactive content on the right. No centered heroes anywhere in the app.
- **Generous whitespace.** Section padding is `py-24` to `py-32`, not the `py-8` or `py-12` that's typical for cramped hackathon layouts.
- **Bento grids where lists would be.** The three schedule cards on the schedules page are laid out in a Z-Axis Cascade — slightly overlapping, subtly rotated, with the top-ranked card at the front. This is the one place the design gets playful.

### Component architecture

- **Double-bezel cards.** From the `high-end-visual-design` skill: every major card has an outer shell (with hairline border and background tint) containing an inner core (with its own background and a mathematically smaller border radius). This nested architecture creates physical depth without relying on drop shadows.
- **Pill buttons with button-in-button arrows.** Primary CTAs are fully rounded pills with a nested circular arrow icon flush-right inside the button. On hover, the outer button scales down slightly while the inner arrow translates diagonally. Industrial, specific, unmistakable.
- **Phosphor Light icons.** The Phosphor icon set at Light weight only. Never Lucide, never Material Icons, never FontAwesome. Phosphor Light has a precise, editorial feel that matches the serif typography.

### Motion

- **Custom cubic-bezier curves.** All transitions use `cubic-bezier(0.32, 0.72, 0, 1)` — an asymmetric ease-out that feels physical. Default `ease-in-out` is banned.
- **Scroll-triggered entry.** Elements fade up with blur resolving as they enter the viewport — `translate-y-16 blur-md opacity-0` to `translate-y-0 blur-0 opacity-100` over 800ms.
- **Staggered reveals on the schedules page.** The three schedule cards animate in with 100ms delays between them, creating a rhythmic cascade that draws the eye through the options.

---

## Consequences

### Positive

- **Instant differentiation.** In a room of 20 hackathon projects, Pathfinder will not look like any of them. Serif headlines, warm cream backgrounds, and asymmetric layouts are rare in the hackathon format. The design reads as "someone thought carefully about this" before a judge reads a single word.
- **Matches the content.** Academic planning is substantive, data-heavy work. An editorial aesthetic is the visual equivalent of the content: serious, considered, calm. Flashy aesthetics would actively fight the product.
- **Enforceable through skills.** The `high-end-visual-design`, `design-taste-frontend`, and `minimalist-ui` skills together provide a complete rulebook that Claude Code can follow. The design direction isn't a vibe; it's a set of concrete constraints that can be checked mechanically.
- **Fast to build.** Restrained designs require fewer components, less animation code, and simpler layouts than maximalist designs. Shipping editorial minimalism in three hours is realistic. Shipping a cinematic 3D hero in three hours is not.
- **Ages well.** Editorial minimalism has been current for roughly 15 years and doesn't look dated. The hackathon demo will still look good in six months when Pathfinder is being used as a portfolio piece.

### Negative

- **Higher execution bar.** Minimalist designs are unforgiving — every spacing decision, every font weight, every color value has to be right because there's nothing else to hide behind. A single `shadow-md` in the wrong place reads as cheap. A maximalist design can absorb one bad decision; a minimalist design cannot.
- **Less obvious "wow moment" on first load.** Flashy designs get an immediate audible reaction from judges. Editorial designs are slower burns — the judge notices something is off (in a good way) and figures out why over the course of the demo. Mitigated by the schedule card cascade animation, which is the one deliberately kinetic moment in the app.
- **Depends on font loading working.** Instrument Serif and Geist both need to load from Google Fonts or a local file. If font loading fails, the fallback is system-default fonts, which would undermine the entire aesthetic. Mitigated by using `next/font/google` which inlines fonts at build time.
- **Locks out some visual techniques.** If halfway through the build I decide I want a gradient mesh background or a 3D calendar viewer, the design system says no. That's the point — locked decisions prevent scope creep — but it means creative ideas that would fit a different aesthetic get rejected.

### How this gets enforced

The design system is enforced through three layers:

1. **Skills loaded in CLAUDE.md.** The four frontend skills are referenced by path at the top of the Claude Code session context. Claude Code is instructed to read them before writing any UI code.
2. **Explicit anti-patterns in CLAUDE.md.** The "Banned" section lists every pattern that cannot appear in the code. When Claude Code is tempted to drop an Inter font import or a `shadow-md`, the instructions say no.
3. **The polish pass.** At the end of the build, `redesign-existing-projects` runs a full audit against the rendered UI and reports any violations of the design system. This is the last-mile quality gate before the demo.

---

## Alternatives Considered

**Brutalist design.** The `industrial-brutalist-ui` skill is available and could produce a striking, memorable interface. Rejected because brutalism fights the content — academic planning should feel trustworthy and calm, not aggressive and raw. A brutalist aesthetic would make Pathfinder feel like a protest zine, not a planning tool.

**Glassmorphism / modern SaaS dashboard.** The dominant aesthetic on Dribbble for the past three years: frosted glass cards, subtle gradients, rounded corners, purple accents. Rejected because it's the exact aesthetic every other hackathon project will ship. Differentiation is the goal; convergence is the failure mode.

**Playful illustrated style.** A Notion-early or Duolingo-style aesthetic with custom illustrations, soft pastels, and friendly iconography. Rejected because illustration work is time-intensive and I can't produce quality illustrations in the build window. Also fights the content — academic planning should feel confident, not cute.

**Shadcn defaults with no customization.** The path of least resistance: install shadcn, use the default theme, write components. Rejected because the shadcn default is a solid baseline but unremarkable, and Pathfinder needs to be more than unremarkable. Shadcn is being used as a component library, not a theme — the typography, colors, and layout decisions override the defaults.

**Dark mode.** Dark mode is visually striking and popular. Rejected for this build because it would require designing both light and dark variants of every component, doubling the work. A future version could add dark mode; the hackathon version is light-only with the warm cream background.

---

## References

- `/mnt/skills/user/high-end-visual-design/SKILL.md` — the Awwwards-tier agency design protocol
- `/mnt/skills/user/design-taste-frontend/SKILL.md` — engineering discipline rules
- `/mnt/skills/user/minimalist-ui/SKILL.md` — the editorial minimalism skill
- `/mnt/skills/public/frontend-design/SKILL.md` — the base anti-slop skill
- `CLAUDE.md` — the operational version of these rules for Claude Code sessions
- `frontend/tailwind.config.ts` — the concrete implementation of the design tokens
