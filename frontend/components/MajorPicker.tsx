"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Briefcase,
  ChartLine,
  Megaphone,
  Users,
  Calculator,
  MagnifyingGlass,
} from "@phosphor-icons/react";
import type { Icon } from "@phosphor-icons/react";
import type { DegreeAudit, OutstandingRequirement } from "@/lib/types";
import { useStore } from "@/lib/store";

interface MajorTemplate {
  id: string;
  label: string;
  full_label?: string;
  type_bucket?: string;
  college?: string | null;
  year_label: string;
  credits_earned_or_inprogress: number;
  credits_required: number;
  expected_graduation: string;
  auto_generated?: boolean;
  outstanding_requirements: OutstandingRequirement[];
  unparseable_rules?: string[];
  source_url?: string;
}

interface TemplatesPayload {
  _metadata: { version: string; generated_at: string; note?: string };
  majors: MajorTemplate[];
}

const FEATURED_ICONS: Record<string, Icon> = {
  finance: ChartLine,
  accounting: Calculator,
  marketing: Megaphone,
  management: Users,
  actuarial_math: Briefcase,
};

type Year = "Freshman" | "Sophomore" | "Junior" | "Senior";
const YEARS: Year[] = ["Freshman", "Sophomore", "Junior", "Senior"];

// Year → expected graduation (rough — student edits later if needed)
const YEAR_GRAD: Record<Year, string> = {
  Freshman: "May 2030",
  Sophomore: "May 2029",
  Junior: "May 2028",
  Senior: "May 2027",
};

// Year → credits earned-or-in-progress (rough Bryant pacing: 30/yr)
const YEAR_CREDITS: Record<Year, number> = {
  Freshman: 12,
  Sophomore: 42,
  Junior: 75,
  Senior: 105,
};

export function MajorPicker() {
  const router = useRouter();
  const { setAudit } = useStore();
  const [templates, setTemplates] = useState<MajorTemplate[] | null>(null);
  const [picking, setPicking] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [year, setYear] = useState<Year>("Sophomore");
  const searchRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    fetch("/major_templates.json")
      .then((r) => (r.ok ? r.json() : null))
      .then((d: TemplatesPayload | null) => setTemplates(d?.majors ?? []))
      .catch(() => setTemplates([]));
  }, []);

  const featured = useMemo(
    () => (templates ?? []).filter((t) => !t.auto_generated),
    [templates],
  );
  const others = useMemo(
    () => (templates ?? []).filter((t) => t.auto_generated),
    [templates],
  );

  // When search has text, all results show (featured + others). Otherwise just featured.
  const isSearching = search.trim().length > 0;
  const searchResults = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return [];
    return [...featured, ...others].filter(
      (t) =>
        t.label.toLowerCase().includes(q) ||
        (t.full_label?.toLowerCase().includes(q) ?? false) ||
        (t.college?.toLowerCase().includes(q) ?? false),
    );
  }, [featured, others, search]);

  const handlePick = (template: MajorTemplate) => {
    setPicking(template.id);
    const audit: DegreeAudit = {
      student_id: "000000000",
      name: "Student",
      major: template.label,
      expected_graduation: YEAR_GRAD[year],
      credits_earned_or_inprogress: YEAR_CREDITS[year],
      credits_required: template.credits_required,
      completed_requirements: [],
      in_progress_requirements: [],
      outstanding_requirements: template.outstanding_requirements,
    };
    setAudit(audit);
    router.push("/preferences");
  };

  return (
    <div className="rounded-[2rem] bg-black/[0.03] p-1.5 ring-1 ring-black/5">
      <div className="rounded-[calc(2rem-0.375rem)] bg-white p-6 md:p-8">
        {/* Header */}
        <div className="mb-1 flex items-baseline justify-between">
          <h2
            className="text-2xl text-[#1A1A1A] md:text-3xl"
            style={{ fontFamily: "var(--font-instrument-serif), serif" }}
          >
            Pick your major
          </h2>
          <span
            className="text-[10px] uppercase tracking-wide text-[#5F5D58]"
            style={{ fontFamily: "var(--font-geist-mono), monospace" }}
          >
            Step 1 of 3
          </span>
        </div>
        <p className="mb-6 text-xs leading-relaxed text-[#5F5D58]">
          We&apos;ll prefill typical requirements from Bryant&apos;s 2025-26 catalog.
          Uncheck what you&apos;ve already taken on the next page.
        </p>

        {/* Year selector */}
        <fieldset className="mb-5">
          <legend
            className="mb-2 text-[10px] uppercase tracking-wide text-[#5F5D58]"
            style={{ fontFamily: "var(--font-geist-mono), monospace" }}
          >
            Year
          </legend>
          <div className="grid grid-cols-4 gap-1 rounded-full bg-[#FAFAF7] p-1">
            {YEARS.map((y) => {
              const active = y === year;
              return (
                <button
                  key={y}
                  type="button"
                  onClick={() => setYear(y)}
                  className={`rounded-full py-1.5 text-xs font-medium transition-all ${
                    active
                      ? "bg-white text-[#1A1A1A] shadow-[0_1px_3px_rgba(0,0,0,0.08)]"
                      : "text-[#5F5D58] hover:text-[#1A1A1A]"
                  }`}
                >
                  {y}
                </button>
              );
            })}
          </div>
        </fieldset>

        {/* Search */}
        <div className="mb-4">
          <label className="sr-only" htmlFor="major-search">
            Search Bryant majors
          </label>
          <div className="relative">
            <MagnifyingGlass
              size={14}
              weight="light"
              className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-[#5F5D58]"
            />
            <input
              id="major-search"
              ref={searchRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={`Search all ${(templates ?? []).length || ""} Bryant majors…`}
              className="w-full rounded-full border border-black/5 bg-white py-2.5 pl-10 pr-3 text-sm text-[#1A1A1A] placeholder-[#5F5D58]/70 outline-none transition-colors focus:border-[#B8985A]/60"
            />
            {isSearching && (
              <button
                type="button"
                onClick={() => setSearch("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-[#5F5D58] hover:text-[#1A1A1A]"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {/* Body */}
        {templates === null ? (
          <ul className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <li key={i} className="h-[58px] animate-pulse rounded-xl bg-[#FAFAF7]" />
            ))}
          </ul>
        ) : isSearching ? (
          searchResults.length === 0 ? (
            <p className="rounded-xl bg-[#FAFAF7] px-4 py-6 text-center text-xs text-[#5F5D58]">
              No majors match &quot;{search}&quot;.
            </p>
          ) : (
            <>
              <p
                className="mb-2 text-[10px] uppercase tracking-wide text-[#5F5D58]"
                style={{ fontFamily: "var(--font-geist-mono), monospace" }}
              >
                {searchResults.length} match{searchResults.length === 1 ? "" : "es"}
              </p>
              <ul className="max-h-[420px] space-y-1.5 overflow-y-auto pr-1">
                {searchResults.map((t) => (
                  <li key={t.id}>
                    <Row template={t} year={year} busy={picking === t.id} onPick={handlePick} Icon={FEATURED_ICONS[t.id] ?? Briefcase} />
                  </li>
                ))}
              </ul>
            </>
          )
        ) : (
          <>
            <p
              className="mb-2 text-[10px] uppercase tracking-wide text-[#5F5D58]"
              style={{ fontFamily: "var(--font-geist-mono), monospace" }}
            >
              Most common
            </p>
            <ul className="space-y-1.5">
              {featured.map((t) => (
                <li key={t.id}>
                  <Row template={t} year={year} busy={picking === t.id} onPick={handlePick} Icon={FEATURED_ICONS[t.id] ?? Briefcase} />
                </li>
              ))}
            </ul>
            <p className="mt-3 text-[11px] text-[#5F5D58]/80">
              Looking for something else? Search above — {others.length} more Bryant majors are available.
            </p>
          </>
        )}
      </div>
    </div>
  );
}

function Row({
  template,
  year,
  busy,
  onPick,
  Icon,
}: {
  template: MajorTemplate;
  year: Year;
  busy: boolean;
  onPick: (t: MajorTemplate) => void;
  Icon: Icon;
}) {
  const reqCount = template.outstanding_requirements.length;
  const college = template.college?.replace("College of ", "").replace("School of ", "") ?? "";
  const unparseCount = template.unparseable_rules?.length ?? 0;

  return (
    <button
      type="button"
      onClick={() => onPick(template)}
      disabled={busy}
      className="group flex w-full items-center justify-between gap-4 rounded-xl border border-black/5 bg-white px-4 py-3 text-left transition-all hover:-translate-y-px hover:border-[#B8985A]/40 hover:bg-[#FAFAF7] disabled:opacity-60"
    >
      <div className="flex min-w-0 items-center gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#FAFAF7] group-hover:bg-white">
          <Icon size={16} weight="light" className="text-[#5F5D58] group-hover:text-[#B8985A]" />
        </span>
        <div className="min-w-0">
          <div className="text-sm font-medium text-[#1A1A1A]">{template.label}</div>
          <div
            className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-[10px] text-[#5F5D58]"
            style={{ fontFamily: "var(--font-geist-mono), monospace" }}
          >
            <span>{reqCount} reqs</span>
            <span>·</span>
            <span>{year}</span>
            {college && (
              <>
                <span>·</span>
                <span>{college}</span>
              </>
            )}
            {template.auto_generated && unparseCount > 0 && (
              <>
                <span>·</span>
                <span
                  className="text-amber-700"
                  title={`${unparseCount} catalog rules couldn't be auto-parsed — review on the next page`}
                >
                  {unparseCount} to review
                </span>
              </>
            )}
          </div>
        </div>
      </div>
      <ArrowRight
        size={14}
        weight="light"
        className="shrink-0 text-[#5F5D58] transition-transform group-hover:translate-x-0.5 group-hover:text-[#B8985A]"
      />
    </button>
  );
}
