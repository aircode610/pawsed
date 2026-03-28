# Pawsed

**AI-powered student engagement detection and analytics platform.** *Paused + Paws — for when attention pauses.*

Pawsed helps lecturers understand where they lose student attention during lectures. Upload a recording or use a live webcam session — the system analyzes facial cues and provides a color-coded engagement timeline, section-by-section scoring, and an AI teaching coach powered by Claude.

## What It Does

1. **Detects** facial landmarks, eye state, gaze direction, head pose, and expressions using MediaPipe (478 landmarks + 52 blendshapes)
2. **Classifies** engagement into three levels: Engaged, Passive, Disengaged
3. **Logs** timestamped distraction events (yawns, looking away, eyes closed, etc.)
4. **Scores** each lecture section with AI-generated teaching advice
5. **Coaches** lecturers via an interactive AI chat that references their session data

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Detection Engine | MediaPipe FaceLandmarker |
| Video Processing | OpenCV |
| Backend API | Python + FastAPI |
| AI Pipelines | LangGraph + Claude API (Anthropic) |
| Frontend | React + TypeScript + Tailwind + shadcn/ui |
| Charts | Recharts |
| Storage | JSON files |

---

## Running the Project

### Prerequisites

- Python 3.11+ (tested with 3.14)
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com/) (for AI insights features)

### 1. Backend

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Start the server
uvicorn app.main:app --reload --port 8000
```

The API is now running at **http://localhost:8000**. Check http://localhost:8000/docs for the interactive Swagger UI.

### 2. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The frontend is now running at **http://localhost:8080**.

### 3. Use It

1. Open **http://localhost:8080** in your browser
2. Upload a lecture video (MP4, WebM, or MOV) or click "Start Live Session"
3. After processing, you'll see the engagement timeline, analytics dashboard, and AI insights
4. On the Insights page, use the teaching coach chat to ask questions about your lecture

> **Note:** If the backend is not running, all pages gracefully fall back to built-in mock data so you can demo the frontend independently.

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze` | POST | Upload video for engagement analysis |
| `/session/{id}` | GET | Full event timeline + analytics |
| `/session/{id}/insights/sections` | GET | Section-by-section scoring with AI notes |
| `/session/{id}/insights/chat` | POST | Teaching coach conversation |
| `/sessions` | GET | Session history with pagination |
| `/ws/live` | WebSocket | Real-time engagement streaming |
| `/health` | GET | Health check |

## Project Structure

```
pawsed/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── core/config.py          # Settings (env vars)
│   │   ├── api/routes/
│   │   │   ├── sessions.py         # /analyze, /session, /sessions
│   │   │   ├── insights.py         # /insights/sections, /insights/chat
│   │   │   └── websocket.py        # /ws/live
│   │   ├── engine/
│   │   │   ├── pipeline.py         # L1→L2→L3 orchestrator
│   │   │   ├── features.py         # L2: EAR, MAR, gaze, head pose
│   │   │   └── classifier.py       # L3: rule-based engagement classifier
│   │   ├── analytics/
│   │   │   ├── prompts.py          # All LLM prompt templates
│   │   │   ├── section_scoring.py  # LangGraph: lecture section scoring
│   │   │   ├── teaching_coach.py   # LangGraph: conversational coach
│   │   │   └── events.py           # L4: timeline event logger
│   │   ├── models/
│   │   │   ├── schemas.py          # Dataclasses: detection pipeline
│   │   │   └── analytics.py        # Pydantic: AI pipeline models
│   │   └── storage/sessions.py     # JSON file persistence
│   ├── tests/                       # pytest test suite
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/                   # 8 pages (Upload, Live, Timeline, etc.)
│   │   ├── components/              # Shared UI components
│   │   ├── hooks/                   # React hooks (session data, mock chat)
│   │   └── lib/
│   │       ├── api.ts               # Backend API client
│   │       ├── types.ts             # TypeScript interfaces
│   │       └── mock-data.ts         # Demo/fallback data
│   ├── package.json
│   └── .env.example
├── docs/
│   ├── roadmap.md                   # Priority tiers and task tracking
│   ├── backend-spec.md              # Layer-by-layer backend spec
│   ├── frontend-spec.md             # Page-by-page frontend spec
│   ├── api-spec.md                  # Full API documentation
│   ├── architecture.md              # System architecture
│   ├── ai-insights-spec.md          # Section scoring + teaching coach spec
│   └── lovable/                     # Step-by-step Lovable prompts
└── CLAUDE.md                        # Agent instructions for this project
```

## Running Tests

```bash
cd backend
source .venv/bin/activate

# Run all tests (skips LLM tests if no API key)
PYTHONPATH=. pytest tests/ -v

# Run only non-LLM tests (fast, no API key needed)
PYTHONPATH=. pytest tests/ -v -k "not LLM"

# Run with LLM evals (requires ANTHROPIC_API_KEY in env)
ANTHROPIC_API_KEY=sk-ant-... PYTHONPATH=. pytest tests/ -v
```

## Documentation

- [Roadmap & Priorities](docs/roadmap.md)
- [Backend Specification](docs/backend-spec.md)
- [Frontend Specification](docs/frontend-spec.md)
- [API Specification](docs/api-spec.md)
- [Architecture Overview](docs/architecture.md)
- [AI Insights Specification](docs/ai-insights-spec.md)
- [Lovable Frontend Guide](docs/lovable/README.md)

## Inspired By

- [attention-monitor](https://github.com/yptheangel/attention-monitor) — Face landmark tracking with dlib + PyQtGraph
- [Student-Attentiveness-System](https://github.com/anupampatil44/Student-Attentiveness-System) — Expression + head pose detection with MTCNN

Pawsed goes beyond both with MediaPipe's superior model, a polished web frontend, session analytics, and AI-powered teaching recommendations.

## License

MIT
