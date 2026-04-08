"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft, Warning } from "@phosphor-icons/react";
import { useStore } from "@/lib/store";
import { EyebrowTag } from "@/components/EyebrowTag";
import { ScheduleCard } from "@/components/ScheduleCard";
import { PillButton } from "@/components/PillButton";
import { WorkloadBar } from "@/components/WorkloadBar";
import { AgentBadges } from "@/components/AgentBadges";
import { NegotiationCard } from "@/components/NegotiationCard";
import { Skeleton } from "@/components/ui/skeleton";

export default function SchedulesPage() {
  const router = useRouter();
  const {
    schedules, solverStats, audit,
    professorData, workloadData, negotiation, agentsRun,
  } = useStore();

  if (!audit) {
    return (
      <main className="min-h-[100dvh]">
        <section className="mx-auto max-w-5xl px-6 py-24 md:px-12 md:py-32">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="mt-4 h-10 w-96" />
          <div className="mt-8">
            <PillButton variant="secondary" onClick={() => router.push("/")}>
              Start over
            </PillButton>
          </div>
        </section>
      </main>
    );
  }

  // Zero-result path with negotiation
  if (schedules && schedules.length === 0) {
    return (
      <main className="min-h-[100dvh]">
        <section className="mx-auto max-w-4xl px-6 py-24 md:px-12 md:py-32">
          <button
            onClick={() => router.push("/preferences")}
            className="mb-8 flex items-center gap-1.5 text-xs text-[#787774] transition-colors hover:text-[#1A1A1A]"
          >
            <ArrowLeft size={14} weight="light" />
            <span>Back to preferences</span>
          </button>

          <div className="animate-fade-up space-y-3">
            <EyebrowTag>Constraint Analysis</EyebrowTag>
            <h1
              className="text-4xl tracking-tight md:text-5xl"
              style={{ fontFamily: "var(--font-instrument-serif), serif" }}
            >
              No valid schedules found
            </h1>
            <p className="text-sm text-[#787774]">
              But the Negotiator Agent found tradeoffs that would work.
            </p>
          </div>

          {/* Agent badges */}
          {agentsRun.length > 0 && (
            <div className="mt-6 animate-fade-up delay-100">
              <AgentBadges
                agents={agentsRun}
                orchestrationMs={solverStats?.orchestration_ms}
              />
            </div>
          )}

          {/* Negotiation card */}
          {negotiation && (
            <div className="mt-8 animate-fade-up delay-200">
              <NegotiationCard data={negotiation} />
            </div>
          )}

          <div className="mt-8 animate-fade-up delay-300">
            <PillButton variant="secondary" onClick={() => router.push("/preferences")}>
              Adjust preferences
            </PillButton>
          </div>
        </section>
      </main>
    );
  }

  if (!schedules) {
    return (
      <main className="min-h-[100dvh]">
        <section className="mx-auto max-w-5xl px-6 py-24 md:px-12 md:py-32">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="mt-4 h-10 w-96" />
          <div className="mt-8">
            <PillButton variant="secondary" onClick={() => router.push("/")}>
              Start over
            </PillButton>
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

        {/* Agent pipeline badges */}
        {agentsRun.length > 0 && (
          <div className="mt-4 animate-fade-up delay-100">
            <AgentBadges
              agents={agentsRun}
              orchestrationMs={solverStats?.orchestration_ms}
            />
          </div>
        )}

        {/* Schedule cards with enrichment data */}
        <div className="mt-12 space-y-8">
          {schedules.map((schedule, i) => {
            const profData = professorData?.[i];
            const workData = workloadData?.[i];

            return (
              <div
                key={schedule.rank}
                className="animate-fade-up"
                style={{ animationDelay: `${(i + 1) * 100}ms` }}
              >
                <ScheduleCard schedule={schedule}>
                  {/* Workload bar */}
                  {workData && (
                    <div className="mt-4 border-t border-black/5 pt-4">
                      <WorkloadBar data={workData} />
                    </div>
                  )}

                  {/* Professor recommendations & warnings */}
                  {profData && (profData.recommendations.length > 0 || profData.warnings.length > 0) && (
                    <div className="mt-3 space-y-1.5">
                      {profData.recommendations.map((rec, j) => (
                        <p key={`rec-${j}`} className="text-[10px] text-emerald-700">
                          {rec}
                        </p>
                      ))}
                      {profData.warnings.map((warn, j) => (
                        <p key={`warn-${j}`} className="text-[10px] text-orange-700">
                          {warn}
                        </p>
                      ))}
                    </div>
                  )}
                </ScheduleCard>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="animate-fade-up delay-500 mt-12 flex flex-wrap items-center gap-3">
          <PillButton variant="secondary" onClick={() => router.push("/preferences")}>
            Try different preferences
          </PillButton>
          <PillButton onClick={() => router.push("/planner")}>
            View 4-semester plan
          </PillButton>
          <p
            className="ml-auto text-[10px] text-[#787774]"
            style={{ fontFamily: "var(--font-geist-mono), monospace" }}
          >
            Pathfinder by NovaWealth
          </p>
        </div>
      </section>
    </main>
  );
}
