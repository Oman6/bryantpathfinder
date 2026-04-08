"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Warning } from "@phosphor-icons/react";
import { useStore } from "@/lib/store";
import { generateSchedules } from "@/lib/api";
import { EyebrowTag } from "@/components/EyebrowTag";
import { PillButton } from "@/components/PillButton";
import { Skeleton } from "@/components/ui/skeleton";
import type { SchedulePreferences } from "@/lib/types";

const CATEGORY_LABELS: Record<string, string> = {
  major: "Major",
  business_core: "Business Core",
  general_education: "Gen Ed",
  elective: "Elective",
  minor: "Minor",
};

export default function PreferencesPage() {
  const router = useRouter();
  const { audit, setPreferences, setSchedules, setSolverStats } = useStore();

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [targetCredits, setTargetCredits] = useState(15);
  const [noFriday, setNoFriday] = useState(false);
  const [noBefore10, setNoBefore10] = useState(false);
  const [noEvening, setNoEvening] = useState(false);
  const [freeText, setFreeText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!audit) {
      router.push("/");
      return;
    }
    setSelectedIds(new Set(audit.outstanding_requirements.map((r) => r.id)));
  }, [audit, router]);

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
      blocked_days: noFriday ? ["F"] : [],
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
      router.push("/schedules");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to generate schedules";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  // Group outstanding requirements by category
  const grouped = audit.outstanding_requirements.reduce(
    (acc, req) => {
      const cat = req.category;
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(req);
      return acc;
    },
    {} as Record<string, typeof audit.outstanding_requirements>
  );

  const categoryOrder = ["major", "business_core", "general_education", "elective", "minor"];

  return (
    <main className="min-h-[100dvh]">
      <section className="mx-auto max-w-3xl px-6 py-24 md:px-12 md:py-32">
        {/* Back link */}
        <button
          onClick={() => router.push("/")}
          className="mb-8 flex items-center gap-1.5 text-xs text-[#787774] transition-colors hover:text-[#1A1A1A]"
        >
          <ArrowLeft size={14} weight="light" />
          <span>Back</span>
        </button>

        <div className="animate-fade-up space-y-3">
          <EyebrowTag>Step 2 of 3</EyebrowTag>
          <h1
            className="text-4xl tracking-tight md:text-5xl"
            style={{ fontFamily: "var(--font-instrument-serif), serif" }}
          >
            Set your preferences
          </h1>
          <p className="text-sm text-[#787774]">
            {audit.name} &middot; {audit.major} &middot;{" "}
            {audit.credits_earned_or_inprogress} of {audit.credits_required} credits
          </p>
        </div>

        {/* Requirements */}
        <div className="animate-fade-up delay-100 mt-12 space-y-8">
          <div>
            <h2 className="text-sm font-medium text-[#1A1A1A]">
              Outstanding requirements
            </h2>
            <p className="mt-1 text-xs text-[#787774]">
              Uncheck any you don't want to schedule this semester.
            </p>
          </div>

          {categoryOrder.map((cat) => {
            const reqs = grouped[cat];
            if (!reqs) return null;
            return (
              <div key={cat} className="space-y-2">
                <h3
                  className="text-[10px] font-medium uppercase tracking-[0.15em] text-[#787774]"
                  style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                >
                  {CATEGORY_LABELS[cat] || cat}
                </h3>
                <div className="space-y-1">
                  {reqs.map((req) => (
                    <label
                      key={req.id}
                      className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 transition-colors hover:bg-black/[0.02]"
                    >
                      <input
                        type="checkbox"
                        checked={selectedIds.has(req.id)}
                        onChange={() => toggleRequirement(req.id)}
                        className="h-4 w-4 rounded border-black/10 text-[#B8985A] accent-[#B8985A]"
                      />
                      <div className="flex-1">
                        <span className="text-sm text-[#1A1A1A]">
                          {req.requirement}
                        </span>
                        <span
                          className="ml-2 text-xs text-[#787774]"
                          style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                        >
                          {req.options.length > 0
                            ? req.options.join(", ")
                            : req.pattern || ""}
                        </span>
                      </div>
                      <span
                        className="text-[10px] text-[#787774]"
                        style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                      >
                        {req.credits_needed} cr
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* Preference controls */}
        <div className="animate-fade-up delay-200 mt-12 space-y-6">
          <h2 className="text-sm font-medium text-[#1A1A1A]">Schedule preferences</h2>

          {/* Target credits */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs text-[#787774]">Target credits</label>
              <span
                className="text-xs font-medium text-[#1A1A1A]"
                style={{ fontFamily: "var(--font-geist-mono), monospace" }}
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
              className="w-full accent-[#B8985A]"
            />
            <div
              className="flex justify-between text-[10px] text-[#787774]"
              style={{ fontFamily: "var(--font-geist-mono), monospace" }}
            >
              <span>12</span>
              <span>18</span>
            </div>
          </div>

          {/* Toggle switches */}
          <div className="space-y-3">
            {[
              { label: "No Friday classes", checked: noFriday, toggle: () => setNoFriday(!noFriday) },
              { label: "No classes before 10 AM", checked: noBefore10, toggle: () => setNoBefore10(!noBefore10) },
              { label: "No evening classes (after 5:30 PM)", checked: noEvening, toggle: () => setNoEvening(!noEvening) },
            ].map((pref) => (
              <label
                key={pref.label}
                className="flex cursor-pointer items-center justify-between rounded-xl px-3 py-3 transition-colors hover:bg-black/[0.02]"
              >
                <span className="text-sm text-[#1A1A1A]">{pref.label}</span>
                <button
                  type="button"
                  role="switch"
                  aria-checked={pref.checked}
                  onClick={pref.toggle}
                  className={`relative h-6 w-11 rounded-full transition-colors duration-300 ${
                    pref.checked ? "bg-[#B8985A]" : "bg-black/10"
                  }`}
                  style={{ transitionTimingFunction: "cubic-bezier(0.32, 0.72, 0, 1)" }}
                >
                  <span
                    className={`absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-300 ${
                      pref.checked ? "translate-x-5" : "translate-x-0"
                    }`}
                    style={{ transitionTimingFunction: "cubic-bezier(0.32, 0.72, 0, 1)" }}
                  />
                </button>
              </label>
            ))}
          </div>

          {/* Free text */}
          <div className="space-y-2">
            <label className="text-xs text-[#787774]">
              Other preferences (plain English)
            </label>
            <textarea
              value={freeText}
              onChange={(e) => setFreeText(e.target.value)}
              placeholder="e.g. I want to start the finance concentration"
              rows={2}
              className="w-full resize-none rounded-xl border border-black/5 bg-white px-4 py-3 text-sm text-[#1A1A1A] placeholder:text-[#787774]/50 focus:border-[#B8985A]/30 focus:outline-none focus:ring-1 focus:ring-[#B8985A]/20"
            />
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mt-6 flex items-center gap-2 rounded-xl bg-red-50 px-4 py-3 text-xs text-red-700">
            <Warning size={14} weight="light" />
            <span>{error}</span>
          </div>
        )}

        {/* Generate button */}
        <div className="animate-fade-up delay-300 mt-10">
          <PillButton onClick={handleGenerate} disabled={loading}>
            {loading ? "Generating..." : "Generate my schedules"}
          </PillButton>
        </div>
      </section>
    </main>
  );
}
