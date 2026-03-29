export interface SessionEvent {
  timestamp: number;
  event_type: string;
  duration: number;
  confidence: number;
  metadata: Record<string, unknown>;
  severity: "brief" | "significant";
}

export interface EngagementSegment {
  start: number;
  end: number;
  state: "engaged" | "passive" | "disengaged";
}

export interface DangerZone {
  start: number;
  end: number;
  avg_score: number;
}

export interface SessionAnalytics {
  focus_time_pct: number;
  distraction_time_pct: number;
  longest_focus_streak: number;
  distraction_breakdown: Record<string, number>;
  engagement_curve: number[];
  danger_zones: DangerZone[];
}

export interface SessionData {
  session_id: string;
  created_at: string;
  duration: number;
  video_filename: string;
  analytics: SessionAnalytics;
  events: SessionEvent[];
  engagement_states: EngagementSegment[];
  has_landmarks: boolean;
}

export interface SessionSummary {
  session_id: string;
  created_at: string;
  duration: number;
  video_filename: string;
  focus_time_pct: number;
  event_count: number;
  status: string;
}

export interface StateBreakdown {
  engaged: number;
  passive: number;
  disengaged: number;
}

export interface LectureSection {
  label: string;
  start: number;
  end: number;
  engagement_pct: number;
  state_breakdown: StateBreakdown;
  top_event: string | null;
  events_in_section: SessionEvent[];
  ai_note: string;
}

export interface SectionScoringData {
  session_id: string;
  overall_summary: string;
  sections: LectureSection[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export type EventType = "yawn" | "looked_away" | "looked_down" | "eyes_closed" | "drowsy" | "distracted" | "zoned_out" | "face_lost";
