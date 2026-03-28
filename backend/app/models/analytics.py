"""Pydantic models for analytics, AI insights, and section scoring."""

from pydantic import BaseModel, Field


class Event(BaseModel):
    """A single distraction event from the timeline."""

    timestamp: float = Field(description="Seconds from session start")
    event_type: str = Field(description="yawn, looked_away, eyes_closed, zoned_out, face_lost")
    duration: float = Field(description="Duration in seconds")
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict = Field(default_factory=dict)


class EngagementSegment(BaseModel):
    """A time range with a single engagement state."""

    start: float
    end: float
    state: str = Field(description="engaged, passive, or disengaged")


class SessionData(BaseModel):
    """Input session data for the analytics and AI pipelines."""

    session_id: str
    duration: float = Field(description="Total session duration in seconds")
    events: list[Event]
    engagement_states: list[EngagementSegment]


class StateBreakdown(BaseModel):
    """Percentage of time in each engagement state for a section."""

    engaged: float = Field(ge=0.0, le=100.0)
    passive: float = Field(ge=0.0, le=100.0)
    disengaged: float = Field(ge=0.0, le=100.0)


class Section(BaseModel):
    """A scored lecture section."""

    label: str
    start: float = Field(description="Section start time in seconds")
    end: float = Field(description="Section end time in seconds")
    engagement_pct: float = Field(ge=0.0, le=100.0)
    state_breakdown: StateBreakdown
    top_event: str | None = Field(default=None, description="Most frequent event type and count")
    events_in_section: list[Event] = Field(default_factory=list)
    ai_note: str = Field(default="", description="AI-generated teaching advice for this section")


class SectionScoringResult(BaseModel):
    """Final output of the section scoring pipeline."""

    session_id: str
    overall_summary: str = ""
    sections: list[Section] = Field(default_factory=list)
