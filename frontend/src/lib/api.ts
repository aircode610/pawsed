import type { SessionData, SessionSummary, InsightData } from "./types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

export async function analyzeVideo(file: File): Promise<{ session_id: string }> {
  const form = new FormData();
  form.append("file", file);
  return request<{ session_id: string }>("/analyze", {
    method: "POST",
    body: form,
  });
}

export async function getSession(id: string): Promise<SessionData> {
  const res = await request<{ data: SessionData }>(`/session/${id}`);
  return res.data;
}

export async function getInsights(id: string): Promise<InsightData> {
  return request<InsightData>(`/session/${id}/insights`);
}

export async function getSessions(): Promise<SessionSummary[]> {
  return request<SessionSummary[]>("/sessions");
}
