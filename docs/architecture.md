# Architecture Overview

## System Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                       │
│                                                           │
│  Upload Page ─── Timeline ─── Dashboard ─── AI Coach     │
│       │              │            │             │         │
│       │         Video Player  Recharts      LLM Cards    │
│       │              │                                    │
│  Live Page ─── WebSocket ─── Overlay                     │
└───────┬──────────────┬────────────┬─────────────┬────────┘
        │              │            │             │
   POST /analyze  GET /session  GET /sessions  GET /insights
        │              │            │             │
        │         WS /ws/live       │             │
        │              │            │             │
┌───────▼──────────────▼────────────▼─────────────▼────────┐
│                  FastAPI Backend                           │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ API      │  │ Pipeline │  │ Storage  │               │
│  │ Routes   │──│          │──│ (SQLite) │               │
│  └──────────┘  │ L1 Detect│  └──────────┘               │
│                │ L2 Feature│                              │
│                │ L3 Classify│  ┌──────────┐              │
│                │ L4 Events │  │ Claude   │              │
│                │ L5 Stats  │──│ API      │              │
│                │ L6 LLM    │  │ (L6)     │              │
│                └──────────┘  └──────────┘               │
│                     │                                     │
│              ┌──────────┐                                │
│              │ MediaPipe│                                │
│              │ + OpenCV │                                │
│              └──────────┘                                │
└───────────────────────────────────────────────────────────┘
```

## Data Flow

### Video Upload Flow
```
User uploads video
  → POST /analyze
    → Save video to temp storage
    → For each frame (at ~10 FPS):
        → L1: MediaPipe FaceLandmarker → landmarks + blendshapes
        → L2: Extract features (EAR, MAR, gaze, head pose, expression variance)
        → L3: Classify engagement state
    → L4: Process feature stream into discrete events
    → L5: Aggregate events into session analytics
    → Store session data
    → Return session_id
  → Frontend redirects to /session/{id}/timeline
    → GET /session/{id} → render timeline + dashboard
```

### Live Session Flow
```
User clicks "Start Live Session"
  → Request camera permission
  → Connect WebSocket to /ws/live
  → For each captured frame:
      → Send frame via WebSocket
      → Server processes through L1-L3
      → Server sends back current state + features
      → Frontend updates overlay colors + indicators
  → On "Stop Session":
      → Server runs L4-L5 on accumulated data
      → Returns session_id
      → Frontend redirects to timeline view
```

### AI Insights Flow
```
GET /session/{id}/insights
  → Load session analytics from storage
  → Format prompt with session data
  → Call Claude API (claude-sonnet-4-6)
  → Parse and return recommendations
  → Cache results for subsequent requests
```

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Face model | MediaPipe FaceLandmarker | 478 landmarks + 52 blendshapes in one model, no training |
| Classification | Rule-based thresholds | No labeled data needed, hackathon-fast to implement |
| Storage | SQLite + JSON files | Zero setup, single file, good enough for demo |
| Frame rate | Process at ~10 FPS | Balance between accuracy and speed |
| LLM model | claude-sonnet-4-6 | Fast responses, good for structured analysis |
| Frontend | React + Recharts + Tailwind | Lovable-compatible, rich charting, fast styling |

## File-Level Dependency Map

```
app/main.py
  └── app/api/routes/*.py
        ├── app/engine/pipeline.py
        │     ├── app/engine/detection.py  (MediaPipe)
        │     ├── app/engine/features.py   (EAR, MAR, gaze, pose)
        │     └── app/engine/classifier.py (rules)
        ├── app/analytics/events.py        (event logger)
        ├── app/analytics/session.py       (aggregation)
        ├── app/analytics/recommendations.py (Claude API)
        └── app/storage/sessions.py        (persistence)
```

## Environment Variables

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...     # For Layer 6 (Claude API recommendations)

# Optional
MEDIAPIPE_MODEL_PATH=models/face_landmarker.task
STORAGE_DIR=data/sessions
MAX_UPLOAD_SIZE_MB=100
FRAME_SAMPLE_RATE=10             # FPS to process
LOG_LEVEL=INFO
```
