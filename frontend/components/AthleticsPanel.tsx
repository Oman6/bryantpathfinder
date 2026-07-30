"use client";

import { useEffect, useState } from "react";
import { House, Trophy } from "@phosphor-icons/react";

interface AthleticEvent {
  title: string;
  sport: string;
  opponent: string;
  location: string;
  is_home: boolean;
  start_local: string | null;
  end_local: string | null;
  link: string | null;
}

interface AthleticsPayload {
  source: string;
  fetched_at: string;
  events: AthleticEvent[];
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

export function AthleticsPanel() {
  const [data, setData] = useState<AthleticsPayload | null>(null);

  useEffect(() => {
    fetch("/bryant_athletics.json")
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => setData(null));
  }, []);

  if (!data) return null;

  const now = Date.now();
  const upcomingHome = data.events
    .filter((e) => e.is_home && e.start_local && new Date(e.start_local).getTime() > now)
    .slice(0, 5);

  if (upcomingHome.length === 0) return null;

  return (
    <div className="rounded-2xl border border-black/5 bg-white px-6 py-4">
      <div className="flex items-baseline justify-between">
        <div className="flex items-center gap-2">
          <Trophy size={13} weight="light" className="text-[#5F5D58]" />
          <span
            className="text-[10px] uppercase tracking-wide text-[#5F5D58]"
            style={{ fontFamily: "var(--font-geist-mono), monospace" }}
          >
            Upcoming Bulldogs home games
          </span>
        </div>
        <span className="text-[9px] text-[#5F5D58]/70">bryantbulldogs.com</span>
      </div>
      <ul className="mt-3 divide-y divide-black/5">
        {upcomingHome.map((e, i) => (
          <li key={i} className="flex items-baseline justify-between gap-3 py-2 text-xs">
            <div className="flex min-w-0 flex-1 items-baseline gap-2">
              <House size={10} weight="fill" className="shrink-0 text-[#B8985A]" />
              <span className="truncate">
                <span className="text-[#1A1A1A]">{e.sport || "Athletics"}</span>
                <span className="text-[#5F5D58]"> vs {e.opponent}</span>
              </span>
            </div>
            <span
              className="shrink-0 text-[#5F5D58]"
              style={{ fontFamily: "var(--font-geist-mono), monospace" }}
            >
              {formatWhen(e.start_local)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
