"use client";

export function EyebrowTag({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="inline-block text-[10px] font-medium uppercase tracking-[0.2em] text-[#5F5D58]"
      style={{ fontFamily: "var(--font-geist-mono), monospace" }}
    >
      {children}
    </span>
  );
}
