"use client";

import { useEffect, useState } from "react";
import { CalendarBlank } from "@phosphor-icons/react";

interface Event {
  date: string;
  label: string;
  raw_when: string;
  semester: string | null;
}

interface CalendarPayload {
  source_url: string;
  fetched_at: string;
  events: Event[];
}

const DAY_MS = 24 * 60 * 60 * 1000;

// Higher-priority labels surface even if they're farther out.
const PRIORITY_LABELS = [
  /add period ends/i,
  /drop period ends/i,
  /last day for ['"]?w['"]?/i,
  /classes begin/i,
  /classes end/i,
  /examination period/i,
  /thanksgiving/i,
  /spring break/i,
  /commencement/i,
];

function isPriority(label: string): boolean {
  return PRIORITY_LABELS.some((p) => p.test(label));
}

function formatDate(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", weekday: "short" });
}

function daysFromNow(iso: string): number {
  const target = new Date(iso + "T00:00:00").getTime();
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((target - today.getTime()) / DAY_MS);
}

export function DeadlinesPanel() {
  const [data, setData] = useState<CalendarPayload | null>(null);

  useEffect(() => {
    fetch("/bryant_academic_calendar.json")
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => setData(null));
  }, []);

  if (!data) return null;

  const upcoming = data.events
    .map((e) => ({ ...e, daysOut: daysFromNow(e.date) }))
    .filter((e) => e.daysOut >= 0 && e.daysOut <= 120 && isPriority(e.label))
    .slice(0, 4);

  if (upcoming.length === 0) return null;

  return (
    <div className="rounded-2xl border border-black/5 bg-white px-6 py-4">
      <div className="flex items-baseline justify-between">
        <div className="flex items-center gap-2">
          <CalendarBlank size={13} weight="light" className="text-[#5F5D58]" />
          <span
            className="text-[10px] uppercase tracking-wide text-[#5F5D58]"
            style={{ fontFamily: "var(--font-geist-mono), monospace" }}
          >
            Bryant deadlines · next 120 days
          </span>
        </div>
      </div>
      <ul className="mt-3 divide-y divide-black/5">
        {upcoming.map((e) => (
          <li
            key={`${e.date}-${e.label}`}
            className="flex items-baseline justify-between gap-3 py-2 text-xs"
          >
            <span className="truncate text-[#1A1A1A]">{e.label}</span>
            <span
              className="shrink-0 text-[#5F5D58]"
              style={{ fontFamily: "var(--font-geist-mono), monospace" }}
            >
              {formatDate(e.date)}{" "}
              <span className="text-[#5F5D58]/60">· {e.daysOut}d</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
