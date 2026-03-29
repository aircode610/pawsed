import type { SessionData, SessionSummary, SectionScoringData, ChatMessage } from "./types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Token management
let _token: string | null = localStorage.getItem("pawsed_token");

export function setToken(token: string | null) {
  _token = token;
  if (token) localStorage.setItem("pawsed_token", token);
  else localStorage.removeItem("pawsed_token");
}

export function getToken(): string | null {
  return _token;
}

export function isLoggedIn(): boolean {
  return !!_token;
}

export function logout() {
  setToken(null);
  localStorage.removeItem("pawsed_user");
  window.location.href = "/login";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string> || {}),
  };
  if (_token) {
    headers["Authorization"] = `Bearer ${_token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (res.status === 401) {
    logout();
    throw new Error("Session expired. Please log in again.");
  }

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

// Auth
export async function signup(email: string, name: string, password: string): Promise<{ token: string; user: any }> {
  const res = await request<{ token: string; user: any }>("/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, name, password }),
  });
  setToken(res.token);
  localStorage.setItem("pawsed_user", JSON.stringify(res.user));
  return res;
}

export async function login(email: string, password: string): Promise<{ token: string; user: any }> {
  const res = await request<{ token: string; user: any }>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  setToken(res.token);
  localStorage.setItem("pawsed_user", JSON.stringify(res.user));
  return res;
}

export function getStoredUser(): { id: number; email: string; name: string } | null {
  const raw = localStorage.getItem("pawsed_user");
  return raw ? JSON.parse(raw) : null;
}

// Sessions
export type PipelineMode = "mediapipe" | "ml-nn" | "ml-paranet" | "ml-rules";

export async function analyzeVideo(file: File, mode: PipelineMode = "mediapipe"): Promise<{ session_id: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await request<{ data: { session_id: string; status: string } }>(`/analyze?mode=${mode}`, {
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

export async function sendCoachMessage(id: string, messages: ChatMessage[]): Promise<string> {
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
