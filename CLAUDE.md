# EngageSense - Project Instructions

## Project Overview
EngageSense is a student engagement detection and analytics platform. It uses MediaPipe's 478 landmarks + 52 blendshapes to detect attention levels from video, then provides personalized recommendations via Claude API.

**Stack:** Python + FastAPI (backend) | React via Lovable (frontend) | MediaPipe + OpenCV | Claude API

## Repository Structure
```
pawsed/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── api/
│   │   │   ├── routes/          # REST + WebSocket endpoints
│   │   │   └── deps.py          # Shared dependencies
│   │   ├── core/
│   │   │   ├── config.py        # Settings (env vars, model paths)
│   │   │   └── security.py      # CORS, auth if needed
│   │   ├── engine/
│   │   │   ├── detection.py     # Layer 1: MediaPipe FaceLandmarker
│   │   │   ├── features.py      # Layer 2: EAR, MAR, gaze, head pose
│   │   │   ├── classifier.py    # Layer 3: Engagement classification
│   │   │   └── pipeline.py      # Orchestrates layers 1-3 per frame
│   │   ├── analytics/
│   │   │   ├── events.py        # Layer 4: Timeline event logger
│   │   │   ├── session.py       # Layer 5: Session analytics
│   │   │   └── recommendations.py # Layer 6: Claude API integration
│   │   ├── models/
│   │   │   ├── schemas.py       # Pydantic models for API
│   │   │   └── events.py        # Event data models
│   │   └── storage/
│   │       └── sessions.py      # Session persistence (SQLite/JSON)
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                    # React app (Lovable-generated or manual)
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
├── docs/
│   ├── roadmap.md               # Feature roadmap & priority order
│   ├── backend-spec.md          # Backend layers specification
│   ├── frontend-spec.md         # Frontend pages specification
│   ├── api-spec.md              # API endpoint documentation
│   └── architecture.md          # System architecture overview
├── models/                      # MediaPipe model files (.task)
├── CLAUDE.md                    # This file
└── README.md
```

## Development Commands

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest tests/
```

### Frontend
```bash
cd frontend
npm install
npm run dev          # dev server on port 5173
npm run build        # production build
```

## Key Technical Decisions

- **MediaPipe FaceLandmarker** over dlib/Haar — 478 landmarks + 52 blendshapes, runs in-browser or Python, no training needed
- **Rule-based classifier** over ML — sufficient for hackathon, no labeled data needed
- **SQLite or JSON file storage** — no database server to manage during hackathon
- **Claude API** for recommendations — Layer 6, nice-to-have priority
- **WebSocket** for live session streaming — `/ws/live` endpoint

## Coding Conventions

- **Python:** Use type hints everywhere. Pydantic models for all data shapes. Async FastAPI handlers.
- **Frontend:** TypeScript strict mode. Components in PascalCase. Hooks prefixed with `use`.
- **API responses:** Always return JSON with consistent envelope: `{ data, error, meta }`.
- **Env vars:** All secrets and config via `.env` file, never hardcoded. Use `pydantic-settings`.

## Important Context

- This is a **hackathon project** — favor speed and working demos over perfection.
- The **priority order** is: Must Have (Day 1) → Should Have (Day 2 AM) → Nice to Have (Day 2 PM). See `docs/roadmap.md`.
- **Must-have for demo:** Upload video → see color-coded timeline with labeled events → see analytics dashboard.
- The frontend may be partially generated via **Lovable** — treat its output as a starting point to customize.
- Two reference repos inspired this project: `attention-monitor` (yptheangel) and `Student-Attentiveness-System` (anupampatil44). We surpass both with MediaPipe 478 landmarks, polished frontend, and personalized recommendations.

## When Working on Backend Layers

- **Layer 1 (Detection):** Use `mediapipe.tasks.vision.FaceLandmarker`. Download the `.task` model file into `models/`.
- **Layer 2 (Features):** EAR formula uses landmarks 33,160,158,133,153,144 (right eye) and mirrored for left. MAR uses lip landmarks. Gaze uses blendshapes `eyeLookDown_L/R`, `eyeLookUp_L/R`, `eyeLookIn_L/R`, `eyeLookOut_L/R`.
- **Layer 3 (Classifier):** Three states: `engaged`, `passive`, `disengaged`. Use thresholds on feature vector. Make thresholds configurable.
- **Layer 4 (Events):** Every event is `{timestamp, event_type, duration, confidence, metadata}`.
- **Layer 5 (Analytics):** Aggregate into focus_time_pct, longest_streak, distraction_breakdown, engagement_curve (1-min bins), danger_zones.
- **Layer 6 (LLM):** Send session summary to Claude API. Use `claude-sonnet-4-6` for speed. Prompt should request actionable, friendly study tips.

## Do NOT

- Do not use dlib or Haar cascades — we use MediaPipe exclusively.
- Do not add authentication unless explicitly asked — hackathon scope.
- Do not over-engineer storage — flat files or SQLite are fine.
- Do not add features beyond the current priority tier without checking with the team.
