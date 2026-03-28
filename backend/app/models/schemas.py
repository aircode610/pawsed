"""Data models for the engagement detection pipeline."""

from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class EngagementState(str, Enum):
    ENGAGED = "engaged"
    PASSIVE = "passive"
    DISENGAGED = "disengaged"


@dataclass
class Landmark:
    x: float
    y: float
    z: float


@dataclass
class BlendshapeScores:
    """Subset of MediaPipe's 52 blendshapes relevant to engagement detection."""

    eye_look_down_left: float = 0.0
    eye_look_down_right: float = 0.0
    eye_look_up_left: float = 0.0
    eye_look_up_right: float = 0.0
    eye_look_in_left: float = 0.0
    eye_look_in_right: float = 0.0
    eye_look_out_left: float = 0.0
    eye_look_out_right: float = 0.0
    eye_blink_left: float = 0.0
    eye_blink_right: float = 0.0
    jaw_open: float = 0.0
    mouth_smile_left: float = 0.0
    mouth_smile_right: float = 0.0
    brow_down_left: float = 0.0
    brow_down_right: float = 0.0
    brow_inner_up: float = 0.0

    def to_array(self) -> np.ndarray:
        """Return all scores as a numpy array for variance calculation."""
        return np.array([
            self.eye_look_down_left, self.eye_look_down_right,
            self.eye_look_up_left, self.eye_look_up_right,
            self.eye_look_in_left, self.eye_look_in_right,
            self.eye_look_out_left, self.eye_look_out_right,
            self.eye_blink_left, self.eye_blink_right,
            self.jaw_open,
            self.mouth_smile_left, self.mouth_smile_right,
            self.brow_down_left, self.brow_down_right,
            self.brow_inner_up,
        ])


@dataclass
class FaceData:
    """Raw output from MediaPipe Face Mesh for one frame."""

    landmarks: list[Landmark]        # 478 landmarks (468-477 = iris, requires refine_landmarks=True)
    raw_mp_landmarks: object         # raw MediaPipe face_landmarks object (needed for solvePnP + iris gaze)
    frame_shape: tuple               # (h, w, c) — needed for coordinate scaling
    blendshapes: BlendshapeScores | None = None        # only available with FaceLandmarker (not Face Mesh)
    transformation_matrix: np.ndarray | None = None    # only available with FaceLandmarker (not Face Mesh)


@dataclass
class FeatureVector:
    """Computed engagement features for one frame."""

    ear_left: float          # Eye Aspect Ratio — left eye
    ear_right: float         # Eye Aspect Ratio — right eye
    ear_avg: float           # Average of both eyes
    mar: float               # Mouth Aspect Ratio
    gaze_score: float        # 0 = looking away, 1 = on screen
    gaze_horizontal: float   # negative = left, positive = right
    gaze_vertical: float     # negative = down, positive = up
    head_pitch: float        # degrees — positive = looking up
    head_yaw: float          # degrees — positive = looking right
    head_roll: float         # degrees — positive = tilting right
    expression_variance: float  # std dev of blendshapes over window
    timestamp: float = 0.0   # seconds from session start
    face_crop: np.ndarray | None = None  # 250×250 grayscale crop for ParaNet CNN


@dataclass
class FrameResult:
    """Complete output for a single processed frame."""

    timestamp: float
    features: FeatureVector
    state: EngagementState
    face_detected: bool = True
