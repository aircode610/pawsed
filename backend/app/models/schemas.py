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
    """Raw output from MediaPipe FaceLandmarker for one frame."""

    landmarks: list[Landmark]  # 478 landmarks
    blendshapes: BlendshapeScores
    transformation_matrix: np.ndarray  # 4x4 matrix


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
    timestamp: float = 0.0  # seconds from session start


@dataclass
class FaceResult:
    """Engagement result for one tracked face in a frame."""

    face_id: int             # Tracked face ID (stable across frames)
    features: FeatureVector
    state: EngagementState
    face_detected: bool = True
    centroid_x: float = 0.0  # Face center for tracking (normalized 0-1)
    centroid_y: float = 0.0


class RiskLevel(str, Enum):
    LOW = "low"              # Most students engaged
    MODERATE = "moderate"    # Some students drifting
    HIGH = "high"            # Many students disengaged
    CRITICAL = "critical"    # Majority disengaged — lecture is failing


@dataclass
class FrameResult:
    """Complete output for a single processed frame (all faces)."""

    timestamp: float
    faces: list[FaceResult] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    disengaged_count: int = 0
    total_faces: int = 0
    disengaged_pct: float = 0.0

    # Backward compat — aggregate state from all faces
    @property
    def features(self) -> FeatureVector:
        """Return features of the first face (backward compat)."""
        if self.faces:
            return self.faces[0].features
        return FeatureVector(
            ear_left=0.0, ear_right=0.0, ear_avg=0.0,
            mar=0.0, gaze_score=0.0, gaze_horizontal=0.0, gaze_vertical=0.0,
            head_pitch=0.0, head_yaw=0.0, head_roll=0.0,
            expression_variance=0.0, timestamp=self.timestamp,
        )

    @property
    def state(self) -> EngagementState:
        """Return the majority engagement state across all faces.

        Uses the classroom-level disengaged_pct to determine the overall state,
        so 1 person disengaged out of 10 doesn't tank the whole frame.
        """
        if not self.faces:
            return EngagementState.DISENGAGED
        # >50% disengaged = frame is disengaged
        if self.disengaged_pct > 50:
            return EngagementState.DISENGAGED
        # >50% passive+disengaged = frame is passive
        passive_count = sum(1 for f in self.faces if f.state == EngagementState.PASSIVE)
        passive_pct = ((passive_count + self.disengaged_count) / self.total_faces * 100) if self.total_faces > 0 else 0
        if passive_pct > 50:
            return EngagementState.PASSIVE
        return EngagementState.ENGAGED

    @property
    def face_detected(self) -> bool:
        return self.total_faces > 0
