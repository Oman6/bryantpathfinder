"""Multi-Semester Planner Agent — orchestrates 3 sub-agents to plan a 4-semester roadmap.

Sub-agents:
1. Prerequisite Agent — builds a dependency graph of course prerequisites
2. Rotation Agent — determines which courses are Fall-only, Spring-only, or both
3. Sequencing Agent — produces the optimal 4-semester plan

This is the most complex agent in Pathfinder and demonstrates true
multi-agent orchestration: three agents run sequentially, each consuming
the previous agent's output to produce a complete graduation roadmap.
"""

import logging
from ..models import DegreeAudit, OutstandingRequirement, Section

logger = logging.getLogger(__name__)

# Known Bryant prerequisite chains for Finance and Business
PREREQUISITES: dict[str, list[str]] = {
    "FIN 310": ["FIN 201"],
    "FIN 312": ["FIN 310"],
    "FIN 315": ["FIN 310"],
    "FIN 370": ["FIN 310"],
    "FIN 371": ["FIN 310"],
    "FIN 380": ["FIN 310"],
    "FIN 465": ["FIN 310", "FIN 312"],
    "FIN 466": ["FIN 310", "FIN 312"],
    "ACG 204": ["ACG 203"],
    "BUS 400": ["FIN 201", "MGT 200", "MKT 201"],
    "GEN 390": ["GEN 201"],
    "ISA 201": [],
    "MKT 201": [],
    "LGLS 211": [],
    "ACG 203": [],
    "GEN 201": [],
}

# Course rotation patterns (which semester a course is typically offered)
ROTATION: dict[str, list[str]] = {
    "FIN 310": ["Fall", "Spring"],
    "FIN 312": ["Fall", "Spring"],
    "FIN 315": ["Fall", "Spring"],
    "FIN 370": ["Fall"],
    "FIN 371": ["Fall", "Spring"],
    "FIN 380": ["Spring"],
    "FIN 465": ["Fall"],
    "FIN 466": ["Spring"],
    "ACG 203": ["Fall", "Spring"],
    "ACG 204": ["Fall", "Spring"],
    "BUS 400": ["Fall", "Spring"],
    "ISA 201": ["Fall", "Spring"],
    "LGLS 211": ["Fall", "Spring"],
    "MKT 201": ["Fall", "Spring"],
    "GEN 201": ["Fall", "Spring"],
    "GEN 390": ["Fall", "Spring"],
}


def _prerequisite_agent(
    requirements: list[OutstandingRequirement],
    completed_courses: set[str],
    in_progress_courses: set[str],
) -> dict:
    """Build a dependency graph and determine which requirements are ready now.

    Returns:
        - dependency_graph: dict mapping course -> list of prerequisites
        - ready_now: courses whose prerequisites are all met
        - blocked: courses waiting on prerequisites
        - chains: ordered prerequisite chains (e.g., FIN 201 -> FIN 310 -> FIN 312)
    """
    all_satisfied = completed_courses | in_progress_courses
    ready_now = []
    blocked = []
    dependency_graph = {}

    for req in requirements:
        # Get the primary course code for this requirement
        if req.options:
            primary = req.options[0]
        elif req.pattern:
            primary = req.pattern.replace("XX", "**")
        else:
            primary = req.id

        prereqs = PREREQUISITES.get(primary, [])
        dependency_graph[req.id] = {
            "course": primary,
            "requirement": req.requirement,
            "prereqs": prereqs,
            "prereqs_met": all(p in all_satisfied for p in prereqs),
        }

        if all(p in all_satisfied for p in prereqs):
            ready_now.append(req.id)
        else:
            missing = [p for p in prereqs if p not in all_satisfied]
            blocked.append({"id": req.id, "waiting_on": missing})

    # Build chains
    chains = []
    visited = set()
    for req in requirements:
        if req.options:
            course = req.options[0]
        else:
            continue
        if course in visited:
            continue
        chain = _build_chain(course, visited)
        if len(chain) > 1:
            chains.append(chain)

    return {
        "dependency_graph": dependency_graph,
        "ready_now": ready_now,
        "blocked": blocked,
        "chains": chains,
    }


def _build_chain(course: str, visited: set) -> list[str]:
    """Recursively build a prerequisite chain."""
    visited.add(course)
    prereqs = PREREQUISITES.get(course, [])
    if not prereqs:
        return [course]
    chain = []
    for p in prereqs:
        if p not in visited:
            chain.extend(_build_chain(p, visited))
    chain.append(course)
    return chain


def _rotation_agent(requirements: list[OutstandingRequirement]) -> dict:
    """Determine course rotation patterns.

    Returns:
        - fall_only: courses only offered in Fall
        - spring_only: courses only offered in Spring
        - both: courses offered in both semesters
        - schedule_critical: courses that must be taken in a specific semester
    """
    fall_only = []
    spring_only = []
    both = []
    schedule_critical = []

    for req in requirements:
        if req.options:
            course = req.options[0]
        elif req.pattern:
            course = req.pattern
        else:
            continue

        rotation = ROTATION.get(course, ["Fall", "Spring"])
        if rotation == ["Fall"]:
            fall_only.append({"id": req.id, "course": course, "requirement": req.requirement})
            schedule_critical.append({"id": req.id, "course": course, "must_take": "Fall"})
        elif rotation == ["Spring"]:
            spring_only.append({"id": req.id, "course": course, "requirement": req.requirement})
            schedule_critical.append({"id": req.id, "course": course, "must_take": "Spring"})
        else:
            both.append({"id": req.id, "course": course, "requirement": req.requirement})

    return {
        "fall_only": fall_only,
        "spring_only": spring_only,
        "both": both,
        "schedule_critical": schedule_critical,
    }


def _sequencing_agent(
    requirements: list[OutstandingRequirement],
    prereq_data: dict,
    rotation_data: dict,
    completed_courses: set[str],
    in_progress_courses: set[str],
    target_credits_per_semester: int = 15,
) -> list[dict]:
    """Produce a 4-semester plan using prerequisite and rotation data.

    Returns:
        A list of semester plans, each containing:
        - semester: "Fall 2026", "Spring 2027", etc.
        - courses: list of requirement IDs scheduled this semester
        - credits: total credits
        - notes: any scheduling notes
    """
    semesters = ["Fall 2026", "Spring 2027", "Fall 2027", "Spring 2028"]
    plan = []
    scheduled = set()
    all_satisfied = completed_courses | in_progress_courses

    req_map = {r.id: r for r in requirements}
    ready = set(prereq_data["ready_now"])

    for semester in semesters:
        is_fall = "Fall" in semester
        semester_courses = []
        semester_credits = 0.0

        # Priority order: schedule-critical courses first, then by category
        category_priority = {"major": 0, "business_core": 1, "general_education": 2, "elective": 3, "minor": 4}

        candidates = []
        for req in requirements:
            if req.id in scheduled:
                continue

            # Check prerequisites
            if req.options:
                course = req.options[0]
                prereqs = PREREQUISITES.get(course, [])
                if not all(p in all_satisfied for p in prereqs):
                    continue

                # Check rotation
                rotation = ROTATION.get(course, ["Fall", "Spring"])
                if is_fall and "Fall" not in rotation:
                    continue
                if not is_fall and "Spring" not in rotation:
                    continue

            priority = category_priority.get(req.category, 3)
            # Boost priority for schedule-critical courses
            critical = [c for c in rotation_data["schedule_critical"] if c["id"] == req.id]
            if critical:
                priority -= 10

            candidates.append((priority, req))

        candidates.sort(key=lambda x: x[0])

        notes = []
        for _, req in candidates:
            if semester_credits + req.credits_needed > target_credits_per_semester + 1:
                continue

            semester_courses.append({
                "id": req.id,
                "requirement": req.requirement,
                "credits": req.credits_needed,
                "category": req.category,
                "course": req.options[0] if req.options else (req.pattern or req.id),
            })
            semester_credits += req.credits_needed
            scheduled.add(req.id)

            # Add completed course to satisfied set for next semester prereq checks
            if req.options:
                all_satisfied.add(req.options[0])

        if semester_courses:
            plan.append({
                "semester": semester,
                "courses": semester_courses,
                "credits": semester_credits,
                "notes": notes,
            })

    return plan


def run(audit: DegreeAudit, all_sections: list[Section]) -> dict:
    """Run the full Multi-Semester Planner with 3 sub-agents.

    This is the orchestrator: it runs the Prerequisite Agent, Rotation Agent,
    and Sequencing Agent in sequence, passing each agent's output to the next.

    Returns:
        - prerequisite_analysis: from the Prerequisite Agent
        - rotation_analysis: from the Rotation Agent
        - semester_plan: 4-semester roadmap from the Sequencing Agent
        - total_credits_planned: sum of all planned credits
        - graduation_on_track: whether the plan covers all outstanding requirements
    """
    completed = {r.course for r in audit.completed_requirements}
    in_progress = {r.course for r in audit.in_progress_requirements}
    requirements = audit.outstanding_requirements

    # Agent 1: Prerequisite analysis
    logger.info("agent.multi_semester.prerequisite.start")
    prereq_data = _prerequisite_agent(requirements, completed, in_progress)
    logger.info("agent.multi_semester.prerequisite.complete", extra={
        "ready": len(prereq_data["ready_now"]),
        "blocked": len(prereq_data["blocked"]),
    })

    # Agent 2: Rotation analysis
    logger.info("agent.multi_semester.rotation.start")
    rotation_data = _rotation_agent(requirements)
    logger.info("agent.multi_semester.rotation.complete", extra={
        "fall_only": len(rotation_data["fall_only"]),
        "spring_only": len(rotation_data["spring_only"]),
    })

    # Agent 3: Sequencing
    logger.info("agent.multi_semester.sequencing.start")
    semester_plan = _sequencing_agent(
        requirements, prereq_data, rotation_data, completed, in_progress
    )
    logger.info("agent.multi_semester.sequencing.complete", extra={
        "semesters_planned": len(semester_plan),
    })

    total_planned = sum(s["credits"] for s in semester_plan)
    planned_ids = set()
    for s in semester_plan:
        for c in s["courses"]:
            planned_ids.add(c["id"])
    unplanned = [r.id for r in requirements if r.id not in planned_ids]

    return {
        "prerequisite_analysis": prereq_data,
        "rotation_analysis": rotation_data,
        "semester_plan": semester_plan,
        "total_credits_planned": total_planned,
        "unplanned_requirements": unplanned,
        "graduation_on_track": len(unplanned) == 0,
        "agents_used": ["prerequisite", "rotation", "sequencing"],
    }
