"use client";

import { ArrowRight } from "@phosphor-icons/react";
import { cn } from "@/lib/utils";

interface PillButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: "primary" | "secondary";
  className?: string;
  type?: "button" | "submit";
}

export function PillButton({
  children,
  onClick,
  disabled = false,
  variant = "primary",
  className,
  type = "button",
}: PillButtonProps) {
  const isPrimary = variant === "primary";

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "group relative inline-flex items-center gap-3 rounded-full px-7 py-3.5 text-sm font-medium transition-all duration-500",
        isPrimary
          ? "bg-[#1A1A1A] text-white hover:bg-[#2a2a2a]"
          : "bg-white text-[#1A1A1A] ring-1 ring-black/10 hover:ring-black/20",
        disabled && "pointer-events-none opacity-40",
        className
      )}
      style={{ transitionTimingFunction: "cubic-bezier(0.32, 0.72, 0, 1)" }}
    >
      <span>{children}</span>
      <span
        className={cn(
          "flex h-7 w-7 items-center justify-center rounded-full transition-transform duration-500 group-hover:translate-x-0.5 group-hover:-translate-y-0.5",
          isPrimary ? "bg-white/15" : "bg-black/5"
        )}
        style={{ transitionTimingFunction: "cubic-bezier(0.32, 0.72, 0, 1)" }}
      >
        <ArrowRight
          size={14}
          weight="light"
          className={isPrimary ? "text-white" : "text-[#1A1A1A]"}
        />
      </span>
    </button>
  );
}
