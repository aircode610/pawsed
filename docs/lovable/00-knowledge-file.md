# Lovable Knowledge File

> Paste this into Lovable's **Knowledge File** setting. It gets sent with every prompt automatically.

---

## Product: Pawsed (paused + paws — for when attention pauses)

An AI-powered student engagement detection platform. Students upload lecture videos or use their webcam live — the system analyzes facial cues (eye closure, yawning, gaze direction, head pose) and provides a detailed engagement timeline, analytics dashboard, and AI-powered study recommendations.

## Design System

- **Style**: Clean, modern SaaS aesthetic. Dark mode primary, light mode optional.
- **Font**: Inter (or system font stack)
- **Border radius**: Rounded (0.75rem default)
- **Spacing**: Generous padding, avoid cramped layouts
- **Animations**: Subtle transitions, no flashy effects

### Color Tokens

| Token | Hex | Usage |
|-------|-----|-------|
| Engaged | `#22c55e` (green-500) | Engaged state indicators, timeline segments |
| Passive | `#eab308` (yellow-500) | Passive state indicators, timeline segments |
| Disengaged | `#ef4444` (red-500) | Disengaged state indicators, timeline segments |
| Primary | `#6366f1` (indigo-500) | Buttons, links, active states |
| Background | `#0f172a` (slate-900) | Page background (dark mode) |
| Surface | `#1e293b` (slate-800) | Card backgrounds (dark mode) |
| Text | `#f8fafc` (slate-50) | Primary text (dark mode) |
| Muted | `#94a3b8` (slate-400) | Secondary text, labels |

Store these in `tailwind.config.ts` under `theme.extend.colors.engage`.

### Component Rules

- Use **shadcn/ui** components for all UI elements (Button, Card, Dialog, etc.)
- Use **Lucide React** for icons
- Use **Recharts** for all charts and data visualization
- All pages must be responsive (mobile-first breakpoints)
- Cards should have subtle borders, not heavy shadows

## Pages & Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | Upload / Capture | Landing page with video upload + live session start |
| `/live` | Live Overlay | Webcam feed with real-time engagement border |
| `/session/:id/timeline` | Session Timeline | Video playback + color-coded timeline bar |
| `/session/:id/analytics` | Analytics Dashboard | Charts and engagement metrics |
| `/session/:id/report` | Focus Report | Shareable one-page summary |
| `/session/:id/insights` | AI Coach | LLM-generated study recommendations |
| `/sessions` | Session History | List of past sessions with comparison |
| `/profile` | Gamification | Streaks, badges, weekly heatmap |

## API Contract

The frontend connects to a FastAPI backend. For now, use mock data. The API will be at `http://localhost:8000`.

### Key Response Shapes

**Session data** (`GET /session/:id`):
```json
{
  "data": {
    "session_id": "abc123",
    "duration": 1800,
    "analytics": {
      "focus_time_pct": 72.5,
      "longest_focus_streak": 660,
      "distraction_breakdown": { "yawn": 3, "looked_away": 7, "eyes_closed": 2 },
      "engagement_curve": [0.85, 0.78, 0.65, 0.72, 0.90, 0.45, 0.80],
      "danger_zones": [{ "start": 720, "end": 1080, "avg_score": 0.35 }]
    },
    "events": [
      { "timestamp": 272, "event_type": "yawn", "duration": 3.2, "confidence": 0.87 },
      { "timestamp": 435, "event_type": "looked_away", "duration": 8.1, "confidence": 0.92 }
    ],
    "engagement_states": [
      { "start": 0, "end": 272, "state": "engaged" },
      { "start": 272, "end": 280, "state": "disengaged" },
      { "start": 280, "end": 435, "state": "engaged" }
    ]
  }
}
```

## Rules

- Always use TypeScript strict mode
- Components in PascalCase, hooks prefixed with `use`
- Keep mock data in `lib/mock-data.ts` — we will replace it with real API calls later
- Do not add authentication or login pages
- Do not use Supabase — we have our own FastAPI backend
