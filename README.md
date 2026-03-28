# Pawsed

**AI-powered student engagement detection and analytics platform.** *Paused + Paws — for when attention pauses.*

Pawsed analyzes video of students during lectures to detect engagement levels in real-time, generates a color-coded timeline of attention events, and provides personalized study recommendations powered by Claude AI.

## What It Does

1. **Detects** facial landmarks, eye state, gaze direction, head pose, and expressions using MediaPipe (478 landmarks + 52 blendshapes)
2. **Classifies** engagement into three levels: Engaged, Passive, Disengaged
3. **Logs** timestamped distraction events (yawns, looking away, eyes closed, etc.)
4. **Analyzes** session-level metrics — focus percentage, streaks, danger zones
5. **Recommends** personalized study tips via Claude AI

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Detection Engine | MediaPipe FaceLandmarker |
| Video Processing | OpenCV |
| Backend API | Python + FastAPI |
| Frontend | React (Lovable) + TypeScript |
| Charts | Recharts |
| AI Recommendations | Claude API (Anthropic) |
| Storage | SQLite / JSON |

## Quick Start

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # Add your ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` — upload a video or start a live session.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze` | POST | Upload video or start webcam analysis |
| `/session/{id}` | GET | Full event timeline + analytics |
| `/session/{id}/insights` | GET | AI-generated recommendations |
| `/sessions` | GET | Session history |
| `/ws/live` | WebSocket | Real-time engagement streaming |

## Project Structure

```
pawsed/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── engine/    # Detection, features, classifier
│   │   ├── analytics/ # Events, session stats, LLM recommendations
│   │   ├── api/       # REST + WebSocket routes
│   │   └── models/    # Pydantic schemas
│   └── tests/
├── frontend/          # React frontend
│   └── src/
│       ├── pages/     # Upload, Live, Timeline, Dashboard, Report, Coach, History, Gamification
│       └── components/
├── docs/              # Detailed specs and roadmap
└── models/            # MediaPipe .task model files
```

## Documentation

- [Roadmap & Priorities](docs/roadmap.md)
- [Backend Specification](docs/backend-spec.md)
- [Frontend Specification](docs/frontend-spec.md)
- [API Specification](docs/api-spec.md)
- [Architecture Overview](docs/architecture.md)

## Inspired By

- [attention-monitor](https://github.com/yptheangel/attention-monitor) — Face landmark tracking with dlib + PyQtGraph
- [Student-Attentiveness-System](https://github.com/anupampatil44/Student-Attentiveness-System) — Expression + head pose detection with MTCNN

Pawsed goes beyond both with MediaPipe's superior model, a polished web frontend, session analytics, and AI-powered recommendations.

## Team

Built for hackathon — see [docs/roadmap.md](docs/roadmap.md) for priority order and task assignments.

## License

MIT
