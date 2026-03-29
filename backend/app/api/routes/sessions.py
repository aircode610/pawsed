"""REST API routes for session management.

All endpoints require authentication — each lecturer sees only their own sessions.
"""

import logging
import os
import pickle
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as DBSession

from app.analytics.section_scoring import run_section_scoring
from app.analytics.transcription import transcribe_video
from app.core.auth import get_current_user, get_optional_user
from app.core.config import settings
from app.db.database import get_db
from app.db.models import Session as SessionModel
from app.db.models import User
from app.engine.overlay import render_annotated_video_from_results
from app.engine.pipeline import Pipeline
from app.models.analytics import EngagementSegment, Event as AnalyticsEvent, SessionData, TranscriptSegment
from app.storage.sessions import (
    create_session,
    get_session,
    list_sessions,
    save_scoring,
    save_session_results,
)

router = APIRouter()


def _results_path(session_id: str) -> Path:
    """Path for the pickle file storing pipeline results (for overlay regeneration)."""
    p = Path(settings.sessions_dir) / "results"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{session_id}_results.pkl"

_CONTENT_TYPE_MAP = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
}


def _videos_dir() -> Path:
    p = Path(settings.sessions_dir) / "videos"
    p.mkdir(parents=True, exist_ok=True)
    return p


@router.post("/analyze")
async def analyze_video(
    file: UploadFile,
    mode: str = Query(default="mediapipe", pattern="^(mediapipe|ml-nn|ml-paranet|ml-rules)$"),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Upload a video file and run the engagement analysis pipeline."""
    max_bytes = settings.max_upload_mb * 1024 * 1024

    allowed = {"video/mp4", "video/webm", "video/quicktime"}
    if file.content_type and file.content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "VALIDATION_ERROR", "message": "Unsupported file type. Use .mp4, .webm, or .mov"}},
        )

    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": {"code": "VALIDATION_ERROR", "message": f"File exceeds {settings.max_upload_mb}MB limit"}},
        )

    session_id = create_session(db, user, file.filename or "upload")

    suffix = os.path.splitext(file.filename or ".mp4")[1] or ".mp4"
    video_path = _videos_dir() / f"{session_id}{suffix}"
    video_path.write_bytes(content)

    try:
        pipeline = Pipeline()
        # Run vision pipeline and audio transcription concurrently
        with ThreadPoolExecutor(max_workers=2) as tex:
            vision_future = tex.submit(pipeline.process_video_parallel, str(video_path))
            transcript_future = tex.submit(transcribe_video, str(video_path))
            results, events, duration = vision_future.result()
            transcript: list[dict] = transcript_future.result()
        pipeline.close()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "PROCESSING_ERROR", "message": str(e)}},
        )

    save_session_results(db, session_id, results, events, duration, transcript=transcript)

    # Persist results to disk so the overlay can be regenerated later
    try:
        with open(_results_path(session_id), "wb") as f:
            pickle.dump(results, f)
    except Exception as e:
        logging.warning(f"Failed to save results pickle: {e}")

    # Render overlay synchronously — ~8s with pre-computed face_data
    annotated_path = _videos_dir() / f"{session_id}_landmarks.mp4"
    try:
        render_annotated_video_from_results(str(video_path), str(annotated_path), results)
    except Exception as e:
        logging.warning(f"Overlay render failed: {e}", exc_info=True)

    # Pre-generate section scoring so insights tab is instant on first open
    try:
        session_dict = get_session(db, session_id)
        session_data = SessionData(
            session_id=session_id,
            duration=session_dict["duration"],
            events=[AnalyticsEvent(**e) for e in session_dict.get("events", [])],
            engagement_states=[EngagementSegment(**s) for s in session_dict.get("engagement_states", [])],
            transcript=[TranscriptSegment(**t) for t in transcript],
        )
        transcript_models = [TranscriptSegment(**t) for t in transcript]
        scoring_result = run_section_scoring(session_data, transcript=transcript_models)
        save_scoring(db, session_id, scoring_result.model_dump())

        # Also warm the in-process insights cache so the first request is instant
        from app.api.routes.insights import _scoring_cache
        _scoring_cache[session_id] = scoring_result
    except Exception as e:
        logging.warning(f"Section scoring pre-generation failed: {e}", exc_info=True)

    return {"data": {"session_id": session_id, "status": "done"}}


@router.get("/session/{session_id}")
async def get_session_data(
    session_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Return full session data including events and analytics."""
    session = get_session(db, session_id, user_id=user.id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "SESSION_NOT_FOUND", "message": f"No session found with ID {session_id}"}},
        )
    return {"data": session}


@router.get("/session/{session_id}/video")
async def get_session_video(
    session_id: str,
    landmarks: bool = False,
    token: str | None = Query(default=None),
    user: User | None = Depends(get_optional_user),
    db: DBSession = Depends(get_db),
):
    """Stream the uploaded video for a session.

    Accepts auth via Bearer header OR ?token= query param (needed for <video> elements).
    """
    # If no user from header, try the query param token
    if user is None and token:
        from jose import jwt as _jwt
        try:
            payload = _jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            uid = int(payload["sub"])
            user = db.query(User).filter(User.id == uid).first()
        except Exception:
            pass

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    session = get_session(db, session_id, user_id=user.id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "SESSION_NOT_FOUND", "message": f"No session found with ID {session_id}"}},
        )

    videos = _videos_dir()

    if landmarks:
        lm_path = videos / f"{session_id}_landmarks.mp4"
        if not lm_path.exists():
            # Try to regenerate from saved results pickle
            pkl = _results_path(session_id)
            if pkl.exists():
                try:
                    with open(pkl, "rb") as f:
                        saved_results = pickle.load(f)
                    orig_path = next(
                        (videos / f"{session_id}{ext}" for ext in (".mp4", ".webm", ".mov")
                         if (videos / f"{session_id}{ext}").exists()),
                        None,
                    )
                    if orig_path:
                        render_annotated_video_from_results(str(orig_path), str(lm_path), saved_results)
                except Exception as e:
                    logging.warning(f"Overlay regeneration failed: {e}", exc_info=True)
        if lm_path.exists():
            return FileResponse(path=str(lm_path), media_type="video/mp4", filename=f"{session_id}_landmarks.mp4")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "LANDMARKS_NOT_AVAILABLE", "message": "Landmarks overlay not available for this session"}},
        )

    for ext in (".mp4", ".webm", ".mov"):
        path = videos / f"{session_id}{ext}"
        if path.exists():
            return FileResponse(
                path=str(path),
                media_type=_CONTENT_TYPE_MAP.get(ext, "video/mp4"),
                filename=f"{session_id}{ext}",
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": {"code": "VIDEO_NOT_FOUND", "message": f"No video found for session {session_id}"}},
    )


@router.get("/sessions")
async def list_all_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(default="date", pattern="^(date|score)$"),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """List all sessions for the authenticated lecturer."""
    sessions, total = list_sessions(db, user_id=user.id, limit=limit, offset=offset, sort=sort)
    return {
        "data": sessions,
        "meta": {"total": total, "limit": limit, "offset": offset},
    }
