"""Layer 2: Feature extraction from MediaPipe FaceLandmarker output.

Computes engagement signals from raw landmarks and blendshapes:
- EAR (Eye Aspect Ratio) → blink rate, eye closure, drowsiness
- MAR (Mouth Aspect Ratio) → yawn detection
- Gaze direction from blendshapes → screen attention
- Head pose from transformation matrix → pitch/yaw/roll
- Head motion → distraction detection (fidgeting vs stillness)
- Brow state → confusion/attention detection
- Expression variance over sliding window → "frozen face" detection
- Blink rate → drowsiness / alertness
- Drowsiness score → composite fatigue indicator
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
RIGHT_EYE = (33, 160, 158, 133, 153, 144)
LEFT_EYE = (362, 385, 387, 263, 373, 380)
MOUTH_TOP = (13,)
MOUTH_BOTTOM = (14,)
MOUTH_LEFT = (78,)
MOUTH_RIGHT = (308,)
MOUTH_UPPER_MID = (82, 312)
MOUTH_LOWER_MID = (87, 317)


def _landmark_dist(a: Landmark, b: Landmark) -> float:
    """Euclidean distance between two landmarks."""
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2) ** 0.5


def compute_ear(landmarks: list[Landmark], eye_indices: tuple[int, ...]) -> float:
    """Compute Eye Aspect Ratio for one eye."""
    p1, p2, p3, p4, p5, p6 = [landmarks[i] for i in eye_indices]
    vertical_1 = _landmark_dist(p2, p6)
    vertical_2 = _landmark_dist(p3, p5)
    horizontal = _landmark_dist(p1, p4)
    if horizontal == 0:
        return 0.0
    return (vertical_1 + vertical_2) / (2.0 * horizontal)


def compute_ear_both(landmarks: list[Landmark]) -> tuple[float, float, float]:
    """Compute EAR for both eyes and their average."""
    ear_right = compute_ear(landmarks, RIGHT_EYE)
    ear_left = compute_ear(landmarks, LEFT_EYE)
    ear_avg = (ear_left + ear_right) / 2.0
    return ear_left, ear_right, ear_avg


def compute_mar(landmarks: list[Landmark], blendshapes: BlendshapeScores | None = None) -> float:
    """Compute Mouth Aspect Ratio for yawn detection.

    Uses jawOpen blendshape when available, falls back to landmarks.
    """
    if blendshapes is not None:
        return blendshapes.jaw_open

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

    Returns: (gaze_score, gaze_horizontal, gaze_vertical)
    """
    look_left = (blendshapes.eye_look_out_left + blendshapes.eye_look_in_right) / 2.0
    look_right = (blendshapes.eye_look_out_right + blendshapes.eye_look_in_left) / 2.0
    gaze_horizontal = look_right - look_left

    look_up = (blendshapes.eye_look_up_left + blendshapes.eye_look_up_right) / 2.0
    look_down = (blendshapes.eye_look_down_left + blendshapes.eye_look_down_right) / 2.0
    gaze_vertical = look_up - look_down

    deviation = max(
        (blendshapes.eye_look_out_left + blendshapes.eye_look_out_right) / 2.0,
        look_down,
        look_up,
    )
    gaze_score = max(0.0, 1.0 - deviation)
    return gaze_score, gaze_horizontal, gaze_vertical


def compute_head_pose(transformation_matrix: np.ndarray) -> tuple[float, float, float]:
    """Extract pitch, yaw, roll (degrees) from 4x4 facial transformation matrix."""
    r = transformation_matrix[:3, :3]
    sy = -r[2, 0]
    sy = max(-1.0, min(1.0, sy))
    yaw = degrees(atan2(-r[2, 0], (r[0, 0] ** 2 + r[1, 0] ** 2) ** 0.5))
    pitch = degrees(atan2(r[2, 1], r[2, 2]))
    roll = degrees(atan2(r[1, 0], r[0, 0]))
    return pitch, yaw, roll


def compute_brow_state(blendshapes: BlendshapeScores) -> tuple[float, float]:
    """Compute brow furrow (confusion) and raise (attention/surprise).

    Returns: (brow_furrow, brow_raise) each 0.0-1.0
    """
    furrow = (blendshapes.brow_down_left + blendshapes.brow_down_right) / 2.0
    raise_ = blendshapes.brow_inner_up
    return furrow, raise_


class ExpressionVarianceTracker:
    """Tracks expression variance over a sliding window of frames."""

    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self._buffer: deque[np.ndarray] = deque(maxlen=window_size)

    def update(self, blendshapes: BlendshapeScores) -> float:
        self._buffer.append(blendshapes.to_array())
        if len(self._buffer) < 2:
            return 0.0
        stacked = np.stack(list(self._buffer))
        per_channel_std = np.std(stacked, axis=0)
        return float(np.mean(per_channel_std))

    def reset(self):
        self._buffer.clear()


class BlinkTracker:
    """Tracks blink rate and drowsiness from EAR over time.

    Blink detection: EAR drops below threshold then recovers = 1 blink.
    Drowsiness: computed from blink duration (slow blinks) + partial closure.
    """

    def __init__(self, ear_blink_threshold: float = 0.2, window_seconds: float = 60.0):
        self._threshold = ear_blink_threshold
        self._window = window_seconds
        self._blink_timestamps: deque[float] = deque()
        self._in_blink = False
        self._blink_start: float = 0.0
        self._recent_blink_durations: deque[float] = deque(maxlen=20)
        self._ear_history: deque[float] = deque(maxlen=30)  # ~3s at 10fps

    def update(self, ear_avg: float, timestamp: float) -> tuple[float, float]:
        """Update with new EAR value. Returns (blink_rate_bpm, drowsiness 0-1)."""
        self._ear_history.append(ear_avg)

        # Detect blink start
        if not self._in_blink and ear_avg < self._threshold:
            self._in_blink = True
            self._blink_start = timestamp

        # Detect blink end
        if self._in_blink and ear_avg >= self._threshold:
            self._in_blink = False
            duration = timestamp - self._blink_start
            if 0.05 < duration < 2.0:  # filter noise and sustained closure
                self._blink_timestamps.append(timestamp)
                self._recent_blink_durations.append(duration)

        # Trim old blinks outside the window
        cutoff = timestamp - self._window
        while self._blink_timestamps and self._blink_timestamps[0] < cutoff:
            self._blink_timestamps.popleft()

        # Blink rate (blinks per minute)
        blink_rate = len(self._blink_timestamps) * (60.0 / self._window)

        # Drowsiness score: combination of slow blinks + dropping EAR baseline
        drowsiness = self._compute_drowsiness(blink_rate)

        return blink_rate, drowsiness

    def _compute_drowsiness(self, blink_rate: float) -> float:
        """Composite drowsiness score 0-1.

        Indicators:
        - Slow blinks (avg duration > 0.3s is slow, normal is ~0.15s)
        - Low blink rate (< 8 bpm = drowsy stare, normal is 15-20)
        - Dropping EAR baseline (partially closing eyes over time)
        """
        score = 0.0

        # Slow blink component
        if self._recent_blink_durations:
            avg_duration = sum(self._recent_blink_durations) / len(self._recent_blink_durations)
            # Normal ~0.15s, slow ~0.3s, very slow ~0.5s+
            slow_factor = min(1.0, max(0.0, (avg_duration - 0.15) / 0.35))
            score += slow_factor * 0.4

        # Low blink rate component (drowsy stare)
        if blink_rate < 8:
            score += 0.3 * (1.0 - blink_rate / 8.0)

        # Dropping EAR baseline
        if len(self._ear_history) >= 10:
            recent_avg = sum(list(self._ear_history)[-5:]) / 5
            older_avg = sum(list(self._ear_history)[:5]) / 5
            if older_avg > 0:
                drop = max(0.0, (older_avg - recent_avg) / older_avg)
                score += drop * 0.3

        return min(1.0, score)

    def reset(self):
        self._blink_timestamps.clear()
        self._recent_blink_durations.clear()
        self._ear_history.clear()
        self._in_blink = False


class HeadMotionTracker:
    """Tracks head movement intensity from pose changes over time.

    High motion = fidgeting/distracted. Very low motion = possibly zoned out.
    """

    def __init__(self, window_size: int = 15):
        self._yaw_buffer: deque[float] = deque(maxlen=window_size)
        self._pitch_buffer: deque[float] = deque(maxlen=window_size)

    def update(self, yaw: float, pitch: float) -> float:
        """Returns head motion intensity (0 = still, higher = more movement)."""
        self._yaw_buffer.append(yaw)
        self._pitch_buffer.append(pitch)

        if len(self._yaw_buffer) < 3:
            return 0.0

        yaw_arr = np.array(self._yaw_buffer)
        pitch_arr = np.array(self._pitch_buffer)

        # Motion = standard deviation of recent head angles
        yaw_std = float(np.std(yaw_arr))
        pitch_std = float(np.std(pitch_arr))

        return (yaw_std + pitch_std) / 2.0

    def reset(self):
        self._yaw_buffer.clear()
        self._pitch_buffer.clear()


class FeatureExtractor:
    """Orchestrates all feature extraction for a stream of frames."""

    def __init__(self, expression_window: int = 30):
        self.variance_tracker = ExpressionVarianceTracker(window_size=expression_window)
        self.blink_tracker = BlinkTracker()
        self.head_motion_tracker = HeadMotionTracker()

    def extract(self, face_data: FaceData, timestamp: float = 0.0) -> FeatureVector:
        """Extract all engagement features from a single frame's face data."""
        ear_left, ear_right, ear_avg = compute_ear_both(face_data.landmarks)
        mar = compute_mar(face_data.landmarks, face_data.blendshapes)
        gaze_score, gaze_h, gaze_v = compute_gaze(face_data.blendshapes)
        pitch, yaw, roll = compute_head_pose(face_data.transformation_matrix)
        expr_var = self.variance_tracker.update(face_data.blendshapes)
        blink_rate, drowsiness = self.blink_tracker.update(ear_avg, timestamp)
        head_motion = self.head_motion_tracker.update(yaw, pitch)
        brow_furrow, brow_raise = compute_brow_state(face_data.blendshapes)

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
            blink_rate=blink_rate,
            drowsiness=drowsiness,
            head_motion=head_motion,
            brow_furrow=brow_furrow,
            brow_raise=brow_raise,
            timestamp=timestamp,
        )

    def reset(self):
        """Reset state between sessions."""
        self.variance_tracker.reset()
        self.blink_tracker.reset()
        self.head_motion_tracker.reset()
