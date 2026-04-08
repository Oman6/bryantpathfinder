"""Conflict Negotiator Agent — proposes specific constraint tradeoffs.

Activated when the solver returns zero valid schedules. Instead of a
generic "loosen your constraints" message, this agent analyzes exactly
which constraint is the bottleneck and proposes concrete trades.
"""

import logging
from itertools import combinations

from ..models import OutstandingRequirement, SchedulePreferences, Section
from ..requirement_expander import expand_requirement
from ..solver import filter_candidates_by_preferences, sections_conflict

logger = logging.getLogger(__name__)


def _count_candidates(
    requirements: list[OutstandingRequirement],
    all_sections: list[Section],
    preferences: SchedulePreferences,
) -> dict[str, int]:
    """Count how many candidate sections survive filtering for each requirement."""
    counts = {}
    for req in requirements:
        expanded = expand_requirement(req, all_sections)
        if req.rule_type == "course_with_lab":
            counts[req.id] = len(expanded)
        else:
            filtered = filter_candidates_by_preferences(expanded, preferences)
            counts[req.id] = len(filtered)
    return counts


def _test_without_constraint(
    requirements: list[OutstandingRequirement],
    all_sections: list[Section],
    base_prefs: SchedulePreferences,
    modification: str,
) -> int:
    """Test how many candidates appear if we remove one constraint."""
    import copy
    prefs = copy.deepcopy(base_prefs)

    if modification == "remove_blocked_days":
        prefs.blocked_days = []
    elif modification == "remove_early_limit":
        prefs.no_earlier_than = None
    elif modification == "remove_late_limit":
        prefs.no_later_than = None

    total = 0
    for req in requirements:
        expanded = expand_requirement(req, all_sections)
        if req.rule_type == "course_with_lab":
            total += len(expanded)
        else:
            filtered = filter_candidates_by_preferences(expanded, prefs)
            total += len(filtered)
    return total


def run(
    outstanding_requirements: list[OutstandingRequirement],
    all_sections: list[Section],
    preferences: SchedulePreferences,
) -> dict:
    """Analyze why the solver returned zero schedules and propose trades.

    Returns:
        A dict containing:
        - bottlenecks: list of constraints causing the most candidate elimination
        - trades: list of proposed tradeoffs with impact estimates
        - zero_candidate_requirements: requirements with zero candidates after filtering
        - analysis: human-readable explanation of the situation
    """
    selected_ids = set(preferences.selected_requirement_ids)
    if selected_ids:
        requirements = [r for r in outstanding_requirements if r.id in selected_ids]
    else:
        requirements = list(outstanding_requirements)

    # Count candidates with current constraints
    current_counts = _count_candidates(requirements, all_sections, preferences)
    zero_reqs = [rid for rid, count in current_counts.items() if count == 0]
    total_current = sum(current_counts.values())

    # Test removing each constraint
    trades = []

    if preferences.blocked_days:
        freed = _test_without_constraint(
            requirements, all_sections, preferences, "remove_blocked_days"
        )
        gained = freed - total_current
        if gained > 0:
            day_names = {"M": "Monday", "T": "Tuesday", "W": "Wednesday", "R": "Thursday", "F": "Friday"}
            blocked_names = [day_names.get(d, d) for d in preferences.blocked_days]
            trades.append({
                "action": f"Remove {', '.join(blocked_names)} block",
                "constraint": "blocked_days",
                "impact": f"Unlocks {gained} additional section options",
                "sections_gained": gained,
                "priority": gained,
            })

    if preferences.no_earlier_than:
        freed = _test_without_constraint(
            requirements, all_sections, preferences, "remove_early_limit"
        )
        gained = freed - total_current
        if gained > 0:
            trades.append({
                "action": f"Allow classes before {preferences.no_earlier_than}",
                "constraint": "no_earlier_than",
                "impact": f"Unlocks {gained} additional section options",
                "sections_gained": gained,
                "priority": gained,
            })

    if preferences.no_later_than:
        freed = _test_without_constraint(
            requirements, all_sections, preferences, "remove_late_limit"
        )
        gained = freed - total_current
        if gained > 0:
            trades.append({
                "action": f"Allow classes after {preferences.no_later_than}",
                "constraint": "no_later_than",
                "impact": f"Unlocks {gained} additional section options",
                "sections_gained": gained,
                "priority": gained,
            })

    # Test dropping individual requirements
    if len(requirements) > 4:
        req_map = {r.id: r for r in requirements}
        for req in requirements:
            reduced = [r for r in requirements if r.id != req.id]
            reduced_credits = sum(r.credits_needed for r in reduced)
            if abs(reduced_credits - preferences.target_credits) <= 3:
                trades.append({
                    "action": f"Drop {req.requirement} ({req.id})",
                    "constraint": "requirement",
                    "impact": f"Reduces to {len(reduced)} requirements, {reduced_credits} credits",
                    "sections_gained": current_counts.get(req.id, 0),
                    "priority": -current_counts.get(req.id, 0),  # prefer dropping reqs with few options
                })

    # Sort trades by priority (most impactful first)
    trades.sort(key=lambda t: t["priority"], reverse=True)

    # Build bottleneck list
    bottlenecks = []
    if preferences.blocked_days:
        bottlenecks.append({
            "constraint": "Blocked days",
            "detail": f"{', '.join(preferences.blocked_days)} blocked",
            "severity": "high" if any(current_counts.get(rid, 0) < 3 for rid in current_counts) else "medium",
        })
    if preferences.no_earlier_than:
        bottlenecks.append({
            "constraint": "No early classes",
            "detail": f"Nothing before {preferences.no_earlier_than}",
            "severity": "medium",
        })
    if preferences.no_later_than:
        bottlenecks.append({
            "constraint": "No late classes",
            "detail": f"Nothing after {preferences.no_later_than}",
            "severity": "medium",
        })
    if len(requirements) > 5:
        total_credits = sum(r.credits_needed for r in requirements)
        bottlenecks.append({
            "constraint": "Too many requirements",
            "detail": f"{len(requirements)} requirements = {total_credits} credits vs {preferences.target_credits} target",
            "severity": "high" if total_credits > preferences.target_credits + 6 else "medium",
        })

    # Analysis summary
    analysis_parts = []
    if zero_reqs:
        analysis_parts.append(
            f"{len(zero_reqs)} requirement(s) have zero available sections after filtering."
        )
    if total_current < len(requirements):
        analysis_parts.append(
            "Some requirements have very few options, making conflict-free combinations unlikely."
        )
    if trades:
        best = trades[0]
        analysis_parts.append(f"Best trade: {best['action']} — {best['impact']}.")

    analysis = " ".join(analysis_parts) if analysis_parts else "The constraints are too tight for the selected requirements."

    logger.info("agent.negotiator.complete", extra={
        "zero_reqs": len(zero_reqs),
        "trades": len(trades),
    })

    return {
        "bottlenecks": bottlenecks,
        "trades": trades[:5],  # top 5 trades
        "zero_candidate_requirements": zero_reqs,
        "candidate_counts": current_counts,
        "analysis": analysis,
    }
