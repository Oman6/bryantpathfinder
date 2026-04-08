"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { Upload, Warning, ArrowClockwise } from "@phosphor-icons/react";
import { parseAudit, getSampleAudit } from "@/lib/api";
import { useStore } from "@/lib/store";
import { Skeleton } from "@/components/ui/skeleton";

export function UploadZone() {
  const router = useRouter();
  const { setAudit, setLoading, setError } = useStore();
  const [dragging, setDragging] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      const validTypes = ["image/png", "image/jpeg", "image/jpg", "application/pdf"];
      if (!validTypes.includes(file.type)) {
        setLocalError("Please upload a PNG, JPEG, or PDF file.");
        return;
      }

      setParsing(true);
      setLocalError(null);

      try {
        const base64 = await fileToBase64(file);
        const audit = await parseAudit(base64);
        setAudit(audit);
        router.push("/preferences");
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to parse audit";
        setLocalError(message);
      } finally {
        setParsing(false);
      }
    },
    [setAudit, router]
  );

  const handleSampleAudit = useCallback(async () => {
    setLoading(true);
    setLocalError(null);
    try {
      const audit = await getSampleAudit();
      setAudit(audit);
      router.push("/preferences");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load sample";
      setLocalError(message);
    } finally {
      setLoading(false);
    }
  }, [setAudit, setLoading, router]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  if (parsing) {
    return (
      <div className="rounded-[2rem] bg-black/[0.03] p-1.5 ring-1 ring-black/5">
        <div className="flex flex-col items-center justify-center gap-6 rounded-[calc(2rem-0.375rem)] bg-white p-12">
          <Skeleton className="h-12 w-12 rounded-full" />
          <div className="space-y-2 text-center">
            <Skeleton className="mx-auto h-5 w-48" />
            <Skeleton className="mx-auto h-4 w-64" />
          </div>
          <p
            className="text-xs text-[#787774]"
            style={{ fontFamily: "var(--font-geist-mono), monospace" }}
          >
            Claude Vision is reading your audit...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Double-bezel card */}
      <div className="rounded-[2rem] bg-black/[0.03] p-1.5 ring-1 ring-black/5">
        <div
          className={`relative flex flex-col items-center justify-center gap-5 rounded-[calc(2rem-0.375rem)] bg-white p-12 transition-all duration-300 ${
            dragging ? "ring-2 ring-[#B8985A]/40" : ""
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          style={{ transitionTimingFunction: "cubic-bezier(0.32, 0.72, 0, 1)" }}
        >
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[#FAFAF7]">
            <Upload size={24} weight="light" className="text-[#787774]" />
          </div>

          <div className="text-center">
            <p className="text-sm font-medium text-[#1A1A1A]">
              Drop your Degree Works screenshot
            </p>
            <p className="mt-1 text-xs text-[#787774]">
              PNG, JPEG, or PDF
            </p>
          </div>

          <label className="cursor-pointer rounded-full bg-[#FAFAF7] px-5 py-2 text-xs font-medium text-[#787774] ring-1 ring-black/5 transition-colors hover:bg-black/[0.04] hover:text-[#1A1A1A]">
            Browse files
            <input
              type="file"
              accept=".png,.jpg,.jpeg,.pdf"
              className="hidden"
              onChange={handleInputChange}
            />
          </label>

          {localError && (
            <div className="flex items-center gap-2 rounded-full bg-red-50 px-4 py-2 text-xs text-red-700">
              <Warning size={14} weight="light" />
              <span>{localError}</span>
              <button
                onClick={() => setLocalError(null)}
                className="ml-1 underline hover:no-underline"
              >
                Dismiss
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Sample audit link */}
      <button
        onClick={handleSampleAudit}
        className="group flex w-full items-center justify-center gap-1.5 py-2 text-xs text-[#787774] transition-colors hover:text-[#1A1A1A]"
      >
        <span>Or use sample audit</span>
        <span className="transition-transform group-hover:translate-x-0.5">&rarr;</span>
      </button>
    </div>
  );
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      resolve(result);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
