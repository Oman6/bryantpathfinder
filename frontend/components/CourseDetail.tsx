"use client";

import { Info, ChartBar, Calendar, BookOpen } from "@phosphor-icons/react";
import type { CourseMetadata } from "@/lib/types";
import { useStore } from "@/lib/store";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface CourseDetailProps {
  courseCode: string;
  open: boolean;
  onClose: () => void;
}

function rotationLabel(meta: CourseMetadata): string {
  if (meta.when_offered) return meta.when_offered;
  if (meta.terms_offered >= 9) return "Every term";
  if (meta.terms_offered >= 6) return "Most terms";
  if (meta.terms_offered >= 3) return "Sometimes";
  if (meta.terms_offered > 0) return "Rarely";
  return "Not offered recently";
}

export function CourseDetail({ courseCode, open, onClose }: CourseDetailProps) {
  const { courseMetadata } = useStore();
  const meta = courseMetadata[courseCode];

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="rounded-2xl border-black/5 bg-white sm:max-w-lg">
        <DialogHeader>
          <DialogTitle
            className="text-xl"
            style={{ fontFamily: "var(--font-instrument-serif), serif" }}
          >
            <span
              className="text-base text-[#5F5D58]"
              style={{ fontFamily: "var(--font-geist-mono), monospace" }}
            >
              {courseCode}
            </span>
            {meta?.title ? <> · {meta.title}</> : null}
          </DialogTitle>
        </DialogHeader>

        {!meta ? (
          <div className="mt-4 rounded-lg bg-[#FAFAF7] p-4">
            <p className="text-xs text-[#5F5D58]">
              No catalog metadata available for {courseCode}.
            </p>
          </div>
        ) : (
          <div className="mt-2 space-y-4 text-sm text-[#1A1A1A]">
            {meta.description && (
              <section>
                <div className="mb-1.5 flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-[#5F5D58]">
                  <BookOpen size={11} weight="light" />
                  <span style={{ fontFamily: "var(--font-geist-mono), monospace" }}>
                    Catalog description
                  </span>
                </div>
                <p className="text-xs leading-relaxed text-[#1A1A1A]">{meta.description}</p>
              </section>
            )}

            <div className="grid grid-cols-2 gap-3 border-t border-black/5 pt-3 text-xs">
              {meta.prerequisites && (
                <div>
                  <div
                    className="text-[9px] uppercase tracking-wide text-[#5F5D58]"
                    style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                  >
                    Prerequisites
                  </div>
                  <div className="mt-0.5 text-[#1A1A1A]">{meta.prerequisites}</div>
                </div>
              )}
              {meta.corequisites && (
                <div>
                  <div
                    className="text-[9px] uppercase tracking-wide text-[#5F5D58]"
                    style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                  >
                    Corequisites
                  </div>
                  <div className="mt-0.5 text-[#1A1A1A]">{meta.corequisites}</div>
                </div>
              )}
              <div>
                <div
                  className="text-[9px] uppercase tracking-wide text-[#5F5D58]"
                  style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                >
                  <Calendar size={9} weight="light" className="inline mr-1" />
                  Rotation
                </div>
                <div className="mt-0.5 text-[#1A1A1A]">
                  {rotationLabel(meta)}{" "}
                  <span className="text-[#5F5D58]">
                    ({meta.terms_offered}/10 recent terms)
                  </span>
                </div>
              </div>
              <div>
                <div
                  className="text-[9px] uppercase tracking-wide text-[#5F5D58]"
                  style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                >
                  <ChartBar size={9} weight="light" className="inline mr-1" />
                  Sections offered
                </div>
                <div className="mt-0.5 text-[#1A1A1A]">
                  {meta.total_sections} across recent terms
                </div>
              </div>
              {meta.credits != null && (
                <div>
                  <div
                    className="text-[9px] uppercase tracking-wide text-[#5F5D58]"
                    style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                  >
                    Credits
                  </div>
                  <div className="mt-0.5 text-[#1A1A1A]">{meta.credits}</div>
                </div>
              )}
              {meta.cross_listed && (
                <div>
                  <div
                    className="text-[9px] uppercase tracking-wide text-[#5F5D58]"
                    style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                  >
                    Cross-listed
                  </div>
                  <div className="mt-0.5 text-[#1A1A1A]">{meta.cross_listed}</div>
                </div>
              )}
            </div>

            {meta.unique_instructors && meta.unique_instructors.length > 0 && (
              <section className="border-t border-black/5 pt-3">
                <div
                  className="mb-1.5 text-[10px] uppercase tracking-wide text-[#5F5D58]"
                  style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                >
                  Recently taught by
                </div>
                <div className="flex flex-wrap gap-1">
                  {meta.unique_instructors.slice(0, 8).map((name) => (
                    <span
                      key={name}
                      className="rounded-full bg-[#FAFAF7] px-2 py-0.5 text-[10px] text-[#1A1A1A]"
                    >
                      {name}
                    </span>
                  ))}
                </div>
              </section>
            )}

            {!meta.in_active_catalog && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-[11px] text-amber-900">
                <Info size={11} weight="light" className="mr-1 inline" />
                Not in the current undergraduate catalog. May be a graduate-level
                or discontinued course that still appears in Banner.
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
