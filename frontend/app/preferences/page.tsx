"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Warning,
  Sparkle,
  GraduationCap,
  Briefcase,
  BookOpen,
  Tag,
  Sun,
  Moon,
  CalendarBlank,
  ChatTeardrop,
} from "@phosphor-icons/react";
import type { Icon } from "@phosphor-icons/react";
import { useStore } from "@/lib/store";
import { generateSchedules } from "@/lib/api";
import { EyebrowTag } from "@/components/EyebrowTag";
import { Skeleton } from "@/components/ui/skeleton";
import { CourseDetail } from "@/components/CourseDetail";
import type { OutstandingRequirement, SchedulePreferences } from "@/lib/types";

const CATEGORY_LABELS: Record<string, string> = {
  major: "Major",
  business_core: "Business Core",
  general_education: "Gen Ed",
  elective: "Elective",
  minor: "Minor",
};

const CATEGORY_ICONS: Record<string, Icon> = {
  major: GraduationCap,
  business_core: Briefcase,
  general_education: BookOpen,
  elective: Tag,
  minor: Tag,
};

const CATEGORY_ORDER = ["major", "business_core", "general_education", "elective", "minor"];

const DAYS = [
  { code: "M", label: "Mon" },
  { code: "T", label: "Tue" },
  { code: "W", label: "Wed" },
  { code: "R", label: "Thu" },
  { code: "F", label: "Fri" },
] as const;

function reqCodes(r: OutstandingRequirement): string {
  if (r.options.length > 0) return r.options.join(" · ");
  if (r.pattern) return r.pattern;
  if (r.pairs && r.pairs.length > 0) return r.pairs.map((p) => p.join(" + ")).join(" or ");
  return "";
}

// Pull the first parseable course code out of a requirement so we can wire
// the catalog dialog to the correct course.
function primaryCourseCode(r: OutstandingRequirement): string | null {
  if (r.options.length > 0) return r.options[0];
  if (r.pairs && r.pairs.length > 0) return r.pairs[0][0];
  return null;
}

export default function PreferencesPage() {
  const router = useRouter();
  const {
    audit, setAudit, setPreferences, setSchedules, setSolverStats,
    setProfessorData, setWorkloadData, setNegotiation, setAgentsRun,
  } = useStore();

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [targetCredits, setTargetCredits] = useState(15);
  const [blockedDays, setBlockedDays] = useState<Set<string>>(new Set());
  const [noBefore10, setNoBefore10] = useState(false);
  const [noEvening, setNoEvening] = useState(false);
  const [freeText, setFreeText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailCourse, setDetailCourse] = useState<string | null>(null);

  useEffect(() => {
    if (!audit) {
      router.push("/");
      return;
    }
    setSelectedIds(new Set(audit.outstanding_requirements.map((r) => r.id)));
  }, [audit, router]);

  const grouped = useMemo(() => {
    if (!audit) return {} as Record<string, OutstandingRequirement[]>;
    return audit.outstanding_requirements.reduce((acc, req) => {
      const cat = req.category;
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(req);
      return acc;
    }, {} as Record<string, OutstandingRequirement[]>);
  }, [audit]);

  const selectedCredits = useMemo(() => {
    if (!audit) return 0;
    return audit.outstanding_requirements
      .filter((r) => selectedIds.has(r.id))
      .reduce((s, r) => s + r.credits_needed, 0);
  }, [audit, selectedIds]);

  if (!audit) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-24">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="mt-4 h-4 w-96" />
      </main>
    );
  }

  const toggleRequirement = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleGenerate = async () => {
    if (selectedIds.size === 0) {
      setError("Select at least one requirement.");
      return;
    }

    const prefs: SchedulePreferences = {
      target_credits: targetCredits,
      blocked_days: Array.from(blockedDays) as ("M" | "T" | "W" | "R" | "F")[],
      no_earlier_than: noBefore10 ? "10:00" : null,
      no_later_than: noEvening ? "17:30" : null,
      preferred_instructors: [],
      avoided_instructors: [],
      free_text: freeText,
      selected_requirement_ids: Array.from(selectedIds),
    };

    setLoading(true);
    setError(null);

    try {
      setPreferences(prefs);
      const response = await generateSchedules(audit, prefs);
      setSchedules(response.schedules);
      setSolverStats(response.solver_stats);
      setProfessorData(response.professor_data ?? null);
      setWorkloadData(response.workload_data ?? null);
      setNegotiation(response.negotiation ?? null);
      setAgentsRun(response.agents_run || []);
      router.push("/schedules");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to generate schedules";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const gradPct = Math.min(100, Math.round((audit.credits_earned_or_inprogress / audit.credits_required) * 100));
  const creditDelta = selectedCredits - targetCredits;
  const creditTone =
    Math.abs(creditDelta) <= 1 ? "ok" : Math.abs(creditDelta) <= 3 ? "warn" : "off";

  return (
    <main className="min-h-[100dvh]">
      <section className="mx-auto max-w-5xl px-6 py-16 md:px-12 md:py-24">
        {/* Back */}
        <button
          onClick={() => router.push("/")}
          className="mb-6 flex items-center gap-1.5 text-xs text-[#5F5D58] transition-colors hover:text-[#1A1A1A]"
        >
          <ArrowLeft size={14} weight="light" />
          <span>Back</span>
        </button>

        {/* Hero */}
        <div className="animate-fade-up space-y-3">
          <EyebrowTag>Step 2 of 3</EyebrowTag>
          <h1
            className="text-4xl tracking-tight md:text-5xl"
            style={{ fontFamily: "var(--font-instrument-serif), serif" }}
          >
            Build your <span className="italic text-[#B8985A]">next semester</span>.
          </h1>
          <p className="text-sm text-[#5F5D58]">
            {audit.name} · {audit.major} · expected {audit.expected_graduation}
          </p>
        </div>

        {/* Stats strip — graduation progress + selected credits */}
        <div className="mt-8 grid grid-cols-1 gap-3 md:grid-cols-2 animate-fade-up delay-100">
          <div className="rounded-2xl border border-black/5 bg-white px-5 py-4">
            <div className="flex items-baseline justify-between">
              <span
                className="text-[10px] uppercase tracking-wide text-[#5F5D58]"
                style={{ fontFamily: "var(--font-geist-mono), monospace" }}
              >
                Progress to graduation
              </span>
              <span
                className="text-[10px] text-[#5F5D58]"
                style={{ fontFamily: "var(--font-geist-mono), monospace" }}
              >
                {gradPct}%
              </span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span
                className="text-3xl text-[#1A1A1A]"
                style={{ fontFamily: "var(--font-instrument-serif), serif" }}
              >
                {audit.credits_earned_or_inprogress}
              </span>
              <span className="text-sm text-[#5F5D58]">of {audit.credits_required} credits</span>
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[#FAFAF7]">
              <div
                className="h-full rounded-full bg-[#B8985A] transition-[width] duration-700"
                style={{
                  width: `${gradPct}%`,
                  transitionTimingFunction: "cubic-bezier(0.32, 0.72, 0, 1)",
                }}
              />
            </div>
          </div>

          <div className="rounded-2xl border border-black/5 bg-white px-5 py-4">
            <div className="flex items-baseline justify-between">
              <span
                className="text-[10px] uppercase tracking-wide text-[#5F5D58]"
                style={{ fontFamily: "var(--font-geist-mono), monospace" }}
              >
                This semester selection
              </span>
              <span
                className={`text-[10px] ${
                  creditTone === "ok"
                    ? "text-emerald-700"
                    : creditTone === "warn"
                      ? "text-amber-700"
                      : "text-red-700"
                }`}
                style={{ fontFamily: "var(--font-geist-mono), monospace" }}
              >
                {creditDelta === 0
                  ? "On target"
                  : creditDelta > 0
                    ? `+${creditDelta} over target`
                    : `${creditDelta} under target`}
              </span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span
                className="text-3xl text-[#1A1A1A]"
                style={{ fontFamily: "var(--font-instrument-serif), serif" }}
              >
                {selectedCredits}
              </span>
              <span className="text-sm text-[#5F5D58]">
                {selectedIds.size === 1 ? "credit" : "credits"} across {selectedIds.size}{" "}
                {selectedIds.size === 1 ? "course" : "courses"} · target {targetCredits}
              </span>
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[#FAFAF7]">
              <div
                className={`h-full rounded-full transition-[width] duration-500 ${
                  creditTone === "ok"
                    ? "bg-emerald-600"
                    : creditTone === "warn"
                      ? "bg-amber-600"
                      : "bg-red-600"
                }`}
                style={{
                  width: `${Math.min(100, (selectedCredits / Math.max(1, targetCredits + 6)) * 100)}%`,
                  transitionTimingFunction: "cubic-bezier(0.32, 0.72, 0, 1)",
                }}
              />
            </div>
          </div>
        </div>

        {/* Two-column layout: requirements (lg:8) + preferences (lg:4) */}
        <div className="mt-10 grid gap-8 lg:grid-cols-12">
          {/* Requirements column */}
          <div className="space-y-4 lg:col-span-7 animate-fade-up delay-200">
            <div className="flex items-baseline justify-between">
              <h2 className="text-sm font-medium text-[#1A1A1A]">Outstanding requirements</h2>
              <span className="text-[11px] text-[#5F5D58]">
                {selectedIds.size} of {audit.outstanding_requirements.length} selected
              </span>
            </div>
            <p className="text-xs text-[#5F5D58]">
              Uncheck what you&apos;ve already taken or won&apos;t schedule this semester.
              Click any course code to see its description.
            </p>

            {audit.outstanding_requirements.length === 0 && (
              <button
                onClick={async () => {
                  try {
                    const { getSampleAudit } = await import("@/lib/api");
                    const sample = await getSampleAudit();
                    setAudit(sample);
                  } catch {}
                }}
                className="rounded-full bg-[#FAFAF7] px-4 py-2 text-xs text-[#5F5D58] ring-1 ring-black/5 transition-colors hover:text-[#1A1A1A]"
              >
                Load sample audit instead
              </button>
            )}

            {CATEGORY_ORDER.map((cat) => {
              const reqs = grouped[cat];
              if (!reqs?.length) return null;
              const CatIcon = CATEGORY_ICONS[cat] ?? Tag;
              const selectedInCat = reqs.filter((r) => selectedIds.has(r.id)).length;
              const creditsInCat = reqs
                .filter((r) => selectedIds.has(r.id))
                .reduce((s, r) => s + r.credits_needed, 0);

              return (
                <div
                  key={cat}
                  className="rounded-2xl border border-black/5 bg-white"
                >
                  {/* Category header */}
                  <div className="flex items-center justify-between border-b border-black/5 px-5 py-3">
                    <div className="flex items-center gap-2">
                      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#FAFAF7]">
                        <CatIcon size={13} weight="light" className="text-[#5F5D58]" />
                      </span>
                      <h3
                        className="text-[11px] font-medium uppercase tracking-[0.12em] text-[#1A1A1A]"
                        style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                      >
                        {CATEGORY_LABELS[cat] || cat}
                      </h3>
                    </div>
                    <span
                      className="text-[10px] text-[#5F5D58]"
                      style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                    >
                      {selectedInCat} of {reqs.length} · {creditsInCat} cr
                    </span>
                  </div>

                  {/* Requirement rows */}
                  <ul className="divide-y divide-black/[0.04]">
                    {reqs.map((req) => {
                      const isSelected = selectedIds.has(req.id);
                      const courseCode = primaryCourseCode(req);
                      const codeStr = reqCodes(req);

                      return (
                        <li key={req.id}>
                          <div
                            className={`flex items-center gap-3 px-5 py-3 transition-colors ${
                              isSelected ? "" : "opacity-50"
                            }`}
                          >
                            <input
                              type="checkbox"
                              id={`req-${req.id}`}
                              checked={isSelected}
                              onChange={() => toggleRequirement(req.id)}
                              className="h-4 w-4 shrink-0 cursor-pointer rounded border-black/10 text-[#B8985A] accent-[#B8985A]"
                            />
                            <label
                              htmlFor={`req-${req.id}`}
                              className="flex-1 cursor-pointer text-sm text-[#1A1A1A]"
                            >
                              {req.requirement}
                            </label>
                            {courseCode ? (
                              <button
                                type="button"
                                onClick={() => setDetailCourse(courseCode)}
                                className="shrink-0 rounded-md bg-[#FAFAF7] px-2 py-1 text-[10px] text-[#5F5D58] transition-colors hover:bg-white hover:text-[#1A1A1A] hover:underline"
                                style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                                title="Course details"
                              >
                                {codeStr}
                              </button>
                            ) : (
                              <span
                                className="shrink-0 text-[10px] text-[#5F5D58]"
                                style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                              >
                                {codeStr}
                              </span>
                            )}
                            <span
                              className="w-12 shrink-0 text-right text-[10px] text-[#5F5D58]"
                              style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                            >
                              {req.credits_needed} cr
                            </span>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              );
            })}
          </div>

          {/* Preferences column */}
          <aside className="space-y-4 lg:col-span-5 animate-fade-up delay-300">
            <h2 className="text-sm font-medium text-[#1A1A1A]">Schedule preferences</h2>

            {/* Target credits */}
            <div className="rounded-2xl border border-black/5 bg-white p-5">
              <div className="flex items-baseline justify-between">
                <span
                  className="text-[10px] uppercase tracking-wide text-[#5F5D58]"
                  style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                >
                  Target credits
                </span>
                <span
                  className="text-2xl text-[#1A1A1A]"
                  style={{ fontFamily: "var(--font-instrument-serif), serif" }}
                >
                  {targetCredits}
                </span>
              </div>
              <input
                type="range"
                min={12}
                max={18}
                value={targetCredits}
                onChange={(e) => setTargetCredits(Number(e.target.value))}
                className="mt-3 w-full accent-[#B8985A]"
              />
              <div
                className="mt-1 flex justify-between text-[10px] text-[#5F5D58]/70"
                style={{ fontFamily: "var(--font-geist-mono), monospace" }}
              >
                <span>12 (light)</span>
                <span>15 (typical)</span>
                <span>18 (heavy)</span>
              </div>
            </div>

            {/* Days off */}
            <div className="rounded-2xl border border-black/5 bg-white p-5">
              <div className="mb-3 flex items-center gap-1.5">
                <CalendarBlank size={11} weight="light" className="text-[#5F5D58]" />
                <span
                  className="text-[10px] uppercase tracking-wide text-[#5F5D58]"
                  style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                >
                  Days off
                </span>
              </div>
              <div className="grid grid-cols-5 gap-2">
                {DAYS.map(({ code, label }) => {
                  const isBlocked = blockedDays.has(code);
                  return (
                    <button
                      key={code}
                      type="button"
                      onClick={() => {
                        setBlockedDays((prev) => {
                          const next = new Set(prev);
                          if (next.has(code)) next.delete(code);
                          else next.add(code);
                          return next;
                        });
                      }}
                      className={`flex h-12 flex-col items-center justify-center rounded-xl text-[10px] font-medium transition-all duration-300 ${
                        isBlocked
                          ? "bg-[#1A1A1A] text-white"
                          : "bg-[#FAFAF7] text-[#5F5D58] ring-1 ring-black/5 hover:ring-black/15"
                      }`}
                      style={{
                        transitionTimingFunction: "cubic-bezier(0.32, 0.72, 0, 1)",
                        fontFamily: "var(--font-geist-mono), monospace",
                      }}
                      aria-pressed={isBlocked}
                      aria-label={`${isBlocked ? "Unblock" : "Block"} ${label}`}
                    >
                      <span className="text-base">{code}</span>
                      <span className="text-[8px] uppercase tracking-wider opacity-70">
                        {label}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Time of day */}
            <div className="rounded-2xl border border-black/5 bg-white p-5 space-y-3">
              <div className="flex items-center gap-1.5">
                <Sun size={11} weight="light" className="text-[#5F5D58]" />
                <span
                  className="text-[10px] uppercase tracking-wide text-[#5F5D58]"
                  style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                >
                  Time of day
                </span>
              </div>
              {[
                { icon: Sun, label: "No classes before 10 AM", checked: noBefore10, toggle: () => setNoBefore10(!noBefore10) },
                { icon: Moon, label: "No evening classes (after 5:30 PM)", checked: noEvening, toggle: () => setNoEvening(!noEvening) },
              ].map((pref) => {
                const PrefIcon = pref.icon;
                return (
                  <label
                    key={pref.label}
                    className="flex cursor-pointer items-center justify-between gap-3 rounded-lg px-1 py-1 transition-colors"
                  >
                    <span className="flex items-center gap-2 text-xs text-[#1A1A1A]">
                      <PrefIcon size={12} weight="light" className="text-[#5F5D58]" />
                      {pref.label}
                    </span>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={pref.checked}
                      onClick={pref.toggle}
                      className={`relative h-5 w-9 shrink-0 rounded-full transition-colors duration-300 ${
                        pref.checked ? "bg-[#B8985A]" : "bg-black/10"
                      }`}
                      style={{ transitionTimingFunction: "cubic-bezier(0.32, 0.72, 0, 1)" }}
                    >
                      <span
                        className={`absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-300 ${
                          pref.checked ? "translate-x-4" : "translate-x-0"
                        }`}
                        style={{ transitionTimingFunction: "cubic-bezier(0.32, 0.72, 0, 1)" }}
                      />
                    </button>
                  </label>
                );
              })}
            </div>

            {/* Free text */}
            <div className="rounded-2xl border border-black/5 bg-white p-5">
              <div className="mb-2 flex items-center gap-1.5">
                <ChatTeardrop size={11} weight="light" className="text-[#5F5D58]" />
                <span
                  className="text-[10px] uppercase tracking-wide text-[#5F5D58]"
                  style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                >
                  Anything else
                </span>
              </div>
              <textarea
                value={freeText}
                onChange={(e) => setFreeText(e.target.value)}
                placeholder="e.g. I want to start the finance concentration with Kumar"
                rows={3}
                className="w-full resize-none rounded-lg border-0 bg-[#FAFAF7] px-3 py-2 text-sm text-[#1A1A1A] placeholder:text-[#5F5D58]/60 focus:bg-white focus:outline-none focus:ring-1 focus:ring-[#B8985A]/30"
              />
              <p className="mt-1.5 text-[10px] text-[#5F5D58]/70">
                <Sparkle size={9} weight="light" className="mr-0.5 inline" />
                Claude reads this when ranking the schedules.
              </p>
            </div>
          </aside>
        </div>

        {/* Error */}
        {error && (
          <div className="mt-6 flex items-center gap-2 rounded-xl bg-red-50 px-4 py-3 text-xs text-red-700 animate-fade-up">
            <Warning size={14} weight="light" />
            <span>{error}</span>
          </div>
        )}

        {/* Generate CTA */}
        <div className="animate-fade-up delay-500 mt-10 flex flex-col items-center gap-3 md:flex-row md:justify-between">
          <p className="text-xs text-[#5F5D58]">
            We&apos;ll search {audit.outstanding_requirements.length} requirements across the live Bryant Fall 2026 catalog.
          </p>
          <button
            onClick={handleGenerate}
            disabled={loading || selectedIds.size === 0}
            className="group inline-flex items-center gap-2 rounded-full bg-[#1A1A1A] px-6 py-3 text-sm font-medium text-white shadow-[0_4px_20px_-4px_rgba(184,152,90,0.3)] transition-all duration-300 hover:bg-[#2a2a2a] hover:shadow-[0_4px_28px_-4px_rgba(184,152,90,0.5)] disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
            style={{ transitionTimingFunction: "cubic-bezier(0.32, 0.72, 0, 1)" }}
          >
            <span>{loading ? "Solving…" : "Generate my schedules"}</span>
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white/15 transition-transform group-hover:translate-x-0.5">
              <ArrowRight size={12} weight="light" />
            </span>
          </button>
        </div>
      </section>

      {/* Course detail dialog */}
      {detailCourse && (
        <CourseDetail
          courseCode={detailCourse}
          open={detailCourse !== null}
          onClose={() => setDetailCourse(null)}
        />
      )}
    </main>
  );
}
