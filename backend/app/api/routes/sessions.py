"""REST API routes for session management.

All endpoints require authentication — each lecturer sees only their own sessions.
"""

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as DBSession

from app.core.auth import get_current_user, get_optional_user
from app.core.config import settings
from app.db.database import get_db
from app.db.models import User
from app.engine.overlay import render_annotated_video
from app.engine.pipeline import Pipeline
from app.storage.sessions import (
    create_session,
    get_session,
    list_sessions,
    save_session_results,
)

router = APIRouter()

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
        results, events, duration = pipeline.process_video(str(video_path))
        save_session_results(db, session_id, results, events, duration)

        annotated_path = _videos_dir() / f"{session_id}_landmarks.mp4"
        try:
            render_annotated_video(str(video_path), str(annotated_path), pipeline)
        except Exception as overlay_err:
            import logging
            logging.warning(f"Failed to generate landmarks overlay: {overlay_err}")
        finally:
            pipeline.close()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "PROCESSING_ERROR", "message": str(e)}},
        )

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
        if lm_path.exists():
            return FileResponse(path=str(lm_path), media_type="video/mp4", filename=f"{session_id}_landmarks.mp4")

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
