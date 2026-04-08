"use client";

import { Robot, Lightning } from "@phosphor-icons/react";

const AGENT_LABELS: Record<string, string> = {
  solver: "Constraint Solver",
  professor_match: "Professor Match",
  workload: "Workload Analyzer",
  explainer: "Schedule Explainer",
  negotiator: "Conflict Negotiator",
  prerequisite: "Prerequisite Agent",
  rotation: "Rotation Agent",
  sequencing: "Sequencing Agent",
};

export function AgentBadges({
  agents,
  orchestrationMs,
}: {
  agents: string[];
  orchestrationMs?: number;
}) {
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
      {agents.map((agent) => (
        <span
          key={agent}
          className="rounded-full bg-black/[0.04] px-2 py-0.5 text-[9px] text-[#787774] ring-1 ring-black/5"
          style={{ fontFamily: "var(--font-geist-mono), monospace" }}
        >
          {AGENT_LABELS[agent] || agent}
        </span>
      ))}
      {orchestrationMs !== undefined && (
        <span
          className="flex items-center gap-0.5 text-[9px] text-[#787774]"
          style={{ fontFamily: "var(--font-geist-mono), monospace" }}
        >
          <Lightning size={9} weight="light" />
          {orchestrationMs}ms
        </span>
      )}
    </div>
  );
}
