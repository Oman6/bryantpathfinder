"""Agent Orchestrator — coordinates all agents in the Pathfinder pipeline.

The orchestrator manages two flows:

1. SCHEDULE ENRICHMENT (post-solver):
   After the solver returns 3 candidate schedules, the orchestrator fans out
   to three agents in parallel:
   - Professor Match Agent
   - Workload Agent
   - Claude Explain Agent (existing)
   Their outputs are merged into enriched ScheduleOption objects.

2. CONSTRAINT NEGOTIATION (zero-result path):
   When the solver returns zero schedules, the orchestrator activates the
   Negotiator Agent to analyze bottlenecks and propose trades.

3. MULTI-SEMESTER PLANNING (separate endpoint):
   The Multi-Semester Agent runs its own 3-agent sub-pipeline
   (Prerequisite → Rotation → Sequencing).
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..models import (
    DegreeAudit,
    OutstandingRequirement,
    ScheduleOption,
    SchedulePreferences,
    Section,
)
from . import professor_match_agent, workload_agent, negotiator_agent, multi_semester_agent

logger = logging.getLogger(__name__)


def enrich_schedules(
    schedules: list[ScheduleOption],
    preferences: SchedulePreferences,
) -> dict:
    """Run Professor Match + Workload agents in parallel to enrich schedules.

    Args:
        schedules: The solver's top 3 candidate schedules.
        preferences: Student preferences for professor matching.

    Returns:
        A dict containing:
        - professor_data: list of per-schedule professor analyses
        - workload_data: list of per-schedule workload analyses
        - agents_run: list of agent names that executed
        - orchestration_ms: total wall-clock time for all agents
    """
    start = time.time()
    results: dict = {
        "professor_data": [],
        "workload_data": [],
        "agents_run": [],
        "orchestration_ms": 0,
    }

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(professor_match_agent.run, schedules, preferences): "professor_match",
            executor.submit(workload_agent.run, schedules): "workload",
        }

        for future in as_completed(futures):
            agent_name = futures[future]
            try:
                data = future.result()
                if agent_name == "professor_match":
                    results["professor_data"] = data
                elif agent_name == "workload":
                    results["workload_data"] = data
                results["agents_run"].append(agent_name)
                logger.info(f"orchestrator.agent_complete.{agent_name}")
            except Exception as e:
                logger.error(f"orchestrator.agent_failed.{agent_name}", extra={"error": str(e)})

    results["orchestration_ms"] = int((time.time() - start) * 1000)
    logger.info("orchestrator.enrichment_complete", extra={
        "agents_run": results["agents_run"],
        "orchestration_ms": results["orchestration_ms"],
    })
    return results


def negotiate_constraints(
    outstanding_requirements: list[OutstandingRequirement],
    all_sections: list[Section],
    preferences: SchedulePreferences,
) -> dict:
    """Run the Negotiator Agent when the solver returns zero schedules.

    Returns:
        The negotiator's analysis with bottlenecks and proposed trades.
    """
    start = time.time()
    result = negotiator_agent.run(outstanding_requirements, all_sections, preferences)
    result["orchestration_ms"] = int((time.time() - start) * 1000)
    result["agents_run"] = ["negotiator"]
    logger.info("orchestrator.negotiation_complete", extra={
        "trades": len(result.get("trades", [])),
        "orchestration_ms": result["orchestration_ms"],
    })
    return result


def plan_multi_semester(
    audit: DegreeAudit,
    all_sections: list[Section],
) -> dict:
    """Run the Multi-Semester Planner's 3-agent sub-pipeline.

    Returns:
        The complete 4-semester roadmap with prerequisite and rotation data.
    """
    start = time.time()
    result = multi_semester_agent.run(audit, all_sections)
    result["orchestration_ms"] = int((time.time() - start) * 1000)
    logger.info("orchestrator.multi_semester_complete", extra={
        "semesters": len(result.get("semester_plan", [])),
        "orchestration_ms": result["orchestration_ms"],
    })
    return result
