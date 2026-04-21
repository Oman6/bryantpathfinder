import type { ScheduleOption, Section } from "./types";

const DAY_TO_BYDAY: Record<string, string> = {
  M: "MO",
  T: "TU",
  W: "WE",
  R: "TH",
  F: "FR",
};

const DAY_TO_INDEX: Record<string, number> = { M: 1, T: 2, W: 3, R: 4, F: 5 };

function parseDate(ymd: string): Date {
  // Treat as local midnight — avoids TZ off-by-one
  const [y, m, d] = ymd.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function fmtDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}${m}${day}`;
}

function fmtTime(hhmm: string): string {
  return hhmm.replace(":", "") + "00";
}

function firstOccurrence(startDate: Date, byday: string[]): Date {
  // Find the first date on/after startDate whose weekday is in `byday`.
  const target = new Set(byday.map((d) => DAY_TO_INDEX[d]).filter(Boolean));
  const d = new Date(startDate);
  for (let i = 0; i < 7; i++) {
    if (target.has(d.getDay())) return d;
    d.setDate(d.getDate() + 1);
  }
  return startDate;
}

function escapeText(s: string): string {
  return s.replace(/\\/g, "\\\\").replace(/,/g, "\\,").replace(/;/g, "\\;").replace(/\n/g, "\\n");
}

function sectionEvents(section: Section, idx: number): string[] {
  if (section.is_async || section.meetings.length === 0) return [];
  const start = section.start_date ? parseDate(section.start_date) : parseDate("2026-08-31");
  const end = section.end_date ? parseDate(section.end_date) : parseDate("2026-12-18");
  const untilStr = fmtDate(end) + "T235959Z";

  return section.meetings.map((meeting, mi) => {
    const bydays = meeting.days.map((d) => DAY_TO_BYDAY[d]).filter(Boolean);
    const first = firstOccurrence(start, meeting.days);
    const dtstart = `${fmtDate(first)}T${fmtTime(meeting.start)}`;
    const dtend = `${fmtDate(first)}T${fmtTime(meeting.end)}`;
    const uid = `${section.crn}-${idx}-${mi}@bryantpathfinder`;
    const location = [meeting.building, meeting.room].filter(Boolean).join(" ") || "Bryant University";
    const summary = `${section.course_code} — ${section.title}`;
    const description = [
      `CRN ${section.crn}`,
      `Section ${section.section}`,
      section.instructor ? `Instructor: ${section.instructor}` : "",
      `${section.credits} credits`,
    ]
      .filter(Boolean)
      .join("\n");

    return [
      "BEGIN:VEVENT",
      `UID:${uid}`,
      `DTSTAMP:${fmtDate(new Date())}T000000Z`,
      `DTSTART;TZID=America/New_York:${dtstart}`,
      `DTEND;TZID=America/New_York:${dtend}`,
      `RRULE:FREQ=WEEKLY;BYDAY=${bydays.join(",")};UNTIL=${untilStr}`,
      `SUMMARY:${escapeText(summary)}`,
      `DESCRIPTION:${escapeText(description)}`,
      `LOCATION:${escapeText(location)}`,
      "END:VEVENT",
    ].join("\r\n");
  });
}

export function scheduleToIcs(schedule: ScheduleOption): string {
  const events = schedule.sections.flatMap((s, i) => sectionEvents(s, i));
  return [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//BryantPathfinder//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    ...events,
    "END:VCALENDAR",
  ].join("\r\n");
}

export function downloadIcs(schedule: ScheduleOption): void {
  const ics = scheduleToIcs(schedule);
  const blob = new Blob([ics], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `bryant-schedule-${schedule.rank}.ics`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
