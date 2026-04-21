"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { Upload, Warning, TextT, ClipboardText } from "@phosphor-icons/react";
import { parseAudit, parseAuditText, getSampleAudit } from "@/lib/api";
import { useStore } from "@/lib/store";
import { Skeleton } from "@/components/ui/skeleton";

type Tab = "upload" | "paste";

export function UploadZone() {
  const router = useRouter();
  const { setAudit, setLoading } = useStore();
  const [tab, setTab] = useState<Tab>("paste");
  const [dragging, setDragging] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [pasteText, setPasteText] = useState("");

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

  const handlePasteSubmit = useCallback(async () => {
    if (!pasteText.trim()) {
      setLocalError("Paste your requirements first.");
      return;
    }

    setParsing(true);
    setLocalError(null);

    try {
      const audit = await parseAuditText(pasteText);
      setAudit(audit);
      router.push("/preferences");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to parse";
      setLocalError(message);
    } finally {
      setParsing(false);
    }
  }, [pasteText, setAudit, router]);

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
            className="text-xs text-[#5F5D58]"
            style={{ fontFamily: "var(--font-geist-mono), monospace" }}
          >
            Claude is reading your requirements...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Double-bezel card */}
      <div className="rounded-[2rem] bg-black/[0.03] p-1.5 ring-1 ring-black/5">
        <div className="rounded-[calc(2rem-0.375rem)] bg-white p-6">
          {/* Tab switcher */}
          <div className="mb-5 flex gap-1 rounded-full bg-[#FAFAF7] p-1">
            <button
              onClick={() => setTab("paste")}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-full py-2 text-xs font-medium transition-all duration-300 ${
                tab === "paste"
                  ? "bg-white text-[#1A1A1A] shadow-sm"
                  : "text-[#5F5D58] hover:text-[#1A1A1A]"
              }`}
              style={{ transitionTimingFunction: "cubic-bezier(0.32, 0.72, 0, 1)" }}
            >
              <ClipboardText size={14} weight="light" />
              Paste text
            </button>
            <button
              onClick={() => setTab("upload")}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-full py-2 text-xs font-medium transition-all duration-300 ${
                tab === "upload"
                  ? "bg-white text-[#1A1A1A] shadow-sm"
                  : "text-[#5F5D58] hover:text-[#1A1A1A]"
              }`}
              style={{ transitionTimingFunction: "cubic-bezier(0.32, 0.72, 0, 1)" }}
            >
              <Upload size={14} weight="light" />
              Upload image
            </button>
          </div>

          {/* Paste tab */}
          {tab === "paste" && (
            <div className="space-y-3">
              <p className="text-xs text-[#5F5D58]">
                Paste your advisor notes, requirement list, or any text describing what courses you still need.
              </p>
              <textarea
                value={pasteText}
                onChange={(e) => setPasteText(e.target.value)}
                placeholder={"e.g. FIN 310, GEN 201, SCI + matching lab from approved list, LCS 200 level from approved list, ACG 203, ACG 204, ISA 201, MKT 201, LGLS 211, BUS 400, GEN 390 capstone"}
                rows={5}
                className="w-full resize-none rounded-xl border border-black/5 bg-[#FAFAF7] px-4 py-3 text-sm text-[#1A1A1A] placeholder:text-[#5F5D58]/40 focus:border-[#B8985A]/30 focus:bg-white focus:outline-none focus:ring-1 focus:ring-[#B8985A]/20"
                style={{ fontFamily: "var(--font-geist-mono), monospace" }}
              />
              <button
                onClick={handlePasteSubmit}
                disabled={!pasteText.trim()}
                className="flex w-full items-center justify-center gap-2 rounded-full bg-[#1A1A1A] py-2.5 text-xs font-medium text-white transition-colors hover:bg-[#2a2a2a] disabled:opacity-30"
              >
                <TextT size={14} weight="light" />
                Parse requirements
              </button>
            </div>
          )}

          {/* Upload tab */}
          {tab === "upload" && (
            <div
              className={`flex flex-col items-center justify-center gap-5 rounded-xl p-8 transition-all duration-300 ${
                dragging ? "ring-2 ring-[#B8985A]/40 bg-[#FAFAF7]" : ""
              }`}
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
            >
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[#FAFAF7]">
                <Upload size={24} weight="light" className="text-[#5F5D58]" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-[#1A1A1A]">
                  Drop your Degree Works screenshot
                </p>
                <p className="mt-1 text-xs text-[#5F5D58]">PNG, JPEG, or PDF</p>
              </div>
              <label className="cursor-pointer rounded-full bg-[#FAFAF7] px-5 py-2 text-xs font-medium text-[#5F5D58] ring-1 ring-black/5 transition-colors hover:bg-black/[0.04] hover:text-[#1A1A1A]">
                Browse files
                <input type="file" accept=".png,.jpg,.jpeg,.pdf" className="hidden" onChange={handleInputChange} />
              </label>
            </div>
          )}

          {/* Error */}
          {localError && (
            <div className="mt-3 flex items-center gap-2 rounded-full bg-red-50 px-4 py-2 text-xs text-red-700">
              <Warning size={14} weight="light" />
              <span>{localError}</span>
              <button onClick={() => setLocalError(null)} className="ml-1 underline hover:no-underline">Dismiss</button>
            </div>
          )}
        </div>
      </div>

      {/* Sample audit link */}
      <button
        onClick={handleSampleAudit}
        className="group flex w-full items-center justify-center gap-1.5 py-2 text-xs text-[#5F5D58] transition-colors hover:text-[#1A1A1A]"
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
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
