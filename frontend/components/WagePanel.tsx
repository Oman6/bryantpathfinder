"use client";

import { useEffect, useState } from "react";
import { TrendUp } from "@phosphor-icons/react";

interface ScorecardProgram {
  cip_code: string;
  title: string;
  credential: string;
  ipeds_awards: number | null;
  earnings_1yr: number | null;
  earnings_4yr: number | null;
  earnings_5yr: number | null;
  earnings_4yr_national: number | null;
}

interface ScorecardPayload {
  source: string;
  school_name: string;
  unitid: number;
  programs: ScorecardProgram[];
}

function fmt(n: number | null): string {
  if (n == null) return "—";
  return `$${(n / 1000).toFixed(0)}K`;
}

function findProgram(programs: ScorecardProgram[], major: string): ScorecardProgram | null {
  const m = major.trim().toLowerCase();
  if (!m) return null;
  const exact = programs.find((p) => p.title.toLowerCase().startsWith(m));
  if (exact) return exact;
  return programs.find((p) => p.title.toLowerCase().includes(m)) ?? null;
}

export function WagePanel({ major }: { major: string }) {
  const [data, setData] = useState<ScorecardPayload | null>(null);

  useEffect(() => {
    fetch("/scorecard_bryant.json")
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => setData(null));
  }, []);

  if (!data) return null;
  const program = findProgram(data.programs, major);
  if (!program || !program.earnings_4yr) return null;

  const vsNational = program.earnings_4yr_national
    ? Math.round(((program.earnings_4yr - program.earnings_4yr_national) / program.earnings_4yr_national) * 100)
    : null;

  return (
    <div className="rounded-2xl border border-black/5 bg-white px-6 py-4">
      <div className="flex items-baseline justify-between gap-3">
        <div>
          <div
            className="text-[10px] uppercase tracking-wide text-[#5F5D58]"
            style={{ fontFamily: "var(--font-geist-mono), monospace" }}
          >
            Outcomes · {program.title}
          </div>
          <div
            className="mt-1 text-3xl text-[#1A1A1A]"
            style={{ fontFamily: "var(--font-instrument-serif), serif" }}
          >
            {fmt(program.earnings_4yr)}{" "}
            <span className="text-sm text-[#5F5D58]">median earnings, 4 yrs after grad</span>
          </div>
        </div>
        {vsNational !== null && vsNational > 0 && (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-medium text-emerald-700">
            <TrendUp size={11} weight="fill" />
            +{vsNational}% vs. national
          </span>
        )}
      </div>
      <div
        className="mt-3 grid grid-cols-3 gap-4 border-t border-black/5 pt-3 text-[11px] text-[#5F5D58]"
        style={{ fontFamily: "var(--font-geist-mono), monospace" }}
      >
        <div>
          <div className="text-[#1A1A1A]">{fmt(program.earnings_1yr)}</div>
          <div>1 yr out</div>
        </div>
        <div>
          <div className="text-[#1A1A1A]">{fmt(program.earnings_4yr)}</div>
          <div>4 yr out</div>
        </div>
        <div>
          <div className="text-[#1A1A1A]">{fmt(program.earnings_5yr)}</div>
          <div>5 yr out</div>
        </div>
      </div>
      <p className="mt-2 text-[9px] text-[#5F5D58]/80">
        Source: U.S. Dept. of Education College Scorecard
      </p>
    </div>
  );
}
