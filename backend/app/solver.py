"""Pure Python constraint solver for BryantPathfinder.

This is the heart of Pathfinder. It takes outstanding requirements, candidate
sections, and student preferences, then returns valid, conflict-free schedules
ranked by a multi-factor scoring function.

No LLM calls. No external optimization libraries. About 500 lines of
documented, deterministic Python.

The solver guarantees correctness: every returned schedule is conflict-free.
Claude is only called after the solver finishes (and after the refiner runs),
to explain and re-rank the final picks.

See docs/adr/0003-deterministic-solver-vs-llm.md for why this design was chosen.
"""

import itertools
import json
import logging
import time
from pathlib import Path
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

# Per-subset cap so one large candidate pool can't consume the entire global
# budget and starve course-set diversity. Once a subset has produced this many
# combinations we move on to the next requirement subset.
MAX_COMBINATIONS_PER_SUBSET = 1_500

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


# --- Static professor ratings for in-solver scoring ---
# Loaded lazily on first call so the solver stays self-contained and doesn't
# require a Pydantic config object — these are the same ratings the agents use.
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_RATINGS_PATH = _DATA_DIR / "professor_ratings.json"
_ratings_cache: dict | None = None


def _ratings() -> dict:
    global _ratings_cache
    if _ratings_cache is None:
        try:
            _ratings_cache = json.loads(_RATINGS_PATH.read_text(encoding="utf-8"))
        except FileNotFoundError:
            _ratings_cache = {}
    return _ratings_cache


def professor_quality_score(section: Section) -> float:
    """Per-section quality signal in roughly the range [-3.0, +3.0].

    Returns 0 when there's insufficient data (no instructor, no rating, or
    fewer than 5 ratings). This avoids penalizing professors who happen to
    have no RMP presence — common at small schools.
    """
    if not section.instructor:
        return 0.0
    r = _ratings().get(section.instructor)
    if not r:
        return 0.0
    num_ratings = r.get("num_ratings", 0)
    if num_ratings < 5:
        return 0.0
    quality = r.get("quality", 0) or 0
    wta = r.get("would_take_again", -1)
    score = 0.0
    # Quality is the headline RMP star (1.0–5.0).
    if quality >= 4.5:
        score += 2.5
    elif quality >= 4.0:
        score += 1.5
    elif quality >= 3.5:
        score += 0.5
    elif quality < 2.5:
        score -= 2.0
    elif quality < 3.0:
        score -= 1.0
    # "Would take again" is a stronger signal but only fires on enough data.
    if num_ratings >= 10:
        if wta >= 80:
            score += 1.0
        elif 0 <= wta < 25:
            score -= 1.0
    return score


def seat_safety_score(section: Section) -> float:
    """Penalize sections that are about to close. Reward healthy headroom."""
    total = section.seats_total
    open_seats = section.seats_open
    if total <= 0:
        return 0.0
    if open_seats <= 0:
        return -5.0  # waitlist-only — strongly avoid
    if open_seats < 3:
        return -3.0  # 1–2 seats left — almost certainly closes during reg
    if open_seats / total >= 0.5:
        return 1.0
    return 0.0


def time_of_day_score(section: Section, preferences: SchedulePreferences) -> float:
    """Penalize evening classes unless the student already opted into them.

    Honors any explicit no_later_than the student set — if they already
    capped at 17:00 the solver wouldn't have offered evenings anyway.
    """
    score = 0.0
    for m in section.meetings:
        start_min = to_minutes(m.start)
        if start_min >= 18 * 60:  # 6:00 PM and later
            score -= 2.0
        elif start_min >= 17 * 60:  # 5:00 PM
            score -= 0.5
    return score


def instructor_diversity_score(sections: list[Section]) -> float:
    """Penalize loading three or more sections with the same instructor.

    A student typically wants variety; if Kumar is teaching half your
    schedule that's a flag (legitimately fine in some cases, but the solver
    should default to spreading the bet).
    """
    counts: dict[str, int] = {}
    for s in sections:
        if s.instructor:
            counts[s.instructor] = counts.get(s.instructor, 0) + 1
    return sum(-2.0 * (c - 2) for c in counts.values() if c >= 3)


def subject_diversity_score(sections: list[Section]) -> float:
    """Penalize loading 5+ sections in the same subject (e.g., 5 FIN courses)."""
    counts: dict[str, int] = {}
    for s in sections:
        counts[s.subject] = counts.get(s.subject, 0) + 1
    excess = sum(c - 4 for c in counts.values() if c >= 5)
    return -3.0 * excess


def score_combination(
    sections: list[Section],
    requirements: list[OutstandingRequirement],
    preferences: SchedulePreferences,
) -> float:
    """Score a valid schedule combination on multiple dimensions.

    Returns a float; higher is better. Components:
      1. Credit match            — how close to target_credits
      2. Instructor preferences  — preferred/avoided lists
      3. Seat safety             — penalize tight-headroom sections
      4. Category balance        — reward mix across major/core/gen-ed
      5. Professor quality       — RMP-weighted signal per section
      6. Time of day             — penalize evening sections
      7. Instructor diversity    — penalize same-prof-3+-times
      8. Subject diversity       — penalize 5+-of-same-subject
    """
    score = 0.0

    # 1. Credit match — strongly prefer being at or just below target
    total_credits = sum(s.credits for s in sections)
    credit_diff = abs(total_credits - preferences.target_credits)
    if credit_diff == 0:
        score += 15.0
    elif credit_diff <= 1:
        score += 12.0
    else:
        score += max(0.0, 12.0 - credit_diff * 3)

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

    # 3. Seat safety
    for section in sections:
        score += seat_safety_score(section)

    # 4. Category balance
    categories = {r.category for r in requirements}
    score += len(categories) * 3.0

    # 5. Professor quality (the big change)
    for section in sections:
        score += professor_quality_score(section) * 1.5

    # 6. Time of day
    for section in sections:
        score += time_of_day_score(section, preferences)

    # 7 & 8. Diversity
    score += instructor_diversity_score(sections)
    score += subject_diversity_score(sections)

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
    *,
    max_candidates: int = 3,
) -> list[ScheduleOption]:
    """Generate up to `max_candidates` valid, conflict-free schedules.

    Pass max_candidates>3 to feed a downstream refiner with diverse options.

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

    # Courses already "claimed" by a specific_course or choose_one_of requirement.
    # Wildcard pools must exclude these, otherwise a wildcard (e.g. FIN 4XX) can
    # re-select a course another requirement already covers — the root cause of the
    # same course appearing twice in one schedule.
    claimed_courses: set[str] = set()
    for r in requirements:
        if r.rule_type in ("specific_course", "choose_one_of"):
            claimed_courses.update(r.options)

    # Step 1 & 2: Expand and filter candidates for each requirement
    candidate_pools: list[list[list[Section]]] = []
    pool_requirements: list[OutstandingRequirement] = []

    for req in requirements:
        # A required specific course (e.g. FIN 310) must still surface even when
        # every one of its sections is full — otherwise it silently vanishes from
        # the plan. Seat-safety scoring down-ranks full sections so they read as
        # waitlist rather than being dropped. choose_one_of / wildcard requirements
        # have alternatives, so full sections stay filtered out for them.
        include_full = req.rule_type == "specific_course"
        expanded = expand_requirement(req, all_sections, include_full=include_full)

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
            # For wildcard rules, exclude sections that are already covered
            # by a specific_course requirement to avoid double-scheduling
            if req.rule_type == "wildcard" and claimed_courses:
                filtered = [s for s in filtered if s.course_code not in claimed_courses]
            if filtered:
                # Each candidate is a single-section list for uniform handling
                candidate_pools.append([[s] for s in filtered])
                pool_requirements.append(req)

    if not candidate_pools:
        logger.warning("solver.no_candidates_after_filtering")
        return []

    # Step 3: Pick subsets of requirements whose credits are within target ± 3.
    # Priority order: major > business_core > general_education > elective > minor.
    # This ensures FIN courses appear in results, not just gen eds.
    req_credits = [r.credits_needed for r in pool_requirements]
    total_all = sum(req_credits)
    target = preferences.target_credits
    credit_low = target - 3
    credit_high = target + 3

    if total_all <= credit_high:
        # All requirements fit in the credit window — use them all
        requirement_subsets = [tuple(range(len(pool_requirements)))]
    else:
        # Generate subsets that fit the credit window, prioritizing major courses.
        requirement_subsets_list: list[tuple[int, ...]] = []
        n = len(pool_requirements)

        # Score each subset by category priority and credit closeness to target
        CATEGORY_PRIORITY = {"major": 4, "business_core": 3, "general_education": 2, "elective": 1, "minor": 1}

        def _subset_score(indices: tuple[int, ...]) -> float:
            """Score a subset: closeness to the target credit count dominates,
            with a mild preference for higher-priority (major/core) requirements.

            Closeness is the primary term so the solver stops overshooting — e.g.
            returning three 18-credit schedules when the student asked for 15.
            Going over target is penalized harder than coming in under it, since an
            over-target schedule is one the student cannot actually register for.
            The category preference is *averaged* over the subset (not summed) so it
            does not grow with subset size and quietly outweigh closeness.
            """
            credits = sum(req_credits[i] for i in indices)
            diff = credits - target
            closeness = -3.0 * diff if diff >= 0 else 2.0 * diff
            avg_priority = (
                sum(CATEGORY_PRIORITY.get(pool_requirements[i].category, 0) for i in indices)
                / len(indices)
            )
            distinct_cats = len({pool_requirements[i].category for i in indices})
            return closeness * 10 + avg_priority + distinct_cats * 0.5

        # Target the ideal subset size (target_credits / avg_credits_per_req)
        avg_credits = sum(req_credits) / len(req_credits) if req_credits else 3
        ideal_size = max(1, round(target / avg_credits))
        sizes_to_try = sorted(
            range(max(1, ideal_size - 2), min(n + 1, ideal_size + 3)),
            key=lambda s: abs(s - ideal_size),
        )

        all_candidates: list[tuple[float, tuple[int, ...]]] = []
        for size in sizes_to_try:
            if size > n:
                continue
            for subset in itertools.combinations(range(n), size):
                subset_credits = sum(req_credits[i] for i in subset)
                if credit_low <= subset_credits <= credit_high:
                    score = _subset_score(subset)
                    all_candidates.append((score, subset))

        if not all_candidates:
            logger.warning("solver.no_valid_subsets", extra={
                "total_credits": total_all,
                "target": target,
                "num_requirements": n,
            })
            return []

        # Sort by score descending, take top subsets, and ensure diversity
        # by picking subsets that cover different requirement combinations
        all_candidates.sort(key=lambda x: x[0], reverse=True)
        seen_req_sets: list[frozenset[str]] = []
        for _, subset in all_candidates:
            req_set = frozenset(pool_requirements[i].id for i in subset)
            if req_set not in seen_req_sets:
                requirement_subsets_list.append(subset)
                seen_req_sets.append(req_set)
            if len(requirement_subsets_list) >= 30:
                break

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

        subset_evaluated = 0
        for combo in itertools.product(*subset_pools):
            combinations_evaluated += 1
            subset_evaluated += 1
            if combinations_evaluated > MAX_COMBINATIONS:
                logger.warning("solver.max_combinations_reached", extra={"cap": MAX_COMBINATIONS})
                break
            if subset_evaluated > MAX_COMBINATIONS_PER_SUBSET:
                break

            # Flatten the combination
            all_combo_sections: list[Section] = []
            for section_group in combo:
                all_combo_sections.extend(section_group)

            # Reject any combination that schedules the same course twice. Two
            # requirements with overlapping pools (a choose_one_of and a wildcard,
            # or two wildcards) can independently pick the same course; dedup-by-CRN
            # downstream would not catch it because the sections have different CRNs.
            combo_course_codes = [s.course_code for s in all_combo_sections]
            if len(set(combo_course_codes)) != len(combo_course_codes):
                continue

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

    # Step 6: Sort by score, then select schedules preferring *distinct course
    # sets* so the options shown to the student differ in which courses they take,
    # not merely in which section/CRN was picked. Section-variants of an already-
    # chosen course set are deferred and only used to backfill if there aren't
    # enough distinct course sets to reach max_candidates.
    valid_schedules.sort(key=lambda x: x[0], reverse=True)

    top_schedules: list[ScheduleOption] = []
    seen_crn_sets: set[frozenset[str]] = set()
    seen_course_sets: set[frozenset[str]] = set()
    deferred: list[tuple[float, list[Section], list[OutstandingRequirement]]] = []

    def _make_option(score: float, sections: list[Section], reqs: list[OutstandingRequirement]) -> ScheduleOption:
        metadata = _get_schedule_metadata(sections)
        return ScheduleOption(
            rank=len(top_schedules) + 1,
            sections=sections,
            requirements_satisfied=[r.id for r in reqs],
            total_credits=sum(s.credits for s in sections),
            days_off=metadata["days_off"],
            earliest_class=metadata["earliest_class"],
            latest_class=metadata["latest_class"],
            score=score,
            explanation="",
        )

    for score, sections, reqs in valid_schedules:
        crn_set = frozenset(s.crn for s in sections)
        if crn_set in seen_crn_sets:
            continue
        seen_crn_sets.add(crn_set)
        course_set = frozenset(s.course_code for s in sections)
        if course_set in seen_course_sets:
            deferred.append((score, sections, reqs))
            continue
        seen_course_sets.add(course_set)
        top_schedules.append(_make_option(score, sections, reqs))
        if len(top_schedules) >= max_candidates:
            break

    if len(top_schedules) < max_candidates:
        for score, sections, reqs in deferred:
            top_schedules.append(_make_option(score, sections, reqs))
            if len(top_schedules) >= max_candidates:
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
