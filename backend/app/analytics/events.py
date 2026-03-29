"""Layer 4: Timeline event logger.

Watches a stream of FrameResults and emits discrete distraction events.
An event is only finalised when the distraction ends (so we have duration).
In live mode, partial events are emitted every PARTIAL_EMIT_INTERVAL seconds.
"""

from dataclasses import dataclass, field
from typing import Generator

from app.models.schemas import EngagementState, FeatureVector, FrameResult

PARTIAL_EMIT_INTERVAL = 2.0  # seconds between partial live-mode emissions

# Maps the root cause of a disengagement to an event type
EVENT_YAWN = "yawn"
EVENT_EYES_CLOSED = "eyes_closed"
EVENT_LOOKED_AWAY = "looked_away"
EVENT_LOOKED_DOWN = "looked_down"
EVENT_DROWSY = "drowsy"
EVENT_DISTRACTED = "distracted"
EVENT_ZONED_OUT = "zoned_out"
EVENT_FACE_LOST = "face_lost"


@dataclass
class Event:
    timestamp: float        # seconds from session start when distraction began
    event_type: str         # one of the EVENT_* constants above
    duration: float         # seconds (0.0 if still ongoing)
    confidence: float       # 0–1
    metadata: dict = field(default_factory=dict)


def _classify_event_type(features: FeatureVector, config_thresholds: dict) -> str:
    """Pick the most prominent distraction signal from the feature vector."""
    mar_yawn = config_thresholds.get("mar_yawn", 0.7)
    ear_open = config_thresholds.get("ear_open", 0.15)
    gaze_passive = config_thresholds.get("gaze_passive", 0.35)
    head_pitch_disengaged = config_thresholds.get("head_pitch_disengaged", 20.0)
    drowsiness_disengaged = config_thresholds.get("drowsiness_disengaged", 0.6)
    head_motion_distracted = config_thresholds.get("head_motion_distracted", 3.0)

    if features.mar > mar_yawn:
        return EVENT_YAWN
    if features.ear_avg < ear_open:
        return EVENT_EYES_CLOSED
    if features.drowsiness > drowsiness_disengaged:
        return EVENT_DROWSY
    if features.head_motion > head_motion_distracted:
        return EVENT_DISTRACTED
    if abs(features.head_pitch) > head_pitch_disengaged:
        return EVENT_LOOKED_DOWN
    if features.gaze_score < gaze_passive:
        return EVENT_LOOKED_AWAY
    return EVENT_ZONED_OUT


class EventLogger:
    """Stateful event logger for a single session.

    Feed FrameResults in timestamp order via `process()`.
    Retrieve completed events at any time via `events`.
    Call `flush()` at end of session to close any open distraction.
    """

    def __init__(self, thresholds: dict | None = None):
        self._thresholds = thresholds or {}
        self._events: list[Event] = []

        # State tracking for current ongoing distraction
        self._distraction_start: float | None = None
        self._distraction_type: str | None = None
        self._distraction_confidence: float = 0.0
        self._distraction_metadata: dict = {}
        self._last_partial_emit: float = 0.0

    @property
    def events(self) -> list[Event]:
        return list(self._events)

    def process(self, result: FrameResult) -> Event | None:
        """Process one frame. Returns a completed Event if one just ended, else None."""
        if not result.face_detected:
            return self._handle_distraction(
                result.timestamp, EVENT_FACE_LOST, 0.95, {}
            )

        if result.state == EngagementState.DISENGAGED:
            event_type = _classify_event_type(result.features, self._thresholds)
            metadata: dict = {}
            if event_type == EVENT_LOOKED_AWAY:
                metadata["direction"] = (
                    "left" if result.features.gaze_horizontal < 0 else "right"
                )
            elif event_type == EVENT_LOOKED_DOWN:
                metadata["direction"] = (
                    "down" if result.features.head_pitch < 0 else "up"
                )
                metadata["pitch"] = round(result.features.head_pitch, 1)
            return self._handle_distraction(
                result.timestamp,
                event_type,
                0.8,
                metadata,
            )
        else:
            return self._handle_engagement(result.timestamp)

    def _handle_distraction(
        self,
        t: float,
        event_type: str,
        confidence: float,
        metadata: dict,
    ) -> Event | None:
        if self._distraction_start is None:
            # Start a new distraction
            self._distraction_start = t
            self._distraction_type = event_type
            self._distraction_confidence = confidence
            self._distraction_metadata = metadata
            self._last_partial_emit = t
        return None

    def _handle_engagement(self, t: float) -> Event | None:
        """Student re-engaged — close any open distraction event."""
        if self._distraction_start is None:
            return None

        event = Event(
            timestamp=self._distraction_start,
            event_type=self._distraction_type or EVENT_ZONED_OUT,
            duration=round(t - self._distraction_start, 3),
            confidence=self._distraction_confidence,
            metadata=self._distraction_metadata,
        )
        self._events.append(event)
        self._distraction_start = None
        self._distraction_type = None
        return event

    def partial_event(self, current_timestamp: float) -> Event | None:
        """For live mode: emit a partial event every PARTIAL_EMIT_INTERVAL seconds."""
        if self._distraction_start is None:
            return None
        if current_timestamp - self._last_partial_emit < PARTIAL_EMIT_INTERVAL:
            return None

        self._last_partial_emit = current_timestamp
        return Event(
            timestamp=self._distraction_start,
            event_type=self._distraction_type or EVENT_ZONED_OUT,
            duration=round(current_timestamp - self._distraction_start, 3),
            confidence=self._distraction_confidence,
            metadata=self._distraction_metadata,
        )

    def flush(self, end_timestamp: float) -> Event | None:
        """Call at session end to close any open distraction."""
        return self._handle_engagement(end_timestamp)

    def reset(self) -> None:
        self._events.clear()
        self._distraction_start = None
        self._distraction_type = None
        self._distraction_confidence = 0.0
        self._distraction_metadata = {}
        self._last_partial_emit = 0.0


def compute_engagement_states(results: list[FrameResult]) -> list[dict]:
    """Collapse frame-by-frame states into contiguous segments.

    Returns list of {start, end, state} dicts matching the API spec.
    """
    if not results:
        return []

    segments: list[dict] = []
    seg_start = results[0].timestamp
    seg_state = results[0].state.value

    for frame in results[1:]:
        if frame.state.value != seg_state:
            segments.append({"start": seg_start, "end": frame.timestamp, "state": seg_state})
            seg_start = frame.timestamp
            seg_state = frame.state.value

    # Close the last segment
    segments.append({"start": seg_start, "end": results[-1].timestamp, "state": seg_state})
    return segments
