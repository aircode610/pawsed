"""SQLAlchemy ORM models."""

import json
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    video_filename = Column(String, default="")
    status = Column(String, default="processing")  # processing, done, failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    duration = Column(Float, default=0.0)

    # Analytics stored as JSON text
    analytics_json = Column(Text, default="{}")
    events_json = Column(Text, default="[]")
    engagement_states_json = Column(Text, default="[]")
    transcript_json = Column(Text, nullable=True)   # audio transcript segments [{start,end,text}]
    scoring_json = Column(Text, nullable=True)       # cached SectionScoringResult JSON

    user = relationship("User", back_populates="sessions")

    @property
    def analytics(self) -> dict:
        return json.loads(self.analytics_json) if self.analytics_json else {}

    @analytics.setter
    def analytics(self, value: dict):
        self.analytics_json = json.dumps(value)

    @property
    def events(self) -> list:
        return json.loads(self.events_json) if self.events_json else []

    @events.setter
    def events(self, value: list):
        self.events_json = json.dumps(value)

    @property
    def engagement_states(self) -> list:
        return json.loads(self.engagement_states_json) if self.engagement_states_json else []

    @engagement_states.setter
    def engagement_states(self, value: list):
        self.engagement_states_json = json.dumps(value)

    @property
    def transcript(self) -> list:
        return json.loads(self.transcript_json) if self.transcript_json else []

    @transcript.setter
    def transcript(self, value: list):
        self.transcript_json = json.dumps(value)

    @property
    def scoring(self) -> dict | None:
        return json.loads(self.scoring_json) if self.scoring_json else None

    @scoring.setter
    def scoring(self, value: dict | None):
        self.scoring_json = json.dumps(value) if value is not None else None

    def to_dict(self) -> dict:
        """Convert to API response format."""
        from pathlib import Path
        from app.core.config import settings
        lm_path = Path(settings.sessions_dir) / "videos" / f"{self.session_id}_landmarks.mp4"
        pkl_path = Path(settings.sessions_dir) / "results" / f"{self.session_id}_results.pkl"
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "duration": self.duration,
            "video_filename": self.video_filename,
            "status": self.status,
            "analytics": self.analytics,
            "events": self.events,
            "engagement_states": self.engagement_states,
            "has_landmarks": lm_path.exists() or pkl_path.exists(),
            "scoring_ready": self.scoring_json is not None,
            "transcript": self.transcript,
        }

    def to_summary(self) -> dict:
        """Convert to list/summary format."""
        analytics = self.analytics
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "duration": self.duration,
            "video_filename": self.video_filename,
            "focus_time_pct": analytics.get("focus_time_pct", 0),
            "event_count": len(self.events),
            "status": self.status,
        }
