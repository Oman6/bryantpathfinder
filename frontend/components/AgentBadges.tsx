"use client";

import { useState } from "react";
import {
  Robot,
  Lightning,
  MagnifyingGlass,
  ChalkboardTeacher,
  Scales,
  ChatText,
  TreeStructure,
  ArrowsClockwise,
  ListNumbers,
} from "@phosphor-icons/react";

const AGENT_INFO: Record<string, {
  label: string;
  description: string;
  icon: typeof Robot;
  color: string;
}> = {
  solver: {
    label: "Constraint Solver",
    description: "Pure Python engine that generates every valid combination of sections, checks pairwise time conflicts using half-open intervals, and scores each schedule on credit match, instructor preferences, seat availability, and category balance. No LLM in the loop — deterministic correctness guaranteed.",
    icon: MagnifyingGlass,
    color: "text-blue-700 bg-blue-50",
  },
  professor_match: {
    label: "Professor Match",
    description: "Analyzes real Rate My Professor data (quality, difficulty, would-take-again %) for every instructor in your schedule. Flags low-rated professors, highlights strong matches, and scores each schedule on overall professor quality. Runs in parallel with the Workload Analyzer.",
    icon: ChalkboardTeacher,
    color: "text-emerald-700 bg-emerald-50",
  },
  workload: {
    label: "Workload Analyzer",
    description: "Estimates your total weekly hours (class time + study time) using credit hours scaled by RMP difficulty ratings. Flags heavy days with 3+ back-to-back classes, warns if total workload exceeds 45 hours/week, and produces a 1-10 workload score per schedule.",
    icon: Scales,
    color: "text-orange-700 bg-orange-50",
  },
  explainer: {
    label: "Schedule Explainer",
    description: "Calls Claude to write a two-sentence natural language explanation for each schedule. Names the professors, mentions days off, and calls out which requirement categories get knocked out. Temperature 0.3 for slight phrasing variation across schedules.",
    icon: ChatText,
    color: "text-violet-700 bg-violet-50",
  },
  negotiator: {
    label: "Conflict Negotiator",
    description: "Activates when no valid schedules exist. Analyzes which constraint is the bottleneck, tests removing each one independently, and proposes specific tradeoffs: 'Remove Friday block to unlock 49 more sections' or 'Drop ACG 204 to keep Fridays free.'",
    icon: ArrowsClockwise,
    color: "text-red-700 bg-red-50",
  },
  prerequisite: {
    label: "Prerequisite Agent",
    description: "Builds a dependency graph of course prerequisites. Identifies which requirements are ready to take now (prerequisites met) and which are blocked. Maps chains like FIN 201 → FIN 310 → FIN 312.",
    icon: TreeStructure,
    color: "text-teal-700 bg-teal-50",
  },
  rotation: {
    label: "Rotation Agent",
    description: "Determines which courses are Fall-only, Spring-only, or offered both semesters. Flags schedule-critical courses that must be taken in a specific semester to stay on track for graduation.",
    icon: ArrowsClockwise,
    color: "text-amber-700 bg-amber-50",
  },
  sequencing: {
    label: "Sequencing Agent",
    description: "Consumes the prerequisite graph and rotation data to produce an optimal 4-semester graduation roadmap. Prioritizes schedule-critical and major courses, respects prerequisite chains, and balances credit load across semesters.",
    icon: ListNumbers,
    color: "text-indigo-700 bg-indigo-50",
  },
};

function AgentPopover({ agentKey, onClose }: { agentKey: string; onClose: () => void }) {
  const info = AGENT_INFO[agentKey];
  if (!info) return null;

  const Icon = info.icon;
  const [colorText, colorBg] = info.color.split(" ");

  return (
    <>
      <div className="fixed inset-0 z-[60]" onClick={onClose} />
      <div className="absolute bottom-full left-0 z-[70] mb-2 w-80 rounded-xl border border-black/5 bg-white p-4 shadow-[0_12px_40px_-8px_rgba(0,0,0,0.1)]">
        <div className="mb-3 flex items-center gap-2.5">
          <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${colorBg}`}>
            <Icon size={16} weight="light" className={colorText} />
          </div>
          <span className="text-sm font-medium text-[#1A1A1A]">{info.label}</span>
        </div>
        <p className="text-xs leading-relaxed text-[#5F5D58]">
          {info.description}
        </p>
      </div>
    </>
  );
}

export function AgentBadges({
  agents,
  orchestrationMs,
}: {
  agents: string[];
  orchestrationMs?: number;
}) {
  const [openAgent, setOpenAgent] = useState<string | null>(null);

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <div className="flex items-center gap-1 rounded-full bg-[#1A1A1A] px-2.5 py-1">
        <Robot size={11} weight="light" className="text-[#B8985A]" />
        <span
          className="text-[9px] font-medium text-white"
          style={{ fontFamily: "var(--font-geist-mono), monospace" }}
        >
          {agents.length} agents
        </span>
      </div>
      {agents.map((agent) => {
        const info = AGENT_INFO[agent];
        const Icon = info?.icon || Robot;
        const colorParts = (info?.color || "text-[#5F5D58] bg-black/5").split(" ");

        return (
          <span key={agent} className="relative">
            <button
              onClick={() => setOpenAgent(openAgent === agent ? null : agent)}
              className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] ring-1 ring-black/5 transition-colors hover:ring-black/15 ${
                openAgent === agent ? "bg-black/[0.06] text-[#1A1A1A]" : "bg-black/[0.02] text-[#5F5D58]"
              }`}
              style={{ fontFamily: "var(--font-geist-mono), monospace" }}
            >
              <Icon size={10} weight="light" />
              {info?.label || agent}
            </button>
            {openAgent === agent && (
              <AgentPopover agentKey={agent} onClose={() => setOpenAgent(null)} />
            )}
          </span>
        );
      })}
      {orchestrationMs !== undefined && (
        <span
          className="flex items-center gap-0.5 text-[9px] text-[#5F5D58]"
          style={{ fontFamily: "var(--font-geist-mono), monospace" }}
        >
          <Lightning size={9} weight="light" />
          {orchestrationMs}ms
        </span>
      )}
    </div>
  );
}
