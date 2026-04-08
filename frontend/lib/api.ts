import type {
  DegreeAudit,
  GenerateSchedulesResponse,
  SchedulePreferences,
} from "./types";

const API_BASE = "http://localhost:8000";

export async function parseAudit(imageBase64: string): Promise<DegreeAudit> {
  const res = await fetch(`${API_BASE}/api/parse-audit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_base64: imageBase64 }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Failed to parse audit" }));
    throw new Error(error.detail || `Parse failed (${res.status})`);
  }
  return res.json();
}

export async function generateSchedules(
  audit: DegreeAudit,
  preferences: SchedulePreferences
): Promise<GenerateSchedulesResponse> {
  const res = await fetch(`${API_BASE}/api/generate-schedules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ audit, preferences }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Failed to generate schedules" }));
    throw new Error(error.detail || `Generation failed (${res.status})`);
  }
  return res.json();
}

export async function getSampleAudit(): Promise<DegreeAudit> {
  const res = await fetch(`${API_BASE}/api/sample-audit`);
  if (!res.ok) {
    throw new Error("Failed to load sample audit");
  }
  return res.json();
}
