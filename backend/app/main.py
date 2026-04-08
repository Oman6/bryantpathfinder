"""FastAPI routes and application lifespan for BryantPathfinder.

Three API endpoints:
- GET  /api/health             — confirm the server is running and sections are loaded
- POST /api/parse-audit        — parse a Degree Works screenshot via Claude Vision
- POST /api/generate-schedules — run the solver and return 3 ranked schedules
- GET  /api/sample-audit       — return the pre-parsed fixture for the demo fallback
"""

import json
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .claude_client import explain_schedule, parse_audit_vision
from .models import (
    DegreeAudit,
    GenerateSchedulesRequest,
    GenerateSchedulesResponse,
    HealthResponse,
    ParseAuditRequest,
    ScheduleOption,
    Section,
)
from .solver import solve

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
SECTIONS_PATH = DATA_DIR / "sections.json"
FIXTURE_PATH = DATA_DIR / "fixtures" / "audit_owen.json"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Load sections.json once at startup, store in app.state."""
    if not SECTIONS_PATH.exists():
        raise RuntimeError(f"sections.json not found at {SECTIONS_PATH}")

    raw = json.loads(SECTIONS_PATH.read_text(encoding="utf-8"))
    sections_list = [Section(**s) for s in raw]

    # Dict keyed by course_code for O(1) lookup in the expander
    sections_by_code: dict[str, list[Section]] = {}
    for section in sections_list:
        sections_by_code.setdefault(section.course_code, []).append(section)

    app.state.sections = sections_list
    app.state.sections_by_code = sections_by_code

    logger.info("Loaded %d sections from %s", len(sections_list), SECTIONS_PATH)

    yield


app = FastAPI(
    title="BryantPathfinder",
    description="AI course scheduling assistant for Bryant University",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Confirm sections.json is loaded and the server is ready."""
    sections: list[Section] = app.state.sections
    return HealthResponse(
        status="ok",
        sections_loaded=len(sections),
        term="Fall 2026",
        anthropic_api="reachable",
    )


@app.post("/api/parse-audit", response_model=DegreeAudit)
async def parse_audit(request: ParseAuditRequest) -> DegreeAudit:
    """Parse a Degree Works audit screenshot using Claude Vision."""
    if not request.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required.")

    # Detect media type from base64 header or default to PNG
    media_type = "image/png"
    b64 = request.image_base64
    if b64.startswith("data:"):
        # Strip data URI prefix: "data:image/png;base64,..."
        header, _, b64 = b64.partition(",")
        if "image/jpeg" in header or "image/jpg" in header:
            media_type = "image/jpeg"
        elif "application/pdf" in header:
            media_type = "application/pdf"

    try:
        audit = parse_audit_vision(b64, media_type=media_type)
        return audit
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-schedules", response_model=GenerateSchedulesResponse)
async def generate_schedules(request: GenerateSchedulesRequest) -> GenerateSchedulesResponse:
    """Run the constraint solver and return 3 ranked schedules with explanations."""
    sections: list[Section] = app.state.sections
    audit = request.audit
    preferences = request.preferences

    start_time = time.time()

    # Run the solver
    schedules = solve(
        outstanding_requirements=audit.outstanding_requirements,
        all_sections=sections,
        preferences=preferences,
    )

    solver_duration_ms = int((time.time() - start_time) * 1000)

    if not schedules:
        # Build a helpful message about which constraints to loosen
        suggestions = []
        if preferences.blocked_days:
            suggestions.append(
                f"Remove blocked days ({', '.join(preferences.blocked_days)})"
            )
        if preferences.no_earlier_than:
            suggestions.append(
                f"Allow classes before {preferences.no_earlier_than}"
            )
        if preferences.no_later_than:
            suggestions.append(
                f"Allow classes after {preferences.no_later_than}"
            )
        if not suggestions:
            suggestions.append("Select fewer requirements or adjust your target credits")

        detail = (
            "No valid schedules found with your current preferences. "
            "Try loosening these constraints: " + "; ".join(suggestions)
        )
        raise HTTPException(status_code=422, detail=detail)

    # Enrich each schedule with a Claude-generated explanation
    for schedule in schedules:
        try:
            explanation = explain_schedule(
                schedule=schedule,
                preferences=preferences,
                requirements_satisfied=schedule.requirements_satisfied,
            )
            schedule.explanation = explanation
        except Exception as e:
            logger.warning("Failed to generate explanation for rank %d: %s", schedule.rank, e)
            schedule.explanation = "Schedule explanation unavailable."

    total_duration_ms = int((time.time() - start_time) * 1000)

    return GenerateSchedulesResponse(
        schedules=schedules,
        solver_stats={
            "solver_duration_ms": solver_duration_ms,
            "total_duration_ms": total_duration_ms,
            "schedules_returned": len(schedules),
        },
    )


@app.get("/api/sample-audit", response_model=DegreeAudit)
async def sample_audit() -> DegreeAudit:
    """Return Owen's pre-parsed degree audit as a demo fallback."""
    if not FIXTURE_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Sample audit fixture not found at {FIXTURE_PATH}",
        )

    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return DegreeAudit(**raw)
