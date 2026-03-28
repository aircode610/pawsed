"""Layer 3: Rule-based engagement classifier.

Takes a FeatureVector and classifies into three engagement levels.
Tracks temporal state so that transient conditions (a single blink)
don't immediately trigger disengaged — only sustained conditions do.

All thresholds are configurable via ClassifierConfig.
"""

from dataclasses import dataclass, field

from app.models.schemas import EngagementState, FeatureVector


@dataclass
class ClassifierConfig:
    """All thresholds used by the engagement classifier."""

    # EAR thresholds
    ear_open: float = 0.2           # above = eyes open
    eye_closed_duration: float = 0.5  # seconds of EAR < ear_open → disengaged

    # MAR thresholds
    mar_yawn: float = 0.6           # above = yawning
    yawn_duration: float = 2.0      # seconds of MAR > mar_yawn → disengaged

    # Gaze thresholds
    gaze_on_screen: float = 0.7     # above = looking at screen
    gaze_passive: float = 0.5       # above this but below on_screen = drifting
    gaze_away_duration: float = 5.0  # seconds of gaze < gaze_passive → disengaged

    # Head pose thresholds (degrees, absolute values)
    head_yaw_engaged: float = 15.0   # below = facing forward
    head_yaw_passive: float = 30.0   # between engaged and this = passive; above = disengaged
    head_pitch_engaged: float = 10.0  # below = head level

    # Expression variance
    expression_var_threshold: float = 0.02  # below = frozen face

    # Confidence weights for combining signals
    # (not used for classification, but reported in output)


@dataclass
class _TemporalState:
    """Tracks how long each condition has been sustained."""

    eyes_closed_since: float | None = None
    yawning_since: float | None = None
    gaze_away_since: float | None = None
    head_turned_since: float | None = None


class EngagementClassifier:
    """Stateful rule-based engagement classifier.

    Call `classify()` for each frame in timestamp order.
    Call `reset()` between sessions.
    """

    def __init__(self, config: ClassifierConfig | None = None):
        self.config = config or ClassifierConfig()
        self._state = _TemporalState()
        self._last_timestamp: float | None = None

    def classify(self, features: FeatureVector) -> tuple[EngagementState, float]:
        """Classify a single frame's features into an engagement state.

        Args:
            features: The extracted feature vector for this frame.

        Returns:
            (state, confidence) where confidence is 0.0-1.0.
        """
        t = features.timestamp
        c = self.config

        # --- Update temporal trackers ---

        # Eyes closed tracking
        if features.ear_avg < c.ear_open:
            if self._state.eyes_closed_since is None:
                self._state.eyes_closed_since = t
        else:
            self._state.eyes_closed_since = None

        # Yawn tracking
        if features.mar > c.mar_yawn:
            if self._state.yawning_since is None:
                self._state.yawning_since = t
        else:
            self._state.yawning_since = None

        # Gaze away tracking
        if features.gaze_score < c.gaze_passive:
            if self._state.gaze_away_since is None:
                self._state.gaze_away_since = t
        else:
            self._state.gaze_away_since = None

        # Head turned tracking
        if abs(features.head_yaw) > c.head_yaw_passive:
            if self._state.head_turned_since is None:
                self._state.head_turned_since = t
        else:
            self._state.head_turned_since = None

        self._last_timestamp = t

        # --- Check disengaged conditions (any one triggers it) ---

        disengaged_signals = 0
        total_signals = 4  # eyes, yawn, gaze, head

        if (self._state.eyes_closed_since is not None
                and (t - self._state.eyes_closed_since) >= c.eye_closed_duration):
            disengaged_signals += 1

        if (self._state.yawning_since is not None
                and (t - self._state.yawning_since) >= c.yawn_duration):
            disengaged_signals += 1

        if (self._state.gaze_away_since is not None
                and (t - self._state.gaze_away_since) >= c.gaze_away_duration):
            disengaged_signals += 1

        if (self._state.head_turned_since is not None
                and (t - self._state.head_turned_since) >= 0):
            # Head yaw > 30° is immediately disengaged (no sustained requirement in spec)
            disengaged_signals += 1

        if disengaged_signals > 0:
            confidence = min(1.0, 0.5 + 0.15 * disengaged_signals)
            return EngagementState.DISENGAGED, confidence

        # --- Check passive conditions ---

        passive_signals = 0
        total_passive = 4

        # Eyes open but gaze drifting
        gaze_drifting = (features.gaze_score < c.gaze_on_screen
                         and features.gaze_score >= c.gaze_passive)
        if gaze_drifting:
            passive_signals += 1

        # Low expression variance (frozen face)
        if features.expression_variance < c.expression_var_threshold:
            passive_signals += 1

        # Head slightly off-center
        if (abs(features.head_yaw) > c.head_yaw_engaged
                and abs(features.head_yaw) <= c.head_yaw_passive):
            passive_signals += 1

        # Head pitch slightly off
        if abs(features.head_pitch) > c.head_pitch_engaged:
            passive_signals += 1

        if passive_signals >= 2:
            confidence = min(1.0, 0.4 + 0.15 * passive_signals)
            return EngagementState.PASSIVE, confidence

        # --- Default: engaged ---

        # Confidence is higher when all engaged signals are strong
        engaged_score = 0.0
        checks = 0

        if features.ear_avg >= c.ear_open:
            engaged_score += 1.0
        checks += 1

        if features.gaze_score >= c.gaze_on_screen:
            engaged_score += 1.0
        checks += 1

        if abs(features.head_yaw) < c.head_yaw_engaged:
            engaged_score += 1.0
        checks += 1

        if features.expression_variance >= c.expression_var_threshold:
            engaged_score += 1.0
        checks += 1

        confidence = max(0.5, engaged_score / checks)
        return EngagementState.ENGAGED, confidence

    def reset(self):
        """Reset temporal state between sessions."""
        self._state = _TemporalState()
        self._last_timestamp = None
