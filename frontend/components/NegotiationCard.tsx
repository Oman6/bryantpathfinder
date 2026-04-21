"use client";

import { Scales, ArrowRight, Warning } from "@phosphor-icons/react";
import type { NegotiationData } from "@/lib/types";

export function NegotiationCard({ data }: { data: NegotiationData }) {
  return (
    <div className="rounded-[2rem] bg-black/[0.03] p-1.5 ring-1 ring-black/5">
      <div className="rounded-[calc(2rem-0.375rem)] bg-white p-8">
        {/* Header */}
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-orange-50">
            <Scales size={20} weight="light" className="text-orange-700" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-[#1A1A1A]">
              Constraint Analysis
            </h3>
            <p className="text-xs text-[#5F5D58]">
              The Negotiator Agent found tradeoffs to unlock valid schedules.
            </p>
          </div>
        </div>

        {/* Analysis */}
        <p className="mb-5 text-sm leading-relaxed text-[#5F5D58]">
          {data.analysis}
        </p>

        {/* Bottlenecks */}
        {data.bottlenecks.length > 0 && (
          <div className="mb-5 space-y-2">
            <h4
              className="text-[10px] font-medium uppercase tracking-[0.15em] text-[#5F5D58]"
              style={{ fontFamily: "var(--font-geist-mono), monospace" }}
            >
              Bottlenecks
            </h4>
            {data.bottlenecks.map((b, i) => (
              <div
                key={i}
                className="flex items-center gap-2 rounded-lg bg-orange-50/50 px-3 py-2"
              >
                <Warning size={12} weight="light" className="text-orange-700" />
                <span className="text-xs text-[#1A1A1A]">{b.constraint}</span>
                <span className="text-[10px] text-[#5F5D58]">{b.detail}</span>
              </div>
            ))}
          </div>
        )}

        {/* Proposed trades */}
        {data.trades.length > 0 && (
          <div className="space-y-2">
            <h4
              className="text-[10px] font-medium uppercase tracking-[0.15em] text-[#5F5D58]"
              style={{ fontFamily: "var(--font-geist-mono), monospace" }}
            >
              Proposed Trades
            </h4>
            {data.trades.map((trade, i) => (
              <div
                key={i}
                className="flex items-center gap-3 rounded-xl bg-[#FAFAF7] px-4 py-3"
              >
                <div className="flex-1">
                  <p className="text-xs font-medium text-[#1A1A1A]">
                    {trade.action}
                  </p>
                  <p className="mt-0.5 text-[10px] text-[#5F5D58]">
                    {trade.impact}
                  </p>
                </div>
                <ArrowRight size={14} weight="light" className="text-[#5F5D58]" />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
