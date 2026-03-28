import type { SessionData, SessionSummary, SectionScoringData, ChatMessage } from "./types";

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
  const res = await request<{ data: { session_id: string; status: string } }>("/analyze", {
    method: "POST",
    body: form,
  });
  return { session_id: res.data.session_id };
}

export async function getSession(id: string): Promise<SessionData> {
  const res = await request<{ data: SessionData }>(`/session/${id}`);
  return res.data;
}

export async function getSessions(): Promise<SessionSummary[]> {
  const res = await request<{ data: SessionSummary[]; meta: Record<string, number> }>("/sessions");
  return res.data;
}

export async function getSectionScoring(id: string): Promise<SectionScoringData> {
  const res = await request<{ data: SectionScoringData }>(`/session/${id}/insights/sections`);
  return res.data;
}

export async function sendCoachMessage(
  id: string,
  messages: ChatMessage[],
): Promise<string> {
  const res = await request<{ data: { role: string; content: string } }>(
    `/session/${id}/insights/chat`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
    },
  );
  return res.data.content;
}
