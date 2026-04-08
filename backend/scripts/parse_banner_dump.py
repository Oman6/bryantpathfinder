"""Parse the raw Banner Fall 2026 catalog dump into structured sections.json.

Reads data/raw/banner_fall2026_raw.txt and produces data/sections.json
with 291 Section objects matching the schema in ARCHITECTURE.md.
"""

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_FILE = PROJECT_ROOT / "data" / "raw" / "banner_fall2026_raw.txt"
OUTPUT_FILE = PROJECT_ROOT / "data" / "sections.json"

DAY_MAP = {
    "Monday": "M",
    "Tuesday": "T",
    "Wednesday": "W",
    "Thursday": "R",
    "Friday": "F",
}


def parse_time_12_to_24(time_str: str) -> str:
    """Convert '12:45 PM' to '12:45', '02:00 PM' to '14:00', '08:00 AM' to '08:00'."""
    match = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)", time_str.strip())
    if not match:
        raise ValueError(f"Cannot parse time: {time_str}")
    hour, minute, period = int(match.group(1)), match.group(2), match.group(3)
    if period == "PM" and hour != 12:
        hour += 12
    elif period == "AM" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute}"


def parse_status(status_line: str) -> dict:
    """Parse 'FULL: 0 of 7 seats remain.' or '18 of 30 seats remain.'"""
    is_full = status_line.startswith("FULL:")
    match = re.search(r"(\d+)\s+of\s+(\d+)\s+seats?\s+remain", status_line)
    if not match:
        raise ValueError(f"Cannot parse status: {status_line}")
    seats_open = int(match.group(1))
    seats_total = int(match.group(2))
    return {
        "seats_open": seats_open,
        "seats_total": seats_total,
        "is_full": is_full,
    }


def parse_waitlist(waitlist_line: str) -> dict:
    """Parse 'Waitlist: 10 of 10 waitlist seats remain.'"""
    match = re.search(r"(\d+)\s+of\s+(\d+)\s+waitlist\s+seats?\s+remain", waitlist_line)
    if not match:
        raise ValueError(f"Cannot parse waitlist: {waitlist_line}")
    return {
        "waitlist_open": int(match.group(1)),
        "waitlist_total": int(match.group(2)),
    }


def parse_meeting_days(days_str: str) -> list[str]:
    """Convert 'Monday,Thursday' to ['M', 'R']."""
    days = []
    for day_name in days_str.split(","):
        day_name = day_name.strip()
        if day_name in DAY_MAP:
            days.append(DAY_MAP[day_name])
    return days


def parse_meeting_time(time_str: str) -> tuple[str, str]:
    """Convert '12:45 PM - 02:00 PM' to ('12:45', '14:00')."""
    parts = time_str.split("-")
    start = parse_time_12_to_24(parts[0].strip())
    end = parse_time_12_to_24(parts[1].strip())
    return start, end


def parse_date(date_str: str) -> str:
    """Convert 'MM/DD/YYYY' to 'YYYY-MM-DD'."""
    match = re.match(r"(\d{2})/(\d{2})/(\d{4})", date_str.strip())
    if not match:
        return date_str.strip()
    return f"{match.group(3)}-{match.group(1)}-{match.group(2)}"


def parse_section_block(lines: list[str]) -> dict | None:
    """Parse a single section block into a Section dict."""
    fields: dict[str, str] = {}
    for line in lines:
        if ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()

    # Skip header lines or empty blocks
    if "Subject" not in fields or "CRN" not in fields:
        return None

    subject = fields["Subject"]
    course_number = fields["Course Number"]
    course_code = f"{subject} {course_number}"
    title = fields["Title"]
    section_letter = fields["Section"]
    credits = float(fields.get("Hours", "3"))
    crn = fields["CRN"]
    instructor = fields.get("Instructor")
    if instructor == "TBA":
        instructor = None

    # Meeting info
    meeting_days_raw = fields.get("Meeting Days", "")
    meeting_time_raw = fields.get("Meeting Time", "")
    building = fields.get("Building")
    room = fields.get("Room")

    if building == "None":
        building = None
    if room == "None":
        room = None

    # Check for async: sentinel time "00:00 AM - 00:01 AM" or missing days
    is_async = False
    meetings = []

    if not meeting_days_raw or meeting_days_raw == "None" or "00:00 AM" in meeting_time_raw:
        is_async = True
    else:
        days = parse_meeting_days(meeting_days_raw)
        start, end = parse_meeting_time(meeting_time_raw)
        meetings.append({
            "days": days,
            "start": start,
            "end": end,
            "building": building,
            "room": room,
        })

    # Status
    status_info = parse_status(fields.get("Status", "0 of 0 seats remain."))

    # Waitlist (optional)
    waitlist_info = {"waitlist_open": 0, "waitlist_total": 0}
    if "Waitlist" in fields:
        waitlist_info = parse_waitlist(fields["Waitlist"])

    # Dates
    start_date = parse_date(fields.get("Start Date", ""))
    end_date = parse_date(fields.get("End Date", ""))

    schedule_type = fields.get("Schedule Type", "Lecture")

    return {
        "crn": crn,
        "subject": subject,
        "course_number": course_number,
        "course_code": course_code,
        "title": title,
        "section": section_letter,
        "credits": credits,
        "instructor": instructor,
        "meetings": meetings,
        "seats_open": status_info["seats_open"],
        "seats_total": status_info["seats_total"],
        "waitlist_open": waitlist_info["waitlist_open"],
        "waitlist_total": waitlist_info["waitlist_total"],
        "is_full": status_info["is_full"],
        "is_async": is_async,
        "schedule_type": schedule_type,
        "term": "Fall 2026",
        "start_date": start_date,
        "end_date": end_date,
    }


def parse_banner_dump(raw_path: Path) -> list[dict]:
    """Parse the full Banner dump file into a list of Section dicts."""
    text = raw_path.read_text(encoding="utf-8")

    # Split on the dashed separator lines
    blocks = re.split(r"-{40,}", text)

    sections = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        section = parse_section_block(lines)
        if section is not None:
            sections.append(section)

    return sections


def main() -> None:
    if not RAW_FILE.exists():
        print(f"Error: Raw file not found at {RAW_FILE}")
        sys.exit(1)

    sections = parse_banner_dump(RAW_FILE)
    print(f"Parsed {len(sections)} sections")

    # Write output
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(sections, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Written to {OUTPUT_FILE}")

    # Verify count
    if len(sections) != 291:
        print(f"WARNING: Expected 291 sections, got {len(sections)}")
        sys.exit(1)
    else:
        print("Section count verified: 291")

    # Print subject distribution
    subjects: dict[str, int] = {}
    for s in sections:
        subjects[s["subject"]] = subjects.get(s["subject"], 0) + 1
    for subj in sorted(subjects):
        print(f"  {subj}: {subjects[subj]}")


if __name__ == "__main__":
    main()
