"""Expand outstanding requirements into candidate sections from the catalog.

Each rule type (specific_course, choose_one_of, wildcard, course_with_lab)
has its own expansion logic. The expander filters the sections.json catalog
down to only the sections that could satisfy a given requirement.
"""

import logging
from typing import Literal

from .models import OutstandingRequirement, Section

logger = logging.getLogger(__name__)


def expand_requirement(
    requirement: OutstandingRequirement,
    all_sections: list[Section],
    *,
    include_full: bool = False,
    include_async: bool = False,
) -> list[Section] | list[tuple[Section, Section]]:
    """Return the candidate sections that satisfy a given requirement.

    Args:
        requirement: The outstanding requirement to expand.
        all_sections: The full catalog of sections from sections.json.
        include_full: If True, include sections with no open seats.
        include_async: If True, include async/online sections.

    Returns:
        For most rule types, a list of Section objects.
        For course_with_lab, a list of (lecture_section, lab_section) tuples.
    """
    if requirement.rule_type == "course_with_lab":
        return _expand_course_with_lab(requirement, all_sections, include_full=include_full, include_async=include_async)

    candidates = _get_matching_sections(requirement, all_sections)
    candidates = _apply_filters(candidates, include_full=include_full, include_async=include_async)

    logger.info(
        "expander.expanded",
        extra={
            "requirement_id": requirement.id,
            "rule_type": requirement.rule_type,
            "candidates": len(candidates),
        },
    )
    return candidates


def _get_matching_sections(
    requirement: OutstandingRequirement,
    all_sections: list[Section],
) -> list[Section]:
    """Find sections that match the requirement by rule type."""
    if requirement.rule_type in ("specific_course", "choose_one_of"):
        return [s for s in all_sections if s.course_code in requirement.options]

    if requirement.rule_type == "wildcard":
        return _expand_wildcard(requirement.pattern, all_sections)

    return []


def _expand_wildcard(pattern: str | None, all_sections: list[Section]) -> list[Section]:
    """Expand a wildcard pattern like 'FIN 4XX' into matching sections.

    Pattern format: '<SUBJECT> <DIGIT>XX' where the digit filters by course level,
    or '<SUBJECT> XXX' which matches any course number for that subject.
    """
    if not pattern:
        return []

    parts = pattern.split()
    if len(parts) != 2:
        return []

    subject_prefix = parts[0]
    number_pattern = parts[1]

    results = []
    for section in all_sections:
        if section.subject != subject_prefix:
            continue

        if number_pattern == "XXX":
            # Match any course number for this subject
            results.append(section)
        elif number_pattern.endswith("XX") and len(number_pattern) == 3:
            # Match by first digit (level), e.g., '4XX' matches 400-499
            level_digit = number_pattern[0]
            if section.course_number.startswith(level_digit):
                results.append(section)

    return results


def _expand_course_with_lab(
    requirement: OutstandingRequirement,
    all_sections: list[Section],
    *,
    include_full: bool = False,
    include_async: bool = False,
) -> list[tuple[Section, Section]]:
    """Expand a course_with_lab requirement into (lecture, lab) tuples.

    Each pair in requirement.pairs defines a valid (lecture_code, lab_code) combination.
    The expander finds all sections for each code, then produces every valid
    lecture+lab combination from matching pairs.
    """
    if not requirement.pairs:
        return []

    results: list[tuple[Section, Section]] = []

    for pair in requirement.pairs:
        if len(pair) != 2:
            continue
        lecture_code, lab_code = pair[0], pair[1]

        lectures = [s for s in all_sections if s.course_code == lecture_code]
        labs = [s for s in all_sections if s.course_code == lab_code]

        lectures = _apply_filters(lectures, include_full=include_full, include_async=include_async)
        labs = _apply_filters(labs, include_full=include_full, include_async=include_async)

        for lecture in lectures:
            for lab in labs:
                results.append((lecture, lab))

    logger.info(
        "expander.expanded_lab",
        extra={
            "requirement_id": requirement.id,
            "pairs": len(results),
        },
    )
    return results


def _apply_filters(
    sections: list[Section],
    *,
    include_full: bool = False,
    include_async: bool = False,
) -> list[Section]:
    """Filter out FULL and async sections unless explicitly included."""
    result = sections
    if not include_full:
        result = [s for s in result if not s.is_full]
    if not include_async:
        result = [s for s in result if not s.is_async]
    return result
