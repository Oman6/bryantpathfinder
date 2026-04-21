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
import os
import time
from collections import deque
from collections.abc import AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pydantic import BaseModel as PydanticBaseModel
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

# Input size limits
MAX_IMAGE_B64_LEN = 10_000_000  # ~7.5MB decoded, generous for Degree Works PDFs
MAX_AUDIT_TEXT_LEN = 20_000

# Simple in-memory per-IP rate limiter (30 req / 60s per IP)
RATE_LIMIT_WINDOW_S = 60
RATE_LIMIT_MAX = 30
_rate_buckets: dict[str, deque] = {}
_rate_lock = Lock()


def _rate_limit_check(ip: str) -> bool:
    now = time.time()
    with _rate_lock:
        bucket = _rate_buckets.setdefault(ip, deque())
        while bucket and bucket[0] < now - RATE_LIMIT_WINDOW_S:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT_MAX:
            return False
        bucket.append(now)
        return True


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

_allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "")
_allowed_origins = [o.strip() for o in _allowed_origins_env.split(",") if o.strip()] or [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    max_age=600,
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Per-IP rate limit for Claude-calling endpoints."""
    expensive = request.url.path in {
        "/api/parse-audit",
        "/api/parse-audit-text",
        "/api/generate-schedules",
    }
    if expensive:
        client_ip = request.client.host if request.client else "unknown"
        if not _rate_limit_check(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again in a minute."},
            )
    return await call_next(request)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — avoids leaking stack traces."""
    logger.exception("unhandled_exception", extra={"path": request.url.path})
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check backend logs."},
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


class ParseAuditTextRequest(PydanticBaseModel):
    text: str


@app.post("/api/parse-audit-text", response_model=DegreeAudit)
async def parse_audit_text(request: ParseAuditTextRequest) -> DegreeAudit:
    """Parse a pasted text description of degree requirements using Claude."""
    from .claude_client import parse_audit_text as _parse_text
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text is required.")
    if len(request.text) > MAX_AUDIT_TEXT_LEN:
        raise HTTPException(status_code=413, detail=f"Text exceeds {MAX_AUDIT_TEXT_LEN} character limit.")
    try:
        audit = _parse_text(request.text)
        return audit
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/parse-audit", response_model=DegreeAudit)
async def parse_audit(request: ParseAuditRequest) -> DegreeAudit:
    if not request.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required.")
    if len(request.image_base64) > MAX_IMAGE_B64_LEN:
        raise HTTPException(status_code=413, detail="Image exceeds 10MB limit.")

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

    # Step 4: Claude explanations — run 3 calls in parallel (~3s vs ~9s sequential)
    def _explain_one(s: ScheduleOption) -> tuple[int, str]:
        try:
            return s.rank, explain_schedule(
                schedule=s,
                preferences=preferences,
                requirements_satisfied=s.requirements_satisfied,
            )
        except Exception as e:
            logger.warning("Failed to generate explanation for rank %d: %s", s.rank, e)
            return s.rank, "Schedule explanation unavailable."

    with ThreadPoolExecutor(max_workers=3) as executor:
        for rank, explanation in executor.map(_explain_one, schedules):
            for s in schedules:
                if s.rank == rank:
                    s.explanation = explanation
                    break

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


@app.get("/api/sections")
async def get_sections(course_code: str) -> list[dict]:
    """Return all sections for a given course code (e.g., ?course_code=FIN 310)."""
    sections: list[Section] = app.state.sections
    matches = [s.model_dump() for s in sections if s.course_code == course_code]
    return matches


@app.post("/api/multi-semester")
async def multi_semester(request: GenerateSchedulesRequest) -> dict:
    """Run the Multi-Semester Planner — 3-agent sub-pipeline.

    Agents: Prerequisite → Rotation → Sequencing
    Produces a 4-semester graduation roadmap.
    """
    sections: list[Section] = app.state.sections
    result = orchestrator.plan_multi_semester(request.audit, sections)
    return result
