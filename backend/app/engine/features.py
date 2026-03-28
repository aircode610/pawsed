"""Layer 2: Feature extraction from MediaPipe FaceLandmarker output.

Computes engagement signals from raw landmarks and blendshapes:
- EAR (Eye Aspect Ratio) → blink rate, eye closure
- MAR (Mouth Aspect Ratio) → yawn detection
- Gaze direction from blendshapes → screen attention
- Head pose from transformation matrix → pitch/yaw/roll
- Expression variance over sliding window → "frozen face" detection
"""

from collections import deque
from math import atan2, degrees

import numpy as np

from app.models.schemas import (
    BlendshapeScores,
    FaceData,
    FeatureVector,
    Landmark,
)

# MediaPipe landmark indices for eye/mouth features
# Right eye
RIGHT_EYE = (33, 160, 158, 133, 153, 144)
# Left eye
LEFT_EYE = (362, 385, 387, 263, 373, 380)
# Mouth — outer lip landmarks for MAR
MOUTH_TOP = (13,)
MOUTH_BOTTOM = (14,)
MOUTH_LEFT = (78,)
MOUTH_RIGHT = (308,)
MOUTH_UPPER_MID = (12, 11)
MOUTH_LOWER_MID = (16, 17)


def _landmark_dist(a: Landmark, b: Landmark) -> float:
    """Euclidean distance between two landmarks."""
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2) ** 0.5


def compute_ear(landmarks: list[Landmark], eye_indices: tuple[int, ...]) -> float:
    """Compute Eye Aspect Ratio for one eye.

    EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)

    Where p1..p6 map to the 6 eye landmark indices:
      p1=corner_outer, p2=upper_1, p3=upper_2,
      p4=corner_inner, p5=lower_2, p6=lower_1
    """
    p1, p2, p3, p4, p5, p6 = [landmarks[i] for i in eye_indices]

    vertical_1 = _landmark_dist(p2, p6)
    vertical_2 = _landmark_dist(p3, p5)
    horizontal = _landmark_dist(p1, p4)

    if horizontal == 0:
        return 0.0

    return (vertical_1 + vertical_2) / (2.0 * horizontal)


def compute_ear_both(landmarks: list[Landmark]) -> tuple[float, float, float]:
    """Compute EAR for both eyes and their average.

    Returns: (ear_left, ear_right, ear_avg)
    """
    ear_right = compute_ear(landmarks, RIGHT_EYE)
    ear_left = compute_ear(landmarks, LEFT_EYE)
    ear_avg = (ear_left + ear_right) / 2.0
    return ear_left, ear_right, ear_avg


def compute_mar(landmarks: list[Landmark]) -> float:
    """Compute Mouth Aspect Ratio for yawn detection.

    MAR = (||upper_mid1-lower_mid1|| + ||upper_mid2-lower_mid2|| + ||top-bottom||)
          / (2 * ||left_corner-right_corner||)
    """
    top = landmarks[MOUTH_TOP[0]]
    bottom = landmarks[MOUTH_BOTTOM[0]]
    left = landmarks[MOUTH_LEFT[0]]
    right = landmarks[MOUTH_RIGHT[0]]
    upper_1 = landmarks[MOUTH_UPPER_MID[0]]
    upper_2 = landmarks[MOUTH_UPPER_MID[1]]
    lower_1 = landmarks[MOUTH_LOWER_MID[0]]
    lower_2 = landmarks[MOUTH_LOWER_MID[1]]

    vertical_1 = _landmark_dist(top, bottom)
    vertical_2 = _landmark_dist(upper_1, lower_1)
    vertical_3 = _landmark_dist(upper_2, lower_2)
    horizontal = _landmark_dist(left, right)

    if horizontal == 0:
        return 0.0

    return (vertical_1 + vertical_2 + vertical_3) / (2.0 * horizontal)


def compute_gaze(blendshapes: BlendshapeScores) -> tuple[float, float, float]:
    """Compute gaze direction from eye blendshapes.

    Returns:
        gaze_score: 0.0 (looking away) to 1.0 (looking at screen)
        gaze_horizontal: negative=left, positive=right
        gaze_vertical: negative=down, positive=up
    """
    # Horizontal: looking out = away from center, looking in = toward center
    look_left = (blendshapes.eye_look_out_left + blendshapes.eye_look_in_right) / 2.0
    look_right = (blendshapes.eye_look_out_right + blendshapes.eye_look_in_left) / 2.0
    gaze_horizontal = look_right - look_left  # positive = looking right

    # Vertical: up vs down
    look_up = (blendshapes.eye_look_up_left + blendshapes.eye_look_up_right) / 2.0
    look_down = (blendshapes.eye_look_down_left + blendshapes.eye_look_down_right) / 2.0
    gaze_vertical = look_up - look_down  # positive = looking up

    # Gaze score: 1.0 when looking straight, drops as eyes deviate
    # Use the max deviation in any direction
    deviation = max(
        (blendshapes.eye_look_out_left + blendshapes.eye_look_out_right) / 2.0,
        look_down,
        look_up,
    )
    gaze_score = max(0.0, 1.0 - deviation)

    return gaze_score, gaze_horizontal, gaze_vertical


def compute_head_pose(transformation_matrix: np.ndarray) -> tuple[float, float, float]:
    """Extract pitch, yaw, roll (degrees) from 4x4 facial transformation matrix.

    Uses rotation matrix decomposition (ZYX convention).

    Returns: (pitch, yaw, roll) in degrees
    """
    r = transformation_matrix[:3, :3]

    # Clamp to avoid numerical issues with asin
    sy = -r[2, 0]
    sy = max(-1.0, min(1.0, sy))

    yaw = degrees(atan2(-r[2, 0], (r[0, 0] ** 2 + r[1, 0] ** 2) ** 0.5))
    pitch = degrees(atan2(r[2, 1], r[2, 2]))
    roll = degrees(atan2(r[1, 0], r[0, 0]))

    return pitch, yaw, roll


class ExpressionVarianceTracker:
    """Tracks expression variance over a sliding window of frames.

    Low variance = "frozen face" = likely zoned out.
    """

    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self._buffer: deque[np.ndarray] = deque(maxlen=window_size)

    def update(self, blendshapes: BlendshapeScores) -> float:
        """Add a frame's blendshapes and return current variance.

        Returns the mean standard deviation across all blendshape channels.
        Returns 0.0 if the buffer has fewer than 2 frames.
        """
        self._buffer.append(blendshapes.to_array())

        if len(self._buffer) < 2:
            return 0.0

        stacked = np.stack(list(self._buffer))  # (window, num_blendshapes)
        per_channel_std = np.std(stacked, axis=0)  # std per blendshape
        return float(np.mean(per_channel_std))

    def reset(self):
        self._buffer.clear()


class FeatureExtractor:
    """Orchestrates all feature extraction for a stream of frames."""

    def __init__(self, expression_window: int = 30):
        self.variance_tracker = ExpressionVarianceTracker(window_size=expression_window)

    def extract(self, face_data: FaceData, timestamp: float = 0.0) -> FeatureVector:
        """Extract all engagement features from a single frame's face data."""
        ear_left, ear_right, ear_avg = compute_ear_both(face_data.landmarks)
        mar = compute_mar(face_data.landmarks)
        gaze_score, gaze_h, gaze_v = compute_gaze(face_data.blendshapes)
        pitch, yaw, roll = compute_head_pose(face_data.transformation_matrix)
        expr_var = self.variance_tracker.update(face_data.blendshapes)

        return FeatureVector(
            ear_left=ear_left,
            ear_right=ear_right,
            ear_avg=ear_avg,
            mar=mar,
            gaze_score=gaze_score,
            gaze_horizontal=gaze_h,
            gaze_vertical=gaze_v,
            head_pitch=pitch,
            head_yaw=yaw,
            head_roll=roll,
            expression_variance=expr_var,
            timestamp=timestamp,
        )

    def reset(self):
        """Reset state between sessions."""
        self.variance_tracker.reset()
