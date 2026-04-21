"use client";

import { Upload, SlidersHorizontal, Calendar } from "@phosphor-icons/react";
import { Logo } from "@/components/Logo";
import { UploadZone } from "@/components/UploadZone";

const steps = [
  {
    icon: Upload,
    number: "1",
    title: "Paste your requirements",
    description:
      "Go to Degree Works, find your outstanding courses, and paste them into the text box above. Or click 'Use sample audit' to try it with demo data.",
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
              Your advisor tells you what to take. Pathfinder tells you{" "}
              <span className="italic text-[#B8985A]">when.</span>
            </h1>

            <p className="max-w-lg text-base leading-relaxed text-[#5F5D58]">
              An AI course scheduling assistant that turns your Degree Works
              audit into a working class schedule in seconds.
            </p>
          </div>

          {/* Right — upload zone */}
          <div className="animate-fade-up delay-200">
            <UploadZone />
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
