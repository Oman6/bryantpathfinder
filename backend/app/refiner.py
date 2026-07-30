"""Refiner pipeline — five critic agents that re-rank solver candidates.

The solver is excellent at constraint satisfaction (no time conflicts, credit
fit, hard preferences) but it's a single scoring function. The refiner runs
five independent critic agents over a wider candidate pool (~30 schedules)
and re-ranks them on quality dimensions the solver underweights:

    1. ProfessorCritic   — RMP quality + would-take-again, per-section
    2. SeatSafetyCritic  — heavy penalty for sections at <3 seats
    3. TimeOfDayCritic   — penalize evening + early-morning load
    4. WorkloadCritic    — penalize estimated hrs/week above a credit-scaled cap
    5. VarietyCritic     — reward category mix + instructor / subject spread

Each critic is a pure function that returns a per-schedule score plus a list
of reason strings. The refiner runs all five in a ThreadPoolExecutor (cheap
since they're CPU-only — but parallelism keeps the pattern uniform with the
post-solver agent pipeline). Outputs are summed with tunable weights and the
top N are returned.

This is a deterministic swarm — no LLM calls. The Claude rank/explain step
that already runs after enrichment isn't replaced; it gets a better top-3.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from .models import ScheduleOption, SchedulePreferences, Section
from .solver import (
    professor_quality_score,
    seat_safety_score,
    time_of_day_score,
    to_minutes,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
RATINGS_PATH = DATA_DIR / "professor_ratings.json"

# Tunable weights — each critic produces a score in roughly [-10, +10] range
# before weighting. Weights tuned so that a typical "great" schedule scores
# 30+ above a "passable" one, and "very heavy workload" can outrank a small
# professor-quality win.
W_PROFESSOR = 1.5
W_SEAT = 1.5
W_TIME_OF_DAY = 1.0
W_WORKLOAD = 2.5
W_VARIETY = 1.0


@dataclass
class CriticReport:
    name: str
    score: float
    reasons: list[str]


def _load_ratings() -> dict:
    try:
        return json.loads(RATINGS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


# ---------- Critic 1: Professor quality ----------
def professor_critic(schedule: ScheduleOption, _prefs: SchedulePreferences) -> CriticReport:
    """Average professor quality across the schedule, normalized to ~[-10, +10]."""
    if not schedule.sections:
        return CriticReport("professor", 0.0, [])
    scores = [professor_quality_score(s) for s in schedule.sections]
    avg = sum(scores) / len(scores)
    score = avg * 3.0  # map ~[-3, +3] per-section avg → ~[-9, +9]
    reasons: list[str] = []
    ratings = _load_ratings()
    for s in schedule.sections:
        if not s.instructor:
            continue
        r = ratings.get(s.instructor)
        if not r or r.get("num_ratings", 0) < 5:
            continue
        q = r.get("quality", 0)
        if q >= 4.5:
            reasons.append(f"{s.course_code}: {s.instructor.split(',')[0]} highly rated ({q}/5)")
        elif q < 2.5:
            reasons.append(f"{s.course_code}: {s.instructor.split(',')[0]} poorly rated ({q}/5)")
    return CriticReport("professor", round(score, 2), reasons)


# ---------- Critic 2: Seat safety ----------
def seat_critic(schedule: ScheduleOption, _prefs: SchedulePreferences) -> CriticReport:
    """Sum per-section seat safety scores."""
    score = sum(seat_safety_score(s) for s in schedule.sections)
    reasons: list[str] = []
    for s in schedule.sections:
        if s.seats_open <= 0:
            reasons.append(f"{s.course_code}: waitlist only")
        elif s.seats_open < 3:
            reasons.append(f"{s.course_code}: only {s.seats_open} seat(s) left")
    return CriticReport("seat_safety", round(score, 2), reasons)


# ---------- Critic 3: Time of day ----------
def time_critic(schedule: ScheduleOption, prefs: SchedulePreferences) -> CriticReport:
    """Penalize evening sections and 8 AM starts unless the student opted in."""
    score = sum(time_of_day_score(s, prefs) for s in schedule.sections)
    # Additional penalty: 8 AM starts when no_earlier_than wasn't set
    if not prefs.no_earlier_than:
        early_starts = 0
        for s in schedule.sections:
            for m in s.meetings:
                if to_minutes(m.start) < 9 * 60:
                    early_starts += 1
                    break
        score -= 0.5 * early_starts
    reasons: list[str] = []
    for s in schedule.sections:
        for m in s.meetings:
            if to_minutes(m.start) >= 18 * 60:
                reasons.append(f"{s.course_code}: evening meeting ({m.start})")
                break
    return CriticReport("time_of_day", round(score, 2), reasons)


# ---------- Critic 4: Workload ----------
# Difficulty multipliers borrowed from workload_agent (kept in sync intentionally).
_BASE_HOURS_PER_CREDIT = 2.0
_DIFFICULTY_SCALE = {1: 0.5, 2: 0.75, 3: 1.0, 4: 1.4, 5: 1.8}


def _difficulty_mult(difficulty: float) -> float:
    lo = max(1, int(difficulty))
    hi = min(5, lo + 1)
    frac = max(0.0, difficulty - lo)
    return _DIFFICULTY_SCALE[lo] * (1 - frac) + _DIFFICULTY_SCALE[hi] * frac


def _estimate_workload_hours(schedule: ScheduleOption, ratings: dict) -> float:
    total = 0.0
    for s in schedule.sections:
        difficulty = 3.0
        if s.instructor and s.instructor in ratings:
            difficulty = ratings[s.instructor].get("difficulty", 3.0) or 3.0
        class_hours = 0.0
        for m in s.meetings:
            duration = (to_minutes(m.end) - to_minutes(m.start)) / 60.0
            class_hours += duration * len(m.days)
        study_hours = s.credits * _BASE_HOURS_PER_CREDIT * _difficulty_mult(difficulty)
        total += class_hours + study_hours
    return total


def workload_critic(schedule: ScheduleOption, prefs: SchedulePreferences) -> CriticReport:
    """Penalty when workload exceeds a credit-scaled threshold.

    Threshold: 3.0 hrs/credit is "normal," 3.5 is "heavy," 4.0+ is "crushing."
    Scaling by credits prevents the agent from screaming about a 12-credit
    schedule that's 40 hrs/week (which is fine) when the student picked 12.
    """
    ratings = _load_ratings()
    estimated = _estimate_workload_hours(schedule, ratings)
    target_credits = max(1, prefs.target_credits or sum(int(s.credits) for s in schedule.sections))
    hrs_per_credit = estimated / target_credits
    reasons: list[str] = []
    if hrs_per_credit >= 4.0:
        score = -8.0
        reasons.append(f"~{estimated:.0f} hrs/week is crushing for {target_credits} credits")
    elif hrs_per_credit >= 3.5:
        score = -3.0
        reasons.append(f"~{estimated:.0f} hrs/week is heavy for {target_credits} credits")
    elif hrs_per_credit >= 3.0:
        score = 0.0
    else:
        score = 1.0
    return CriticReport("workload", round(score, 2), reasons)


# ---------- Critic 5: Variety ----------
def variety_critic(schedule: ScheduleOption, _prefs: SchedulePreferences) -> CriticReport:
    """Reward subject + instructor variety; penalize loading >50% in one subject."""
    sections = schedule.sections
    if not sections:
        return CriticReport("variety", 0.0, [])
    subj_counts: dict[str, int] = {}
    instr_counts: dict[str, int] = {}
    for s in sections:
        subj_counts[s.subject] = subj_counts.get(s.subject, 0) + 1
        if s.instructor:
            instr_counts[s.instructor] = instr_counts.get(s.instructor, 0) + 1

    score = 0.0
    reasons: list[str] = []

    # Subject concentration penalty
    n = len(sections)
    for subj, c in subj_counts.items():
        if c / n > 0.6:
            score -= 2.0 * (c - max(2, n // 2))
            reasons.append(f"{c}/{n} sections are {subj}")
    # Instructor stacking penalty
    for instr, c in instr_counts.items():
        if c >= 3:
            score -= 2.0 * (c - 2)
            reasons.append(f"{instr.split(',')[0]} teaches {c} sections")
    # Reward distinct subjects
    score += min(3.0, len(subj_counts)) * 0.5
    return CriticReport("variety", round(score, 2), reasons)


CRITICS: list = [
    (professor_critic, W_PROFESSOR),
    (seat_critic, W_SEAT),
    (time_critic, W_TIME_OF_DAY),
    (workload_critic, W_WORKLOAD),
    (variety_critic, W_VARIETY),
]


def refine(
    candidates: list[ScheduleOption],
    preferences: SchedulePreferences,
    *,
    top_n: int = 3,
) -> list[ScheduleOption]:
    """Re-rank candidates by combined critic score; return top N.

    Each candidate's `.score` is replaced with the refined score so the rest
    of the pipeline (Claude rank, frontend display) sees the new ordering.
    The original solver score is preserved as `.score` *before* refinement —
    intentionally overwritten because every consumer treats higher == better
    and the new score is the authoritative ranking.
    """
    if not candidates:
        return []

    def score_one(schedule: ScheduleOption) -> tuple[float, list[CriticReport]]:
        reports: list[CriticReport] = []
        with ThreadPoolExecutor(max_workers=len(CRITICS)) as ex:
            futures = [ex.submit(c, schedule, preferences) for c, _ in CRITICS]
            reports = [f.result() for f in futures]
        weighted = sum(r.score * w for r, (_, w) in zip(reports, CRITICS))
        # Add the solver's own score at a small weight so unambiguously good
        # schedules don't get unseated by a single critic.
        return (schedule.score * 0.4) + weighted, reports

    scored: list[tuple[float, ScheduleOption, list[CriticReport]]] = []
    for c in candidates:
        total, reports = score_one(c)
        scored.append((total, c, reports))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Prefer distinct course sets so the options shown to the student differ in
    # which courses they take, not merely in which section/CRN was picked.
    # Section-variants of an already-selected course set are deferred and only
    # used to backfill if there aren't enough distinct course sets to reach top_n.
    out: list[ScheduleOption] = []
    seen_course_sets: set[frozenset[str]] = set()
    deferred: list[tuple[float, ScheduleOption]] = []
    for total, schedule, _reports in scored:
        course_set = frozenset(s.course_code for s in schedule.sections)
        if course_set in seen_course_sets:
            deferred.append((total, schedule))
            continue
        seen_course_sets.add(course_set)
        schedule.score = round(total, 1)
        out.append(schedule)
        if len(out) >= top_n:
            break

    if len(out) < top_n:
        for total, schedule in deferred:
            schedule.score = round(total, 1)
            out.append(schedule)
            if len(out) >= top_n:
                break

    for rank, schedule in enumerate(out, start=1):
        schedule.rank = rank

    if scored:
        top_total = scored[0][0]
        logger.info(
            "refiner.complete candidates=%d top_score=%.1f kept=%d",
            len(candidates), top_total, len(out),
        )

    return out
