"""Layer 3: Rule-based engagement classifier.

Takes a FeatureVector and classifies into three engagement levels.
Tracks temporal state so that transient conditions (a single blink)
don't immediately trigger disengaged — only sustained conditions do.

Disengagement signals for classroom settings:
- Eyes closed (sleeping)
- Yawning (fatigue)
- Gaze away from screen (distraction)
- Head turned away (talking to neighbor, looking elsewhere)
- Head pitched down (phone, sleeping)
- Drowsiness (slow blinks, drooping eyelids)
- Fidgeting (rapid head movement = looking around the room)

Passive signals:
- Gaze drifting (not fully away, but not on-screen)
- Frozen face (low expression variance = zoned out)
- Head slightly off-center
- Confused (sustained brow furrow)
- Low head motion with low expression variance (catatonic stare)

All thresholds are configurable via ClassifierConfig.
"""

from dataclasses import dataclass, field

from app.models.schemas import EngagementState, FeatureVector


@dataclass
class ClassifierConfig:
    """All thresholds used by the engagement classifier."""

    # EAR thresholds
    ear_open: float = 0.15          # above = eyes open
    eye_closed_duration: float = 0.5  # seconds of EAR < ear_open → disengaged

    # MAR thresholds (using jawOpen blendshape: 0.0-1.0)
    mar_yawn: float = 0.7           # above = yawning
    yawn_duration: float = 2.0      # seconds of MAR > mar_yawn → disengaged

    # Gaze thresholds
    gaze_on_screen: float = 0.5     # above = looking at screen (widened: 0.5→1.0 is "on screen")
    gaze_passive: float = 0.35      # above this but below on_screen = drifting
    gaze_away_duration: float = 3.0  # seconds of gaze < gaze_passive → disengaged

    # Head pose thresholds (degrees)
    head_yaw_engaged: float = 12.0   # below = facing forward (raised: normal posture varies ±12°)
    head_yaw_passive: float = 15.0   # between engaged and this = passive; above = disengaged
    head_pitch_engaged: float = 15.0  # below = head level
    head_pitch_disengaged: float = 20.0  # above = looking down/up significantly
    head_pitch_duration: float = 3.0  # seconds of pitch > threshold → disengaged

    # Expression variance
    expression_var_threshold: float = 0.01  # below = frozen face (tightened: only very still faces)

    # Drowsiness thresholds
    drowsiness_passive: float = 0.3   # above = getting drowsy (passive signal)
    drowsiness_disengaged: float = 0.6  # above = clearly drowsy (disengaged)
    drowsiness_duration: float = 2.0  # seconds sustained → disengaged

    # Head motion (fidgeting)
    head_motion_distracted: float = 3.0  # above = fidgeting/looking around
    head_motion_distracted_duration: float = 2.0  # seconds sustained → disengaged
    head_motion_still: float = 0.3  # below = unnaturally still (passive signal)

    # Brow state
    brow_furrow_threshold: float = 0.3  # above = confused/frustrated (passive signal)
    brow_furrow_duration: float = 5.0  # seconds of sustained furrow → passive


@dataclass
class _TemporalState:
    """Tracks how long each condition has been sustained."""

    eyes_closed_since: float | None = None
    yawning_since: float | None = None
    gaze_away_since: float | None = None
    head_turned_since: float | None = None
    head_pitched_since: float | None = None
    drowsy_since: float | None = None
    fidgeting_since: float | None = None
    brow_furrowed_since: float | None = None


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
        """Classify a single frame's features into an engagement state."""
        t = features.timestamp
        c = self.config

        # --- Update temporal trackers ---

        # Eyes closed
        if features.ear_avg < c.ear_open:
            if self._state.eyes_closed_since is None:
                self._state.eyes_closed_since = t
        else:
            self._state.eyes_closed_since = None

        # Yawning
        if features.mar > c.mar_yawn:
            if self._state.yawning_since is None:
                self._state.yawning_since = t
        else:
            self._state.yawning_since = None

        # Gaze away
        if features.gaze_score < c.gaze_passive:
            if self._state.gaze_away_since is None:
                self._state.gaze_away_since = t
        else:
            self._state.gaze_away_since = None

        # Head turned (yaw)
        if abs(features.head_yaw) > c.head_yaw_passive:
            if self._state.head_turned_since is None:
                self._state.head_turned_since = t
        else:
            self._state.head_turned_since = None

        # Head pitched (looking down/up)
        if abs(features.head_pitch) > c.head_pitch_disengaged:
            if self._state.head_pitched_since is None:
                self._state.head_pitched_since = t
        else:
            self._state.head_pitched_since = None

        # Drowsiness
        if features.drowsiness > c.drowsiness_disengaged:
            if self._state.drowsy_since is None:
                self._state.drowsy_since = t
        else:
            self._state.drowsy_since = None

        # Fidgeting (high head motion)
        if features.head_motion > c.head_motion_distracted:
            if self._state.fidgeting_since is None:
                self._state.fidgeting_since = t
        else:
            self._state.fidgeting_since = None

        # Brow furrow
        if features.brow_furrow > c.brow_furrow_threshold:
            if self._state.brow_furrowed_since is None:
                self._state.brow_furrowed_since = t
        else:
            self._state.brow_furrowed_since = None

        self._last_timestamp = t

        # --- Check disengaged conditions (any one triggers it) ---

        disengaged_signals = 0

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
            disengaged_signals += 1

        if (self._state.head_pitched_since is not None
                and (t - self._state.head_pitched_since) >= c.head_pitch_duration):
            disengaged_signals += 1

        # Drowsiness sustained → disengaged
        if (self._state.drowsy_since is not None
                and (t - self._state.drowsy_since) >= c.drowsiness_duration):
            disengaged_signals += 1

        # Fidgeting sustained → disengaged (looking around the room)
        if (self._state.fidgeting_since is not None
                and (t - self._state.fidgeting_since) >= c.head_motion_distracted_duration):
            disengaged_signals += 1

        if disengaged_signals > 0:
            confidence = min(1.0, 0.5 + 0.12 * disengaged_signals)
            return EngagementState.DISENGAGED, confidence

        # --- Default: engaged ---

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

        if features.drowsiness < c.drowsiness_passive:
            engaged_score += 1.0
        checks += 1

        if features.brow_raise > 0.1:  # raised brows = attentive
            engaged_score += 0.5
        checks += 1

        confidence = max(0.5, engaged_score / checks)
        return EngagementState.ENGAGED, confidence

    def reset(self):
        """Reset temporal state between sessions."""
        self._state = _TemporalState()
        self._last_timestamp = None
