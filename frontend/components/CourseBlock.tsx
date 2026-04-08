"use client";

import type { Section } from "@/lib/types";

const CATEGORY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  FIN: { bg: "bg-[#B8985A]/8", text: "text-[#8B6E2F]", border: "border-[#B8985A]/15" },
  ACG: { bg: "bg-blue-50/60", text: "text-blue-800/70", border: "border-blue-200/30" },
  GEN: { bg: "bg-emerald-50/60", text: "text-emerald-800/70", border: "border-emerald-200/30" },
  ISA: { bg: "bg-violet-50/60", text: "text-violet-800/70", border: "border-violet-200/30" },
  MKT: { bg: "bg-orange-50/60", text: "text-orange-800/70", border: "border-orange-200/30" },
  LGLS: { bg: "bg-rose-50/60", text: "text-rose-800/70", border: "border-rose-200/30" },
  SCI: { bg: "bg-teal-50/60", text: "text-teal-800/70", border: "border-teal-200/30" },
  LCS: { bg: "bg-amber-50/60", text: "text-amber-800/70", border: "border-amber-200/30" },
  BUS: { bg: "bg-slate-50/60", text: "text-slate-800/70", border: "border-slate-200/30" },
  COM: { bg: "bg-pink-50/60", text: "text-pink-800/70", border: "border-pink-200/30" },
};

const DEFAULT_COLOR = { bg: "bg-gray-50/60", text: "text-gray-800/70", border: "border-gray-200/30" };

interface CourseBlockProps {
  section: Section;
  dayIndex: number;
  startMinutes: number;
  endMinutes: number;
  calendarStartHour: number;
  pixelsPerMinute: number;
}

export function CourseBlock({
  section,
  dayIndex,
  startMinutes,
  endMinutes,
  calendarStartHour,
  pixelsPerMinute,
}: CourseBlockProps) {
  const colors = CATEGORY_COLORS[section.subject] || DEFAULT_COLOR;
  const top = (startMinutes - calendarStartHour * 60) * pixelsPerMinute;
  const height = (endMinutes - startMinutes) * pixelsPerMinute;

  const lastName = section.instructor?.split(",")[0] || "TBA";

  return (
    <div
      className={`absolute left-0.5 right-0.5 overflow-hidden rounded-lg border px-2 py-1.5 ${colors.bg} ${colors.border}`}
      style={{ top: `${top}px`, height: `${height}px` }}
    >
      <p
        className={`text-[10px] font-semibold leading-tight ${colors.text}`}
        style={{ fontFamily: "var(--font-geist-mono), monospace" }}
      >
        {section.course_code}
      </p>
      {height > 30 && (
        <p className={`mt-0.5 text-[9px] leading-tight ${colors.text} opacity-70`}>
          {lastName}
        </p>
      )}
    </div>
  );
}
