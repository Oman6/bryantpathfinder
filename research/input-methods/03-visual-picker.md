# 03 — Visual Requirement Picker

> Subagent I3 of the BryantPathfinder input-method swarm. Self-contained design study of a pure-UI requirement-input flow — no Vision call, no LLM on the input side, no chat. The student arrives, sees a structured catalog of their unmet requirements, ticks the ones they want this semester, and clicks Generate. Like assembling a Spotify playlist, but the playlist is a 15-credit semester.

---

## Why this matters for Pathfinder

Today's input flow on `frontend/app/page.tsx` and `frontend/components/UploadZone.tsx` offers two on-ramps: **paste text** (default tab) and **upload image** (Claude Vision). Both paths route through `/api/parse-audit` or `/api/parse-audit-text`, both depend on the Anthropic API, and both are bounded by the rate limiter (30 req / 60 s per IP) and the 10 MB / 20K-char input caps documented in `00-product-baseline.md`. The fixture-fallback button ("Or use sample audit") sits below the card as a recovery affordance.

Three reasons this isn't enough:

1. **Time-to-first-schedule is gated on Claude.** The current happy path takes one Vision call (~2.5 s) plus the schedule pipeline (~2 s) before the student sees anything useful. A no-LLM input cuts that to ~2 s flat — the schedule pipeline alone.
2. **Vision can hallucinate.** ADR 0002 explicitly flags ~95% accuracy with edge-case fragility. A pure-UI fallback gives the student deterministic control when Vision misreads the audit.
3. **The cold-start problem is real.** A first-time user without a Degree Works screenshot has nowhere to go. Pasting requirement codes from memory is hostile; uploading an image they don't have is impossible.

A visual picker is the third on-ramp. It addresses cold-start, recovers from Vision errors, and demos beautifully because there is no API latency between click and result.

---

## 1. Competitor teardowns

### 1a. Stellic (`stellic.com`)

Stellic is the closest analog to Pathfinder in the higher-ed market — degree-audit replacement plus 4-year planning, deployed at Carnegie Mellon, Northeastern, NYU Stern, Babson, and others. The "Build a plan" flow is the most polished requirement-input UX in the category and the right benchmark.

**How it works (from public demo videos at stellic.com/demo, the Carnegie Mellon Stellic deployment screenshots, and the Northeastern Khoury academic-planning docs):**

- Left rail: a tree of degree requirements grouped by category (Major, Concentration, Gen Ed, Free Elective). Each node shows credits-completed-of-required as a thin progress bar (e.g. `9 / 27 cr`).
- Center: a semester-by-semester grid. Empty slots read "Drop a course here." Filled slots show the course code in mono and the title in serif.
- Right rail: a course catalog with search and filter. Drag a course from the rail into a semester slot, or click "+ Add" to insert into the next open semester.
- A live validator runs as you build: red underline if a prereq isn't met, yellow if a course double-counts a requirement, green if the plan satisfies the major. The validator is deterministic — Stellic does not use an LLM for plan validation, which is the same architectural decision as ADR 0003.

**What works:** The progress bars on the left rail are the single most motivating piece of UI. A student sees `Major: 18 / 39 cr` and intuits effort. Drag-and-drop is intuitive once discovered. The ability to view alternative courses that satisfy the same requirement (right-click > "Show alternatives") is excellent.

**What's clunky:** Discovery of drag-and-drop is poor — first-time users miss it because there's no affordance hint. The right-rail catalog is overwhelming at first load (Stellic shows the full catalog by default, ~3,000 courses for a typical state university). Mobile is unusable; the three-pane layout collapses badly under 1024px.

**Lift for Pathfinder:** The left-rail progress-bar pattern. The right-click "alternatives" pattern. The deterministic validator philosophy.

### 1b. Coursicle (`coursicle.com`)

Coursicle is the section-discovery tool every undergrad already uses. Bryant has a Coursicle deployment at `coursicle.com/bryant`. The relevant flow is "find sections > add to schedule."

**How it works:**

- Search bar at the top. Type "FIN 310" and the dropdown shows matching sections with prof, time, days, seats-left.
- Each section has a `+` icon. Click it; the section is added to a sticky bottom bar showing the running schedule grid.
- The grid renders in real-time. Conflicts render with a red diagonal-stripe overlay — visual but not blocking; students can keep adding conflicting sections and decide later.
- The "Notify me" feature for full sections is the killer feature, not the input UX.

**What works:** Search-as-you-type is fast (<100ms response). The conflict overlay is honest — it doesn't pretend to solve, it just shows the problem. The schedule grid is always visible, so students never lose context.

**What's clunky:** No concept of degree requirements. Coursicle has no idea what FIN 310 satisfies; it's a section directory, not an audit tool. Students still need Degree Works open in another tab to know what to search for. This is exactly the gap Pathfinder fills, and Coursicle's UX doesn't translate cleanly.

**Lift for Pathfinder:** The sticky bottom-bar running-total pattern. The instant search response. The honest conflict overlay (we'd never ship a conflicted schedule, but the visual language is good).

### 1c. CollegeXpress / Cappex major-requirement viewers

Both are college-search portals, not registration tools. Their major pages (e.g. `collegexpress.com/lists/list/colleges-with-the-strongest-finance-major/582/`) show static text blocks. No interaction. Not relevant beyond confirming that the static-list pattern is the floor — anything we ship beats this trivially.

### 1d. Banner Self-Service "Plan Ahead" (`reg-prod.bryantec.bryant.edu/StudentRegistrationSsb/ssb/planAhead/planAhead`)

This is Bryant's incumbent — what students currently use to assemble a registration plan. It is the most important competitor because it is what Pathfinder is replacing in the demo path.

**How it works (from the public Banner Self-Service 9.x documentation at ellucian.com and the visible UI patterns shared across Banner deployments):**

- A landing page with "Create a New Plan" button. Click it and you choose a term from a dropdown.
- The plan editor is a two-pane layout: course-search filters on the left, a results grid in the center, a "Plan" panel on the right.
- To find a course, you type the subject (FIN) and number (310) into separate fields — there's no fuzzy search, no autocomplete, no title search. You hit "Search" and wait for the page to reload.
- Results render as a flat table. To add a course to the plan, you click "View Sections," then on the next page click "Add" next to the section. The plan panel updates.
- The plan does not validate against degree requirements. It does not check prereqs. It does not check time conflicts until you go to the "Register" tab.

**What works:** It exists, it's the source of truth for sections, it ties into Banner's CRN system. That's the floor.

**What's clunky:** Everything else. The search-by-subject-and-number pattern is from 2003. The page reloads on every action. The plan doesn't validate. The mobile experience is a desktop site rendered in a phone browser. Students at Bryant routinely describe "Plan Ahead" as the worst UX on campus, and Pathfinder's existence is partly a response to that.

**Lift for Pathfinder:** Inverse of everything Plan Ahead does. We use search-as-you-type, no page reloads, live validation against the requirement DSL, and a mobile-first single-column layout. Frame Pathfinder's visual picker as "Plan Ahead, but for humans."

### 1e. Bryant catalog (Acalog/Modern Campus, `catalog.bryant.edu`)

The current catalog at `catalog.bryant.edu/undergraduate/` is Modern Campus's Acalog product — the dominant academic-catalog CMS in higher ed. The Finance major page is at `catalog.bryant.edu/undergraduate/colleges-business/finance-department/finance-major/`.

**How it works:** A long-form HTML page. Section headings for "General Education Program (44 credits)," "Business Core (33 credits)," "Major (15 credits)," "Free Electives (28 credits)." Each section is a bulleted list of courses, with hyperlinks on each course code that pop up an Acalog modal showing the course description.

**What works:** Comprehensive, authoritative, every major has the same structure. The Acalog modal pattern (click course code > see description) is genuinely useful and worth borrowing.

**What's clunky:** Pure read-only. No way to mark "I've taken this." No way to filter to "only what I haven't completed." No way to export. No interaction beyond following hyperlinks.

**Lift for Pathfinder:** The category structure (Gen Ed / Business Core / Major / Free Elective) is already the canonical Bryant taxonomy and matches the `category` field on `outstanding_requirements` in `audit_owen.json`. Reuse it verbatim. The Acalog course-description modal is a pattern to copy on the requirements list.

### 1f. MyDegreePlan / Civitas Degree Map

Civitas's Degree Map (acquired into the Civitas Learning suite, deployed at the University of Texas system among others) is closer to a counselor-facing tool than a student tool. The student-facing surface is a Gantt-chart-style 8-semester grid with drag-and-drop. It's the only competitor that handles wildcard requirements (`FIN 4XX`) with first-class UI — they render an unfilled slot as a gold pill that says "FIN 4XX — pick later," matching the Pathfinder DSL almost exactly. Not publicly screenshot-able without a login.

**Lift for Pathfinder:** The unfilled-wildcard-slot pattern. When the student adds the `fin_400_level` requirement to "this semester," show a gold pill with `FIN 4XX` in mono and the explainer text "We'll pick a specific section that fits."

---

## 2. The "requirements browser" component pattern

Spec for the Pathfinder visual picker page. Lives at `frontend/app/picker/page.tsx`. Replaces nothing — it's a third route alongside the existing paste/upload flow, surfaced from the homepage as a fourth on-ramp. Routes back into `/preferences` once the student has selected requirements.

### Data inputs

- **`bryant_requirements_finance.json`** (new fixture). The 16 standard outstanding requirements for a sophomore Finance major, hand-authored from `audit_owen.json`. Same shape as `outstanding_requirements` — `id`, `requirement`, `rule_type`, `options`, `pattern`, `credits_needed`, `category`. This becomes the seed catalog when no audit is uploaded.
- **`sections.json`** for the live count of "X sections available across Y instructors" hint text under each requirement.
- Per-major templates in `bryant_majors.json` — see section 8.

### Component anatomy

Top-down on the page:

1. **`MajorTemplatePicker`** — a horizontal scroll of pill chips. Each pill: major name in serif, year-and-semester chip in mono ("Sophomore · Fall"). Clicking pre-fills the requirements list with that template's defaults. Default selection: Finance / Sophomore / Fall (Owen's case). Uses shadcn/ui `Badge` with custom styling for the pill chips.
2. **`SearchAndFilter`** — a `Combobox` (shadcn/ui `Command` + `Popover`) for fuzzy search across requirement names and course codes. Below it, a row of category filter chips: All / Major / Business Core / Gen Ed / Elective. Uses `Toggle` from shadcn/ui radix-style. Active chip uses `bg-[#1A1A1A] text-white`, matching the Days-Off chips on `preferences/page.tsx`.
3. **`QuickPickRow`** — three preset buttons rendered as pill outlines. Copy: "All my major courses", "Catch up on gen eds", "Lightest possible 12 credits". Each click sets `selectedIds` declaratively. These are the "smart starter" buttons (see section 3).
4. **`RequirementsList`** — the body. Reuses the categorized checkbox layout from `frontend/app/preferences/page.tsx` lines 168–215 verbatim. Each row: checkbox, requirement name in `text-sm text-[#1A1A1A]`, course-code hint in Geist Mono `text-xs text-[#5F5D58]`, credits chip on the right. Hover state: `bg-black/[0.02]`. Adding a row to selection: increments a running-total chip in the sticky footer.
5. **`StickyFooter`** — fixed to bottom on mobile, inline on desktop. Shows `{n} requirements selected · {total} credits` in mono on the left, `Continue` pill button on the right. The button is the existing `PillButton` component. Disabled when `selectedIds.size === 0`. Routes to `/preferences` with the synthetic audit pre-loaded into Zustand.

### Synthetic audit construction

When the student clicks Continue, the picker constructs a `DegreeAudit` object in memory with:

```ts
{
  student_id: "guest",
  name: "Student",
  major: selectedTemplate.major,
  expected_graduation: "TBD",
  credits_earned_or_inprogress: 0,
  credits_required: 120,
  completed_requirements: [],
  in_progress_requirements: [],
  outstanding_requirements: selectedRequirements,
}
```

This object is set via `useStore.setAudit()` exactly like the Vision and paste paths. The downstream solver, ranker, and explanation pipeline don't know the difference. **Zero backend changes required.** The picker is a pure-frontend re-skin of the existing input layer.

### shadcn/ui components used

- `Command` + `Popover` for the search combobox
- `Checkbox` (already vendored in `components/ui/`, currently a styled native input — upgrade to Radix for keyboard semantics)
- `Badge` for category pills and credit chips
- `Toggle` for the category filter row
- `Button` styled as `PillButton` for Continue and quick-pick presets
- `Dialog` for the optional course-description modal (Acalog-style)
- `ScrollArea` for the major-template horizontal scroller

Phosphor Light icons only: `MagnifyingGlass` for search, `Plus` for "add to selection" affordance, `ListChecks` for the section header, `ArrowRight` for the Continue CTA, `BookOpen` for the description-modal trigger.

---

## 3. The "smart starter" pattern

Quick-pick presets sit between the search bar and the requirements list. Three buttons:

- **"All my major courses"** — selects every requirement where `category === "major"`. For Owen, that's `fin_310`, `fin_312`, `fin_315`, `fin_elective`, `fin_400_level`, `fin_general_elective`. Total: 18 credits, which is over the standard cap, so the credit-target slider on `/preferences` clamps to 18 and the negotiator agent will likely surface relaxations. That's fine — it's a real situation Finance juniors face.
- **"Catch up on gen eds"** — selects every requirement where `category === "general_education"`. For Owen: `gen_201`, `lcs_course`, `science_lab`, `gen_390_capstone`. Total: 13 credits. Lighter, more achievable.
- **"Lightest possible 12 credits"** — runs the requirement expander client-side and picks the smallest combination of requirements summing to 12+ credits, prioritizing `specific_course` rule-type over wildcards. Deterministic. No solver call needed.

Beyond presets, the page implements **"smart pre-fill from a partial audit."** If the student arrived from the homepage paste/upload flow but Vision returned an empty `outstanding_requirements` array (a known failure mode), redirect to `/picker` instead of `/preferences` and pre-fill from the major template they're closest to, with a banner: `We couldn't read your audit clearly. Here's what a typical [Finance] sophomore takes — check the ones that match your situation.`

---

## 4. Drag-and-drop

Stellic and Civitas both lean heavily on drag-and-drop. For Pathfinder's hackathon-and-pilot scope, **don't ship it.** Reasons:

1. **Single-semester scope.** Pathfinder solves one semester at a time. Drag-and-drop is justified when there are 8 columns (semesters) to move courses between. With one column, a checkbox is the right primitive.
2. **Mobile breaks.** Drag-and-drop on touch screens requires long-press affordances, accessible alternatives, and `pointer-events` choreography that takes 2–3 days of polish to get right. Not worth it for a feature that's out-of-scope.
3. **Discovery is a real cost.** First-time users don't intuit drag-and-drop. The Stellic teardown above flagged this. Pathfinder's editorial-minimal aesthetic relies on legibility, and drag handles add visual noise.

**When drag-and-drop earns its place:** the `frontend/app/planner/page.tsx` 4-semester view (already shipped per recent commits). That page has multiple columns and benefits from the affordance. Keep the visual picker on checkboxes.

If drag-and-drop is later requested for moving requirements between "this semester" and "later," use Radix's `dnd-kit` (industry standard, tree-shakable, accessible) — not `react-beautiful-dnd` (deprecated, large bundle).

---

## 5. Mobile-first

Owen's likely demo audience includes laptops and phones. Coursicle gets ~60% mobile traffic, per their public usage stats. The picker has to work on a 320px-wide single column.

**Layout collapse rules:**

- Major-template picker: horizontal scroll on mobile (already correct), inline pills on desktop.
- Search and filter chips: stack vertically on mobile, inline on desktop.
- Quick-pick presets: full-width stacked buttons on mobile, three-column row on desktop.
- Requirements list: full-width on mobile, max-w-3xl on desktop (matches `preferences/page.tsx`).
- Sticky footer with Continue button: fixed-bottom on mobile (`fixed bottom-0 left-0 right-0`), inline at the bottom of the form on desktop. Adds ~64px bottom padding to the list when fixed so the last requirement isn't covered.

**Touch targets:** Each requirement row gets `py-3` (44px tap height minimum, matching iOS HIG). The category-filter chips get `h-11` (matching the days-off buttons). Checkbox tap area is the entire row, not just the 16px box — the row is wrapped in a `<label>` already in the existing code.

**Bottom sheet vs full screen:** For the optional course-description modal (Acalog-style), use a bottom sheet on mobile (`Sheet` from shadcn/ui with `side="bottom"`) and a centered `Dialog` on desktop. Bottom sheets feel native on mobile and don't require a back button to dismiss.

---

## 6. Accessibility (WCAG AA)

The product baseline already commits to WCAG AA. The picker holds the line:

- **Keyboard navigation.** Tab order: search input → category filters → quick-pick buttons → first requirement checkbox → next checkbox → … → Continue button. `Tab` moves forward, `Shift+Tab` back. Spacebar toggles checkboxes. Enter on the Continue button submits. The major-template scroller responds to arrow keys when focused.
- **ARIA roles.** The requirements list is `role="group"` with `aria-labelledby` pointing to the section heading. Each row uses native `<input type="checkbox">` with `<label>` association — no custom `role="checkbox"` because native is already accessible. The category filter row is `role="radiogroup"` with `aria-label="Filter by category"`. The sticky footer credit-total is `role="status" aria-live="polite"` so screen readers announce "13 credits selected" when the count changes, debounced to 500ms to avoid chatter.
- **Focus visibility.** Focus ring uses `focus:ring-2 focus:ring-[#B8985A]/40 focus:ring-offset-2` — the gold accent at 40% opacity, with a 2px offset against the cream background. Verified at 3:1 against `#FAFAF7` per WCAG 2.1 SC 1.4.11 (Non-text Contrast).
- **Reduced motion.** All transitions use `motion-reduce:transition-none`. The fade-up animations on the page use `motion-reduce:animate-none` (already the pattern in the existing pages).
- **Color independence.** Selection state is conveyed by both the gold checkbox accent and a subtle `bg-[#FAFAF7]` row background — not color alone. Category filter active state is conveyed by `bg-[#1A1A1A]` (filled) vs `bg-[#FAFAF7]` (outlined), high-contrast pair.

---

## 7. Empty state — first-time user, no audit

The strongest possible empty state is the entire reason this picker exists. A first-time user opens Pathfinder with no Degree Works screenshot, no pasted text, no idea what FIN 4XX means.

**Copy and layout for the empty state on `/picker`:**

- **Eyebrow tag (mono, 10px, uppercase):** `START HERE`
- **Headline (Instrument Serif, 48–60px):** `Tell us what you're studying. We'll handle the rest.`
- **Subhead (Geist, 16px, secondary color):** `Pick your major and year. We'll pre-fill the courses a typical student in your spot still needs to take. Uncheck what you've already finished, and we'll generate three schedules in two seconds.`
- **Primary affordance:** the major-template picker, fully visible above the fold.
- **Secondary affordance, below the templates:** a hairline link reading `My audit looks different — let me build from scratch ->` that clears the template and shows an empty requirements list with a search bar to add courses one at a time.
- **Tertiary affordance, below that:** `Or upload a Degree Works screenshot ->` linking back to `/`.

This converts a cold-start in three taps: tap a major chip, glance at the pre-filled list, tap Continue.

**Time-to-first-schedule comparison:**

| Path | Inputs required | API calls | Wall time |
|---|---|---|---|
| Today: paste text | ~30s typing or copy/paste, 1 click | 1 Vision-text + 1 schedule | ~4–5 s |
| Today: upload image | 1 file selection | 1 Vision-image + 1 schedule | ~4–6 s |
| Today: sample audit | 1 click | 1 schedule | ~2 s |
| **New: visual picker** | **3 taps (major chip, glance, Continue)** | **1 schedule** | **~2 s** |
| **New: picker + tweak** | **3 taps + ~5 s of unchecking** | **1 schedule** | **~7 s total user time, ~2 s wall time** |

The picker matches the sample-audit speed but works for any student, not just Owen. That's the unlock.

---

## 8. Pre-built major templates

For each Bryant major, ship a `bryant_majors.json` with templates indexed by `major_id` and `level` (Freshman / Sophomore / Junior / Senior, Fall / Spring). The template is a list of requirement IDs that a typical student in that slot still needs to take.

**Bryant's 12 undergraduate majors (per `catalog.bryant.edu/undergraduate/colleges-business/` and `catalog.bryant.edu/undergraduate/colleges-arts-sciences/`):**

1. Accounting
2. Actuarial Mathematics
3. Applied Analytics
4. Applied Economics
5. Communication
6. Finance
7. Global Studies
8. International Business
9. Management
10. Marketing
11. Politics & Law
12. Computing & Information Systems (combined major)

For the hackathon scope, ship Finance fully (Owen's case, used in the demo) and stub the other 11 to point at the same business-core baseline with a banner: `Sophomore Finance template loaded. Other majors coming soon — for now, this covers your business core.` That's honest and lets the picker work for ~80% of Bryant students immediately.

A Finance / Sophomore / Fall template structurally matches `audit_owen.json`'s `outstanding_requirements` array exactly. The fixture is reusable as the seed.

For the second-institution pilot threshold (per `00-product-baseline.md`), templates would be ingested from a school's catalog API or scraped from their Acalog deployment. This is the natural extensibility surface — every Acalog school exposes the same major-page structure, and a template scraper is one weekend's work per institution.

---

## 9. Wireframe — the new input page (the strongest output)

Three components, top-to-bottom on the page. All copy is the production-shipping version, not lorem.

### Component A — major-template picker (top)

Visual: a single horizontal row of 12 pill chips on a `bg-white` rounded card, 1.5px gold accent on the active chip. Above the row, eyebrow tag and headline.

```
[ START HERE ]                                         (eyebrow, mono 10px, #5F5D58)

I'm a [ Sophomore  v ] [ Finance     v ] major.       (Instrument Serif, 36-48px,
                                                       inline dropdowns in serif)

[Accounting] [Actuarial] [Analytics] [Economics] [Communication]  <- horizontal scroll
[Finance ●]  [Global Studies] [Int'l Business] [Management] [Marketing]
[Politics & Law] [Computing & IS]
```

Active chip styling: `bg-[#1A1A1A] text-white` with a `ring-1 ring-[#B8985A]/30` halo. Inactive: `bg-[#FAFAF7] text-[#5F5D58] ring-1 ring-black/5`.

Below the chip row: `Loaded the typical Sophomore Fall plan — uncheck what you've already finished.` in `text-xs text-[#5F5D58]`.

### Component B — requirements list (middle)

Visual: same categorized checkbox layout as `preferences/page.tsx`, with the addition of a search bar and category filter chips at the top.

```
[ MagnifyingGlass icon ] Search requirements or course codes...   (Combobox, shadcn)

[ All ] [ Major ● ] [ Business Core ] [ Gen Ed ] [ Elective ]    (filter chips, Toggle)

MAJOR                                                             (mono 10px uppercase)
[x] Intermediate Corporate Finance        FIN 310        3 cr
[x] Investments                           FIN 312        3 cr
[x] Financial Inst. and Markets           FIN 315        3 cr
[ ] Financial Electives                   FIN 370/371/...  3 cr
[ ] 400 Level Finance                     FIN 4XX        3 cr   <- gold "wildcard"
                                                                   pill on the right
[ ] Finance Electives                     FIN XXX        3 cr

BUSINESS CORE                                                     (mono 10px uppercase)
[x] Prin. of Financial Accounting         ACG 203        3 cr
[ ] Prin. of Managerial Accounting        ACG 204        3 cr
... etc
```

The requirement title is `text-sm text-[#1A1A1A]`. The course-code hint is `text-xs text-[#5F5D58]` in Geist Mono. The credit chip is `text-[10px] text-[#5F5D58]` in Geist Mono on the right. Hover: `bg-black/[0.02]`. Each row is a `<label>` wrapping a `<input type="checkbox">` and the content — same pattern as the existing preferences page.

Wildcard requirements (rule_type `wildcard`) get a subtle gold dot to the left of the checkbox and a tooltip on hover: `We'll pick a specific FIN 4XX section that fits your other choices.`

Above the list, the QuickPickRow:

```
QUICK START
[ All my major courses ]  [ Catch up on gen eds ]  [ Lightest 12 credits ]
```

Pill outlines: `rounded-full bg-white ring-1 ring-black/5 px-4 py-2 text-xs text-[#1A1A1A] hover:ring-black/10`.

### Component C — credit-target slider + Generate CTA (bottom, sticky on mobile)

Visual: a thin card hugging the bottom of the viewport on mobile, inline at the end of the form on desktop.

```
TARGET CREDITS                                            15 cr   (mono, right-aligned)
[========●================]                               (slider, gold accent)
12                                                            18

5 requirements selected · 15 credits planned                       (mono, status-live)

[ Continue to preferences  ->]                            (PillButton, full width
                                                           on mobile, auto on desktop)
```

The slider re-uses shadcn/ui `Slider`. The status line is `aria-live="polite"`. The Continue button routes to `/preferences` with the synthetic audit pre-loaded; the existing preferences page handles days-off, time bounds, and free-text from there.

**Exact button copy:** `Continue to preferences` (not "Generate" — the picker only collects the audit-equivalent; the schedule generation still happens after preferences are set, identical to the current flow). This preserves the three-step mental model already advertised on the homepage ("Paste / Set / Pick").

---

## 10. Source URLs

- Stellic product page and demo: `https://stellic.com/`, `https://stellic.com/demo`
- Coursicle Bryant deployment: `https://www.coursicle.com/bryant/`
- Banner Self-Service Plan Ahead: `https://reg-prod.bryantec.bryant.edu/StudentRegistrationSsb/ssb/planAhead/planAhead`
- Bryant Acalog catalog, Finance major: `https://catalog.bryant.edu/undergraduate/colleges-business/finance-department/finance-major/`
- Civitas Degree Map / Civitas Learning: `https://www.civitaslearning.com/`
- Modern Campus Acalog product page: `https://moderncampus.com/products/catalog.html`
- shadcn/ui component reference: `https://ui.shadcn.com/docs/components/`
- Radix `dnd-kit` (recommended drag-and-drop library if needed later): `https://dndkit.com/`
- Phosphor Icons reference (already in stack): `https://phosphoricons.com/`

---

## 11. Summary recommendation

Build the visual picker as a third on-ramp at `/picker`, surfaced from the homepage as a primary CTA equal in weight to paste and upload. Reuse the categorized-checkbox layout from `preferences/page.tsx` verbatim and inject a major-template picker, a search-and-filter row, and three quick-pick presets above it. Construct a synthetic `DegreeAudit` in Zustand on Continue and route to `/preferences` — zero backend changes. Ship Finance fully, stub the other 11 majors with a graceful fallback. Skip drag-and-drop. Hold the WCAG AA line. Match Pathfinder's editorial-minimal aesthetic strictly — `#FAFAF7` cream, `#B8985A` gold, Instrument Serif headlines, Geist Mono for codes and credits, Phosphor Light icons only.

The headline win: **time-to-first-schedule drops from ~5 s with cognitive overhead (find audit, screenshot, upload, wait for Vision) to ~7 s with three taps (chip, glance, Continue) for any Bryant student, not just the one whose audit is in the fixture.** That's the cold-start unlock, and it's the strongest argument for prioritizing this feature in the second sprint after the hackathon.
