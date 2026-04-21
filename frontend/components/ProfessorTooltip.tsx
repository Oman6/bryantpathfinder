"use client";

import { useEffect, useRef, useState } from "react";
import { Star, ChalkboardTeacher, PaperPlaneTilt } from "@phosphor-icons/react";
import type { ProfessorRating } from "@/lib/types";
import { useStore } from "@/lib/store";

function getQualityColor(quality: number): string {
  if (quality >= 4.0) return "text-emerald-700";
  if (quality >= 3.0) return "text-amber-700";
  return "text-red-700";
}

function getQualityBg(quality: number): string {
  if (quality >= 4.0) return "bg-emerald-50";
  if (quality >= 3.0) return "bg-amber-50";
  return "bg-red-50";
}

interface ProfessorTooltipProps {
  name: string;
  rating: ProfessorRating | undefined;
  className?: string;
}

function StarSelector({
  value,
  onChange,
  label,
}: {
  value: number;
  onChange: (v: number) => void;
  label: string;
}) {
  const [hover, setHover] = useState(0);

  return (
    <div>
      <p className="mb-1 text-[10px] text-[#5F5D58]">{label}</p>
      <div className="flex gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onMouseEnter={() => setHover(star)}
            onMouseLeave={() => setHover(0)}
            onClick={() => onChange(star)}
            className="p-0.5 transition-transform hover:scale-110"
          >
            <Star
              size={14}
              weight={(hover || value) >= star ? "fill" : "light"}
              className={
                (hover || value) >= star ? "text-[#B8985A]" : "text-[#5F5D58]/30"
              }
            />
          </button>
        ))}
      </div>
    </div>
  );
}

export function ProfessorTooltip({ name, rating, className = "" }: ProfessorTooltipProps) {
  const { rateProfessor } = useStore();
  const [show, setShow] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [quality, setQuality] = useState(0);
  const [difficulty, setDifficulty] = useState(0);
  const [submitted, setSubmitted] = useState(false);

  if (name === "TBA") {
    return <span className={className}>{name}</span>;
  }

  const handleSubmit = () => {
    if (quality === 0 || difficulty === 0) return;
    rateProfessor(name, quality, difficulty);
    setSubmitted(true);
    setTimeout(() => {
      setShowForm(false);
      setSubmitted(false);
      setQuality(0);
      setDifficulty(0);
    }, 1200);
  };

  const handleMouseLeave = () => {
    if (!showForm) setShow(false);
  };

  const wrapperRef = useRef<HTMLSpanElement>(null);

  // Close on outside click when pinned open via tap
  useEffect(() => {
    if (!show && !showForm) return;
    const handleClick = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShow(false);
        setShowForm(false);
      }
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setShow(false);
        setShowForm(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [show, showForm]);

  return (
    <span
      ref={wrapperRef}
      className={`relative cursor-default ${className}`}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={handleMouseLeave}
    >
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setShow((v) => !v);
        }}
        className="border-b border-dotted border-[#5F5D58]/40 text-left"
        aria-expanded={show || showForm}
        aria-label={`Professor details for ${name}`}
      >
        {name}
      </button>

      {(show || showForm) && (
        <div
          className="absolute bottom-full left-0 z-50 mb-2 w-60 rounded-xl border border-black/5 bg-white p-3.5 shadow-[0_12px_40px_-8px_rgba(0,0,0,0.1)]"
          onMouseEnter={() => setShow(true)}
          onMouseLeave={() => {
            setShow(false);
            setShowForm(false);
          }}
        >
          {/* Header */}
          <div className="mb-2.5 flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-[#FAFAF7]">
              <ChalkboardTeacher size={13} weight="light" className="text-[#5F5D58]" />
            </div>
            <span className="text-xs font-medium text-[#1A1A1A]">{name}</span>
          </div>

          {rating ? (
            <>
              {/* Existing rating display */}
              <div className="mb-2 flex items-center gap-2">
                <div
                  className={`flex items-center gap-1 rounded-md px-2 py-1 ${getQualityBg(rating.quality)}`}
                >
                  <Star size={11} weight="fill" className={getQualityColor(rating.quality)} />
                  <span
                    className={`text-xs font-semibold ${getQualityColor(rating.quality)}`}
                    style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                  >
                    {rating.quality.toFixed(1)}
                  </span>
                </div>
                <span className="text-[10px] text-[#5F5D58]">quality</span>
              </div>

              <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
                <div>
                  <p className="text-[10px] text-[#5F5D58]">Difficulty</p>
                  <p
                    className="text-xs font-medium text-[#1A1A1A]"
                    style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                  >
                    {rating.difficulty.toFixed(1)}/5
                  </p>
                </div>
                <div>
                  <p className="text-[10px] text-[#5F5D58]">Would retake</p>
                  <p
                    className="text-xs font-medium text-[#1A1A1A]"
                    style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                  >
                    {rating.would_take_again >= 0
                      ? `${rating.would_take_again}%`
                      : "N/A"}
                  </p>
                </div>
              </div>

              <p
                className="mt-2 text-[9px] text-[#5F5D58]"
                style={{ fontFamily: "var(--font-geist-mono), monospace" }}
              >
                Based on {rating.num_ratings} rating{rating.num_ratings !== 1 ? "s" : ""}
              </p>

              {/* Add your rating toggle */}
              {!showForm && (
                <button
                  onClick={() => setShowForm(true)}
                  className="mt-2.5 w-full rounded-lg bg-[#FAFAF7] py-1.5 text-[10px] font-medium text-[#5F5D58] transition-colors hover:bg-black/[0.04] hover:text-[#1A1A1A]"
                >
                  Add your rating
                </button>
              )}

              {/* Inline rating form */}
              {showForm && !submitted && (
                <div className="mt-2.5 space-y-2 border-t border-black/5 pt-2.5">
                  <StarSelector value={quality} onChange={setQuality} label="Your quality rating" />
                  <StarSelector value={difficulty} onChange={setDifficulty} label="Difficulty" />
                  <button
                    onClick={handleSubmit}
                    disabled={quality === 0 || difficulty === 0}
                    className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-[#1A1A1A] py-1.5 text-[10px] font-medium text-white transition-colors hover:bg-[#2a2a2a] disabled:opacity-30"
                  >
                    <PaperPlaneTilt size={11} weight="light" />
                    Submit
                  </button>
                </div>
              )}

              {showForm && submitted && (
                <p className="mt-2.5 text-center text-[10px] font-medium text-emerald-700">
                  Rating submitted
                </p>
              )}
            </>
          ) : (
            <>
              {/* No rating — prompt to rate */}
              <p className="mb-3 text-[10px] text-[#5F5D58]">
                No ratings yet. Be the first to rate this professor.
              </p>

              {!submitted ? (
                <div className="space-y-2">
                  <StarSelector value={quality} onChange={setQuality} label="Quality" />
                  <StarSelector value={difficulty} onChange={setDifficulty} label="Difficulty" />
                  <button
                    onClick={handleSubmit}
                    disabled={quality === 0 || difficulty === 0}
                    className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-[#1A1A1A] py-1.5 text-[10px] font-medium text-white transition-colors hover:bg-[#2a2a2a] disabled:opacity-30"
                  >
                    <PaperPlaneTilt size={11} weight="light" />
                    Submit rating
                  </button>
                </div>
              ) : (
                <p className="text-center text-[10px] font-medium text-emerald-700">
                  Rating submitted
                </p>
              )}
            </>
          )}
        </div>
      )}
    </span>
  );
}
