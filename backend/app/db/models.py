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

    def to_dict(self) -> dict:
        """Convert to API response format."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "duration": self.duration,
            "video_filename": self.video_filename,
            "status": self.status,
            "analytics": self.analytics,
            "events": self.events,
            "engagement_states": self.engagement_states,
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
