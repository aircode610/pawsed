"""REST API routes for AI insights — section scoring + teaching coach chat."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.analytics.section_scoring import run_section_scoring
from app.analytics.teaching_coach import chat_with_coach
from app.core.auth import get_current_user
from app.db.database import get_db
from app.db.models import Session as SessionModel
from app.db.models import User
from app.models.analytics import (
    EngagementSegment,
    Event,
    SectionScoringResult,
    SessionData,
    TranscriptSegment,
)
from app.storage.sessions import get_session, save_scoring

router = APIRouter()


def _session_to_analytics_model(session: dict) -> SessionData:
    return SessionData(
        session_id=session["session_id"],
        duration=session["duration"],
        events=[Event(**e) for e in session.get("events", [])],
        engagement_states=[
            EngagementSegment(**s) for s in session.get("engagement_states", [])
        ],
        transcript=[
            TranscriptSegment(**t) for t in session.get("transcript", [])
        ],
    )


# In-process cache (survives across requests in the same uvicorn worker)
_scoring_cache: dict[str, SectionScoringResult] = {}


@router.get("/session/{session_id}/insights/sections")
async def get_section_scoring(
    session_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Return section-by-section lecture scoring with AI teaching notes.

    Returns immediately if pre-generated during analyze; otherwise generates on demand.
    """
    # 1. In-process memory cache (fastest)
    if session_id in _scoring_cache:
        return {"data": _scoring_cache[session_id].model_dump()}

    session = get_session(db, session_id, user_id=user.id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "SESSION_NOT_FOUND", "message": f"No session found with ID {session_id}"}},
        )

    # 2. DB cache (survives process restarts)
    session_obj = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    if session_obj and session_obj.scoring_json:
        try:
            result = SectionScoringResult.model_validate(session_obj.scoring)
            _scoring_cache[session_id] = result
            return {"data": result.model_dump()}
        except Exception:
            pass  # corrupted — regenerate below

    # 3. Generate on demand (first open after server restart for old sessions)
    try:
        session_data = _session_to_analytics_model(session)
        transcript = [TranscriptSegment(**t) for t in session.get("transcript", [])]
        result = run_section_scoring(session_data, transcript=transcript)

        # Persist so subsequent requests and other workers are instant
        save_scoring(db, session_id, result.model_dump())
        _scoring_cache[session_id] = result

        return {"data": result.model_dump()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "LLM_ERROR", "message": str(e)}},
        )


class ChatRequest(BaseModel):
    messages: list[dict]


@router.post("/session/{session_id}/insights/chat")
async def teaching_coach_chat(
    session_id: str,
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Send a message to the teaching coach and get a response."""
    session = get_session(db, session_id, user_id=user.id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "SESSION_NOT_FOUND", "message": f"No session found with ID {session_id}"}},
        )

    try:
        session_data = _session_to_analytics_model(session)
        # Use cached scoring (already has topic data) if available
        section_scoring = _scoring_cache.get(session_id)
        if section_scoring is None:
            # Try DB cache
            session_obj = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
            if session_obj and session_obj.scoring_json:
                try:
                    section_scoring = SectionScoringResult.model_validate(session_obj.scoring)
                    _scoring_cache[session_id] = section_scoring
                except Exception:
                    pass

        response = chat_with_coach(
            session_data=session_data,
            messages=body.messages,
            section_scoring=section_scoring,
        )
        return {"data": {"role": "assistant", "content": response}}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "LLM_ERROR", "message": str(e)}},
        )
