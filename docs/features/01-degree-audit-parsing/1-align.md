# Feature 01 -- Degree Audit Parsing

## 1-Align: Why This Feature Exists

---

### The Problem

Bryant University uses two separate systems for degree tracking and course registration: Degree Works for audit and progress tracking, and Banner Self-Service for course search and registration. These systems do not share data in any student-accessible way. A student can see what they still need on the Degree Works audit page, and they can see what is offered on the Banner course search page, but there is no connection between the two.

The result is a manual, error-prone process that every Bryant student repeats every semester:

1. Open Degree Works in one browser tab
2. Open Banner Self-Service in another tab
3. Read through the audit line by line, noting which requirements are still outstanding
4. For each outstanding requirement, switch to Banner and search for sections being offered
5. Mentally check whether the section times conflict with other chosen courses
6. Write down CRNs on a piece of paper or a notes app
7. Copy the CRNs into Banner's registration page during the registration window

This process typically takes 30-60 minutes per student per semester. For a sophomore like Owen Ash with 16 outstanding requirements spanning general education, business core, and finance concentration courses, the complexity is significant. Owen needs to know that FIN 310 is a specific course he must take, that his Literary and Cultural Studies requirement could be satisfied by any of 20 different LCS courses, and that his Science Lab requirement requires registering for both a lecture and a paired lab section simultaneously.

Students routinely make mistakes in this process. They miss requirements, register for courses that do not satisfy any outstanding requirement, create schedules with time conflicts that they only discover on the first day of classes, or fail to register for both halves of a lecture/lab pair. Academic advisors like Kristina Anthony catch some of these errors during advising appointments, but advisors are reviewing dozens of student plans in a compressed pre-registration window.

---

### Why Claude Vision

The Degree Works audit page is a complex, semi-structured document. It contains nested categories (General Education, Business Core, Finance Concentration), each with their own sub-requirements. Some requirements show a single course ("Still needed: 1 Class in FIN 310"). Others show a list of options ("Still needed: 1 Class in FIN 370 or 371 or 380 or 465 or 466"). Others use wildcard patterns ("Still needed: 1 Class in @ 4@ with attribute = FIN"). The page mixes completed courses with their grades, in-progress courses with a "REG" status, and outstanding requirements with their "Still needed" descriptions.

Traditional OCR would extract the raw text but would not understand the semantic structure. It would not know that "or 371 or 380" inherits the "FIN" subject prefix from the first course in the list. It would not know that "@ 4@" is a wildcard meaning "any 400-level course." It would not know that "2 Classes in SCI 251 and L251" means the student must register for both the lecture and the lab.

Claude Vision handles all of this. Given the `VISION_AUDIT_PROMPT` with worked examples for each rule type, Claude reads the screenshot, identifies every requirement, classifies each by rule type, and returns clean JSON matching the `DegreeAudit` schema. The prompt includes concrete examples showing how to parse "1 Class in FIN 310" as a `specific_course` rule and how to parse "1 Class in FIN 370 or 371 or 380 or 465 or 466" as a `choose_one_of` rule with the subject prefix propagated to all options.

This is exactly the kind of task Claude excels at: reading a messy visual document and producing structured, typed output. It is the opposite of combinatorial scheduling, where deterministic code must guarantee correctness.

---

### The Demo User

Owen Ash is the sole demo user for the hackathon build. His audit is representative of a typical Bryant sophomore Finance major:

- **Student ID:** 001118725
- **Major:** Finance
- **Expected graduation:** May 2029
- **Credits earned or in progress:** 42 of 120 required
- **Completed:** 6 courses (GEN 100, IDEA 101, ACI 220, BUS 100, MATH 201, POLS 241)
- **In progress (Spring 2026):** 9 courses including FIN 201, ECO 114, MATH 110
- **Outstanding:** 16 requirements across general education, business core, and finance concentration

Owen's audit exercises all four rule types:
- `specific_course`: FIN 310, FIN 312, FIN 315, GEN 201, ACG 203, ACG 204, BUS 400, ISA 201, LGLS 211, MKT 201 (one course, no choice)
- `choose_one_of`: LCS course (20 options), Financial Electives (FIN 370/371/380/465/466)
- `wildcard`: FIN 4XX (any 400-level Finance), FIN XXX (any Finance course)
- `course_with_lab`: Science and Lab Requirement (10 lecture/lab pairs like SCI 251 + SCI L251)

This makes Owen's audit a comprehensive test case for the parser.

---

### The "Use Sample Audit" Fallback

The Vision parsing path is powerful but introduces a runtime dependency on the Anthropic API. During a live hackathon demo, API latency, rate limits, or malformed JSON responses could interrupt the demo flow. The "Use sample audit" button on the homepage loads `data/fixtures/audit_owen.json` directly into the frontend Zustand store, bypassing Claude entirely.

This fallback exists for three reasons:

1. **Demo safety.** If the Claude API is slow or returns an error during the live demo, Owen clicks the sample button and the demo continues without interruption. The judges see the same data, the same preferences page, the same generated schedules.

2. **Development velocity.** During the build, every code change to the solver, the expander, or the frontend can be tested instantly using the fixture. No API call, no cost, no latency. The fixture is the ground truth that all tests run against.

3. **Reproducibility.** The fixture produces identical results every time. This makes it possible to write deterministic tests for the solver and to debug issues without worrying about whether the audit data changed between runs.

The fixture was generated by `backend/scripts/parse_degree_audit.py`, which reads Owen's raw audit text and produces the JSON file. The script includes a verification step that confirms all 16 expected outstanding requirement IDs are present in the output.

---

### What Success Looks Like

The degree audit parsing feature succeeds when:

- A student uploads a Degree Works screenshot and receives a correct `DegreeAudit` within 5 seconds
- Every outstanding requirement is classified with the correct rule type
- The `choose_one_of` rules have the full list of options with the subject prefix correctly propagated
- The `wildcard` rules have the correct pattern (e.g., "FIN 4XX" not "4@" or "@ 4@")
- The `course_with_lab` rules have all valid lecture/lab pairs
- The fixture fallback loads instantly and produces the same downstream behavior as a live parse
- A malformed JSON response from Claude triggers one automatic retry before failing

The feature does not need to handle every possible Degree Works audit format at every university. It needs to handle Bryant Business Administration audits reliably, with Owen Ash's audit as the reference implementation.

---

### Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Claude returns malformed JSON | Medium | Retry once with same prompt. Two-attempt loop in `parse_audit_vision()`. |
| Claude hallucinates a requirement | Low | Temperature set to 0. Prompt says "Do not invent requirements that aren't visible in the image." |
| Claude misclassifies a rule type | Low | Prompt includes four worked examples, one per rule type. |
| API key rate limited during demo | Low | "Use sample audit" button bypasses Claude entirely. |
| Degree Works UI changes layout | N/A for hackathon | Only Owen's current audit matters. Production would need prompt updates. |
| Multi-page audits | N/A for hackathon | Owen's audit fits on one screenshot. Production would accept multi-page PDFs. |

---

### Alignment with the Core Insight

Degree audit parsing is the canonical example of Pathfinder's design philosophy: Claude where language and perception matter, Python where correctness matters. Parsing a messy visual document full of domain-specific shorthand (the "@" wildcards, the implicit subject prefix propagation, the lecture/lab pairing syntax) is fundamentally a perception and language task. Claude handles it. Once the audit is parsed into a typed `DegreeAudit` object, every downstream operation -- expanding requirements into sections, detecting time conflicts, generating valid schedules -- runs in deterministic Python where the answer is provably correct.

The handoff point is clean: `parse_audit_vision()` returns a Pydantic-validated `DegreeAudit` or raises an exception. There is no ambiguity, no partial result, no "probably right." The rest of the system trusts the schema.
