"""REST API routes for session management.

POST  /analyze            — upload video, run pipeline, return session_id
GET   /session/{id}       — get full session data
GET   /session/{id}/video — stream the original uploaded video
GET   /sessions           — list all sessions
"""

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.core.config import settings
from app.engine.pipeline import Pipeline
from app.storage.sessions import create_session, get_session, list_sessions, save_session_results

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
async def analyze_video(file: UploadFile):
    """Upload a video file and run the engagement analysis pipeline."""
    max_bytes = settings.max_upload_mb * 1024 * 1024

    # Validate file type
    allowed = {"video/mp4", "video/webm", "video/quicktime"}
    if file.content_type and file.content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "VALIDATION_ERROR", "message": "Unsupported file type. Use .mp4, .webm, or .mov"}},
        )

    # Read and size-check
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": {"code": "VALIDATION_ERROR", "message": f"File exceeds {settings.max_upload_mb}MB limit"}},
        )

    # Create session record
    session_id = create_session(file.filename or "upload")

    # Save video permanently for playback
    suffix = os.path.splitext(file.filename or ".mp4")[1] or ".mp4"
    video_path = _videos_dir() / f"{session_id}{suffix}"
    video_path.write_bytes(content)

    try:
        pipeline = Pipeline()
        results, events, duration = pipeline.process_video(str(video_path))
        save_session_results(session_id, results, events, duration)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "PROCESSING_ERROR", "message": str(e)}},
        )

    return {"data": {"session_id": session_id, "status": "done"}}


@router.get("/session/{session_id}/video")
async def get_session_video(session_id: str):
    """Stream the original uploaded video for a session."""
    # Find the video file (could be .mp4, .webm, .mov)
    videos = _videos_dir()
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


@router.get("/session/{session_id}")
async def get_session_data(session_id: str):
    """Return full session data including events and analytics."""
    session = get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "SESSION_NOT_FOUND", "message": f"No session found with ID {session_id}"}},
        )
    return {"data": session}


@router.get("/sessions")
async def list_all_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(default="date", pattern="^(date|score)$"),
):
    """List all sessions with summary info."""
    sessions, total = list_sessions(limit=limit, offset=offset, sort=sort)
    return {
        "data": sessions,
        "meta": {"total": total, "limit": limit, "offset": offset},
    }
