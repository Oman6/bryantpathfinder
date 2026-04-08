"use client";

import type { Section } from "@/lib/types";
import { CourseBlock } from "./CourseBlock";

const DAYS = ["M", "T", "W", "R", "F"] as const;
const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri"];
const START_HOUR = 8;
const END_HOUR = 22;
const PIXELS_PER_MINUTE = 0.8;

function timeToMinutes(time: string): number {
  const [h, m] = time.split(":").map(Number);
  return h * 60 + m;
}

function formatHour(hour: number): string {
  const suffix = hour >= 12 ? "p" : "a";
  if (hour === 0 || hour === 12) return `12${suffix}`;
  return hour > 12 ? `${hour - 12}${suffix}` : `${hour}${suffix}`;
}

interface WeeklyCalendarProps {
  sections: Section[];
}

export function WeeklyCalendar({ sections }: WeeklyCalendarProps) {
  const totalMinutes = (END_HOUR - START_HOUR) * 60;
  const calendarHeight = totalMinutes * PIXELS_PER_MINUTE;
  const hours = Array.from({ length: END_HOUR - START_HOUR }, (_, i) => START_HOUR + i);

  return (
    <div className="w-full overflow-hidden rounded-xl bg-[#FAFAF7]/50">
      {/* Day headers */}
      <div className="grid grid-cols-[2.5rem_repeat(5,1fr)] border-b border-black/5">
        <div />
        {DAY_LABELS.map((day) => (
          <div
            key={day}
            className="py-2 text-center text-[10px] font-medium uppercase tracking-widest text-[#787774]"
          >
            {day}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="relative grid grid-cols-[2.5rem_repeat(5,1fr)]" style={{ height: `${calendarHeight}px` }}>
        {/* Hour labels and gridlines */}
        <div className="relative">
          {hours.map((hour) => {
            const top = (hour - START_HOUR) * 60 * PIXELS_PER_MINUTE;
            return (
              <div
                key={hour}
                className="absolute right-1 text-[9px] text-[#787774]/60"
                style={{
                  top: `${top}px`,
                  fontFamily: "var(--font-geist-mono), monospace",
                  transform: "translateY(-50%)",
                }}
              >
                {formatHour(hour)}
              </div>
            );
          })}
        </div>

        {/* Day columns */}
        {DAYS.map((day) => (
          <div key={day} className="relative border-l border-black/[0.03]">
            {/* Hour gridlines */}
            {hours.map((hour) => {
              const top = (hour - START_HOUR) * 60 * PIXELS_PER_MINUTE;
              return (
                <div
                  key={hour}
                  className="absolute left-0 right-0 border-t border-black/[0.03]"
                  style={{ top: `${top}px` }}
                />
              );
            })}

            {/* Course blocks */}
            {sections.map((section) =>
              section.meetings
                .filter((m) => m.days.includes(day))
                .map((meeting, meetingIdx) => (
                  <CourseBlock
                    key={`${section.crn}-${meetingIdx}`}
                    section={section}
                    startMinutes={timeToMinutes(meeting.start)}
                    endMinutes={timeToMinutes(meeting.end)}
                    calendarStartHour={START_HOUR}
                    pixelsPerMinute={PIXELS_PER_MINUTE}
                  />
                ))
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
