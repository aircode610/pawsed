# Frontend Specification

## Overview
React + TypeScript frontend. Can be scaffolded with Lovable or Vite. Uses Recharts for data viz, Tailwind for styling, and connects to the FastAPI backend via REST + WebSocket.

## Shared Components

### EngagementBadge
Colored badge showing engagement state. Green = engaged, yellow = passive, red = disengaged.

### TimelineBar
Horizontal bar divided into colored segments based on engagement over time. Clickable segments.

### MetricCard
Card displaying a headline number with label (e.g., "72% Focused").

### EventMarker
Small icon on the timeline representing a distraction event. Tooltip on hover, click to seek video.

---

## Page 1: Upload / Capture (`/`)
**Priority:** P0

**Layout:**
- Header with logo + nav
- Two-column or tabbed layout: "Upload Video" | "Live Session"
- Upload side: drag-and-drop zone, accepted formats (.mp4, .webm, .mov), file size limit display
- Live side: "Start Session" button, permission prompt for camera
- Processing state: progress bar, video thumbnail, estimated time

**API calls:**
- `POST /analyze` with video file (multipart form) → returns `{ session_id }`
- On success, redirect to `/session/{id}/timeline`

**Live mode:**
- Request camera permission
- Open WebSocket to `/ws/live`
- Redirect to `/live` page

---

## Page 2: Live Engagement Overlay (`/live`)
**Priority:** P1

**Layout:**
- Full-width webcam feed (via `<video>` element + getUserMedia)
- Colored border around video: green/yellow/red based on current state
- Corner overlay panel showing:
  - Current engagement state label
  - EAR value (small gauge or number)
  - Gaze direction indicator (arrow or dot on a small face diagram)
  - Head pose (pitch/yaw numbers)
- "Stop Session" button → closes WebSocket, redirects to timeline page

**WebSocket:**
- Connect to `/ws/live`
- Send video frames as base64 or use server-side capture
- Receive: `{ state: "engaged"|"passive"|"disengaged", features: {...}, event?: {...} }`

---

## Page 3: Session Timeline (`/session/{id}/timeline`)
**Priority:** P0

**Layout:**
- Top: Video player (uploaded video playback)
- Below video: TimelineBar — color-coded horizontal bar synced with video playback
  - Green segments = engaged
  - Yellow segments = passive
  - Red segments = disengaged
  - EventMarkers as clickable icons on the bar
- Below timeline: Event list table
  - Columns: Time, Event Type, Duration, Confidence
  - Click row → seek video to that timestamp
- Sidebar or top-right: Quick stats (focus %, session duration, event count)

**API calls:**
- `GET /session/{id}` → event timeline + engagement states

**Interactions:**
- Video playback updates timeline cursor position
- Click on timeline segment → seek video
- Click on event marker → seek video + highlight event in list

---

## Page 4: Analytics Dashboard (`/session/{id}/analytics`)
**Priority:** P0

**Layout:**
- Header: Session date, duration, headline metric ("72% Focused")
- Row 1: Engagement over time — area chart (Recharts AreaChart), x-axis = minutes, y-axis = engagement score, colored fill
- Row 2:
  - Left: Pie chart — time distribution (engaged/passive/disengaged)
  - Right: Bar chart — distraction types (yawn, looked_away, eyes_closed, zoned_out)
- Row 3:
  - Focus streak card (longest streak duration)
  - Danger zones list (time ranges with low engagement)

**API calls:**
- `GET /session/{id}` → analytics data

---

## Page 5: Personal Focus Report (`/session/{id}/report`)
**Priority:** P1

**Layout:**
- Designed to be shareable / printable (clean layout, no nav chrome)
- Top: Date, duration, overall engagement score (large circular gauge)
- Middle: Top 3 distraction patterns with icons and counts
- Bottom: Comparison to student's average (if multiple sessions exist)
- "Share" button (copy link or download as image)
- Think "Spotify Wrapped" aesthetic — bold colors, large numbers, minimal text

---

## Page 6: AI Coach Suggestions (`/session/{id}/insights`)
**Priority:** P2

**Layout:**
- Conversational card layout — each recommendation is a card
- Cards include: icon, title, description, specific reference to session data
- Example card: "Your longest focus streak was 11 minutes — try extending it to 15 using the Pomodoro technique."
- Loading state while LLM generates (streaming text effect if possible)
- "Regenerate" button to get fresh suggestions

**API calls:**
- `GET /session/{id}/insights` → recommendation strings

---

## Page 7: Session History (`/sessions`)
**Priority:** P2

**Layout:**
- List/grid of past sessions
- Each card: date, duration, focus %, sparkline engagement curve
- Select two sessions → side-by-side comparison view
  - Two engagement curves overlaid or stacked
  - Delta metrics: "+12% improvement"
- Sort by date, focus score

**API calls:**
- `GET /sessions` → list of session summaries

---

## Page 8: Gamification (`/profile`)
**Priority:** P2

**Layout:**
- Focus streak counter (consecutive sessions above threshold)
- Badge gallery: "5-day streak!", "First session", "90%+ focus", "Night owl" (late session)
- Weekly heatmap calendar — engagement scores color-coded by day
- Weekly/monthly trend line

---

## Frontend Dependencies
```json
{
  "react": "^18",
  "react-router-dom": "^6",
  "recharts": "^2",
  "tailwindcss": "^3",
  "@radix-ui/react-*": "latest",
  "lucide-react": "latest",
  "clsx": "^2",
  "tailwind-merge": "^2"
}
```

## Design Tokens
- **Engaged:** `#22c55e` (green-500)
- **Passive:** `#eab308` (yellow-500)
- **Disengaged:** `#ef4444` (red-500)
- **Background:** `#0f172a` (slate-900) or white depending on theme
- **Font:** Inter or system font stack
