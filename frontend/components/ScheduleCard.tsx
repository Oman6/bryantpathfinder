"use client";

import { useState, useEffect } from "react";
import { Copy, Check, PencilSimple, ArrowsLeftRight, CalendarPlus, PushPin, PushPinSlash, Warning } from "@phosphor-icons/react";
import type { ScheduleOption, Section } from "@/lib/types";
import { useStore } from "@/lib/store";
import { to12h } from "@/lib/utils";
import { downloadIcs } from "@/lib/ics";
import { WeeklyCalendar } from "./WeeklyCalendar";
import { ProfessorTooltip } from "./ProfessorTooltip";
import { SectionSwap } from "./SectionSwap";
import { PillButton } from "./PillButton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

const DAY_MAP: Record<string, string> = {
  M: "Mon",
  T: "Tue",
  W: "Wed",
  R: "Thu",
  F: "Fri",
};

interface ScheduleCardProps {
  schedule: ScheduleOption;
  className?: string;
  children?: React.ReactNode;
}

function seatUrgency(section: Section): { label: string; tone: "red" | "amber" } | null {
  if (section.seats_open <= 0) return { label: "Waitlist", tone: "red" };
  if (section.seats_open <= 3) return { label: `${section.seats_open} left`, tone: "red" };
  if (section.seats_total > 0 && section.seats_open / section.seats_total < 0.2) {
    return { label: `${section.seats_open} left`, tone: "amber" };
  }
  return null;
}

export function ScheduleCard({ schedule, className = "", children }: ScheduleCardProps) {
  const { professorRatings, gradeDistributions, pinnedCrns, togglePinnedCrn } = useStore();
  const [crnDialogOpen, setCrnDialogOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [editing, setEditing] = useState(false);
  const [swappingSection, setSwappingSection] = useState<Section | null>(null);
  const [localSections, setLocalSections] = useState(schedule.sections);

  useEffect(() => {
    setLocalSections(schedule.sections);
  }, [schedule.sections]);

  const handleSwap = (newSection: Section) => {
    setLocalSections((prev) =>
      prev.map((s) => (s.crn === swappingSection?.crn ? newSection : s))
    );
    setSwappingSection(null);
  };

  const displaySections = editing ? localSections : schedule.sections;

  const crns = displaySections.map((s) => s.crn).join(", ");

  // Predicted schedule GPA: credit-weighted avg of per-course avg_gpa when data exists.
  const gpaData = displaySections
    .map((s) => {
      const d = gradeDistributions[s.course_code];
      return d ? { credits: s.credits, gpa: d.avg_gpa } : null;
    })
    .filter((x): x is { credits: number; gpa: number } => x !== null);
  const totalGpaCredits = gpaData.reduce((sum, x) => sum + x.credits, 0);
  const predictedGpa =
    totalGpaCredits > 0
      ? gpaData.reduce((sum, x) => sum + x.credits * x.gpa, 0) / totalGpaCredits
      : null;
  const gpaCoverage = totalGpaCredits / displaySections.reduce((sum, s) => sum + s.credits, 0);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(crns);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <>
      {/* Double-bezel card */}
      <div className={`rounded-[2rem] bg-black/[0.03] p-1.5 ring-1 ring-black/5 ${className}`}>
        <div className="rounded-[calc(2rem-0.375rem)] bg-white p-6">
          {/* Rank badge */}
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span
                className="flex h-8 w-8 items-center justify-center rounded-full bg-[#1A1A1A] text-xs font-semibold text-white"
                style={{ fontFamily: "var(--font-geist-mono), monospace" }}
              >
                {schedule.rank}
              </span>
              <span className="text-sm font-medium text-[#1A1A1A]">
                {schedule.rank === 1 ? "Top pick" : schedule.rank === 2 ? "Alternative" : "Option"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span
                className="text-xs text-[#5F5D58]"
                style={{ fontFamily: "var(--font-geist-mono), monospace" }}
              >
                {editing
                  ? `${localSections.reduce((s, sec) => s + sec.credits, 0)} credits`
                  : `${schedule.total_credits} credits`}
              </span>
              <button
                onClick={() => setEditing(!editing)}
                className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] transition-colors ${
                  editing
                    ? "bg-[#B8985A] text-white"
                    : "bg-black/[0.04] text-[#5F5D58] hover:text-[#1A1A1A]"
                }`}
                style={{ fontFamily: "var(--font-geist-mono), monospace" }}
              >
                <PencilSimple size={9} weight="light" />
                {editing ? "Editing" : "Edit"}
              </button>
            </div>
          </div>

          {/* Weekly calendar */}
          <WeeklyCalendar sections={displaySections} />

          {/* Course list */}
          <div className="mt-4 space-y-1.5">
            {displaySections.map((section) => {
              const meetingStr = section.meetings
                .map(
                  (m) =>
                    `${m.days.join("")} ${to12h(m.start)}\u2013${to12h(m.end)}`
                )
                .join(", ");
              const urgency = seatUrgency(section);
              const pinned = pinnedCrns.includes(section.crn);
              return (
                <div
                  key={section.crn}
                  className={`flex items-baseline justify-between gap-2 py-1 ${
                    editing
                      ? "cursor-pointer rounded-lg px-2 -mx-2 transition-colors hover:bg-[#FAFAF7]"
                      : ""
                  }`}
                  onClick={editing ? () => setSwappingSection(section) : undefined}
                >
                  <div className="flex items-baseline gap-2">
                    <span
                      className="text-xs font-medium text-[#1A1A1A]"
                      style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                    >
                      {section.course_code}
                    </span>
                    <ProfessorTooltip
                      name={section.instructor || "TBA"}
                      rating={section.instructor ? professorRatings[section.instructor] : undefined}
                      className="text-xs text-[#5F5D58]"
                    />
                    {editing && (
                      <ArrowsLeftRight size={10} weight="light" className="text-[#B8985A]" />
                    )}
                    {urgency && (
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[9px] font-medium ${
                          urgency.tone === "red"
                            ? "bg-red-50 text-red-700"
                            : "bg-amber-50 text-amber-700"
                        }`}
                      >
                        <Warning size={9} weight="fill" />
                        {urgency.label}
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        togglePinnedCrn(section.crn);
                      }}
                      aria-label={pinned ? `Unpin ${section.course_code}` : `Pin ${section.course_code}`}
                      title={pinned ? "Unpin section" : "Pin section (lock for re-solve)"}
                      className={`rounded p-0.5 transition-colors ${
                        pinned ? "text-[#B8985A]" : "text-[#5F5D58]/40 hover:text-[#5F5D58]"
                      }`}
                    >
                      {pinned ? (
                        <PushPin size={10} weight="fill" />
                      ) : (
                        <PushPinSlash size={10} weight="light" />
                      )}
                    </button>
                  </div>
                  <div className="flex items-baseline gap-3">
                    <span
                      className="text-[10px] text-[#5F5D58]"
                      style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                    >
                      {meetingStr}
                    </span>
                    <span
                      className="text-[10px] text-[#5F5D58]"
                      style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                    >
                      {section.seats_open}/{section.seats_total}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Explanation */}
          {schedule.explanation && schedule.explanation !== "Schedule explanation unavailable." && (
            <p
              className="mt-4 text-sm italic leading-relaxed text-[#5F5D58]"
              style={{ fontFamily: "var(--font-instrument-serif), serif" }}
            >
              {schedule.explanation}
            </p>
          )}

          {/* Stats row */}
          <div
            className="mt-4 flex flex-wrap gap-x-5 gap-y-1 border-t border-black/5 pt-3 text-[10px] text-[#5F5D58]"
            style={{ fontFamily: "var(--font-geist-mono), monospace" }}
          >
            <span>{schedule.total_credits} credits</span>
            <span>
              {schedule.days_off.length > 0
                ? `${schedule.days_off.map((d) => DAY_MAP[d] || d).join(", ")} off`
                : "No days off"}
            </span>
            <span>{to12h(schedule.earliest_class)}\u2013{to12h(schedule.latest_class)}</span>
            {predictedGpa !== null && gpaCoverage >= 0.5 && (
              <span title={`Based on ${Math.round(gpaCoverage * 100)}% of credits with grade data`}>
                ~{predictedGpa.toFixed(2)} GPA
              </span>
            )}
          </div>

          {/* Agent enrichment data */}
          {children}

          {/* CTA */}
          <div className="mt-5 flex flex-wrap items-center gap-2">
            <PillButton onClick={() => setCrnDialogOpen(true)}>
              Use this schedule
            </PillButton>
            <button
              type="button"
              onClick={() =>
                downloadIcs({
                  ...schedule,
                  sections: displaySections,
                })
              }
              className="inline-flex items-center gap-1.5 rounded-full border border-black/10 bg-white px-4 py-2.5 text-xs font-medium text-[#1A1A1A] transition-colors hover:bg-[#FAFAF7]"
              title="Download .ics for Google Calendar / Apple Calendar / Outlook"
            >
              <CalendarPlus size={13} weight="light" />
              Add to calendar
            </button>
          </div>
        </div>
      </div>

      {/* CRN Dialog */}
      <Dialog open={crnDialogOpen} onOpenChange={setCrnDialogOpen}>
        <DialogContent className="rounded-2xl border-black/5 bg-white sm:max-w-md">
          <DialogHeader>
            <DialogTitle
              className="text-lg"
              style={{ fontFamily: "var(--font-instrument-serif), serif" }}
            >
              Your CRNs
            </DialogTitle>
            <DialogDescription className="text-xs text-[#5F5D58]">
              Copy these into Banner Self-Service to register.
            </DialogDescription>
          </DialogHeader>

          <div className="mt-2 space-y-3">
            {displaySections.map((s) => (
              <div
                key={s.crn}
                className="flex items-center justify-between rounded-lg bg-[#FAFAF7] px-4 py-2.5"
              >
                <span
                  className="text-sm font-medium"
                  style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                >
                  {s.crn}
                </span>
                <span className="text-xs text-[#5F5D58]">{s.course_code}</span>
              </div>
            ))}
          </div>

          <button
            onClick={handleCopy}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-full bg-[#1A1A1A] py-3 text-sm font-medium text-white transition-colors hover:bg-[#2a2a2a]"
          >
            {copied ? (
              <>
                <Check size={16} weight="light" />
                <span>Copied</span>
              </>
            ) : (
              <>
                <Copy size={16} weight="light" />
                <span>Copy all CRNs</span>
              </>
            )}
          </button>

          <button
            onClick={() => setCrnDialogOpen(false)}
            className="mt-2 flex w-full items-center justify-center rounded-full py-2.5 text-xs text-[#5F5D58] transition-colors hover:text-[#1A1A1A]"
          >
            Done
          </button>
        </DialogContent>
      </Dialog>

      {/* Section swap modal */}
      {swappingSection && (
        <SectionSwap
          currentSection={swappingSection}
          otherSections={localSections.filter((s) => s.crn !== swappingSection.crn)}
          onSwap={handleSwap}
          onClose={() => setSwappingSection(null)}
        />
      )}
    </>
  );
}
