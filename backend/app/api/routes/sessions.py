"""REST API routes for session management.

POST  /analyze            — upload video, run pipeline, return session_id
GET   /session/{id}       — get full session data
GET   /sessions           — list all sessions
"""

import os
import tempfile

from fastapi import APIRouter, HTTPException, Query, UploadFile, status

from app.core.config import settings
from app.engine.pipeline import Pipeline
from app.storage.sessions import create_session, get_session, list_sessions, save_session_results

router = APIRouter()


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

    # Write to temp file for OpenCV
    suffix = os.path.splitext(file.filename or ".mp4")[1] or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        pipeline = Pipeline()
        results, events, duration = pipeline.process_video(tmp_path)
        save_session_results(session_id, results, events, duration)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "PROCESSING_ERROR", "message": str(e)}},
        )
    finally:
        os.unlink(tmp_path)

    return {"data": {"session_id": session_id, "status": "done"}}


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
