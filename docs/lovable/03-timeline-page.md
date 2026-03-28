# Step 3: Session Timeline Page

> Paste this into Lovable. This is the core feature page. **Do not modify existing pages or the sidebar.**

---

Build the Session Timeline page at route `/session/:id/timeline`. This is the main differentiator — video playback synced with a color-coded engagement timeline.

## Mock data

Create this in `lib/mock-data.ts` (or add to it if it already exists). This data simulates a 30-minute session:

```typescript
export const mockSession = {
  session_id: "demo",
  created_at: "2026-03-28T14:30:00Z",
  duration: 1800, // 30 minutes in seconds
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
```

## Layout

### Top section: Video Player
- A placeholder video player area (dark rectangle, 16:9 aspect ratio)
- Since we don't have a real video file, show a dark area with a play button icon and text "Video playback — connect to upload"
- Show a standard video scrub bar underneath
- Display current time / total time in the corner (use the mock session duration)

### Middle section: Timeline Bar
- A horizontal bar spanning the full width, about 40px tall
- Divided into colored segments based on `engagement_states`:
  - Green (`#22c55e`) for engaged
  - Yellow (`#eab308`) for passive
  - Red (`#ef4444`) for disengaged
- Each segment's width is proportional to its duration relative to total session time
- Event markers appear as small dots/icons on the timeline at their timestamp position:
  - 😴 or `Eye` icon for eyes_closed
  - 🥱 or `Circle` icon for yawn
  - 👀 or `ArrowLeft`/`ArrowRight` icon for looked_away
  - 💤 or `Moon` icon for zoned_out
- Hovering an event marker shows a tooltip: "Yawn at 4:32 — 3.2s"
- A vertical cursor line shows the current playback position
- Clicking anywhere on the timeline updates the "current time"

### Bottom section: Event List
- A table/list of all events, sorted by timestamp
- Columns: Time (formatted as mm:ss), Event Type (with colored icon), Duration, Confidence
- Each row is clickable — clicking updates the timeline cursor to that timestamp
- The event type should have a small colored dot: red for disengaged events, yellow for passive
- Highlight the "active" event (the one closest to current playback time)

### Top-right corner: Quick Stats
- Three small metric cards in a row:
  - Focus: "72.5%" with green text
  - Duration: "30:00"
  - Events: "13"

## Sub-navigation
Add a tab bar or secondary nav between the video and timeline that links to the sub-pages for this session:
- **Timeline** (current, active) → `/session/:id/timeline`
- **Analytics** → `/session/:id/analytics`
- **Report** → `/session/:id/report`
- **AI Coach** → `/session/:id/insights`

## Interactions
- Clicking a timeline segment or event marker updates the current time display
- Clicking an event in the list scrolls the timeline cursor to that position
- The timeline cursor position is shared state (React state or context)

## Style
- The timeline bar should have rounded corners and a subtle border
- Event markers should have a slight pop-up animation on hover
- The event list should have alternating row backgrounds for readability
- Danger zones from the analytics should have a subtle red background overlay on the timeline
