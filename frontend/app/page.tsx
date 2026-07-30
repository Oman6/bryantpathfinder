"use client";

import { useState } from "react";
import { Upload, SlidersHorizontal, Calendar, CaretDown, CaretUp } from "@phosphor-icons/react";
import { Logo } from "@/components/Logo";
import { MajorPicker } from "@/components/MajorPicker";
import { UploadZone } from "@/components/UploadZone";

const steps = [
  {
    icon: Upload,
    number: "1",
    title: "Pick your major",
    description:
      "Select your major and we'll pre-fill the typical sophomore-year requirements. Or upload your Degree Works audit if you've got one handy.",
  },
  {
    icon: SlidersHorizontal,
    number: "2",
    title: "Set your preferences",
    description:
      "Choose which days you want off, set your target credit hours, and tell us if you want to avoid early mornings or evening classes.",
  },
  {
    icon: Calendar,
    number: "3",
    title: "Pick your schedule",
    description:
      "We generate three conflict-free schedules instantly. Compare professors, workloads, and time slots. Copy the CRNs and register in Banner.",
  },
];

export default function HomePage() {
  const [showAudit, setShowAudit] = useState(false);

  return (
    <main className="min-h-[100dvh]">
      {/* Hero section */}
      <section className="mx-auto max-w-7xl px-6 py-24 md:px-12 md:py-32">
        <div className="grid grid-cols-1 items-center gap-16 md:grid-cols-2 md:gap-20">
          {/* Left — editorial typography */}
          <div className="animate-fade-up space-y-8">
            <Logo />

            <h1
              className="text-5xl leading-[1.05] tracking-tight text-[#1A1A1A] md:text-7xl"
              style={{ fontFamily: "var(--font-instrument-serif), serif" }}
            >
              Tell us what you're studying.{" "}
              <span className="italic text-[#B8985A]">We'll handle the rest.</span>
            </h1>

            <p className="max-w-lg text-base leading-relaxed text-[#5F5D58]">
              An AI course scheduling assistant that turns your Bryant requirements
              into three conflict-free schedules in seconds.
            </p>
          </div>

          {/* Right — major picker (primary) + upload disclosure (secondary) */}
          <div className="animate-fade-up delay-200 space-y-3">
            <MajorPicker />

            <div className="rounded-[2rem] bg-black/[0.03] p-1.5 ring-1 ring-black/5">
              <button
                type="button"
                onClick={() => setShowAudit((v) => !v)}
                className="flex w-full items-center justify-between rounded-[calc(2rem-0.375rem)] bg-white px-6 py-3 text-left"
                aria-expanded={showAudit}
              >
                <span className="text-xs text-[#5F5D58]">
                  Have a Degree Works audit?{" "}
                  <span className="text-[#1A1A1A]">Paste or upload it.</span>
                </span>
                {showAudit ? (
                  <CaretUp size={14} weight="light" className="text-[#5F5D58]" />
                ) : (
                  <CaretDown size={14} weight="light" className="text-[#5F5D58]" />
                )}
              </button>
              {showAudit && (
                <div className="mt-1 rounded-[calc(2rem-0.375rem)] bg-white p-2 animate-fade-up">
                  <UploadZone />
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-7xl px-6 pb-32 md:px-12">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {steps.map((step, i) => (
            <div
              key={step.title}
              className={`animate-fade-up rounded-[2rem] bg-black/[0.03] p-1.5 ring-1 ring-black/5`}
              style={{ animationDelay: `${(i + 1) * 100}ms` }}
            >
              <div className="flex h-full flex-col gap-4 rounded-[calc(2rem-0.375rem)] bg-white p-8">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#FAFAF7]">
                    <step.icon size={20} weight="light" className="text-[#5F5D58]" />
                  </div>
                  <span
                    className="text-[10px] font-medium text-[#5F5D58]"
                    style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                  >
                    Step {step.number}
                  </span>
                </div>
                <h3 className="text-sm font-medium text-[#1A1A1A]">
                  {step.title}
                </h3>
                <p className="text-xs leading-relaxed text-[#5F5D58]">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
