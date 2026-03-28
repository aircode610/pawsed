export const mockSession = {
  session_id: "demo",
  created_at: "2026-03-28T14:30:00Z",
  duration: 1800,
  video_filename: "lecture_tuesday.mp4",
  analytics: {
    focus_time_pct: 72.5,
    distraction_time_pct: 27.5,
    longest_focus_streak: 660,
    distraction_breakdown: {
      yawn: 3,
      looked_away: 7,
      eyes_closed: 2,
      zoned_out: 1,
    },
    engagement_curve: [
      0.85, 0.88, 0.78, 0.65, 0.60, 0.72, 0.80, 0.90, 0.92,
      0.88, 0.75, 0.55, 0.45, 0.40, 0.50, 0.58, 0.70, 0.78,
      0.82, 0.85, 0.90, 0.88, 0.80, 0.75, 0.72, 0.68, 0.60,
      0.65, 0.70, 0.80,
    ],
    danger_zones: [
      { start: 720, end: 1080, avg_score: 0.35 },
    ],
  },
  events: [
    { timestamp: 272, event_type: "yawn", duration: 3.2, confidence: 0.87, metadata: {} },
    { timestamp: 435, event_type: "looked_away", duration: 8.1, confidence: 0.92, metadata: { direction: "left" } },
    { timestamp: 620, event_type: "eyes_closed", duration: 2.1, confidence: 0.78, metadata: {} },
    { timestamp: 760, event_type: "looked_away", duration: 5.5, confidence: 0.85, metadata: { direction: "right" } },
    { timestamp: 850, event_type: "yawn", duration: 4.0, confidence: 0.91, metadata: {} },
    { timestamp: 920, event_type: "looked_away", duration: 12.3, confidence: 0.94, metadata: { direction: "left" } },
    { timestamp: 980, event_type: "zoned_out", duration: 45.0, confidence: 0.72, metadata: {} },
    { timestamp: 1100, event_type: "eyes_closed", duration: 5.5, confidence: 0.95, metadata: {} },
    { timestamp: 1250, event_type: "looked_away", duration: 6.2, confidence: 0.88, metadata: { direction: "right" } },
    { timestamp: 1380, event_type: "yawn", duration: 3.8, confidence: 0.83, metadata: {} },
    { timestamp: 1500, event_type: "looked_away", duration: 4.5, confidence: 0.80, metadata: { direction: "left" } },
    { timestamp: 1620, event_type: "looked_away", duration: 7.0, confidence: 0.86, metadata: { direction: "right" } },
    { timestamp: 1720, event_type: "looked_away", duration: 3.2, confidence: 0.79, metadata: { direction: "left" } },
  ],
  engagement_states: [
    { start: 0, end: 272, state: "engaged" },
    { start: 272, end: 280, state: "disengaged" },
    { start: 280, end: 435, state: "engaged" },
    { start: 435, end: 445, state: "disengaged" },
    { start: 445, end: 620, state: "passive" },
    { start: 620, end: 625, state: "disengaged" },
    { start: 625, end: 720, state: "engaged" },
    { start: 720, end: 1080, state: "disengaged" },
    { start: 1080, end: 1250, state: "passive" },
    { start: 1250, end: 1380, state: "engaged" },
    { start: 1380, end: 1500, state: "passive" },
    { start: 1500, end: 1620, state: "engaged" },
    { start: 1620, end: 1720, state: "passive" },
    { start: 1720, end: 1800, state: "engaged" },
  ],
};

export const mockSectionScoring = {
  session_id: "demo",
  overall_summary:
    "Your lecture had a strong opening and close, but lost the class between minutes 12–18. That 6-minute danger zone brought your overall score down from what could have been 80%+ to 72.5%. The fix is structural — break that middle section with an interactive moment.",
  sections: [
    {
      label: "Introduction",
      start: 0,
      end: 300,
      engagement_pct: 89.2,
      state_breakdown: { engaged: 82, passive: 14, disengaged: 4 },
      top_event: null as string | null,
      ai_note:
        "Strong opening — students were attentive. Whatever you did here (greeting, agenda overview, hook question), keep doing it.",
    },
    {
      label: "Core Content A",
      start: 300,
      end: 720,
      engagement_pct: 71.5,
      state_breakdown: { engaged: 60, passive: 28, disengaged: 12 },
      top_event: "looked_away (4 times)",
      ai_note:
        "Gradual drift starting around minute 7. Students were passive but not fully checked out — a mid-point check-in question or quick poll could reset attention here.",
    },
    {
      label: "Danger Zone",
      start: 720,
      end: 1080,
      engagement_pct: 38.4,
      state_breakdown: { engaged: 25, passive: 30, disengaged: 45 },
      top_event: "zoned_out (45s), yawn (2 times)",
      ai_note:
        "This was the lowest-engagement stretch. 45% of the time was spent disengaged. This often happens during extended theory without interaction. Consider breaking this into two shorter blocks with an active learning exercise (think-pair-share, quick problem) in between.",
    },
    {
      label: "Recovery",
      start: 1080,
      end: 1500,
      engagement_pct: 74.8,
      state_breakdown: { engaged: 65, passive: 25, disengaged: 10 },
      top_event: "looked_away (3 times)",
      ai_note:
        "The class re-engaged here. If this section involved a demo, worked example, or change of pace, that's likely what brought them back. Try to bring that energy earlier next time.",
    },
    {
      label: "Wrap-up",
      start: 1500,
      end: 1800,
      engagement_pct: 80.1,
      state_breakdown: { engaged: 72, passive: 22, disengaged: 6 },
      top_event: null as string | null,
      ai_note:
        "Solid finish. Students were mostly attentive through the closing. Ending strong helps with retention of the final points.",
    },
  ],
};

export const mockSessionList = [
  {
    session_id: "sess-001",
    created_at: "2026-03-24T10:00:00Z",
    duration: 2400,
    focus_time_pct: 65.2,
    event_count: 18,
    video_filename: "monday_lecture.mp4",
    engagement_curve: [0.7, 0.65, 0.6, 0.55, 0.5, 0.6, 0.7, 0.75],
  },
  {
    session_id: "sess-002",
    created_at: "2026-03-25T14:30:00Z",
    duration: 1800,
    focus_time_pct: 71.8,
    event_count: 14,
    video_filename: "tuesday_lecture.mp4",
    engagement_curve: [0.8, 0.75, 0.7, 0.65, 0.7, 0.75, 0.8, 0.85],
  },
  {
    session_id: "sess-003",
    created_at: "2026-03-26T10:15:00Z",
    duration: 2100,
    focus_time_pct: 78.4,
    event_count: 10,
    video_filename: "wednesday_lecture.mp4",
    engagement_curve: [0.85, 0.82, 0.78, 0.8, 0.85, 0.88, 0.9, 0.85],
  },
  {
    session_id: "demo",
    created_at: "2026-03-28T14:30:00Z",
    duration: 1800,
    focus_time_pct: 72.5,
    event_count: 13,
    video_filename: "lecture_tuesday.mp4",
    engagement_curve: [0.85, 0.78, 0.65, 0.45, 0.50, 0.70, 0.80, 0.80],
  },
];

export const mockBadges = [
  { id: "first-session", name: "First Session", icon: "🎯", earned: true, date: "2026-03-24", description: "Complete your first session" },
  { id: "three-sessions", name: "Hat Trick", icon: "🎩", earned: true, date: "2026-03-26", description: "Complete 3 sessions" },
  { id: "streak-3", name: "3-Day Streak", icon: "🔥", earned: true, date: "2026-03-26", description: "3 consecutive days" },
  { id: "focus-80", name: "Laser Focus", icon: "🎯", earned: false, description: "Score 80%+ in a session" },
  { id: "streak-5", name: "5-Day Streak", icon: "⚡", earned: false, description: "5 consecutive days" },
  { id: "night-owl", name: "Night Owl", icon: "🦉", earned: false, description: "Complete a session after 9pm" },
  { id: "focus-90", name: "In The Zone", icon: "🧠", earned: false, description: "Score 90%+ in a session" },
  { id: "ten-sessions", name: "Dedicated", icon: "💪", earned: false, description: "Complete 10 sessions" },
];

export const mockWeeklyHeatmap = [
  { date: "2026-03-22", score: null as number | null },
  { date: "2026-03-23", score: null as number | null },
  { date: "2026-03-24", score: 0.65 },
  { date: "2026-03-25", score: 0.72 },
  { date: "2026-03-26", score: 0.78 },
  { date: "2026-03-27", score: null as number | null },
  { date: "2026-03-28", score: 0.73 },
];

export type SessionData = typeof mockSession;
export type EngagementState = "engaged" | "passive" | "disengaged";
export type EventType = "yawn" | "looked_away" | "eyes_closed" | "zoned_out";
