"""ParaNet CNN engagement classifier wrapper.

Loads the ParaNet model trained in Colab (models/paranet.pt) and
classifies 250×250 grayscale face crops into engagement states.

The model outputs 6 classes matching the training dataset structure:
    Engaged_focused, Engaged_confused, Engaged_looking_away,
    Disengaged_sleepy, Disengaged_distracted, Disengaged_looking_away

These are mapped to our 3 states: engaged / passive / disengaged.
Update CLASS_MAP below once you know your dataset's exact class names
(run label_mapping.keys() in the Colab to find them).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from app.models.schemas import EngagementState

# ── Label mapping: ParaNet class index → EngagementState ─────────────────────
# Fill this in after running the Colab and printing label_mapping.
# Key   = integer class index (0-5)
# Value = one of: EngagementState.ENGAGED / PASSIVE / DISENGAGED
#
# Example (update with your actual class names):
#   0: Engaged_focused      → ENGAGED
#   1: Engaged_confused     → PASSIVE
#   2: Engaged_distracted   → PASSIVE
#   3: Disengaged_sleepy    → DISENGAGED
#   4: Disengaged_looking   → DISENGAGED
#   5: Disengaged_bored     → DISENGAGED
# LabelEncoder sorts alphabetically, so the mapping is:
# 0: Engaged_confused      → PASSIVE
# 1: Engaged_engaged       → ENGAGED
# 2: Engaged_frustrated    → PASSIVE
# 3: Not engaged_Looking Away → DISENGAGED
# 4: Not engaged_bored     → DISENGAGED
# 5: Not engaged_drowsy    → DISENGAGED
CLASS_MAP: dict[int, EngagementState] = {
    0: EngagementState.PASSIVE,
    1: EngagementState.ENGAGED,
    2: EngagementState.PASSIVE,
    3: EngagementState.DISENGAGED,
    4: EngagementState.DISENGAGED,
    5: EngagementState.DISENGAGED,
}

# Map to 3-class probability vector [engaged, passive, disengaged]
_STATE_IDX = {
    EngagementState.ENGAGED:    0,
    EngagementState.PASSIVE:    1,
    EngagementState.DISENGAGED: 2,
}


# ── ParaNet architecture (must match the Colab exactly) ──────────────────────

class ParaNet(nn.Module):
    """Dual-stream CNN. Input: (N, 1, 250, 250) grayscale."""

    def __init__(self, num_classes: int = 6):
        super().__init__()

        self.conv2Dblock1 = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(16), nn.ReLU(),
            nn.MaxPool2d(2, 2), nn.Dropout(0.4),

            nn.Conv2d(16, 32, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(32), nn.ReLU(),
            nn.MaxPool2d(4, 4), nn.Dropout(0.4),

            nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(64), nn.ReLU(),
            nn.MaxPool2d(4, 4), nn.Dropout(0.4),
        )

        self.conv2Dblock2 = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(32), nn.ReLU(),
            nn.MaxPool2d(2, 2), nn.Dropout(0.4),

            nn.Conv2d(32, 64, kernel_size=5, stride=1, padding=2),
            nn.BatchNorm2d(64), nn.ReLU(),
            nn.MaxPool2d(4, 4), nn.Dropout(0.4),

            nn.Conv2d(64, 128, kernel_size=7, stride=1, padding=3),
            nn.BatchNorm2d(128), nn.ReLU(),
            nn.MaxPool2d(4, 4), nn.Dropout(0.4),
        )

        self.fc1_linear  = nn.Linear(9408, num_classes)
        self.softmax_out = nn.Softmax(dim=1)

    def forward(self, x: torch.Tensor):
        e1 = torch.flatten(self.conv2Dblock1(x), start_dim=1)
        e2 = torch.flatten(self.conv2Dblock2(x), start_dim=1)
        combined = torch.cat([e1, e2], dim=1)
        logits   = self.fc1_linear(combined)
        return logits, self.softmax_out(logits)


# ── Classifier wrapper ────────────────────────────────────────────────────────

class ParaNetClassifier:
    """Loads a trained ParaNet and classifies 250×250 grayscale face crops."""

    def __init__(self, model: ParaNet, num_classes: int = 6) -> None:
        self.model       = model
        self.num_classes = num_classes
        self.model.eval()

    @classmethod
    def load(cls, path: str | Path, num_classes: int = 6) -> "ParaNetClassifier":
        model = ParaNet(num_classes=num_classes)
        state_dict = torch.load(path, map_location="cpu", weights_only=True)
        model.load_state_dict(state_dict)
        return cls(model, num_classes)

    def predict(self, face_crop: np.ndarray) -> tuple[EngagementState, np.ndarray]:
        """Classify a 250×250 grayscale face crop.

        Returns:
            state: predicted EngagementState
            probs: float32 array of shape (3,) → [p_engaged, p_passive, p_disengaged]
        """
        # Normalize pixel values to [0, 1]
        img = face_crop.astype(np.float32) / 255.0
        x   = torch.tensor(img).unsqueeze(0).unsqueeze(0)  # (1, 1, 250, 250)

        with torch.no_grad():
            _, softmax_probs = self.model(x)

        raw_probs = softmax_probs.squeeze(0).numpy()  # shape (num_classes,)

        # Aggregate 6-class probs into 3-class probs using CLASS_MAP
        three_class = np.zeros(3, dtype=np.float32)
        for idx, prob in enumerate(raw_probs):
            state = CLASS_MAP.get(idx, EngagementState.DISENGAGED)
            three_class[_STATE_IDX[state]] += prob

        predicted_state = [
            EngagementState.ENGAGED,
            EngagementState.PASSIVE,
            EngagementState.DISENGAGED,
        ][int(np.argmax(three_class))]

        return predicted_state, three_class
