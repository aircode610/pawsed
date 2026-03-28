"""Session persistence — stores session data as JSON files.

Each session is one file: sessions/<session_id>.json
"""

import json
import os
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from app.analytics.events import Event, compute_engagement_states
from app.core.config import settings
from app.models.schemas import FrameResult


def _sessions_dir() -> Path:
    p = Path(settings.sessions_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _session_path(session_id: str) -> Path:
    return _sessions_dir() / f"{session_id}.json"


def create_session(video_filename: str) -> str:
    """Create a new session record. Returns the session_id."""
    session_id = uuid.uuid4().hex
    data = {
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "processing",
        "video_filename": video_filename,
        "duration": 0,
        "analytics": None,
        "events": [],
        "engagement_states": [],
    }
    _session_path(session_id).write_text(json.dumps(data, indent=2))
    return session_id


def save_session_results(
    session_id: str,
    results: list[FrameResult],
    events: list[Event],
    duration: float,
) -> None:
    """Persist processed pipeline results for a session."""
    path = _session_path(session_id)
    data = json.loads(path.read_text())

    # Engagement states (collapsed segments)
    engagement_states = compute_engagement_states(results)

    # Build analytics
    total = duration or 1.0
    disengaged_time = sum(
        (seg["end"] - seg["start"])
        for seg in engagement_states
        if seg["state"] == "disengaged"
    )
    engaged_time = sum(
        (seg["end"] - seg["start"])
        for seg in engagement_states
        if seg["state"] == "engaged"
    )
    focus_pct = round(engaged_time / total * 100, 1)

    # Longest focus streak
    longest_streak = 0.0
    for seg in engagement_states:
        if seg["state"] == "engaged":
            length = seg["end"] - seg["start"]
            if length > longest_streak:
                longest_streak = length

    # Distraction breakdown
    breakdown: dict[str, int] = {}
    for e in events:
        breakdown[e.event_type] = breakdown.get(e.event_type, 0) + 1

    # Engagement curve: average engagement score per 60-second bin
    bin_size = 60.0
    num_bins = max(1, int(total / bin_size) + 1)
    bins: list[list[float]] = [[] for _ in range(num_bins)]
    for r in results:
        idx = min(int(r.timestamp / bin_size), num_bins - 1)
        score = 1.0 if r.state.value == "engaged" else (0.5 if r.state.value == "passive" else 0.0)
        bins[idx].append(score)
    engagement_curve = [
        round(sum(b) / len(b), 2) if b else 0.0 for b in bins
    ]

    # Danger zones: contiguous disengaged segments > 30s
    danger_zones = []
    for seg in engagement_states:
        if seg["state"] == "disengaged" and (seg["end"] - seg["start"]) >= 30:
            danger_zones.append({
                "start": seg["start"],
                "end": seg["end"],
                "avg_score": 0.0,
            })

    data.update({
        "status": "done",
        "duration": round(duration, 2),
        "analytics": {
            "focus_time_pct": focus_pct,
            "distraction_time_pct": round(100 - focus_pct, 1),
            "longest_focus_streak": round(longest_streak, 2),
            "distraction_breakdown": breakdown,
            "engagement_curve": engagement_curve,
            "danger_zones": danger_zones,
        },
        "events": [
            {
                "timestamp": e.timestamp,
                "event_type": e.event_type,
                "duration": e.duration,
                "confidence": e.confidence,
                "metadata": e.metadata,
            }
            for e in events
        ],
        "engagement_states": engagement_states,
    })

    path.write_text(json.dumps(data, indent=2))


def get_session(session_id: str) -> dict | None:
    path = _session_path(session_id)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def list_sessions(limit: int = 20, offset: int = 0, sort: str = "date") -> tuple[list[dict], int]:
    """Returns (sessions, total_count)."""
    dir_ = _sessions_dir()
    files = sorted(dir_.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)

    summaries = []
    for f in files:
        try:
            d = json.loads(f.read_text())
            summaries.append({
                "session_id": d["session_id"],
                "created_at": d["created_at"],
                "duration": d.get("duration", 0),
                "focus_time_pct": (d.get("analytics") or {}).get("focus_time_pct", 0),
                "event_count": len(d.get("events", [])),
                "video_filename": d.get("video_filename", ""),
                "status": d.get("status", "unknown"),
            })
        except Exception:
            continue

    if sort == "score":
        summaries.sort(key=lambda s: s["focus_time_pct"], reverse=True)

    total = len(summaries)
    return summaries[offset: offset + limit], total
