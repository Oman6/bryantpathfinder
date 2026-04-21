"use client";

import { useState } from "react";
import { CaretDown, CaretUp } from "@phosphor-icons/react";
import type {
  GradeDistributions,
  ProfessorMatchData,
  ScheduleOption,
  WorkloadData,
} from "@/lib/types";
import { useStore } from "@/lib/store";
import { to12h } from "@/lib/utils";

const DAY_MAP: Record<string, string> = { M: "M", T: "T", W: "W", R: "R", F: "F" };

interface ScheduleComparisonProps {
  schedules: ScheduleOption[];
  workloadData: WorkloadData[] | null;
  professorData: ProfessorMatchData[] | null;
}

function predictedGpa(
  sections: ScheduleOption["sections"],
  gradeDistributions: GradeDistributions,
): number | null {
  const data = sections
    .map((s) => {
      const d = gradeDistributions[s.course_code];
      return d ? { c: s.credits, g: d.avg_gpa } : null;
    })
    .filter((x): x is { c: number; g: number } => x !== null);
  const total = data.reduce((sum, x) => sum + x.c, 0);
  if (total === 0) return null;
  return data.reduce((sum, x) => sum + x.c * x.g, 0) / total;
}

export function ScheduleComparison({ schedules, workloadData, professorData }: ScheduleComparisonProps) {
  const { gradeDistributions } = useStore();
  const [open, setOpen] = useState(false);

  if (schedules.length < 2) return null;

  return (
    <div className="rounded-2xl border border-black/5 bg-white">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-6 py-4 text-left"
        aria-expanded={open}
      >
        <div>
          <h3
            className="text-sm font-medium text-[#1A1A1A]"
            style={{ fontFamily: "var(--font-instrument-serif), serif" }}
          >
            Compare all {schedules.length} schedules
          </h3>
          <p className="text-[10px] text-[#5F5D58]">Side-by-side credits, hours, GPA, and professor match</p>
        </div>
        {open ? <CaretUp size={14} weight="light" /> : <CaretDown size={14} weight="light" />}
      </button>

      {open && (
        <div className="border-t border-black/5 p-6">
          <div className="overflow-x-auto">
            <table
              className="w-full text-xs"
              style={{ fontFamily: "var(--font-geist-mono), monospace" }}
            >
              <thead>
                <tr className="border-b border-black/5 text-left text-[10px] uppercase tracking-wide text-[#5F5D58]">
                  <th className="py-2 pr-4 font-normal">Metric</th>
                  {schedules.map((s) => (
                    <th key={s.rank} className="py-2 pr-4 font-normal">
                      #{s.rank}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="text-[#1A1A1A]">
                <tr className="border-b border-black/[0.03]">
                  <td className="py-2 pr-4 text-[#5F5D58]">Credits</td>
                  {schedules.map((s) => (
                    <td key={s.rank} className="py-2 pr-4">
                      {s.total_credits}
                    </td>
                  ))}
                </tr>
                <tr className="border-b border-black/[0.03]">
                  <td className="py-2 pr-4 text-[#5F5D58]">Days off</td>
                  {schedules.map((s) => (
                    <td key={s.rank} className="py-2 pr-4">
                      {s.days_off.length > 0
                        ? s.days_off.map((d) => DAY_MAP[d] || d).join(",")
                        : "—"}
                    </td>
                  ))}
                </tr>
                <tr className="border-b border-black/[0.03]">
                  <td className="py-2 pr-4 text-[#5F5D58]">Hours</td>
                  {schedules.map((s) => (
                    <td key={s.rank} className="py-2 pr-4">
                      {to12h(s.earliest_class)}–{to12h(s.latest_class)}
                    </td>
                  ))}
                </tr>
                <tr className="border-b border-black/[0.03]">
                  <td className="py-2 pr-4 text-[#5F5D58]">Weekly workload</td>
                  {schedules.map((s, i) => (
                    <td key={s.rank} className="py-2 pr-4">
                      {workloadData?.[i]?.total_weekly_hours.toFixed(0) ?? "—"} hrs
                    </td>
                  ))}
                </tr>
                <tr className="border-b border-black/[0.03]">
                  <td className="py-2 pr-4 text-[#5F5D58]">Predicted GPA</td>
                  {schedules.map((s) => {
                    const gpa = predictedGpa(s.sections, gradeDistributions);
                    return (
                      <td key={s.rank} className="py-2 pr-4">
                        {gpa !== null ? `~${gpa.toFixed(2)}` : "—"}
                      </td>
                    );
                  })}
                </tr>
                <tr className="border-b border-black/[0.03]">
                  <td className="py-2 pr-4 text-[#5F5D58]">Professor match</td>
                  {schedules.map((s, i) => (
                    <td key={s.rank} className="py-2 pr-4">
                      {professorData?.[i] ? `${professorData[i].avg_professor_score}` : "—"}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="py-2 pr-4 text-[#5F5D58]">Solver score</td>
                  {schedules.map((s) => (
                    <td key={s.rank} className="py-2 pr-4">
                      {s.score.toFixed(1)}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
