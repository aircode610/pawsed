export interface SessionEvent {
  timestamp: number;
  event_type: string;
  duration: number;
  confidence: number;
  metadata: Record<string, unknown>;
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
}

export interface SessionSummary {
  session_id: string;
  created_at: string;
  duration: number;
  video_filename: string;
  focus_time_pct: number;
}

export interface InsightData {
  session_id: string;
  recommendations: string[];
  summary: string;
}
