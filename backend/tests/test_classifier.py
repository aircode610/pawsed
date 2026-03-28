"""Tests for Layer 3: Engagement classifier.

Uses synthetic FeatureVectors to test classification rules,
temporal tracking, edge cases, and threshold configurability.
"""

import pytest

from app.engine.classifier import ClassifierConfig, EngagementClassifier
from app.models.schemas import EngagementState, FeatureVector


# ---------------------------------------------------------------------------
# Helpers to build feature vectors for each state
# ---------------------------------------------------------------------------

def _engaged_features(timestamp: float = 0.0) -> FeatureVector:
    """Clearly engaged: eyes open, on-screen gaze, head forward, expressive."""
    return FeatureVector(
        ear_left=0.30, ear_right=0.30, ear_avg=0.30,
        mar=0.15,
        gaze_score=0.90, gaze_horizontal=0.0, gaze_vertical=0.0,
        head_pitch=3.0, head_yaw=5.0, head_roll=1.0,
        expression_variance=0.05,
        timestamp=timestamp,
    )


def _passive_features(timestamp: float = 0.0) -> FeatureVector:
    """Passive: eyes open but gaze drifting, low expression, head slightly off."""
    return FeatureVector(
        ear_left=0.25, ear_right=0.25, ear_avg=0.25,
        mar=0.12,
        gaze_score=0.60, gaze_horizontal=-0.2, gaze_vertical=-0.1,
        head_pitch=12.0, head_yaw=20.0, head_roll=3.0,
        expression_variance=0.01,
        timestamp=timestamp,
    )


def _disengaged_eyes_closed(timestamp: float = 0.0) -> FeatureVector:
    """Disengaged via eyes closed."""
    return FeatureVector(
        ear_left=0.10, ear_right=0.10, ear_avg=0.10,
        mar=0.10,
        gaze_score=0.80, gaze_horizontal=0.0, gaze_vertical=-0.1,
        head_pitch=5.0, head_yaw=5.0, head_roll=1.0,
        expression_variance=0.03,
        timestamp=timestamp,
    )


def _disengaged_yawning(timestamp: float = 0.0) -> FeatureVector:
    """Disengaged via yawning."""
    return FeatureVector(
        ear_left=0.25, ear_right=0.25, ear_avg=0.25,
        mar=0.75,
        gaze_score=0.80, gaze_horizontal=0.0, gaze_vertical=-0.2,
        head_pitch=5.0, head_yaw=5.0, head_roll=1.0,
        expression_variance=0.04,
        timestamp=timestamp,
    )


def _disengaged_looking_away(timestamp: float = 0.0) -> FeatureVector:
    """Disengaged via gaze away from screen."""
    return FeatureVector(
        ear_left=0.28, ear_right=0.28, ear_avg=0.28,
        mar=0.10,
        gaze_score=0.20, gaze_horizontal=-0.5, gaze_vertical=-0.3,
        head_pitch=5.0, head_yaw=10.0, head_roll=1.0,
        expression_variance=0.04,
        timestamp=timestamp,
    )


def _disengaged_head_turned(timestamp: float = 0.0) -> FeatureVector:
    """Disengaged via head turned far away (yaw > 30°)."""
    return FeatureVector(
        ear_left=0.25, ear_right=0.25, ear_avg=0.25,
        mar=0.10,
        gaze_score=0.80, gaze_horizontal=0.0, gaze_vertical=0.0,
        head_pitch=5.0, head_yaw=40.0, head_roll=2.0,
        expression_variance=0.04,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# Basic classification tests
# ---------------------------------------------------------------------------

class TestBasicClassification:
    def test_engaged_state(self):
        clf = EngagementClassifier()
        state, conf = clf.classify(_engaged_features(0.0))
        assert state == EngagementState.ENGAGED
        assert conf >= 0.5

    def test_passive_state(self):
        clf = EngagementClassifier()
        state, conf = clf.classify(_passive_features(0.0))
        assert state == EngagementState.PASSIVE

    def test_disengaged_head_turned(self):
        """Head yaw > 30° should immediately classify as disengaged."""
        clf = EngagementClassifier()
        state, conf = clf.classify(_disengaged_head_turned(0.0))
        assert state == EngagementState.DISENGAGED

    def test_returns_confidence(self):
        clf = EngagementClassifier()
        _, conf = clf.classify(_engaged_features(0.0))
        assert 0.0 <= conf <= 1.0


# ---------------------------------------------------------------------------
# Temporal tracking tests — disengaged requires sustained conditions
# ---------------------------------------------------------------------------

class TestTemporalTracking:
    def test_brief_eye_closure_not_disengaged(self):
        """Eyes closed for less than 0.5s should NOT trigger disengaged."""
        clf = EngagementClassifier()
        # Eyes closed at t=0.0, only 0.3s elapsed
        clf.classify(_disengaged_eyes_closed(0.0))
        state, _ = clf.classify(_disengaged_eyes_closed(0.3))
        # Should not be disengaged yet (need 0.5s)
        assert state != EngagementState.DISENGAGED

    def test_sustained_eye_closure_disengaged(self):
        """Eyes closed for >= 0.5s should trigger disengaged."""
        clf = EngagementClassifier()
        clf.classify(_disengaged_eyes_closed(0.0))
        clf.classify(_disengaged_eyes_closed(0.3))
        state, _ = clf.classify(_disengaged_eyes_closed(0.6))
        assert state == EngagementState.DISENGAGED

    def test_brief_yawn_not_disengaged(self):
        """Yawning for < 2s should NOT trigger disengaged."""
        clf = EngagementClassifier()
        clf.classify(_disengaged_yawning(0.0))
        state, _ = clf.classify(_disengaged_yawning(1.5))
        assert state != EngagementState.DISENGAGED

    def test_sustained_yawn_disengaged(self):
        """Yawning for >= 2s should trigger disengaged."""
        clf = EngagementClassifier()
        clf.classify(_disengaged_yawning(0.0))
        clf.classify(_disengaged_yawning(1.0))
        state, _ = clf.classify(_disengaged_yawning(2.5))
        assert state == EngagementState.DISENGAGED

    def test_brief_gaze_away_not_disengaged(self):
        """Gaze away for < 5s should NOT trigger disengaged."""
        clf = EngagementClassifier()
        clf.classify(_disengaged_looking_away(0.0))
        state, _ = clf.classify(_disengaged_looking_away(3.0))
        assert state != EngagementState.DISENGAGED

    def test_sustained_gaze_away_disengaged(self):
        """Gaze away for >= 5s should trigger disengaged."""
        clf = EngagementClassifier()
        clf.classify(_disengaged_looking_away(0.0))
        clf.classify(_disengaged_looking_away(3.0))
        state, _ = clf.classify(_disengaged_looking_away(5.5))
        assert state == EngagementState.DISENGAGED

    def test_eye_closure_resets_on_open(self):
        """If eyes open mid-closure, the timer resets."""
        clf = EngagementClassifier()
        clf.classify(_disengaged_eyes_closed(0.0))
        clf.classify(_disengaged_eyes_closed(0.3))
        # Eyes open briefly
        clf.classify(_engaged_features(0.4))
        # Eyes close again
        clf.classify(_disengaged_eyes_closed(0.5))
        state, _ = clf.classify(_disengaged_eyes_closed(0.8))
        # Only 0.3s since re-closure, should not be disengaged
        assert state != EngagementState.DISENGAGED

    def test_yawn_resets_on_mouth_close(self):
        """Yawn timer resets when mouth closes."""
        clf = EngagementClassifier()
        clf.classify(_disengaged_yawning(0.0))
        clf.classify(_disengaged_yawning(1.5))
        # Mouth closes
        clf.classify(_engaged_features(1.8))
        # Yawn starts again
        clf.classify(_disengaged_yawning(2.0))
        state, _ = clf.classify(_disengaged_yawning(3.0))
        # Only 1.0s since new yawn, need 2.0s
        assert state != EngagementState.DISENGAGED


# ---------------------------------------------------------------------------
# Transition tests — simulating realistic sequences
# ---------------------------------------------------------------------------

class TestTransitions:
    def test_engaged_to_passive(self):
        """Student starts engaged then drifts to passive."""
        clf = EngagementClassifier()
        state1, _ = clf.classify(_engaged_features(0.0))
        state2, _ = clf.classify(_passive_features(1.0))
        assert state1 == EngagementState.ENGAGED
        assert state2 == EngagementState.PASSIVE

    def test_engaged_to_disengaged_via_eye_closure(self):
        """Student closes eyes gradually."""
        clf = EngagementClassifier()
        state1, _ = clf.classify(_engaged_features(0.0))
        clf.classify(_disengaged_eyes_closed(1.0))
        clf.classify(_disengaged_eyes_closed(1.3))
        state2, _ = clf.classify(_disengaged_eyes_closed(1.6))
        assert state1 == EngagementState.ENGAGED
        assert state2 == EngagementState.DISENGAGED

    def test_disengaged_back_to_engaged(self):
        """Student was disengaged but snaps back."""
        clf = EngagementClassifier()
        # Build up disengaged state
        clf.classify(_disengaged_eyes_closed(0.0))
        clf.classify(_disengaged_eyes_closed(0.6))
        state1, _ = clf.classify(_disengaged_eyes_closed(1.0))
        # Now engaged
        state2, _ = clf.classify(_engaged_features(1.5))
        assert state1 == EngagementState.DISENGAGED
        assert state2 == EngagementState.ENGAGED

    def test_full_session_sequence(self):
        """Simulate a realistic session: engaged → passive → disengaged → engaged."""
        clf = EngagementClassifier()
        results = []

        # Engaged period (0-5s)
        for t in [0.0, 0.5, 1.0, 1.5, 2.0]:
            state, _ = clf.classify(_engaged_features(t))
            results.append((t, state))

        # Passive period (5-10s)
        for t in [5.0, 5.5, 6.0, 6.5, 7.0]:
            state, _ = clf.classify(_passive_features(t))
            results.append((t, state))

        # Disengaged via yawning (10-15s)
        for t in [10.0, 10.5, 11.0, 12.0, 12.5]:
            state, _ = clf.classify(_disengaged_yawning(t))
            results.append((t, state))

        # Recovery (15-20s)
        for t in [15.0, 15.5, 16.0, 16.5, 17.0]:
            state, _ = clf.classify(_engaged_features(t))
            results.append((t, state))

        # Check key transitions
        assert results[0][1] == EngagementState.ENGAGED
        assert results[5][1] == EngagementState.PASSIVE
        # Yawning at t=12.5 is 2.5s after start at t=10.0
        assert results[-6][1] == EngagementState.DISENGAGED
        assert results[-1][1] == EngagementState.ENGAGED


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_borderline_ear(self):
        """EAR exactly at threshold."""
        clf = EngagementClassifier()
        features = _engaged_features(0.0)
        features.ear_avg = 0.2  # exactly at threshold — should count as open
        state, _ = clf.classify(features)
        assert state == EngagementState.ENGAGED

    def test_all_signals_disengaged(self):
        """Every signal is bad — should be disengaged with high confidence."""
        clf = EngagementClassifier()
        features = FeatureVector(
            ear_left=0.08, ear_right=0.08, ear_avg=0.08,
            mar=0.80,
            gaze_score=0.10, gaze_horizontal=-0.5, gaze_vertical=-0.5,
            head_pitch=30.0, head_yaw=45.0, head_roll=10.0,
            expression_variance=0.005,
            timestamp=0.0,
        )
        # First frame — eyes closed and yawning need sustained time,
        # but head yaw > 30 is immediate
        state, conf = clf.classify(features)
        assert state == EngagementState.DISENGAGED
        assert conf >= 0.5

    def test_only_one_passive_signal_stays_engaged(self):
        """A single passive signal shouldn't downgrade to passive (need >= 2)."""
        clf = EngagementClassifier()
        features = _engaged_features(0.0)
        # Only make gaze slightly drifting
        features.gaze_score = 0.65  # between 0.5 and 0.7 = drifting
        state, _ = clf.classify(features)
        assert state == EngagementState.ENGAGED

    def test_two_passive_signals_triggers_passive(self):
        """Two passive signals should classify as passive."""
        clf = EngagementClassifier()
        features = _engaged_features(0.0)
        features.gaze_score = 0.60  # drifting
        features.expression_variance = 0.01  # frozen face
        state, _ = clf.classify(features)
        assert state == EngagementState.PASSIVE


# ---------------------------------------------------------------------------
# Config customization tests
# ---------------------------------------------------------------------------

class TestConfigurability:
    def test_custom_ear_threshold(self):
        """Lowering EAR threshold means more tolerance for squinting."""
        config = ClassifierConfig(ear_open=0.15)
        clf = EngagementClassifier(config=config)
        features = _engaged_features(0.0)
        features.ear_avg = 0.16  # below default 0.2 but above custom 0.15
        state, _ = clf.classify(features)
        assert state == EngagementState.ENGAGED

    def test_custom_eye_closed_duration(self):
        """Shorter eye closure threshold triggers disengaged sooner."""
        config = ClassifierConfig(eye_closed_duration=0.2)
        clf = EngagementClassifier(config=config)
        clf.classify(_disengaged_eyes_closed(0.0))
        state, _ = clf.classify(_disengaged_eyes_closed(0.25))
        assert state == EngagementState.DISENGAGED

    def test_custom_gaze_thresholds(self):
        """Adjusting gaze thresholds changes passive/engaged boundary."""
        config = ClassifierConfig(gaze_on_screen=0.5)
        clf = EngagementClassifier(config=config)
        features = _engaged_features(0.0)
        features.gaze_score = 0.55  # above custom threshold
        state, _ = clf.classify(features)
        assert state == EngagementState.ENGAGED

    def test_custom_head_yaw_thresholds(self):
        """Wider head yaw tolerance keeps student engaged."""
        config = ClassifierConfig(head_yaw_engaged=25.0, head_yaw_passive=45.0)
        clf = EngagementClassifier(config=config)
        features = _engaged_features(0.0)
        features.head_yaw = 20.0  # above default 15 but below custom 25
        state, _ = clf.classify(features)
        assert state == EngagementState.ENGAGED

    def test_custom_yawn_duration(self):
        """Longer yawn duration threshold requires more sustained yawning."""
        config = ClassifierConfig(yawn_duration=5.0)
        clf = EngagementClassifier(config=config)
        clf.classify(_disengaged_yawning(0.0))
        state, _ = clf.classify(_disengaged_yawning(3.0))
        # 3s < 5s custom threshold
        assert state != EngagementState.DISENGAGED


# ---------------------------------------------------------------------------
# Reset tests
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_clears_temporal_state(self):
        """After reset, accumulated durations should be gone."""
        clf = EngagementClassifier()
        # Build up eye closure state
        clf.classify(_disengaged_eyes_closed(0.0))
        clf.classify(_disengaged_eyes_closed(0.4))
        # Reset
        clf.reset()
        # Same features but timer should have restarted
        state, _ = clf.classify(_disengaged_eyes_closed(0.5))
        # Only one frame, shouldn't be disengaged
        assert state != EngagementState.DISENGAGED

    def test_reset_allows_fresh_session(self):
        """After reset, classification should work cleanly."""
        clf = EngagementClassifier()
        clf.classify(_disengaged_head_turned(0.0))
        clf.reset()
        state, _ = clf.classify(_engaged_features(0.0))
        assert state == EngagementState.ENGAGED
