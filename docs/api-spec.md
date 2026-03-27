# API Specification

## Base URL
```
http://localhost:8000
```

---

## POST /analyze

Upload a video file for engagement analysis.

**Request:**
```
Content-Type: multipart/form-data

file: <video file> (.mp4, .webm, .mov)
```

**Response:**
```json
{
  "data": {
    "session_id": "abc123",
    "status": "processing",
    "estimated_duration": 45
  }
}
```

**Notes:**
- For hackathon, processing can be synchronous (block until done) or return immediately and poll
- Max file size: 100MB

---

## GET /session/{id}

Get full session data including event timeline and analytics.

**Response:**
```json
{
  "data": {
    "session_id": "abc123",
    "created_at": "2026-03-27T14:30:00Z",
    "duration": 1800,
    "video_filename": "lecture_tuesday.mp4",
    "analytics": {
      "focus_time_pct": 72.5,
      "distraction_time_pct": 27.5,
      "longest_focus_streak": 660,
      "distraction_breakdown": {
        "yawn": 3,
        "looked_away": 7,
        "eyes_closed": 2,
        "zoned_out": 1
      },
      "engagement_curve": [0.85, 0.78, 0.65, 0.72, 0.90, 0.45, 0.80],
      "danger_zones": [
        {"start": 720, "end": 1080, "avg_score": 0.35}
      ]
    },
    "events": [
      {
        "timestamp": 272,
        "event_type": "yawn",
        "duration": 3.2,
        "confidence": 0.87,
        "metadata": {}
      },
      {
        "timestamp": 435,
        "event_type": "looked_away",
        "duration": 8.1,
        "confidence": 0.92,
        "metadata": {"direction": "left"}
      },
      {
        "timestamp": 760,
        "event_type": "eyes_closed",
        "duration": 5.5,
        "confidence": 0.95,
        "metadata": {}
      }
    ],
    "engagement_states": [
      {"start": 0, "end": 272, "state": "engaged"},
      {"start": 272, "end": 280, "state": "disengaged"},
      {"start": 280, "end": 435, "state": "engaged"},
      {"start": 435, "end": 445, "state": "disengaged"},
      {"start": 445, "end": 720, "state": "passive"},
      {"start": 720, "end": 1080, "state": "disengaged"},
      {"start": 1080, "end": 1800, "state": "engaged"}
    ]
  }
}
```

---

## GET /session/{id}/insights

Get AI-generated recommendations for the session.

**Response:**
```json
{
  "data": {
    "session_id": "abc123",
    "recommendations": [
      {
        "title": "Schedule study sessions earlier",
        "body": "Your yawn frequency peaked at 4:30pm. Research shows alertness drops in the late afternoon. Try scheduling your most demanding study sessions before 2pm.",
        "category": "timing"
      },
      {
        "title": "Break up theory-heavy sections",
        "body": "You lost focus 3 times between minutes 12-18, which coincided with the lecture's theory-heavy section. Try the Pomodoro technique — review that segment in 10-minute focused bursts.",
        "category": "technique"
      },
      {
        "title": "Build on your focus strength",
        "body": "Your longest focus streak was 11 minutes — that's a solid foundation. Try extending it to 15 minutes by removing phone notifications during study blocks.",
        "category": "encouragement"
      }
    ],
    "generated_at": "2026-03-27T14:35:00Z"
  }
}
```

---

## GET /sessions

List all sessions.

**Query params:**
- `limit` (int, default 20)
- `offset` (int, default 0)
- `sort` (string: "date" | "score", default "date")

**Response:**
```json
{
  "data": [
    {
      "session_id": "abc123",
      "created_at": "2026-03-27T14:30:00Z",
      "duration": 1800,
      "focus_time_pct": 72.5,
      "event_count": 13,
      "video_filename": "lecture_tuesday.mp4"
    }
  ],
  "meta": {
    "total": 5,
    "limit": 20,
    "offset": 0
  }
}
```

---

## WebSocket /ws/live

Real-time engagement streaming during a live webcam session.

**Client → Server:**
```json
{
  "type": "frame",
  "data": "<base64 encoded JPEG frame>",
  "timestamp": 1234567890.123
}
```

**Server → Client:**
```json
{
  "type": "state",
  "data": {
    "state": "engaged",
    "confidence": 0.89,
    "features": {
      "ear": 0.28,
      "mar": 0.15,
      "gaze_score": 0.85,
      "head_yaw": 5.2,
      "head_pitch": 3.1,
      "expression_variance": 0.045
    },
    "event": null
  }
}
```

When an event occurs:
```json
{
  "type": "event",
  "data": {
    "timestamp": 45.2,
    "event_type": "looked_away",
    "duration": null,
    "confidence": 0.88,
    "metadata": {"direction": "right"}
  }
}
```

Session end:
```json
{
  "type": "session_end",
  "data": {
    "session_id": "def456"
  }
}
```

---

## Error Format

All errors follow this structure:
```json
{
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "No session found with ID abc123"
  }
}
```

Common error codes:
- `VALIDATION_ERROR` — invalid input
- `SESSION_NOT_FOUND` — unknown session ID
- `PROCESSING_ERROR` — video processing failed
- `LLM_ERROR` — Claude API call failed
