"""Neural network engagement classifier (L3 supplement).

Architecture: 11-feature MLP → 3 classes (engaged / passive / disengaged)
Training:     synthetic data generated from known engagement patterns.
Weights:      models/engagement_nn.pt  (produced by scripts/train_nn_classifier.py)

Usage:
    clf = NNClassifier.load("models/engagement_nn.pt")
    state, probs = clf.predict(features)   # probs shape: (3,)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from app.models.schemas import EngagementState, FeatureVector

# ── Feature order (must stay in sync with training) ──────────────────────────
FEATURE_NAMES = [
    "ear_left", "ear_right", "ear_avg",
    "mar",
    "gaze_score", "gaze_horizontal", "gaze_vertical",
    "head_pitch", "head_yaw", "head_roll",
    "expression_variance",
]
N_FEATURES = len(FEATURE_NAMES)  # 11

# Approximate normalization stats (mean / std over the synthetic distribution)
FEATURE_MEANS = np.array(
    [0.24, 0.24, 0.24, 0.38, 0.60, 0.00, 0.00, 3.0, 5.0, 0.0, 0.025],
    dtype=np.float32,
)
FEATURE_STDS = np.array(
    [0.05, 0.05, 0.05, 0.16, 0.22, 0.16, 0.14, 8.0, 12.0, 5.0, 0.022],
    dtype=np.float32,
)

# Label index ↔ EngagementState (must match training label order)
IDX_TO_STATE = [EngagementState.ENGAGED, EngagementState.PASSIVE, EngagementState.DISENGAGED]
STATE_TO_IDX = {s: i for i, s in enumerate(IDX_TO_STATE)}


# ── Model architecture ────────────────────────────────────────────────────────

class EngagementNet(nn.Module):
    """Small MLP: 11 → 64 → 32 → 3."""

    def __init__(self, input_dim: int = N_FEATURES):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.25),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 3),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# ── Helper ────────────────────────────────────────────────────────────────────

def features_to_array(fv: FeatureVector) -> np.ndarray:
    """Convert a FeatureVector to a normalized float32 array."""
    raw = np.array(
        [
            fv.ear_left, fv.ear_right, fv.ear_avg,
            fv.mar,
            fv.gaze_score, fv.gaze_horizontal, fv.gaze_vertical,
            fv.head_pitch, fv.head_yaw, fv.head_roll,
            fv.expression_variance,
        ],
        dtype=np.float32,
    )
    return (raw - FEATURE_MEANS) / (FEATURE_STDS + 1e-8)


# ── Classifier wrapper ────────────────────────────────────────────────────────

class NNClassifier:
    """Wraps a trained EngagementNet for single-frame inference."""

    def __init__(self, model: EngagementNet) -> None:
        self.model = model
        self.model.eval()

    @classmethod
    def load(cls, path: str | Path) -> "NNClassifier":
        model = EngagementNet()
        state_dict = torch.load(path, map_location="cpu", weights_only=True)
        model.load_state_dict(state_dict)
        return cls(model)

    def predict(self, features: FeatureVector) -> tuple[EngagementState, np.ndarray]:
        """Return (predicted_state, class_probabilities).

        class_probabilities is shape (3,): [p_engaged, p_passive, p_disengaged]
        """
        x = torch.tensor(features_to_array(features)).unsqueeze(0)
        with torch.no_grad():
            probs = torch.softmax(self.model(x), dim=1).squeeze(0).numpy()
        return IDX_TO_STATE[int(np.argmax(probs))], probs
