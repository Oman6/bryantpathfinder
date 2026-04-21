"""Professor Match Agent — analyzes RMP data against student preferences.

Runs in parallel with other agents after the solver returns candidates.
Produces per-section professor insights and match scores that feed back
into the schedule ranking.
"""

import json
import logging
from pathlib import Path

from ..models import ScheduleOption, SchedulePreferences, Section

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
RATINGS_PATH = DATA_DIR / "professor_ratings.json"


def _load_ratings() -> dict:
    """Load professor ratings from the static JSON file."""
    if not RATINGS_PATH.exists():
        return {}
    return json.loads(RATINGS_PATH.read_text(encoding="utf-8"))


def _analyze_professor(
    instructor: str | None,
    ratings: dict,
    preferences: SchedulePreferences,
) -> dict:
    """Produce an insight dict for a single professor."""
    if not instructor or instructor not in ratings:
        return {
            "instructor": instructor or "TBA",
            "has_data": False,
            "insight": "No rating data available.",
            "match_score": 0,
            "flags": [],
        }

    r = ratings[instructor]
    quality = r["quality"]
    difficulty = r["difficulty"]
    num_ratings = r["num_ratings"]
    wta = r["would_take_again"]

    # Treat the (0.0, 0.0, 0 ratings) sentinel as "no data" so these profs
    # aren't penalized as if they were actually rated 0/5.
    if num_ratings == 0 and quality == 0.0:
        return {
            "instructor": instructor,
            "has_data": False,
            "insight": "No rating data available.",
            "match_score": 0,
            "flags": [],
        }

    flags: list[str] = []
    match_score = 0

    # Quality assessment
    if quality >= 4.0:
        match_score += 3
        flags.append("highly_rated")
    elif quality < 2.5:
        match_score -= 3
        flags.append("low_rated")

    # Difficulty assessment
    if difficulty >= 4.0:
        flags.append("very_challenging")
        match_score -= 1
    elif difficulty <= 2.5:
        flags.append("manageable_workload")
        match_score += 1

    # Would take again
    if wta >= 0:
        if wta >= 80:
            match_score += 2
            flags.append("students_love")
        elif wta < 40:
            match_score -= 2
            flags.append("low_approval")

    # Check against preferences
    last_name = instructor.split(",")[0].strip().lower()
    for pref in preferences.preferred_instructors:
        if pref.lower() in last_name:
            match_score += 5
            flags.append("preferred")
    for avoid in preferences.avoided_instructors:
        if avoid.lower() in last_name:
            match_score -= 5
            flags.append("avoided")

    # Confidence based on number of ratings
    if num_ratings < 5:
        flags.append("few_ratings")

    # Generate natural language insight
    last = instructor.split(",")[0]
    parts = []
    if quality >= 4.0:
        parts.append(f"{last} is rated {quality}/5")
    elif quality < 3.0:
        parts.append(f"{last} has a {quality}/5 rating")
    else:
        parts.append(f"{last} is rated {quality}/5")

    if difficulty >= 4.0:
        parts.append(f"known for challenging coursework ({difficulty}/5 difficulty)")
    elif difficulty <= 2.0:
        parts.append(f"with a light workload ({difficulty}/5 difficulty)")

    if wta >= 80:
        parts.append(f"{wta}% of students would take again")
    elif 0 <= wta < 40:
        parts.append(f"only {wta}% would retake")

    insight = ", ".join(parts) + "."

    return {
        "instructor": instructor,
        "has_data": True,
        "quality": quality,
        "difficulty": difficulty,
        "num_ratings": num_ratings,
        "would_take_again": wta,
        "match_score": match_score,
        "insight": insight,
        "flags": flags,
    }


def run(
    schedules: list[ScheduleOption],
    preferences: SchedulePreferences,
) -> list[dict]:
    """Run the Professor Match Agent on a list of schedule options.

    Args:
        schedules: The solver's candidate schedules.
        preferences: Student preferences for matching context.

    Returns:
        A list of dicts, one per schedule, each containing:
        - professor_insights: list of per-section professor analyses
        - avg_professor_score: average match score across all sections
        - warnings: list of flagged concerns
        - recommendations: list of positive highlights
    """
    ratings = _load_ratings()
    results = []

    for schedule in schedules:
        insights = []
        warnings = []
        recommendations = []

        for section in schedule.sections:
            analysis = _analyze_professor(section.instructor, ratings, preferences)
            insights.append(analysis)

            if "low_rated" in analysis.get("flags", []) or "low_approval" in analysis.get("flags", []):
                warnings.append(
                    f"{section.course_code}: {analysis['instructor']} has low ratings — consider another section"
                )
            if "avoided" in analysis.get("flags", []):
                warnings.append(
                    f"{section.course_code}: {analysis['instructor']} is on your avoid list"
                )
            if "highly_rated" in analysis.get("flags", []) or "students_love" in analysis.get("flags", []):
                recommendations.append(
                    f"{section.course_code}: {analysis['instructor']} is highly rated by students"
                )
            if "preferred" in analysis.get("flags", []):
                recommendations.append(
                    f"{section.course_code}: {analysis['instructor']} is one of your preferred instructors"
                )

        scores = [i["match_score"] for i in insights]
        avg_score = sum(scores) / len(scores) if scores else 0

        results.append({
            "professor_insights": insights,
            "avg_professor_score": round(avg_score, 1),
            "warnings": warnings,
            "recommendations": recommendations,
        })

    logger.info("agent.professor_match.complete", extra={"schedules": len(schedules)})
    return results
