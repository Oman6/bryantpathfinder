"""FastAPI routes and application lifespan for BryantPathfinder.

Endpoints:
- GET  /api/health             — server status
- POST /api/parse-audit        — Claude Vision audit parsing
- POST /api/generate-schedules — solver + multi-agent enrichment pipeline
- GET  /api/sample-audit       — demo fixture fallback
- POST /api/multi-semester     — 4-semester graduation roadmap (3-agent pipeline)
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
from .agents import orchestrator

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

    sections_by_code: dict[str, list[Section]] = {}
    for section in sections_list:
        sections_by_code.setdefault(section.course_code, []).append(section)

    app.state.sections = sections_list
    app.state.sections_by_code = sections_by_code

    logger.info("Loaded %d sections from %s", len(sections_list), SECTIONS_PATH)
    yield


app = FastAPI(
    title="BryantPathfinder",
    description="AI course scheduling assistant with multi-agent orchestration",
    version="2.0.0",
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
    sections: list[Section] = app.state.sections
    return HealthResponse(
        status="ok",
        sections_loaded=len(sections),
        term="Fall 2026",
        anthropic_api="reachable",
    )


@app.post("/api/parse-audit", response_model=DegreeAudit)
async def parse_audit(request: ParseAuditRequest) -> DegreeAudit:
    if not request.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required.")

    media_type = "image/png"
    b64 = request.image_base64
    if b64.startswith("data:"):
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


@app.post("/api/generate-schedules")
async def generate_schedules(request: GenerateSchedulesRequest) -> dict:
    """Run solver + multi-agent enrichment pipeline.

    Pipeline:
    1. Constraint solver generates top 3 schedules
    2. If zero results → Negotiator Agent analyzes bottlenecks
    3. If results → Professor Match + Workload agents run in parallel
    4. Claude explains each schedule (if API key available)
    5. All agent outputs merged into final response
    """
    sections: list[Section] = app.state.sections
    audit = request.audit
    preferences = request.preferences

    start_time = time.time()

    # Step 1: Run the solver
    schedules = solve(
        outstanding_requirements=audit.outstanding_requirements,
        all_sections=sections,
        preferences=preferences,
    )

    solver_duration_ms = int((time.time() - start_time) * 1000)

    # Step 2: Zero-result path → Negotiator Agent
    if not schedules:
        negotiation = orchestrator.negotiate_constraints(
            audit.outstanding_requirements, sections, preferences
        )
        return {
            "schedules": [],
            "solver_stats": {
                "solver_duration_ms": solver_duration_ms,
                "total_duration_ms": int((time.time() - start_time) * 1000),
                "schedules_returned": 0,
            },
            "negotiation": negotiation,
            "agents_run": negotiation.get("agents_run", ["negotiator"]),
        }

    # Step 3: Enrichment — Professor Match + Workload in parallel
    enrichment = orchestrator.enrich_schedules(schedules, preferences)

    # Step 4: Claude explanations (sequential, needs API)
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

    return {
        "schedules": [s.model_dump() for s in schedules],
        "solver_stats": {
            "solver_duration_ms": solver_duration_ms,
            "total_duration_ms": total_duration_ms,
            "schedules_returned": len(schedules),
            "orchestration_ms": enrichment.get("orchestration_ms", 0),
        },
        "professor_data": enrichment.get("professor_data", []),
        "workload_data": enrichment.get("workload_data", []),
        "agents_run": ["solver"] + enrichment.get("agents_run", []) + ["explainer"],
    }


@app.get("/api/sample-audit", response_model=DegreeAudit)
async def sample_audit() -> DegreeAudit:
    if not FIXTURE_PATH.exists():
        raise HTTPException(status_code=500, detail="Sample audit fixture not found")
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return DegreeAudit(**raw)


@app.post("/api/multi-semester")
async def multi_semester(request: GenerateSchedulesRequest) -> dict:
    """Run the Multi-Semester Planner — 3-agent sub-pipeline.

    Agents: Prerequisite → Rotation → Sequencing
    Produces a 4-semester graduation roadmap.
    """
    sections: list[Section] = app.state.sections
    result = orchestrator.plan_multi_semester(request.audit, sections)
    return result
