"use client";

import { Compass } from "@phosphor-icons/react";

export function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#1A1A1A]">
        <Compass size={16} weight="light" className="text-[#B8985A]" />
      </div>
      <div className="flex items-baseline gap-1">
        <span
          className="text-sm tracking-tight text-[#1A1A1A]"
          style={{ fontFamily: "var(--font-instrument-serif), serif" }}
        >
          Pathfinder
        </span>
        <span
          className="text-[10px] text-[#787774]"
          style={{ fontFamily: "var(--font-geist-mono), monospace" }}
        >
          by NovaWealth
        </span>
      </div>
    </div>
  );
}
