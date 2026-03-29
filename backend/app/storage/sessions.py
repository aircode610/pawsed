"""Session persistence — SQLite via SQLAlchemy.

All session data (analytics, events, engagement states) is stored
in the database. Video files remain on disk.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session as DBSession

from app.analytics.events import Event, compute_engagement_states
from app.core.config import settings
from app.db.models import Session as SessionModel
from app.db.models import User
from app.models.schemas import FrameResult


def _videos_dir() -> Path:
    p = Path(settings.sessions_dir) / "videos"
    p.mkdir(parents=True, exist_ok=True)
    return p


def create_session(db: DBSession, user: User, video_filename: str) -> str:
    """Create a new session record. Returns the session_id."""
    session_id = uuid.uuid4().hex
    session = SessionModel(
        session_id=session_id,
        user_id=user.id,
        video_filename=video_filename,
        status="processing",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session_id


def save_scoring(db: DBSession, session_id: str, scoring: dict) -> None:
    """Persist pre-generated section scoring result for a session."""
    session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    if session is None:
        return
    session.scoring = scoring
    db.commit()


def save_session_results(
    db: DBSession,
    session_id: str,
    results: list[FrameResult],
    events: list[Event],
    duration: float,
    transcript: list[dict] | None = None,
) -> None:
    """Persist processed pipeline results for a session."""
    session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    if session is None:
        return

    # Engagement states (collapsed segments)
    engagement_states = compute_engagement_states(results)

    # Build analytics
    total = duration or 1.0
    engaged_time = sum(
        (seg["end"] - seg["start"])
        for seg in engagement_states
        if seg["state"] == "engaged"
    )
    passive_time = sum(
        (seg["end"] - seg["start"])
        for seg in engagement_states
        if seg["state"] == "passive"
    )
    disengaged_time = sum(
        (seg["end"] - seg["start"])
        for seg in engagement_states
        if seg["state"] == "disengaged"
    )
    # Passive treated as engaged (classifier no longer emits passive state).
    # Distraction % is disengaged-only, not (100 - focus).
    focus_pct = round((engaged_time + passive_time) / total * 100, 1)

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

    # Engagement curve: per-60s bin
    bin_size = 60.0
    num_bins = max(1, int(total / bin_size) + 1)
    bins: list[list[float]] = [[] for _ in range(num_bins)]
    for r in results:
        idx = min(int(r.timestamp / bin_size), num_bins - 1)
        if r.total_faces > 0:
            engaged_count = sum(1 for f in r.faces if f.state.value == "engaged")
            passive_count = sum(1 for f in r.faces if f.state.value == "passive")
            score = (engaged_count + passive_count * 0.5) / r.total_faces
        else:
            score = 0.0
        bins[idx].append(score)
    engagement_curve = [
        round(sum(b) / len(b), 2) if b else 0.0 for b in bins
    ]

    # Danger zones
    danger_zones = []
    for seg in engagement_states:
        if seg["state"] == "disengaged" and (seg["end"] - seg["start"]) >= 30:
            danger_zones.append({
                "start": seg["start"],
                "end": seg["end"],
                "avg_score": 0.0,
            })

    # Multi-face metrics
    risk_curve = []
    face_count_curve = []
    for bin_idx in range(num_bins):
        bin_results = [
            r for r in results
            if min(int(r.timestamp / bin_size), num_bins - 1) == bin_idx
        ]
        if bin_results:
            avg_disengaged_pct = sum(r.disengaged_pct for r in bin_results) / len(bin_results)
            avg_faces = sum(r.total_faces for r in bin_results) / len(bin_results)
            risk_curve.append(round(avg_disengaged_pct, 1))
            face_count_curve.append(round(avg_faces, 1))
        else:
            risk_curve.append(0.0)
            face_count_curve.append(0.0)

    # Peak risk
    peak_risk_frames = [r for r in results if r.risk_level.value in ("high", "critical")]
    peak_risk_moments = []
    if peak_risk_frames:
        start = peak_risk_frames[0].timestamp
        prev_t = start
        for r in peak_risk_frames[1:]:
            if r.timestamp - prev_t > 2.0:
                peak_risk_moments.append({"start": round(start, 1), "end": round(prev_t, 1)})
                start = r.timestamp
            prev_t = r.timestamp
        peak_risk_moments.append({"start": round(start, 1), "end": round(prev_t, 1)})

    max_faces = max((r.total_faces for r in results), default=0)

    # Save transcript if provided
    if transcript is not None:
        session.transcript = transcript

    # Update session
    session.status = "done"
    session.duration = round(duration, 2)
    session.analytics = {
        "focus_time_pct": focus_pct,
        "distraction_time_pct": round(disengaged_time / total * 100, 1),
        "longest_focus_streak": round(longest_streak, 2),
        "distraction_breakdown": breakdown,
        "engagement_curve": engagement_curve,
        "danger_zones": danger_zones,
        "max_faces_detected": max_faces,
        "risk_curve": risk_curve,
        "face_count_curve": face_count_curve,
        "peak_risk_moments": peak_risk_moments,
    }
    session.events = [
        {
            "timestamp": e.timestamp,
            "event_type": e.event_type,
            "duration": e.duration,
            "confidence": e.confidence,
            "metadata": e.metadata,
            "severity": e.severity,
        }
        for e in events
    ]
    session.engagement_states = engagement_states

    db.commit()


def get_session(db: DBSession, session_id: str, user_id: int | None = None) -> dict | None:
    """Fetch a session. Optionally filter by user."""
    query = db.query(SessionModel).filter(SessionModel.session_id == session_id)
    if user_id is not None:
        query = query.filter(SessionModel.user_id == user_id)
    session = query.first()
    if session is None:
        return None
    return session.to_dict()


def list_sessions(
    db: DBSession,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    sort: str = "date",
) -> tuple[list[dict], int]:
    """List sessions for a user. Returns (summaries, total_count)."""
    query = db.query(SessionModel).filter(SessionModel.user_id == user_id)
    total = query.count()

    if sort == "score":
        # Sort by focus_time_pct — need to do it in Python since it's in JSON
        all_sessions = query.all()
        all_sessions.sort(key=lambda s: s.analytics.get("focus_time_pct", 0), reverse=True)
        sessions = all_sessions[offset: offset + limit]
    else:
        sessions = query.order_by(SessionModel.created_at.desc()).offset(offset).limit(limit).all()

    return [s.to_summary() for s in sessions], total
