"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft, Warning } from "@phosphor-icons/react";
import { useStore } from "@/lib/store";
import { EyebrowTag } from "@/components/EyebrowTag";
import { ScheduleCard } from "@/components/ScheduleCard";
import { PillButton } from "@/components/PillButton";
import { Skeleton } from "@/components/ui/skeleton";

export default function SchedulesPage() {
  const router = useRouter();
  const { schedules, solverStats, audit } = useStore();

  if (!schedules || !audit) {
    return (
      <main className="min-h-[100dvh]">
        <section className="mx-auto max-w-5xl px-6 py-24 md:px-12 md:py-32">
          <div className="space-y-4">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-10 w-96" />
            <Skeleton className="h-4 w-64" />
          </div>
          <div className="mt-12 space-y-8">
            <Skeleton className="h-96 w-full rounded-[2rem]" />
            <Skeleton className="h-96 w-full rounded-[2rem]" />
          </div>

          <div className="mt-8">
            <PillButton variant="secondary" onClick={() => router.push("/")}>
              Start over
            </PillButton>
          </div>
        </section>
      </main>
    );
  }

  if (schedules.length === 0) {
    return (
      <main className="min-h-[100dvh]">
        <section className="mx-auto max-w-3xl px-6 py-24 md:px-12 md:py-32">
          <button
            onClick={() => router.push("/preferences")}
            className="mb-8 flex items-center gap-1.5 text-xs text-[#787774] transition-colors hover:text-[#1A1A1A]"
          >
            <ArrowLeft size={14} weight="light" />
            <span>Back to preferences</span>
          </button>

          <div className="rounded-[2rem] bg-black/[0.03] p-1.5 ring-1 ring-black/5">
            <div className="flex flex-col items-center gap-4 rounded-[calc(2rem-0.375rem)] bg-white p-12 text-center">
              <Warning size={32} weight="light" className="text-[#787774]" />
              <h2
                className="text-2xl tracking-tight"
                style={{ fontFamily: "var(--font-instrument-serif), serif" }}
              >
                No valid schedules found
              </h2>
              <p className="max-w-md text-sm text-[#787774]">
                Your preferences are too restrictive. Try removing a blocked
                day, expanding your time window, or selecting fewer
                requirements.
              </p>
              <PillButton variant="secondary" onClick={() => router.push("/preferences")}>
                Adjust preferences
              </PillButton>
            </div>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-[100dvh]">
      <section className="mx-auto max-w-5xl px-6 py-24 md:px-12 md:py-32">
        {/* Back link */}
        <button
          onClick={() => router.push("/preferences")}
          className="mb-8 flex items-center gap-1.5 text-xs text-[#787774] transition-colors hover:text-[#1A1A1A]"
        >
          <ArrowLeft size={14} weight="light" />
          <span>Back to preferences</span>
        </button>

        {/* Header */}
        <div className="animate-fade-up space-y-3">
          <EyebrowTag>Step 3 of 3</EyebrowTag>
          <h1
            className="text-4xl tracking-tight md:text-5xl"
            style={{ fontFamily: "var(--font-instrument-serif), serif" }}
          >
            Your schedules
          </h1>
          <p className="text-sm text-[#787774]">
            {schedules.length} options for {audit.name} &middot; Fall 2026
            {solverStats && (
              <span
                className="ml-2"
                style={{ fontFamily: "var(--font-geist-mono), monospace" }}
              >
                ({solverStats.solver_duration_ms}ms)
              </span>
            )}
          </p>
        </div>

        {/* Schedule cards — staggered reveal */}
        <div className="mt-12 space-y-8">
          {schedules.map((schedule, i) => (
            <div
              key={schedule.rank}
              className="animate-fade-up"
              style={{ animationDelay: `${(i + 1) * 100}ms` }}
            >
              <ScheduleCard schedule={schedule} />
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="animate-fade-up delay-500 mt-12 flex items-center justify-between">
          <PillButton variant="secondary" onClick={() => router.push("/preferences")}>
            Try different preferences
          </PillButton>
          <p
            className="text-[10px] text-[#787774]"
            style={{ fontFamily: "var(--font-geist-mono), monospace" }}
          >
            Pathfinder by NovaWealth
          </p>
        </div>
      </section>
    </main>
  );
}
