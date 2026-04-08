"""Anthropic API wrapper for BryantPathfinder.

A thin layer over the official anthropic Python SDK that exposes three
functions matching the three Claude use cases in the pipeline:
1. parse_audit_vision — Degree Works screenshot to structured DegreeAudit
2. explain_schedule — generate a two-sentence explanation for a schedule
3. rank_schedules — rank three candidate schedules with rationale
"""

import json
import logging
import os

import anthropic
from dotenv import load_dotenv

from .models import DegreeAudit, ScheduleOption, SchedulePreferences
from .prompts import EXPLAIN_SCHEDULE_PROMPT, RANK_SCHEDULES_PROMPT, VISION_AUDIT_PROMPT

load_dotenv()

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-5-20250514"


def _get_client() -> anthropic.Anthropic:
    """Create an Anthropic client using the API key from environment."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key."
        )
    return anthropic.Anthropic(api_key=api_key)


def _parse_json_response(text: str) -> dict:
    """Extract and parse JSON from a Claude response, handling markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Strip markdown code fences
        lines = cleaned.splitlines()
        # Remove first line (```json or ```) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    return json.loads(cleaned)


def parse_audit_vision(image_base64: str, media_type: str = "image/png") -> DegreeAudit:
    """Parse a Degree Works audit screenshot using Claude Vision.

    Args:
        image_base64: Base64-encoded image data.
        media_type: MIME type of the image (image/png, image/jpeg, application/pdf).

    Returns:
        A validated DegreeAudit object.

    Raises:
        anthropic.APIError: On authentication or rate limit errors.
        ValueError: If Claude returns malformed JSON after one retry.
    """
    client = _get_client()
    last_error = None

    for attempt in range(2):
        try:
            logger.info("claude.vision_parse", extra={"attempt": attempt + 1})

            message = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                temperature=0,
                system=VISION_AUDIT_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": "Parse this Degree Works audit and return the structured JSON.",
                            },
                        ],
                    }
                ],
            )

            response_text = message.content[0].text
            parsed = _parse_json_response(response_text)
            audit = DegreeAudit(**parsed)
            logger.info("claude.vision_parse_success", extra={"requirements": len(audit.outstanding_requirements)})
            return audit

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            last_error = e
            logger.warning("claude.vision_parse_malformed_json", extra={"attempt": attempt + 1, "error": str(e)})
            if attempt == 0:
                continue
        except anthropic.AuthenticationError:
            logger.error("claude.auth_error")
            raise
        except anthropic.RateLimitError:
            logger.error("claude.rate_limit")
            raise

    raise ValueError(f"Claude returned malformed JSON after 2 attempts: {last_error}")


def explain_schedule(
    schedule: ScheduleOption,
    preferences: SchedulePreferences,
    requirements_satisfied: list[str],
) -> str:
    """Generate a two-sentence explanation for a schedule.

    Args:
        schedule: The schedule to explain.
        preferences: Student preferences for context.
        requirements_satisfied: List of requirement IDs this schedule covers.

    Returns:
        A two-sentence explanation string.
    """
    client = _get_client()

    schedule_data = []
    for s in schedule.sections:
        schedule_data.append({
            "course_code": s.course_code,
            "title": s.title,
            "section": s.section,
            "instructor": s.instructor,
            "meetings": [{"days": m.days, "start": m.start, "end": m.end} for m in s.meetings],
            "credits": s.credits,
            "seats_open": s.seats_open,
            "seats_total": s.seats_total,
        })

    prompt = EXPLAIN_SCHEDULE_PROMPT.format(
        schedule_json=json.dumps(schedule_data, indent=2),
        preferences_json=json.dumps(preferences.model_dump(), indent=2),
        requirements_json=json.dumps(requirements_satisfied, indent=2),
    )

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=300,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except anthropic.APIError as e:
        logger.error("claude.explain_error", extra={"error": str(e)})
        return "Schedule explanation unavailable."


def rank_schedules(
    schedules: list[ScheduleOption],
    preferences: SchedulePreferences,
) -> list[dict]:
    """Rank three candidate schedules with rationale.

    Args:
        schedules: Exactly three ScheduleOption objects to rank.
        preferences: Student preferences for ranking context.

    Returns:
        A list of dicts with 'schedule', 'rank', and 'rationale' keys.

    Raises:
        ValueError: If Claude returns malformed ranking JSON after one retry.
    """
    client = _get_client()

    def schedule_to_summary(schedule: ScheduleOption) -> str:
        sections_info = []
        for s in schedule.sections:
            meetings_str = ", ".join(
                f"{''.join(m.days)} {m.start}-{m.end}" for m in s.meetings
            )
            sections_info.append(
                f"{s.course_code} ({s.title}) sec {s.section} - {s.instructor or 'TBA'} - {meetings_str} - {s.seats_open}/{s.seats_total} seats"
            )
        return "\n".join([
            f"Total credits: {schedule.total_credits}",
            f"Days off: {', '.join(schedule.days_off) or 'None'}",
            f"Time range: {schedule.earliest_class} - {schedule.latest_class}",
            f"Score: {schedule.score}",
            "Sections:",
            *[f"  - {info}" for info in sections_info],
        ])

    labels = ["A", "B", "C"]
    schedule_summaries = {
        f"schedule_{labels[i].lower()}_json": schedule_to_summary(s)
        for i, s in enumerate(schedules[:3])
    }

    prompt = RANK_SCHEDULES_PROMPT.format(
        preferences_json=json.dumps(preferences.model_dump(), indent=2),
        **schedule_summaries,
    )

    last_error = None
    for attempt in range(2):
        try:
            message = client.messages.create(
                model=MODEL,
                max_tokens=500,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = _parse_json_response(message.content[0].text)
            return parsed["rankings"]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            last_error = e
            logger.warning("claude.rank_malformed_json", extra={"attempt": attempt + 1, "error": str(e)})
            if attempt == 0:
                continue
        except anthropic.AuthenticationError:
            logger.error("claude.auth_error")
            raise

    raise ValueError(f"Claude returned malformed ranking JSON after 2 attempts: {last_error}")
