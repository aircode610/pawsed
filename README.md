# Pawsed

**AI-powered student engagement detection and analytics for lecturers.** *Paused + Paws — for when attention pauses.*

Pawsed lets lecturers upload a recorded lecture (or run a live webcam session) and get back a color-coded engagement timeline, per-student distraction events, section-by-section AI scoring, and an interactive teaching coach — all powered by MediaPipe's face model and Claude.

---

## How It Works

### The Detection Pipeline (6 Layers)

Every video frame passes through a sequential stack of layers before results hit the database:

```
Video frame
    │
    ▼
Layer 1 — Detection (MediaPipe FaceLandmarker)
    478 facial landmarks + 52 ARKit blendshapes per face
    Tiled detection fallback for small faces (Zoom/Teams grids)
    │
    ▼
Layer 2 — Feature Extraction
    EAR  (Eye Aspect Ratio)     — eye open/closed state
    MAR  (Mouth Aspect Ratio)   — yawn detection via jawOpen blendshape
    Gaze score                  — eyeLook* blendshapes → on-screen vs away
    Head pose                   — yaw / pitch / roll from 4×4 transform matrix
    Expression variance         — 30-frame rolling std dev of blendshapes
    Drowsiness score            — composite: blink rate + partial closure
    Head motion                 — fidgeting intensity from pose std deviation
    Brow furrow                 — confusion / cognitive load
    │
    ▼
Layer 3 — Engagement Classifier (rule-based, stateful)
    ENGAGED      — default; fewer than 2 passive signals
    PASSIVE      — 2+ simultaneous signals (drifting gaze, frozen face, slight turn…)
    DISENGAGED   — any single sustained trigger:
                   eyes closed >0.5s, yawn >2s, gaze away >3s,
                   head turned >15°, drowsiness >0.6 for >2s, fidgeting >2s
    │
    ▼
Layer 4 — Event Logger
    Emits discrete timestamped events when a distraction ends
    Types: yawn, eyes_closed, looked_away, looked_down,
           drowsy, distracted, zoned_out, face_lost
    │
    ▼
Layer 5 — Session Analytics
    focus_time_pct, longest_streak, distraction_breakdown
    engagement_curve (per-minute bins), danger_zones
    Classroom-level risk: LOW / MODERATE / HIGH / CRITICAL
    │
    ▼
Layer 6 — AI Insights (Claude + LangGraph)
    Section scoring  — lecture split into ~5-min windows,
                       Claude generates per-section teaching notes
    Teaching coach   — multi-turn chat with full session context injected
```

### Multi-Face Support

The pipeline tracks **multiple students simultaneously** using stable face IDs across frames. Each face gets its own feature extractor and classifier instance. Classroom-level risk is computed from the percentage of disengaged faces per frame — so one distracted student in a class of 20 doesn't spike the risk level.

### Landmarks Overlay

After analysis, Pawsed renders an annotated video with face mesh, engagement state border, and per-face metrics overlaid. The overlay reuses the landmarks already extracted during analysis — **MediaPipe runs exactly once per session**, not twice.

---

## Performance

MediaPipe inference (62ms/frame on CPU) is the sole bottleneck — feature extraction and classification combined take under 0.2ms/frame. Three optimizations were applied to make processing fast enough for full lecture videos:

### 1. Parallel Chunk Processing

The video is split into N equal frame ranges and each chunk is processed by a separate worker process with its own MediaPipe instance. Results are merged by timestamp after all workers complete.

```
Video ──┬── chunk 0 → worker 0 → [FrameResult, ...]
        ├── chunk 1 → worker 1 → [FrameResult, ...]
        ├── chunk 2 → worker 2 → [FrameResult, ...]   ──► merge ──► analytics
        ├── chunk 3 → worker 3 → [FrameResult, ...]
        └── chunk N → worker N → [FrameResult, ...]
```

Workers use `ProcessPoolExecutor` (bypasses the GIL for CPU-bound inference). Each chunk seeks once to its start frame and then reads sequentially — per-frame random seeking in H.264 is ~12× slower than sequential decoding and was explicitly benchmarked and ruled out.

### 2. Reduced Processing FPS

Engagement states require sustained conditions (0.5–3s) to trigger, so sampling every 200ms (5fps) captures all real events. This halves the number of MediaPipe calls vs the naive 10fps default.

### 3. Overlay Reuse

The landmarks overlay is rendered from the face data already captured during analysis (`FaceData` stored in `FaceResult`). No second detection pass.

### Benchmark — 96.8s test video, 60fps source, Apple M1 Max

| Optimization | Pipeline time | Total API response |
|---|---|---|
| Baseline (sequential, 10fps) | 62.7s | ~107s (overlay blocking) |
| + Parallel workers (5×) | 21.5s | ~30s |
| + Overlay from pre-computed results | 21.5s | ~30s |
| + 8 workers + 5fps | **9.5s** | **~17s** |
| **Overall speedup** | **6.6×** | **6.3×** |

For a 1-hour lecture: **~6 minutes** to process (down from ~39 minutes with the original sequential approach).

---

## Tech Stack

| Component | Technology |
|---|---|
| Face detection | MediaPipe FaceLandmarker (478 landmarks + 52 blendshapes) |
| Video I/O | OpenCV |
| Parallelism | Python `ProcessPoolExecutor` |
| Backend API | FastAPI + Python 3.11 |
| AI pipelines | LangGraph + Claude API (`claude-sonnet-4-6`) |
| Auth | JWT (python-jose) |
| Database | SQLite via SQLAlchemy |
| Results persistence | Pickle sidecar files (for overlay regeneration) |
| Frontend | React + TypeScript + Vite + Tailwind + shadcn/ui |
| Charts | Recharts |

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Anthropic API key](https://console.anthropic.com/) (for AI insights; all other features work without it)

### Backend

```bash
cd backend

python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

uvicorn app.main:app --reload --port 8000
```

API docs available at **http://localhost:8000/docs**.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:8080**.

### Usage

1. Open **http://localhost:8080**
2. Sign up, then upload a lecture video (MP4, WebM, MOV) or start a Live Session
3. Wait ~17s for a 2-min video — the analytics dashboard and landmarks overlay are ready together
4. Toggle **Landmarks** on the video player to see the face mesh and per-frame engagement state
5. Go to the **Insights** tab for section-by-section AI scoring and the teaching coach chat

> The frontend falls back to built-in mock data if the backend is unreachable, so you can demo the UI standalone.

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/analyze` | POST | Upload video — runs full pipeline, returns `session_id` |
| `/session/{id}` | GET | Full session: events, analytics, `has_landmarks` flag |
| `/session/{id}/video` | GET | Serve original video or landmarks overlay (`?landmarks=true`) |
| `/session/{id}/insights/sections` | GET | Section scoring with AI teaching notes |
| `/session/{id}/insights/chat` | POST | Teaching coach conversation |
| `/sessions` | GET | Session history (paginated, sortable by date or score) |
| `/ws/live` | WebSocket | Real-time per-frame engagement streaming |
| `/auth/signup` | POST | Create lecturer account |
| `/auth/login` | POST | Get JWT token |

---

## Project Structure

```
pawsed/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   └── config.py              # Settings — processing_fps, model_path, etc.
│   │   ├── api/routes/
│   │   │   ├── sessions.py            # /analyze, /session, /sessions, /video
│   │   │   ├── insights.py            # /insights/sections, /insights/chat
│   │   │   ├── auth.py                # /auth/signup, /auth/login
│   │   │   └── websocket.py           # /ws/live
│   │   ├── engine/
│   │   │   ├── pipeline.py            # Orchestrator: parallel chunk processing
│   │   │   ├── detection.py           # L1: MediaPipe FaceLandmarker wrapper
│   │   │   ├── features.py            # L2: EAR, MAR, gaze, head pose, drowsiness
│   │   │   ├── classifier.py          # L3: stateful rule-based classifier
│   │   │   ├── tracker.py             # Multi-face stable ID tracker
│   │   │   └── overlay.py             # Landmarks video renderer (no re-detection)
│   │   ├── analytics/
│   │   │   ├── events.py              # L4: timestamped distraction event logger
│   │   │   ├── session.py             # L5: session aggregation
│   │   │   ├── section_scoring.py     # L6: LangGraph section scoring pipeline
│   │   │   ├── teaching_coach.py      # L6: LangGraph teaching coach
│   │   │   └── recommendations.py     # Claude API integration
│   │   ├── models/
│   │   │   └── schemas.py             # FaceData, FeatureVector, FrameResult, etc.
│   │   ├── db/
│   │   │   ├── database.py            # SQLAlchemy setup
│   │   │   └── models.py              # Session, User ORM models
│   │   └── storage/
│   │       └── sessions.py            # Session persistence — analytics, events
│   ├── tests/                         # pytest suite (50 tests, no API key needed)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/                     # Upload, Timeline, Insights, History, Live
│   │   ├── components/                # Shared UI components
│   │   ├── hooks/                     # useSessionData, useSectionScoring, etc.
│   │   └── lib/
│   │       ├── api.ts                 # Backend client
│   │       ├── types.ts               # TypeScript interfaces
│   │       └── mock-data.ts           # Fallback demo data
│   └── package.json
├── docs/                              # Specs, roadmap, architecture diagrams
├── models/                            # face_landmarker.task (MediaPipe model file)
└── CLAUDE.md
```

---

## Running Tests

```bash
cd backend
source .venv/bin/activate

# Full test suite (50 tests, no API key required)
PYTHONPATH=. pytest tests/ -v

# Skip LLM integration tests
PYTHONPATH=. pytest tests/ -v -k "not LLM"
```

---

## Inspired By

- [attention-monitor](https://github.com/yptheangel/attention-monitor) — dlib + PyQtGraph face tracking
- [Student-Attentiveness-System](https://github.com/anupampatil44/Student-Attentiveness-System) — MTCNN expression + head pose detection

Pawsed goes beyond both: MediaPipe's 478-landmark model, multi-face classroom tracking, a polished React dashboard, session persistence, and AI-generated teaching advice.

---

## License

MIT
