# Roadmap & Priority Order

## Priority Tiers

### P0 — Must Have (Day 1)
**Goal:** Working demo — upload video, see timeline with labeled events, see dashboard.

| Task | Layer/Page | Owner | Status |
|------|-----------|-------|--------|
| MediaPipe FaceLandmarker integration | Backend L1 | | TODO |
| EAR, MAR, gaze, head pose extraction | Backend L2 | Amir | IN PROGRESS |
| Rule-based engagement classifier | Backend L3 | | TODO |
| Timeline event logger | Backend L4 | | TODO |
| `/analyze` POST endpoint | Backend L7 | | TODO |
| `/session/{id}` GET endpoint | Backend L7 | | TODO |
| Upload / Capture page | Frontend P1 | | TODO |
| Session Timeline page | Frontend P3 | | TODO |
| Analytics Dashboard page | Frontend P4 | | TODO |

### P1 — Should Have (Day 2 AM)
**Goal:** Live demo with webcam + polished output.

| Task | Layer/Page | Owner | Status |
|------|-----------|-------|--------|
| Session analytics engine | Backend L5 | | TODO |
| `/ws/live` WebSocket endpoint | Backend L7 | | TODO |
| Live Engagement Overlay page | Frontend P2 | | TODO |
| Personal Focus Report page | Frontend P5 | | TODO |

### P2 — Nice to Have (Day 2 PM)
**Goal:** AI coach + gamification = winning demo.

| Task | Layer/Page | Owner | Status |
|------|-----------|-------|--------|
| Claude API recommendation layer | Backend L6 | | TODO |
| `/session/{id}/insights` GET endpoint | Backend L7 | | TODO |
| AI Coach Suggestions page | Frontend P6 | | TODO |
| Session History + Compare page | Frontend P7 | | TODO |
| Focus Streak + Gamification page | Frontend P8 | | TODO |

## Work Split Suggestion

- **Backend dev(s):** Start with Layers 1-4 + API endpoints. Test with sample video before frontend is ready.
- **Frontend dev(s):** Start with Upload page + Timeline page using mock data. Wire to real API once backend endpoints are up.
- **Integration:** Connect frontend to backend once both sides have their P0 tasks working independently.

## Key Milestones

1. **Milestone 1:** Backend processes a video and outputs event JSON → test with curl/Postman
2. **Milestone 2:** Frontend renders a timeline from mock JSON data
3. **Milestone 3:** End-to-end — upload in browser, see real results
4. **Milestone 4:** Live webcam session works
5. **Milestone 5:** AI recommendations render on frontend
