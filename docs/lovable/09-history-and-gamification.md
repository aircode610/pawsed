# Step 9: Session History + Gamification

> Paste this into Lovable. **Do not modify existing pages.**

---

Build two pages: Session History at `/sessions` and Gamification/Profile at `/profile`.

## Mock data

Add to `lib/mock-data.ts`:

```typescript
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
  { id: "first-session", name: "First Session", icon: "🎯", earned: true, date: "2026-03-24" },
  { id: "three-sessions", name: "Hat Trick", icon: "🎩", earned: true, date: "2026-03-26", description: "Complete 3 sessions" },
  { id: "streak-3", name: "3-Day Streak", icon: "🔥", earned: true, date: "2026-03-26", description: "3 consecutive days" },
  { id: "focus-80", name: "Laser Focus", icon: "🎯", earned: false, description: "Score 80%+ in a session" },
  { id: "streak-5", name: "5-Day Streak", icon: "⚡", earned: false, description: "5 consecutive days" },
  { id: "night-owl", name: "Night Owl", icon: "🦉", earned: false, description: "Complete a session after 9pm" },
  { id: "focus-90", name: "In The Zone", icon: "🧠", earned: false, description: "Score 90%+ in a session" },
  { id: "ten-sessions", name: "Dedicated", icon: "💪", earned: false, description: "Complete 10 sessions" },
];

export const mockWeeklyHeatmap = [
  { date: "2026-03-22", score: null },
  { date: "2026-03-23", score: null },
  { date: "2026-03-24", score: 0.65 },
  { date: "2026-03-25", score: 0.72 },
  { date: "2026-03-26", score: 0.78 },
  { date: "2026-03-27", score: null },
  { date: "2026-03-28", score: 0.73 },
];
```

---

## Page A: Session History (`/sessions`)

### Layout

**Top: Header**
- Heading: "Session History"
- Subtext: "Track your progress across sessions"

**Main: Session Cards (grid)**
- 2-column grid on desktop, 1 column on mobile
- Each card shows:
  - Video filename as title
  - Date (formatted nicely: "Mon, Mar 24")
  - Duration (formatted: "40 min")
  - Focus score as a prominent number with color (green/yellow/red)
  - Event count in muted text
  - **Sparkline**: a tiny line chart (Recharts `LineChart`, 100px wide, 30px tall, no axes) showing the engagement curve
- Clicking a card navigates to `/session/:id/timeline`

**Compare feature:**
- Each card has a checkbox in the corner: "Compare"
- When exactly 2 cards are checked, show a **comparison panel** that slides in at the bottom:
  - Side by side: Session A name & score vs Session B name & score
  - Delta: "+6.6% improvement" (or decline) with colored arrow
  - A "View Comparison" button (for now, just show the delta — no separate page needed)
- When fewer or more than 2 are checked, hide the comparison panel

**Sort controls:**
- Small dropdown or toggle: "Sort by: Date / Focus Score"

---

## Page B: Gamification / Profile (`/profile`)

### Layout

**Top: Streak Counter**
- Large number: "3" with a flame icon
- Label: "Day Streak"
- Subtext: "Keep it going! 2 more days for the 5-Day Streak badge"
- Animated flame icon (subtle CSS pulse animation)

**Section: Weekly Heatmap**
- A row of 7 squares (Mon–Sun) for the current week
- Each square colored by engagement score:
  - No session: dark/empty (`slate-800`)
  - Score < 0.5: red
  - Score 0.5–0.7: yellow
  - Score > 0.7: green
  - Color intensity varies with score (higher = more saturated)
- Day label below each square (M, T, W, T, F, S, S)
- Heading: "This Week"

**Section: Badges**
- Grid of badge cards (3 columns on desktop, 2 on mobile)
- Earned badges: full color, icon large, name bold, date earned in muted text
- Unearned badges: greyed out (opacity 40%), with the requirement shown: "Score 80%+ in a session"
- Earned badges should have a subtle shine/glow effect

**Section: Trend**
- A small Recharts `LineChart` showing focus_time_pct across the 4 mock sessions
- X-axis: dates, Y-axis: focus %
- Line should trend upward (our mock data does)
- Heading: "Your Focus Trend"
- Subtext showing overall change: "+7.3% from first session"

## Style
- Session cards should be interactive — slight scale on hover
- The gamification page should feel rewarding and motivational
- Badges grid should feel like a collection — think achievement gallery
- Use warm colors for the streak section (orange/flame tones)
