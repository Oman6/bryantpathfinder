"use client";

import { useEffect, useState } from "react";
import { Sparkle } from "@phosphor-icons/react";

interface Event {
  id: number;
  title: string;
  url: string;
  location: string | null;
  start: string | null;
  end: string | null;
  all_day: boolean;
  ranking: number;
  tags: string[];
}

interface Payload {
  source: string;
  fetched_at: string;
  events: Event[];
}

function formatWhen(iso: string | null): string {
  if (!iso) return "TBA";
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    weekday: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

const WINDOW_HOURS = 72;

export function EventsPanel() {
  const [data, setData] = useState<Payload | null>(null);

  useEffect(() => {
    fetch("/bryant_events.json")
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => setData(null));
  }, []);

  if (!data) return null;

  const now = Date.now();
  const cutoff = now + WINDOW_HOURS * 60 * 60 * 1000;
  const upcoming = data.events
    .filter((e) => {
      if (!e.start) return false;
      const t = new Date(e.start).getTime();
      return t > now && t < cutoff;
    })
    .sort((a, b) => (b.ranking ?? 0) - (a.ranking ?? 0))
    .slice(0, 5);

  if (upcoming.length === 0) return null;

  return (
    <div className="rounded-2xl border border-black/5 bg-white px-6 py-4">
      <div className="flex items-baseline justify-between">
        <div className="flex items-center gap-2">
          <Sparkle size={13} weight="light" className="text-[#5F5D58]" />
          <span
            className="text-[10px] uppercase tracking-wide text-[#5F5D58]"
            style={{ fontFamily: "var(--font-geist-mono), monospace" }}
          >
            On campus · next 72 hours
          </span>
        </div>
        <span className="text-[9px] text-[#5F5D58]/70">events.bryant.edu</span>
      </div>
      <ul className="mt-3 divide-y divide-black/5">
        {upcoming.map((e) => (
          <li key={e.id} className="flex items-baseline justify-between gap-3 py-2 text-xs">
            <a
              href={e.url}
              target="_blank"
              rel="noreferrer noopener"
              className="min-w-0 flex-1 truncate text-[#1A1A1A] hover:underline"
            >
              {e.title}
              {e.location && <span className="text-[#5F5D58]"> · {e.location}</span>}
            </a>
            <span
              className="shrink-0 text-[#5F5D58]"
              style={{ fontFamily: "var(--font-geist-mono), monospace" }}
            >
              {formatWhen(e.start)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
