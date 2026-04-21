"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowsLeftRight, Check, Warning, Star } from "@phosphor-icons/react";
import { getAlternateSections } from "@/lib/api";
import { useStore } from "@/lib/store";
import { to12h } from "@/lib/utils";
import type { Section } from "@/lib/types";

function timeToMinutes(t: string): number {
  const [h, m] = t.split(":").map(Number);
  return h * 60 + m;
}

function sectionsConflict(a: Section, b: Section): boolean {
  for (const ma of a.meetings) {
    for (const mb of b.meetings) {
      const shared = ma.days.filter((d) => mb.days.includes(d));
      if (shared.length === 0) continue;
      const aStart = timeToMinutes(ma.start);
      const aEnd = timeToMinutes(ma.end);
      const bStart = timeToMinutes(mb.start);
      const bEnd = timeToMinutes(mb.end);
      if (aStart < bEnd && bStart < aEnd) return true;
    }
  }
  return false;
}

interface SectionSwapProps {
  currentSection: Section;
  otherSections: Section[];
  onSwap: (newSection: Section) => void;
  onClose: () => void;
}

export function SectionSwap({ currentSection, otherSections, onSwap, onClose }: SectionSwapProps) {
  const { professorRatings } = useStore();
  const [alternatives, setAlternatives] = useState<Section[]>([]);
  const [loading, setLoading] = useState(true);
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    getAlternateSections(currentSection.course_code)
      .then((sections) => {
        const filtered = sections.filter((s) => s.crn !== currentSection.crn);
        setAlternatives(filtered);
      })
      .catch(() => setAlternatives([]))
      .finally(() => setLoading(false));
  }, [currentSection.course_code, currentSection.crn]);

  // Focus management + keyboard handlers
  useEffect(() => {
    previouslyFocusedRef.current = document.activeElement as HTMLElement | null;
    closeBtnRef.current?.focus();

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key === "Tab" && dialogRef.current) {
        const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input, [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", handleKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.body.style.overflow = prevOverflow;
      previouslyFocusedRef.current?.focus();
    };
  }, [onClose]);

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/10 backdrop-blur-[2px]" onClick={onClose} />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="section-swap-title"
        className="fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-black/5 bg-white p-6 shadow-[0_25px_50px_-12px_rgba(0,0,0,0.08)]">
        {/* Header */}
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#FAFAF7]">
            <ArrowsLeftRight size={16} weight="light" className="text-[#5F5D58]" />
          </div>
          <div>
            <h3
              id="section-swap-title"
              className="text-base font-medium"
              style={{ fontFamily: "var(--font-instrument-serif), serif" }}
            >
              Swap {currentSection.course_code}
            </h3>
            <p className="text-[10px] text-[#5F5D58]">
              Currently: sec {currentSection.section} with {currentSection.instructor || "TBA"}
            </p>
          </div>
        </div>

        {/* Alternatives list */}
        {loading ? (
          <div className="py-8 text-center text-xs text-[#5F5D58]">Loading sections...</div>
        ) : alternatives.length === 0 ? (
          <div className="py-8 text-center text-xs text-[#5F5D58]">No other sections available.</div>
        ) : (
          <div className="max-h-80 space-y-2 overflow-y-auto">
            {alternatives.map((alt) => {
              const hasConflict = otherSections.some((other) => sectionsConflict(alt, other));
              const rating = alt.instructor ? professorRatings[alt.instructor] : undefined;
              const meetingStr = alt.meetings
                .map((m) => `${m.days.join("")} ${to12h(m.start)}\u2013${to12h(m.end)}`)
                .join(", ");

              return (
                <button
                  key={alt.crn}
                  onClick={() => {
                    if (!hasConflict && !alt.is_full) onSwap(alt);
                  }}
                  disabled={hasConflict || alt.is_full}
                  className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left transition-colors ${
                    hasConflict || alt.is_full
                      ? "cursor-not-allowed opacity-50"
                      : "hover:bg-[#FAFAF7]"
                  }`}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span
                        className="text-xs font-medium text-[#1A1A1A]"
                        style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                      >
                        Sec {alt.section}
                      </span>
                      <span className="text-xs text-[#5F5D58]">
                        {alt.instructor || "TBA"}
                      </span>
                      {rating && (
                        <span className="flex items-center gap-0.5 text-[10px] text-[#5F5D58]">
                          <Star size={9} weight="fill" className={rating.quality >= 4 ? "text-emerald-600" : rating.quality >= 3 ? "text-amber-600" : "text-red-600"} />
                          {rating.quality.toFixed(1)}
                        </span>
                      )}
                    </div>
                    <div className="mt-0.5 flex items-center gap-3">
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
                        {alt.seats_open}/{alt.seats_total} seats
                      </span>
                    </div>
                  </div>

                  {/* Status */}
                  <div className="flex-shrink-0">
                    {hasConflict && (
                      <span className="flex items-center gap-1 text-[10px] text-orange-600">
                        <Warning size={10} weight="light" />
                        Conflict
                      </span>
                    )}
                    {alt.is_full && (
                      <span className="text-[10px] text-red-600">Full</span>
                    )}
                    {!hasConflict && !alt.is_full && (
                      <Check size={14} weight="light" className="text-emerald-600" />
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {/* Close */}
        <button
          ref={closeBtnRef}
          onClick={onClose}
          className="mt-4 flex w-full items-center justify-center rounded-full py-2.5 text-xs text-[#5F5D58] transition-colors hover:text-[#1A1A1A]"
        >
          Cancel
        </button>
      </div>
    </>
  );
}
