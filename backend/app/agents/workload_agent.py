"""Workload Balancer Agent — estimates weekly study hours and flags overload.

Runs in parallel with the Professor Match Agent after the solver returns
candidates. Uses RMP difficulty ratings and credit hours to compute a
workload estimate per schedule, per day, and per course.
"""

import json
import logging
from pathlib import Path

from ..models import ScheduleOption, Section
from ..solver import to_minutes

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
RATINGS_PATH = DATA_DIR / "professor_ratings.json"

# Study hours per credit per week, scaled by difficulty
# A 3-credit course with difficulty 3.0 = 3 * 2.0 = 6 hrs/week outside class
BASE_HOURS_PER_CREDIT = 2.0
DIFFICULTY_SCALE = {1: 0.5, 2: 0.75, 3: 1.0, 4: 1.4, 5: 1.8}


def _get_difficulty_multiplier(difficulty: float) -> float:
    """Map a 1-5 difficulty to a workload multiplier."""
    lower = int(difficulty)
    upper = lower + 1
    if upper > 5:
        return DIFFICULTY_SCALE[5]
    if lower < 1:
        return DIFFICULTY_SCALE[1]
    frac = difficulty - lower
    return DIFFICULTY_SCALE[lower] * (1 - frac) + DIFFICULTY_SCALE.get(upper, DIFFICULTY_SCALE[5]) * frac


def _load_ratings() -> dict:
    if not RATINGS_PATH.exists():
        return {}
    return json.loads(RATINGS_PATH.read_text(encoding="utf-8"))


def _analyze_section(section: Section, ratings: dict) -> dict:
    """Estimate workload for a single section."""
    difficulty = 3.0  # default if no RMP data
    if section.instructor and section.instructor in ratings:
        difficulty = ratings[section.instructor]["difficulty"]

    multiplier = _get_difficulty_multiplier(difficulty)
    class_hours = 0.0
    for m in section.meetings:
        duration = (to_minutes(m.end) - to_minutes(m.start)) / 60.0
        class_hours += duration * len(m.days)

    study_hours = section.credits * BASE_HOURS_PER_CREDIT * multiplier
    total_hours = class_hours + study_hours

    return {
        "course_code": section.course_code,
        "instructor": section.instructor,
        "credits": section.credits,
        "difficulty": round(difficulty, 1),
        "class_hours_per_week": round(class_hours, 1),
        "study_hours_per_week": round(study_hours, 1),
        "total_hours_per_week": round(total_hours, 1),
    }


def _analyze_daily_load(schedule: ScheduleOption) -> dict[str, dict]:
    """Compute per-day class hours and identify overloaded days."""
    day_labels = {"M": "Monday", "T": "Tuesday", "W": "Wednesday", "R": "Thursday", "F": "Friday"}
    daily: dict[str, float] = {d: 0.0 for d in ["M", "T", "W", "R", "F"]}
    daily_classes: dict[str, int] = {d: 0 for d in ["M", "T", "W", "R", "F"]}
    daily_gaps: dict[str, float] = {d: 0.0 for d in ["M", "T", "W", "R", "F"]}

    # Collect all meetings per day
    day_meetings: dict[str, list[tuple[int, int]]] = {d: [] for d in ["M", "T", "W", "R", "F"]}

    for section in schedule.sections:
        for meeting in section.meetings:
            duration = (to_minutes(meeting.end) - to_minutes(meeting.start)) / 60.0
            for day in meeting.days:
                daily[day] += duration
                daily_classes[day] += 1
                day_meetings[day].append((to_minutes(meeting.start), to_minutes(meeting.end)))

    # Calculate gaps between classes
    for day, meetings in day_meetings.items():
        if len(meetings) < 2:
            continue
        sorted_meetings = sorted(meetings, key=lambda x: x[0])
        for i in range(1, len(sorted_meetings)):
            gap = (sorted_meetings[i][0] - sorted_meetings[i - 1][1]) / 60.0
            daily_gaps[day] += gap

    result = {}
    for day in ["M", "T", "W", "R", "F"]:
        if daily[day] == 0:
            continue
        result[day] = {
            "label": day_labels[day],
            "class_hours": round(daily[day], 1),
            "num_classes": daily_classes[day],
            "gap_hours": round(daily_gaps[day], 1),
            "is_heavy": daily[day] > 4.0 or daily_classes[day] >= 3,
        }

    return result


def run(schedules: list[ScheduleOption]) -> list[dict]:
    """Run the Workload Agent on a list of schedule options.

    Returns:
        A list of dicts, one per schedule, containing:
        - course_breakdown: per-course workload estimates
        - daily_load: per-day class hours and flags
        - total_weekly_hours: estimated total hours (class + study)
        - workload_score: 1-10 rating (1=light, 10=crushing)
        - warnings: list of overload concerns
        - summary: one-sentence workload assessment
    """
    ratings = _load_ratings()
    results = []

    for schedule in schedules:
        course_breakdown = [_analyze_section(s, ratings) for s in schedule.sections]
        daily_load = _analyze_daily_load(schedule)

        total_class = sum(c["class_hours_per_week"] for c in course_breakdown)
        total_study = sum(c["study_hours_per_week"] for c in course_breakdown)
        total_weekly = round(total_class + total_study, 1)

        # Workload score: 1-10
        # 20 hrs/week = 3, 30 = 5, 40 = 7, 50+ = 9
        workload_score = min(10, max(1, round(total_weekly / 5.5)))

        warnings = []
        heavy_days = [d for d, info in daily_load.items() if info["is_heavy"]]
        if heavy_days:
            day_names = [daily_load[d]["label"] for d in heavy_days]
            warnings.append(f"Heavy days: {', '.join(day_names)} (3+ classes or 4+ hours)")

        hard_courses = [c for c in course_breakdown if c["difficulty"] >= 4.0]
        if len(hard_courses) >= 2:
            codes = [c["course_code"] for c in hard_courses]
            warnings.append(f"Multiple challenging courses: {', '.join(codes)}")

        if total_weekly > 45:
            warnings.append(f"Total estimated workload is {total_weekly} hrs/week — consider dropping a course")

        # Summary
        if workload_score <= 3:
            intensity = "light"
        elif workload_score <= 5:
            intensity = "moderate"
        elif workload_score <= 7:
            intensity = "heavy"
        else:
            intensity = "very heavy"

        summary = f"{total_weekly} estimated hours per week ({total_class} in class, {total_study} studying). {intensity.capitalize()} workload."

        results.append({
            "course_breakdown": course_breakdown,
            "daily_load": daily_load,
            "total_class_hours": round(total_class, 1),
            "total_study_hours": round(total_study, 1),
            "total_weekly_hours": total_weekly,
            "workload_score": workload_score,
            "warnings": warnings,
            "summary": summary,
        })

    logger.info("agent.workload.complete", extra={"schedules": len(schedules)})
    return results
