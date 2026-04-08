"""Pure Python constraint solver for BryantPathfinder.

This is the heart of Pathfinder. It takes outstanding requirements, candidate
sections, and student preferences, then returns the top three valid, conflict-free
schedules ranked by a multi-factor scoring function.

No LLM calls. No external optimization libraries. About 400 lines of
documented, deterministic Python.

The solver guarantees correctness: every returned schedule is conflict-free.
Claude is only called after the solver finishes, to explain and re-rank
the top three options.

See docs/adr/0003-deterministic-solver-vs-llm.md for why this design was chosen.
"""

import itertools
import logging
import time
from typing import Literal

from .models import (
    Meeting,
    OutstandingRequirement,
    ScheduleOption,
    SchedulePreferences,
    Section,
)
from .requirement_expander import expand_requirement

logger = logging.getLogger(__name__)

# Safety cap: stop evaluating after this many combinations to avoid
# pathological cases blowing up the response time.
MAX_COMBINATIONS = 10_000

ALL_DAYS: list[str] = ["M", "T", "W", "R", "F"]


def to_minutes(time_str: str) -> int:
    """Convert an 'HH:MM' string to minutes since midnight.

    Args:
        time_str: Time in 24-hour 'HH:MM' format, e.g. '14:30'.

    Returns:
        Integer minutes since midnight, e.g. 870 for '14:30'.
    """
    hours, minutes = time_str.split(":")
    return int(hours) * 60 + int(minutes)


def sections_conflict(a: Section, b: Section) -> bool:
    """Check whether two sections have overlapping meeting times.

    Uses the half-open interval rule: two time ranges overlap if each starts
    strictly before the other ends. Back-to-back classes (one ending at 10:50,
    another starting at 10:50) do NOT conflict — Bryant's block schedule is
    designed this way.

    Handles multi-meeting sections by checking all pairs of meetings across
    the two sections.

    Args:
        a: First section.
        b: Second section.

    Returns:
        True if any meeting of a overlaps with any meeting of b on a shared day.
    """
    for meeting_a in a.meetings:
        for meeting_b in b.meetings:
            shared_days = set(meeting_a.days) & set(meeting_b.days)
            if not shared_days:
                continue
            a_start = to_minutes(meeting_a.start)
            a_end = to_minutes(meeting_a.end)
            b_start = to_minutes(meeting_b.start)
            b_end = to_minutes(meeting_b.end)
            if a_start < b_end and b_start < a_end:
                return True
    return False


def _section_on_blocked_day(section: Section, blocked_days: list[str]) -> bool:
    """Check if a section meets on any blocked day."""
    for meeting in section.meetings:
        if set(meeting.days) & set(blocked_days):
            return True
    return False


def _section_outside_time_window(
    section: Section,
    no_earlier_than: str | None,
    no_later_than: str | None,
) -> bool:
    """Check if a section's meetings fall outside the allowed time window."""
    for meeting in section.meetings:
        if no_earlier_than and to_minutes(meeting.start) < to_minutes(no_earlier_than):
            return True
        if no_later_than and to_minutes(meeting.end) > to_minutes(no_later_than):
            return True
    return False


def _has_avoided_instructor(section: Section, avoided: list[str]) -> bool:
    """Check if a section is taught by an avoided instructor."""
    if not section.instructor:
        return False
    instructor_lower = section.instructor.lower()
    return any(a.lower() in instructor_lower for a in avoided)


def filter_candidates_by_preferences(
    sections: list[Section],
    preferences: SchedulePreferences,
) -> list[Section]:
    """Remove sections that violate hard preference constraints.

    Hard constraints (sections are removed entirely):
    - Section meets on a blocked day
    - Section starts before no_earlier_than
    - Section ends after no_later_than

    Soft constraints (handled in scoring, not filtering):
    - Preferred/avoided instructors
    - Target credits

    Args:
        sections: List of candidate sections.
        preferences: Student preferences.

    Returns:
        Filtered list with only sections that pass hard constraints.
    """
    result = []
    for section in sections:
        if preferences.blocked_days and _section_on_blocked_day(section, preferences.blocked_days):
            continue
        if _section_outside_time_window(section, preferences.no_earlier_than, preferences.no_later_than):
            continue
        result.append(section)
    return result


def score_combination(
    sections: list[Section],
    requirements: list[OutstandingRequirement],
    preferences: SchedulePreferences,
) -> float:
    """Score a valid schedule combination on four dimensions.

    Scoring dimensions:
    1. Credit match — how close to target_credits (max +10)
    2. Preference fit — preferred/avoided instructors (+5 / -10 each)
    3. Seat availability — +1 per section with >50% seats open
    4. Category balance — +3 per distinct requirement category covered

    Args:
        sections: The sections in this schedule combination.
        requirements: The requirements these sections satisfy.
        preferences: Student preferences for scoring context.

    Returns:
        A float score. Higher is better.
    """
    score = 0.0

    # 1. Credit match
    total_credits = sum(s.credits for s in sections)
    credit_diff = abs(total_credits - preferences.target_credits)
    if credit_diff <= 1:
        score += 10.0
    else:
        score += max(0.0, 10.0 - credit_diff * 2)

    # 2. Instructor preferences
    for section in sections:
        if not section.instructor:
            continue
        instructor_lower = section.instructor.lower()
        for pref in preferences.preferred_instructors:
            if pref.lower() in instructor_lower:
                score += 5.0
        for avoid in preferences.avoided_instructors:
            if avoid.lower() in instructor_lower:
                score -= 10.0

    # 3. Seat availability
    for section in sections:
        if section.seats_total > 0 and section.seats_open / section.seats_total > 0.5:
            score += 1.0

    # 4. Category balance
    categories = {r.category for r in requirements}
    score += len(categories) * 3.0

    return score


def _get_schedule_metadata(sections: list[Section]) -> dict:
    """Compute derived metadata for a schedule: days off, earliest/latest class."""
    active_days: set[str] = set()
    earliest = "23:59"
    latest = "00:00"

    for section in sections:
        for meeting in section.meetings:
            active_days.update(meeting.days)
            if to_minutes(meeting.start) < to_minutes(earliest):
                earliest = meeting.start
            if to_minutes(meeting.end) > to_minutes(latest):
                latest = meeting.end

    days_off = sorted([d for d in ALL_DAYS if d not in active_days], key=ALL_DAYS.index)

    return {
        "days_off": days_off,
        "earliest_class": earliest,
        "latest_class": latest,
    }


def solve(
    outstanding_requirements: list[OutstandingRequirement],
    all_sections: list[Section],
    preferences: SchedulePreferences,
) -> list[ScheduleOption]:
    """Generate the top three valid, conflict-free schedules.

    Algorithm:
    1. For each selected requirement, expand into candidate sections.
    2. Filter candidates by hard preference constraints.
    3. Generate every combination of one section per requirement.
    4. For each combination, check pairwise time conflicts.
    5. Score each valid combination on credit match, preference fit,
       seat availability, and category balance.
    6. Return the top 3 distinct ScheduleOption objects.

    Args:
        outstanding_requirements: The requirements to schedule this term.
        all_sections: The full catalog from sections.json.
        preferences: Student preferences.

    Returns:
        A list of up to 3 ScheduleOption objects, sorted by score descending.
        Returns an empty list if no valid schedules exist.
    """
    start_time = time.time()

    # Filter to selected requirements only
    selected_ids = set(preferences.selected_requirement_ids)
    if selected_ids:
        requirements = [r for r in outstanding_requirements if r.id in selected_ids]
    else:
        requirements = list(outstanding_requirements)

    if not requirements:
        logger.warning("solver.no_requirements", extra={"selected_ids": list(selected_ids)})
        return []

    # Step 1 & 2: Expand and filter candidates for each requirement
    candidate_pools: list[list[list[Section]]] = []
    pool_requirements: list[OutstandingRequirement] = []

    for req in requirements:
        expanded = expand_requirement(req, all_sections)

        if req.rule_type == "course_with_lab":
            # Each tuple is (lecture, lab) — flatten to a list of section-pairs
            lab_pairs: list[list[Section]] = []
            for lecture, lab in expanded:
                pair = [lecture, lab]
                # Filter each section in the pair by preferences
                lecture_ok = not (
                    (preferences.blocked_days and _section_on_blocked_day(lecture, preferences.blocked_days))
                    or _section_outside_time_window(lecture, preferences.no_earlier_than, preferences.no_later_than)
                )
                lab_ok = not (
                    (preferences.blocked_days and _section_on_blocked_day(lab, preferences.blocked_days))
                    or _section_outside_time_window(lab, preferences.no_earlier_than, preferences.no_later_than)
                )
                # Also check that the lecture and lab don't conflict with each other
                if lecture_ok and lab_ok and not sections_conflict(lecture, lab):
                    lab_pairs.append(pair)
            if lab_pairs:
                candidate_pools.append(lab_pairs)
                pool_requirements.append(req)
        else:
            filtered = filter_candidates_by_preferences(expanded, preferences)
            if filtered:
                # Each candidate is a single-section list for uniform handling
                candidate_pools.append([[s] for s in filtered])
                pool_requirements.append(req)

    if not candidate_pools:
        logger.warning("solver.no_candidates_after_filtering")
        return []

    # Step 3: Pick subsets of requirements whose credits are within target ± 3.
    # If all requirements together exceed the credit window, we generate
    # subsets that fit. This is the key step that makes the solver work
    # when many requirements are selected.
    req_credits = [r.credits_needed for r in pool_requirements]
    total_all = sum(req_credits)
    target = preferences.target_credits
    credit_low = target - 3
    credit_high = target + 3

    if total_all <= credit_high:
        # All requirements fit in the credit window — use them all
        requirement_subsets = [tuple(range(len(pool_requirements)))]
    else:
        # Generate subsets whose total credits fall within the window.
        # Use itertools.combinations with increasing subset sizes.
        requirement_subsets_list: list[tuple[int, ...]] = []
        n = len(pool_requirements)
        # Try subset sizes from largest that could fit down to smallest
        max_courses = min(n, int(credit_high // 1) + 1)  # generous upper bound
        min_courses = max(1, int(credit_low // 4))  # at least this many 3-credit courses

        for size in range(max_courses, min_courses - 1, -1):
            if size > n:
                continue
            for subset in itertools.combinations(range(n), size):
                subset_credits = sum(req_credits[i] for i in subset)
                if credit_low <= subset_credits <= credit_high:
                    requirement_subsets_list.append(subset)
            # Cap the number of subsets to keep runtime bounded
            if len(requirement_subsets_list) >= 50:
                break

        if not requirement_subsets_list:
            logger.warning("solver.no_valid_subsets", extra={
                "total_credits": total_all,
                "target": target,
                "num_requirements": n,
            })
            return []

        requirement_subsets = requirement_subsets_list

    logger.info(
        "solver.subsets",
        extra={
            "total_requirements": len(pool_requirements),
            "subsets_to_try": len(requirement_subsets),
            "target_credits": target,
        },
    )

    # Step 4 & 5: For each subset, generate combinations, check conflicts, score
    valid_schedules: list[tuple[float, list[Section], list[OutstandingRequirement]]] = []
    combinations_evaluated = 0

    for subset_indices in requirement_subsets:
        subset_pools = [candidate_pools[i] for i in subset_indices]
        subset_reqs = [pool_requirements[i] for i in subset_indices]

        for combo in itertools.product(*subset_pools):
            combinations_evaluated += 1
            if combinations_evaluated > MAX_COMBINATIONS:
                logger.warning("solver.max_combinations_reached", extra={"cap": MAX_COMBINATIONS})
                break

            # Flatten the combination
            all_combo_sections: list[Section] = []
            for section_group in combo:
                all_combo_sections.extend(section_group)

            # Check pairwise conflicts
            has_conflict = False
            for i in range(len(all_combo_sections)):
                for j in range(i + 1, len(all_combo_sections)):
                    if sections_conflict(all_combo_sections[i], all_combo_sections[j]):
                        has_conflict = True
                        break
                if has_conflict:
                    break

            if has_conflict:
                continue

            # Score the valid combination
            combo_score = score_combination(all_combo_sections, subset_reqs, preferences)
            valid_schedules.append((combo_score, all_combo_sections, subset_reqs))

        if combinations_evaluated > MAX_COMBINATIONS:
            break

    # Step 6: Sort by score and take top 3 distinct schedules
    valid_schedules.sort(key=lambda x: x[0], reverse=True)

    # Deduplicate by CRN set
    seen_crn_sets: list[frozenset[str]] = []
    top_schedules: list[ScheduleOption] = []

    for score, sections, reqs in valid_schedules:
        crn_set = frozenset(s.crn for s in sections)
        if crn_set in seen_crn_sets:
            continue
        seen_crn_sets.append(crn_set)

        metadata = _get_schedule_metadata(sections)
        total_credits = sum(s.credits for s in sections)

        option = ScheduleOption(
            rank=len(top_schedules) + 1,
            sections=sections,
            requirements_satisfied=[r.id for r in reqs],
            total_credits=total_credits,
            days_off=metadata["days_off"],
            earliest_class=metadata["earliest_class"],
            latest_class=metadata["latest_class"],
            score=score,
            explanation="",
        )
        top_schedules.append(option)

        if len(top_schedules) >= 3:
            break

    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(
        "solver.completed",
        extra={
            "combinations_evaluated": combinations_evaluated,
            "valid_combinations": len(valid_schedules),
            "returned": len(top_schedules),
            "duration_ms": duration_ms,
        },
    )

    return top_schedules
