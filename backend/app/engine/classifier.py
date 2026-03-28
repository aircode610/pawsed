"""Layer 3: Ensemble engagement classifier.

Combines three classifiers for maximum accuracy:
  1. ParaNet CNN   (50%) — reads raw face pixels, trained on real student images
  2. Lokdin NN     (35%) — reads 11 feature numbers, trained on synthetic data
  3. Rule-based    (15%) — fast if/else thresholds, always available as fallback

If a model's weights file is missing, its weight is redistributed to the others
so the system always produces a valid prediction.

All thresholds and weights are configurable via ClassifierConfig.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from app.models.schemas import EngagementState, FeatureVector

# Label index mapping shared by all sub-classifiers
_LABELS   = [EngagementState.ENGAGED, EngagementState.PASSIVE, EngagementState.DISENGAGED]
_STATE_IDX = {s: i for i, s in enumerate(_LABELS)}


# ── Config ────────────────────────────────────────────────────────────────────

@dataclass
class ClassifierConfig:
    """All thresholds and ensemble weights."""

    # EAR thresholds
    ear_open: float = 0.2
    eye_closed_duration: float = 0.5

    # MAR thresholds
    mar_yawn: float = 0.6
    yawn_duration: float = 2.0

    # Gaze thresholds
    gaze_on_screen: float = 0.7
    gaze_passive: float = 0.5
    gaze_away_duration: float = 5.0

    # Head pose thresholds (degrees)
    head_yaw_engaged: float = 15.0
    head_yaw_passive: float = 30.0
    head_pitch_engaged: float = 10.0

    # Expression variance
    expression_var_threshold: float = 0.02

    # Ensemble model weight paths
    nn_weights_path: str = "models/engagement_nn.pt"
    paranet_weights_path: str = "models/paranet.pt"

    # Ensemble weights (must sum to 1.0)
    # Automatically renormalized if a model is unavailable
    weight_paranet: float = 0.50
    weight_nn: float = 0.35
    weight_rule: float = 0.15


# ── Temporal state for rule-based ─────────────────────────────────────────────

@dataclass
class _TemporalState:
    eyes_closed_since: float | None = None
    yawning_since: float | None = None
    gaze_away_since: float | None = None
    head_turned_since: float | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _state_to_probs(state: EngagementState, conf: float) -> np.ndarray:
    """Convert a single state + confidence into a probability distribution."""
    probs = np.full(3, (1.0 - conf) / 2.0, dtype=np.float32)
    probs[_STATE_IDX[state]] = conf
    return probs


def _try_load_nn(path: str):
    """Load NNClassifier if weights exist, else return None."""
    try:
        from app.engine.ml.nn_classifier import NNClassifier
        p = Path(path)
        if p.exists():
            return NNClassifier.load(p)
    except Exception:
        pass
    return None


def _try_load_paranet(path: str):
    """Load ParaNetClassifier if weights exist, else return None."""
    try:
        from app.engine.ml.paranet_classifier import ParaNetClassifier
        p = Path(path)
        if p.exists():
            return ParaNetClassifier.load(p)
    except Exception:
        pass
    return None


# ── Main classifier ───────────────────────────────────────────────────────────

class EngagementClassifier:
    """Ensemble engagement classifier.

    At init time it tries to load both neural network models.
    If weights are missing it falls back gracefully, redistributing
    weights to available models so the output is always valid.

    Call classify() per frame in timestamp order.
    Call reset() between sessions.
    """

    def __init__(self, config: ClassifierConfig | None = None):
        self.config = config or ClassifierConfig()
        self._temporal = _TemporalState()

        self._nn      = _try_load_nn(self.config.nn_weights_path)
        self._paranet = _try_load_paranet(self.config.paranet_weights_path)

        # Compute effective weights based on what loaded
        self._weights = self._resolve_weights()

        available = []
        if self._paranet: available.append("ParaNet CNN")
        if self._nn:      available.append("Lokdin NN")
        available.append("Rule-based")
        print(f"[Classifier] Active models: {', '.join(available)}")

    def _resolve_weights(self) -> dict[str, float]:
        c = self.config
        w = {"paranet": c.weight_paranet if self._paranet else 0.0,
             "nn":      c.weight_nn      if self._nn      else 0.0,
             "rule":    c.weight_rule}
        total = sum(w.values())
        return {k: v / total for k, v in w.items()}

    def classify(self, features: FeatureVector) -> tuple[EngagementState, float]:
        """Classify a single frame. Returns (state, confidence)."""

        # Always run rule-based (needs temporal state update)
        rule_state, rule_conf = self._rule_classify(features)
        rule_probs = _state_to_probs(rule_state, rule_conf)

        # Blend probabilities from available models
        blended = self._weights["rule"] * rule_probs

        if self._nn is not None:
            _, nn_probs = self._nn.predict(features)
            blended += self._weights["nn"] * nn_probs

        if self._paranet is not None and features.face_crop is not None:
            _, pn_probs = self._paranet.predict(features.face_crop)
            blended += self._weights["paranet"] * pn_probs

        idx        = int(np.argmax(blended))
        final_state = _LABELS[idx]
        confidence  = float(blended[idx])
        return final_state, confidence

    def reset(self):
        """Reset temporal state between sessions."""
        self._temporal = _TemporalState()

    # ── Rule-based logic ──────────────────────────────────────────────────────

    def _rule_classify(self, features: FeatureVector) -> tuple[EngagementState, float]:
        t = features.timestamp
        c = self.config
        s = self._temporal

        # Update temporal trackers
        s.eyes_closed_since = t if features.ear_avg < c.ear_open else None
        s.yawning_since     = t if features.mar > c.mar_yawn     else None

        if features.gaze_score < c.gaze_passive:
            if s.gaze_away_since is None:
                s.gaze_away_since = t
        else:
            s.gaze_away_since = None

        if abs(features.head_yaw) > c.head_yaw_passive:
            if s.head_turned_since is None:
                s.head_turned_since = t
        else:
            s.head_turned_since = None

        # Check disengaged
        dis = 0
        if s.eyes_closed_since  and (t - s.eyes_closed_since)  >= c.eye_closed_duration:  dis += 1
        if s.yawning_since       and (t - s.yawning_since)       >= c.yawn_duration:        dis += 1
        if s.gaze_away_since     and (t - s.gaze_away_since)     >= c.gaze_away_duration:   dis += 1
        if s.head_turned_since:                                                              dis += 1

        if dis > 0:
            return EngagementState.DISENGAGED, min(1.0, 0.5 + 0.15 * dis)

        # Check passive
        pas = 0
        if c.gaze_passive <= features.gaze_score < c.gaze_on_screen:       pas += 1
        if features.expression_variance < c.expression_var_threshold:       pas += 1
        if c.head_yaw_engaged < abs(features.head_yaw) <= c.head_yaw_passive: pas += 1
        if abs(features.head_pitch) > c.head_pitch_engaged:                 pas += 1

        if pas >= 2:
            return EngagementState.PASSIVE, min(1.0, 0.4 + 0.15 * pas)

        # Engaged
        score = sum([
            features.ear_avg >= c.ear_open,
            features.gaze_score >= c.gaze_on_screen,
            abs(features.head_yaw) < c.head_yaw_engaged,
            features.expression_variance >= c.expression_var_threshold,
        ])
        return EngagementState.ENGAGED, max(0.5, score / 4.0)
