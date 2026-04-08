"""Pydantic data models for BryantPathfinder.

These models are the source of truth for every data contract in the system.
They define the shapes passed between the Banner parser, the degree audit parser,
the requirement expander, the constraint solver, the Claude client, and the API layer.
"""

from typing import Literal

from pydantic import BaseModel, Field


class Meeting(BaseModel):
    """A single meeting block for a course section — day(s), time range, and location."""

    days: list[Literal["M", "T", "W", "R", "F"]]
    start: str = Field(description="Start time in HH:MM 24-hour format")
    end: str = Field(description="End time in HH:MM 24-hour format")
    building: str | None = None
    room: str | None = None


class Section(BaseModel):
    """A single offering of a course at a specific time, taught by a specific instructor.

    The atomic unit of scheduling. Loaded from data/sections.json at startup.
    """

    crn: str
    subject: str
    course_number: str
    course_code: str
    title: str
    section: str
    credits: float
    instructor: str | None = None
    meetings: list[Meeting]
    seats_open: int
    seats_total: int
    waitlist_open: int = 0
    waitlist_total: int = 0
    is_full: bool
    is_async: bool
    schedule_type: str
    term: str
    start_date: str | None = None
    end_date: str | None = None


class CompletedRequirement(BaseModel):
    """A degree requirement that the student has already satisfied with a specific course."""

    requirement: str
    course: str
    grade: str
    credits: float
    term: str


class OutstandingRequirement(BaseModel):
    """A degree requirement the student still needs to complete.

    The rule_type determines how the requirement expander finds candidate sections:
    - specific_course: exactly one course code in options
    - choose_one_of: pick any one course from the options list
    - wildcard: match sections against a pattern like 'FIN 4XX'
    - course_with_lab: must register for both a lecture and its paired lab
    """

    id: str
    requirement: str
    rule_type: Literal["specific_course", "choose_one_of", "wildcard", "course_with_lab"]
    options: list[str] = Field(default_factory=list)
    pattern: str | None = None
    pairs: list[list[str]] | None = None
    credits_needed: float
    category: Literal["general_education", "business_core", "major", "elective", "minor"]


class DegreeAudit(BaseModel):
    """The parsed output of a Degree Works screenshot.

    Contains student metadata, completed requirements, in-progress requirements,
    and the outstanding requirements that Pathfinder will try to schedule.
    """

    student_id: str
    name: str
    major: str
    expected_graduation: str
    credits_earned_or_inprogress: int
    credits_required: int
    completed_requirements: list[CompletedRequirement]
    in_progress_requirements: list[CompletedRequirement]
    outstanding_requirements: list[OutstandingRequirement]


class SchedulePreferences(BaseModel):
    """Student preferences captured on the preferences page.

    A mix of structured toggles and free-text that Claude can interpret.
    """

    target_credits: int = 15
    blocked_days: list[Literal["M", "T", "W", "R", "F"]] = Field(default_factory=list)
    no_earlier_than: str | None = None
    no_later_than: str | None = None
    preferred_instructors: list[str] = Field(default_factory=list)
    avoided_instructors: list[str] = Field(default_factory=list)
    free_text: str = ""
    selected_requirement_ids: list[str] = Field(default_factory=list)


class ScheduleOption(BaseModel):
    """One of the three schedules returned by the solver, enriched with a Claude explanation."""

    rank: int
    sections: list[Section]
    requirements_satisfied: list[str]
    total_credits: float
    days_off: list[str]
    earliest_class: str
    latest_class: str
    score: float
    explanation: str = ""


class GenerateSchedulesRequest(BaseModel):
    """Request body for POST /api/generate-schedules."""

    audit: DegreeAudit
    preferences: SchedulePreferences


class GenerateSchedulesResponse(BaseModel):
    """Response body for POST /api/generate-schedules."""

    schedules: list[ScheduleOption]
    solver_stats: dict


class ParseAuditRequest(BaseModel):
    """Request body for POST /api/parse-audit."""

    image_base64: str


class HealthResponse(BaseModel):
    """Response body for GET /api/health."""

    status: str
    sections_loaded: int
    term: str
    anthropic_api: str
