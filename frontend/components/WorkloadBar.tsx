"use client";

import { Lightning, Clock, Books } from "@phosphor-icons/react";
import type { WorkloadData } from "@/lib/types";

function getScoreColor(score: number): string {
  if (score <= 3) return "bg-emerald-500";
  if (score <= 5) return "bg-[#B8985A]";
  if (score <= 7) return "bg-orange-500";
  return "bg-red-500";
}

function getScoreLabel(score: number): string {
  if (score <= 3) return "Light";
  if (score <= 5) return "Moderate";
  if (score <= 7) return "Heavy";
  return "Very Heavy";
}

export function WorkloadBar({ data }: { data: WorkloadData }) {
  return (
    <div className="space-y-3">
      {/* Workload score bar */}
      <div className="flex items-center gap-3">
        <Lightning size={14} weight="light" className="text-[#787774]" />
        <div className="flex-1">
          <div className="mb-1 flex items-center justify-between">
            <span className="text-[10px] text-[#787774]">Workload</span>
            <span
              className="text-[10px] font-medium text-[#1A1A1A]"
              style={{ fontFamily: "var(--font-geist-mono), monospace" }}
            >
              {getScoreLabel(data.workload_score)}
            </span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-black/5">
            <div
              className={`h-1.5 rounded-full transition-all duration-700 ${getScoreColor(data.workload_score)}`}
              style={{
                width: `${data.workload_score * 10}%`,
                transitionTimingFunction: "cubic-bezier(0.32, 0.72, 0, 1)",
              }}
            />
          </div>
        </div>
      </div>

      {/* Hours breakdown */}
      <div
        className="flex gap-4 text-[10px] text-[#787774]"
        style={{ fontFamily: "var(--font-geist-mono), monospace" }}
      >
        <span className="flex items-center gap-1">
          <Clock size={10} weight="light" />
          {data.total_class_hours}h class
        </span>
        <span className="flex items-center gap-1">
          <Books size={10} weight="light" />
          {data.total_study_hours}h study
        </span>
        <span className="font-medium text-[#1A1A1A]">
          {data.total_weekly_hours}h/week
        </span>
      </div>

      {/* Warnings */}
      {data.warnings.length > 0 && (
        <div className="space-y-1">
          {data.warnings.map((w, i) => (
            <p key={i} className="text-[10px] text-orange-700">
              {w}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
