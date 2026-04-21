"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle,
  Warning,
  GraduationCap,
  CalendarBlank,
} from "@phosphor-icons/react";
import { useStore } from "@/lib/store";
import { getMultiSemesterPlan } from "@/lib/api";
import { EyebrowTag } from "@/components/EyebrowTag";
import { PillButton } from "@/components/PillButton";
import { AgentBadges } from "@/components/AgentBadges";
import type { MultiSemesterResult, SemesterCourse } from "@/lib/types";

const CATEGORY_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  major: {
    bg: "bg-[#B8985A]/10",
    text: "text-[#8B6D2F]",
    label: "Major",
  },
  business_core: {
    bg: "bg-blue-50",
    text: "text-blue-700",
    label: "Business Core",
  },
  general_education: {
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    label: "Gen Ed",
  },
  elective: {
    bg: "bg-violet-50",
    text: "text-violet-700",
    label: "Elective",
  },
  minor: {
    bg: "bg-orange-50",
    text: "text-orange-700",
    label: "Minor",
  },
};

function CategoryBadge({ category }: { category: string }) {
  const style = CATEGORY_STYLES[category] || {
    bg: "bg-black/5",
    text: "text-[#5F5D58]",
    label: category,
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[9px] font-medium ${style.bg} ${style.text}`}
      style={{ fontFamily: "var(--font-geist-mono), monospace" }}
    >
      {style.label}
    </span>
  );
}

function SemesterCard({
  semester,
  courses,
  credits,
  notes,
  index,
}: {
  semester: string;
  courses: SemesterCourse[];
  credits: number;
  notes: string[];
  index: number;
}) {
  return (
    <div
      className="animate-fade-up flex min-w-[260px] flex-1 flex-col"
      style={{ animationDelay: `${(index + 2) * 100}ms` }}
    >
      {/* Semester header */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CalendarBlank size={14} weight="light" className="text-[#5F5D58]" />
          <span
            className="text-sm font-medium text-[#1A1A1A]"
            style={{ fontFamily: "var(--font-instrument-serif), serif" }}
          >
            {semester}
          </span>
        </div>
        <span
          className="text-[10px] text-[#5F5D58]"
          style={{ fontFamily: "var(--font-geist-mono), monospace" }}
        >
          {credits} cr
        </span>
      </div>

      {/* Double-bezel card */}
      <div className="flex-1 rounded-[2rem] bg-black/[0.03] p-1.5 ring-1 ring-black/5">
        <div className="flex h-full flex-col rounded-[calc(2rem-0.375rem)] bg-white p-5">
          {/* Course list */}
          <div className="flex-1 space-y-3">
            {courses.map((course) => (
              <div key={course.id} className="space-y-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span
                    className="text-xs font-medium text-[#1A1A1A]"
                    style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                  >
                    {course.course}
                  </span>
                  <span
                    className="text-[10px] text-[#5F5D58]"
                    style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                  >
                    {course.credits} cr
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <CategoryBadge category={course.category} />
                  <span className="text-[10px] leading-tight text-[#5F5D58]">
                    {course.requirement}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Notes */}
          {notes.length > 0 && (
            <div className="mt-4 border-t border-black/5 pt-3 space-y-1">
              {notes.map((note, i) => (
                <p key={i} className="text-[10px] leading-relaxed text-[#5F5D58]">
                  {note}
                </p>
              ))}
            </div>
          )}

          {/* Credit bar */}
          <div className="mt-4 border-t border-black/5 pt-3">
            <div className="flex items-center gap-2">
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-black/5">
                <div
                  className="h-full rounded-full bg-[#B8985A] transition-all duration-700"
                  style={{
                    width: `${Math.min((credits / 18) * 100, 100)}%`,
                    transitionTimingFunction: "cubic-bezier(0.32, 0.72, 0, 1)",
                  }}
                />
              </div>
              <span
                className="text-[9px] text-[#5F5D58]"
                style={{ fontFamily: "var(--font-geist-mono), monospace" }}
              >
                {credits}/18
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function PrerequisiteChain({ chain }: { chain: string[] }) {
  return (
    <div className="flex flex-wrap items-center gap-1">
      {chain.map((course, i) => (
        <span key={course} className="flex items-center gap-1">
          <span
            className="rounded-lg bg-[#FAFAF7] px-2.5 py-1 text-[11px] font-medium text-[#1A1A1A] ring-1 ring-black/5"
            style={{ fontFamily: "var(--font-geist-mono), monospace" }}
          >
            {course}
          </span>
          {i < chain.length - 1 && (
            <ArrowRight size={12} weight="light" className="text-[#B8985A]" />
          )}
        </span>
      ))}
    </div>
  );
}

export default function PlannerPage() {
  const router = useRouter();
  const { audit, preferences } = useStore();
  const [plan, setPlan] = useState<MultiSemesterResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!audit) {
      router.push("/");
      return;
    }

    let cancelled = false;

    async function fetchPlan() {
      try {
        setLoading(true);
        setError(null);
        const result = await getMultiSemesterPlan(audit!, preferences);
        if (!cancelled) {
          setPlan(result);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to generate plan");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchPlan();

    return () => {
      cancelled = true;
    };
  }, [audit, preferences, router]);

  // Redirect handled in effect
  if (!audit) return null;

  // Loading state
  if (loading) {
    return (
      <main className="min-h-[100dvh]">
        <section className="mx-auto max-w-6xl px-6 py-24 md:px-12 md:py-32">
          <button
            onClick={() => router.push("/schedules")}
            className="mb-8 flex items-center gap-1.5 text-xs text-[#5F5D58] transition-colors hover:text-[#1A1A1A]"
          >
            <ArrowLeft size={14} weight="light" />
            <span>Back to schedules</span>
          </button>

          <div className="animate-fade-up space-y-3">
            <EyebrowTag>Multi-Semester Planning</EyebrowTag>
            <h1
              className="text-4xl tracking-tight md:text-5xl"
              style={{ fontFamily: "var(--font-instrument-serif), serif" }}
            >
              Building your roadmap...
            </h1>
            <p className="text-sm text-[#5F5D58]">
              Analyzing prerequisites, course rotations, and optimal sequencing.
            </p>
          </div>

          {/* Skeleton semester cards */}
          <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="animate-fade-up" style={{ animationDelay: `${(i + 2) * 100}ms` }}>
                <div className="rounded-[2rem] bg-black/[0.03] p-1.5 ring-1 ring-black/5">
                  <div className="rounded-[calc(2rem-0.375rem)] bg-white p-5">
                    <div className="h-4 w-24 animate-pulse rounded bg-black/5" />
                    <div className="mt-4 space-y-3">
                      {[0, 1, 2].map((j) => (
                        <div key={j} className="space-y-1">
                          <div className="h-3 w-20 animate-pulse rounded bg-black/5" />
                          <div className="h-2 w-32 animate-pulse rounded bg-black/5" />
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>
    );
  }

  // Error state
  if (error) {
    return (
      <main className="min-h-[100dvh]">
        <section className="mx-auto max-w-6xl px-6 py-24 md:px-12 md:py-32">
          <button
            onClick={() => router.push("/schedules")}
            className="mb-8 flex items-center gap-1.5 text-xs text-[#5F5D58] transition-colors hover:text-[#1A1A1A]"
          >
            <ArrowLeft size={14} weight="light" />
            <span>Back to schedules</span>
          </button>

          <div className="animate-fade-up space-y-3">
            <EyebrowTag>Planning Error</EyebrowTag>
            <h1
              className="text-4xl tracking-tight md:text-5xl"
              style={{ fontFamily: "var(--font-instrument-serif), serif" }}
            >
              Could not generate plan
            </h1>
            <div className="mt-4 flex items-start gap-2 rounded-xl bg-red-50 px-4 py-3">
              <Warning size={16} weight="light" className="mt-0.5 text-red-700" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>

          <div className="mt-8">
            <PillButton variant="secondary" onClick={() => router.push("/schedules")}>
              Back to schedules
            </PillButton>
          </div>
        </section>
      </main>
    );
  }

  if (!plan) return null;

  const hasChains = plan.prerequisite_analysis.chains.length > 0;
  const hasRotation =
    plan.rotation_analysis.fall_only.length > 0 ||
    plan.rotation_analysis.spring_only.length > 0 ||
    plan.rotation_analysis.schedule_critical.length > 0;

  return (
    <main className="min-h-[100dvh]">
      <section className="mx-auto max-w-6xl px-6 py-24 md:px-12 md:py-32">
        {/* Back link */}
        <button
          onClick={() => router.push("/schedules")}
          className="mb-8 flex items-center gap-1.5 text-xs text-[#5F5D58] transition-colors hover:text-[#1A1A1A]"
        >
          <ArrowLeft size={14} weight="light" />
          <span>Back to schedules</span>
        </button>

        {/* Header */}
        <div className="animate-fade-up space-y-3">
          <EyebrowTag>Multi-Semester Planning</EyebrowTag>
          <h1
            className="text-4xl tracking-tight md:text-5xl"
            style={{ fontFamily: "var(--font-instrument-serif), serif" }}
          >
            4-Semester Roadmap
          </h1>
          <p className="text-sm text-[#5F5D58]">
            {plan.total_credits_planned} credits planned for {audit.name} across{" "}
            {plan.semester_plan.length} semesters
          </p>
        </div>

        {/* Agent badges */}
        <div className="mt-4 animate-fade-up delay-100">
          <AgentBadges
            agents={plan.agents_used}
            orchestrationMs={plan.orchestration_ms}
          />
        </div>

        {/* Graduation indicator */}
        <div
          className={`animate-fade-up delay-200 mt-8 inline-flex items-center gap-2 rounded-full px-4 py-2 ring-1 ${
            plan.graduation_on_track
              ? "bg-emerald-50/50 ring-emerald-200"
              : "bg-amber-50/50 ring-amber-200"
          }`}
        >
          {plan.graduation_on_track ? (
            <CheckCircle size={16} weight="light" className="text-emerald-600" />
          ) : (
            <Warning size={16} weight="light" className="text-amber-600" />
          )}
          <span
            className={`text-xs font-medium ${
              plan.graduation_on_track ? "text-emerald-700" : "text-amber-700"
            }`}
          >
            {plan.graduation_on_track
              ? "On track for graduation"
              : "Graduation timeline needs attention"}
          </span>
          <GraduationCap
            size={14}
            weight="light"
            className={plan.graduation_on_track ? "text-emerald-600" : "text-amber-600"}
          />
        </div>

        {/* Semester timeline */}
        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
          {plan.semester_plan.map((sem, i) => (
            <SemesterCard
              key={sem.semester}
              semester={sem.semester}
              courses={sem.courses}
              credits={sem.credits}
              notes={sem.notes}
              index={i}
            />
          ))}
        </div>

        {/* Prerequisite chains */}
        {hasChains && (
          <div className="animate-fade-up mt-16" style={{ animationDelay: "600ms" }}>
            <div className="space-y-3">
              <EyebrowTag>Prerequisite Chains</EyebrowTag>
              <h2
                className="text-2xl tracking-tight"
                style={{ fontFamily: "var(--font-instrument-serif), serif" }}
              >
                Course dependencies
              </h2>
              <p className="text-sm text-[#5F5D58]">
                These courses must be taken in sequence. Each arrow represents a prerequisite relationship.
              </p>
            </div>

            <div className="mt-6 space-y-4">
              {plan.prerequisite_analysis.chains.map((chain, i) => (
                <div
                  key={i}
                  className="rounded-[2rem] bg-black/[0.03] p-1.5 ring-1 ring-black/5"
                >
                  <div className="rounded-[calc(2rem-0.375rem)] bg-white px-5 py-4">
                    <PrerequisiteChain chain={chain} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Rotation analysis */}
        {hasRotation && (
          <div className="animate-fade-up mt-16" style={{ animationDelay: "700ms" }}>
            <div className="space-y-3">
              <EyebrowTag>Course Rotation</EyebrowTag>
              <h2
                className="text-2xl tracking-tight"
                style={{ fontFamily: "var(--font-instrument-serif), serif" }}
              >
                Semester availability
              </h2>
              <p className="text-sm text-[#5F5D58]">
                Some courses are only offered in specific semesters. Missing them could delay graduation.
              </p>
            </div>

            <div className="mt-6 rounded-[2rem] bg-black/[0.03] p-1.5 ring-1 ring-black/5">
              <div className="rounded-[calc(2rem-0.375rem)] bg-white p-5">
                <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
                  {/* Fall only */}
                  {plan.rotation_analysis.fall_only.length > 0 && (
                    <div className="space-y-2">
                      <span
                        className="text-[10px] font-medium uppercase tracking-[0.15em] text-[#5F5D58]"
                        style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                      >
                        Fall only
                      </span>
                      <div className="space-y-1.5">
                        {plan.rotation_analysis.fall_only.map((item) => (
                          <div key={item.id} className="flex items-baseline gap-2">
                            <span
                              className="text-xs font-medium text-[#1A1A1A]"
                              style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                            >
                              {item.course}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Spring only */}
                  {plan.rotation_analysis.spring_only.length > 0 && (
                    <div className="space-y-2">
                      <span
                        className="text-[10px] font-medium uppercase tracking-[0.15em] text-[#5F5D58]"
                        style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                      >
                        Spring only
                      </span>
                      <div className="space-y-1.5">
                        {plan.rotation_analysis.spring_only.map((item) => (
                          <div key={item.id} className="flex items-baseline gap-2">
                            <span
                              className="text-xs font-medium text-[#1A1A1A]"
                              style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                            >
                              {item.course}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Schedule critical */}
                  {plan.rotation_analysis.schedule_critical.length > 0 && (
                    <div className="space-y-2">
                      <span
                        className="text-[10px] font-medium uppercase tracking-[0.15em] text-amber-700"
                        style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                      >
                        Schedule critical
                      </span>
                      <div className="space-y-1.5">
                        {plan.rotation_analysis.schedule_critical.map((item) => (
                          <div key={item.id} className="space-y-0.5">
                            <span
                              className="text-xs font-medium text-[#1A1A1A]"
                              style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                            >
                              {item.course}
                            </span>
                            <p className="text-[10px] text-amber-700">
                              Must take {item.must_take}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="animate-fade-up mt-16 flex items-center justify-between" style={{ animationDelay: "800ms" }}>
          <PillButton variant="secondary" onClick={() => router.push("/schedules")}>
            Back to schedules
          </PillButton>
          <p
            className="text-[10px] text-[#5F5D58]"
            style={{ fontFamily: "var(--font-geist-mono), monospace" }}
          >
            Pathfinder by NovaWealth
          </p>
        </div>
      </section>
    </main>
  );
}
