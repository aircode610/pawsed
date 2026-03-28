"""Tests for Layer 2: Feature extraction with synthetic sample data.

Creates realistic fake landmark/blendshape data for three engagement states
and verifies the extractors produce expected values.
"""

import numpy as np
import pytest

from app.engine.features import (
    ExpressionVarianceTracker,
    FeatureExtractor,
    compute_ear,
    compute_ear_both,
    compute_gaze,
    compute_head_pose,
    compute_mar,
    LEFT_EYE,
    RIGHT_EYE,
)
from app.models.schemas import BlendshapeScores, FaceData, Landmark


# ---------------------------------------------------------------------------
# Helpers to build synthetic face data
# ---------------------------------------------------------------------------

def _make_landmarks(count: int = 478) -> list[Landmark]:
    """Create 478 default landmarks at origin."""
    return [Landmark(x=0.0, y=0.0, z=0.0) for _ in range(count)]


def _set_eye_landmarks(
    landmarks: list[Landmark],
    eye_indices: tuple[int, ...],
    openness: float,
) -> None:
    """Set eye landmarks to simulate a given openness level.

    openness ~0.3 = normal open eye
    openness ~0.1 = squinting / partially closed
    openness ~0.02 = closed
    """
    p1, p2, p3, p4, p5, p6 = eye_indices
    # Horizontal span
    landmarks[p1] = Landmark(x=0.0, y=0.0, z=0.0)
    landmarks[p4] = Landmark(x=1.0, y=0.0, z=0.0)
    # Upper lid
    landmarks[p2] = Landmark(x=0.3, y=openness, z=0.0)
    landmarks[p3] = Landmark(x=0.7, y=openness, z=0.0)
    # Lower lid
    landmarks[p5] = Landmark(x=0.7, y=-openness, z=0.0)
    landmarks[p6] = Landmark(x=0.3, y=-openness, z=0.0)


def _set_mouth_landmarks(landmarks: list[Landmark], openness: float) -> None:
    """Set mouth landmarks to simulate open/closed mouth.

    openness ~0.1 = closed mouth (MAR low)
    openness ~0.5 = yawning (MAR high)
    """
    # Corners
    landmarks[78] = Landmark(x=0.0, y=0.0, z=0.0)
    landmarks[308] = Landmark(x=1.0, y=0.0, z=0.0)
    # Top/bottom center
    landmarks[13] = Landmark(x=0.5, y=openness, z=0.0)
    landmarks[14] = Landmark(x=0.5, y=-openness, z=0.0)
    # Upper mid
    landmarks[12] = Landmark(x=0.35, y=openness * 0.8, z=0.0)
    landmarks[11] = Landmark(x=0.65, y=openness * 0.8, z=0.0)
    # Lower mid
    landmarks[16] = Landmark(x=0.35, y=-openness * 0.8, z=0.0)
    landmarks[17] = Landmark(x=0.65, y=-openness * 0.8, z=0.0)


def _rotation_matrix(pitch_deg: float, yaw_deg: float, roll_deg: float) -> np.ndarray:
    """Build a 4x4 transformation matrix from Euler angles (degrees)."""
    p, y, r = np.radians([pitch_deg, yaw_deg, roll_deg])

    Rx = np.array([
        [1, 0, 0],
        [0, np.cos(p), -np.sin(p)],
        [0, np.sin(p), np.cos(p)],
    ])
    Ry = np.array([
        [np.cos(y), 0, np.sin(y)],
        [0, 1, 0],
        [-np.sin(y), 0, np.cos(y)],
    ])
    Rz = np.array([
        [np.cos(r), -np.sin(r), 0],
        [np.sin(r), np.cos(r), 0],
        [0, 0, 1],
    ])

    rot = Rz @ Ry @ Rx
    mat = np.eye(4)
    mat[:3, :3] = rot
    return mat


def make_engaged_face() -> FaceData:
    """Simulate an engaged student: eyes open, mouth closed, looking forward."""
    landmarks = _make_landmarks()
    _set_eye_landmarks(landmarks, RIGHT_EYE, openness=0.15)
    _set_eye_landmarks(landmarks, LEFT_EYE, openness=0.15)
    _set_mouth_landmarks(landmarks, openness=0.05)

    blendshapes = BlendshapeScores(
        eye_look_down_left=0.05,
        eye_look_down_right=0.05,
        eye_look_up_left=0.05,
        eye_look_up_right=0.05,
        eye_look_in_left=0.1,
        eye_look_in_right=0.1,
        eye_look_out_left=0.02,
        eye_look_out_right=0.02,
        eye_blink_left=0.05,
        eye_blink_right=0.05,
        jaw_open=0.02,
        mouth_smile_left=0.1,
        mouth_smile_right=0.1,
        brow_down_left=0.0,
        brow_down_right=0.0,
        brow_inner_up=0.1,
    )

    matrix = _rotation_matrix(pitch_deg=2.0, yaw_deg=3.0, roll_deg=1.0)

    return FaceData(landmarks=landmarks, blendshapes=blendshapes, transformation_matrix=matrix)


def make_passive_face() -> FaceData:
    """Simulate a passive student: eyes open but gaze drifting, slight head tilt."""
    landmarks = _make_landmarks()
    _set_eye_landmarks(landmarks, RIGHT_EYE, openness=0.12)
    _set_eye_landmarks(landmarks, LEFT_EYE, openness=0.12)
    _set_mouth_landmarks(landmarks, openness=0.06)

    blendshapes = BlendshapeScores(
        eye_look_down_left=0.3,
        eye_look_down_right=0.3,
        eye_look_up_left=0.0,
        eye_look_up_right=0.0,
        eye_look_in_left=0.05,
        eye_look_in_right=0.05,
        eye_look_out_left=0.25,
        eye_look_out_right=0.25,
        eye_blink_left=0.1,
        eye_blink_right=0.1,
        jaw_open=0.05,
        mouth_smile_left=0.02,
        mouth_smile_right=0.02,
        brow_down_left=0.05,
        brow_down_right=0.05,
        brow_inner_up=0.02,
    )

    matrix = _rotation_matrix(pitch_deg=8.0, yaw_deg=20.0, roll_deg=5.0)

    return FaceData(landmarks=landmarks, blendshapes=blendshapes, transformation_matrix=matrix)


def make_disengaged_face() -> FaceData:
    """Simulate a disengaged student: eyes closing, yawning, head turned away."""
    landmarks = _make_landmarks()
    _set_eye_landmarks(landmarks, RIGHT_EYE, openness=0.03)
    _set_eye_landmarks(landmarks, LEFT_EYE, openness=0.03)
    _set_mouth_landmarks(landmarks, openness=0.45)

    blendshapes = BlendshapeScores(
        eye_look_down_left=0.7,
        eye_look_down_right=0.7,
        eye_look_up_left=0.0,
        eye_look_up_right=0.0,
        eye_look_in_left=0.0,
        eye_look_in_right=0.0,
        eye_look_out_left=0.6,
        eye_look_out_right=0.6,
        eye_blink_left=0.8,
        eye_blink_right=0.8,
        jaw_open=0.7,
        mouth_smile_left=0.0,
        mouth_smile_right=0.0,
        brow_down_left=0.3,
        brow_down_right=0.3,
        brow_inner_up=0.0,
    )

    matrix = _rotation_matrix(pitch_deg=25.0, yaw_deg=45.0, roll_deg=10.0)

    return FaceData(landmarks=landmarks, blendshapes=blendshapes, transformation_matrix=matrix)


# ---------------------------------------------------------------------------
# EAR Tests
# ---------------------------------------------------------------------------

class TestEAR:
    def test_open_eyes_high_ear(self):
        face = make_engaged_face()
        ear = compute_ear(face.landmarks, RIGHT_EYE)
        assert ear > 0.2, f"Open eyes should give EAR > 0.2, got {ear:.3f}"

    def test_closed_eyes_low_ear(self):
        face = make_disengaged_face()
        ear = compute_ear(face.landmarks, RIGHT_EYE)
        assert ear < 0.1, f"Closed eyes should give EAR < 0.1, got {ear:.3f}"

    def test_both_eyes_symmetric(self):
        face = make_engaged_face()
        ear_l, ear_r, ear_avg = compute_ear_both(face.landmarks)
        assert abs(ear_l - ear_r) < 0.01, "Symmetric face should give similar EAR for both eyes"
        assert abs(ear_avg - (ear_l + ear_r) / 2) < 1e-6

    def test_ear_decreases_as_eyes_close(self):
        """EAR should monotonically decrease as openness decreases."""
        ears = []
        for openness in [0.2, 0.15, 0.1, 0.05, 0.02]:
            landmarks = _make_landmarks()
            _set_eye_landmarks(landmarks, RIGHT_EYE, openness)
            ears.append(compute_ear(landmarks, RIGHT_EYE))
        for i in range(len(ears) - 1):
            assert ears[i] > ears[i + 1], f"EAR should decrease: {ears}"


# ---------------------------------------------------------------------------
# MAR Tests
# ---------------------------------------------------------------------------

class TestMAR:
    def test_closed_mouth_low_mar(self):
        face = make_engaged_face()
        mar = compute_mar(face.landmarks)
        assert mar < 0.3, f"Closed mouth should give low MAR, got {mar:.3f}"

    def test_yawning_high_mar(self):
        face = make_disengaged_face()
        mar = compute_mar(face.landmarks)
        assert mar > 0.4, f"Yawning should give high MAR, got {mar:.3f}"

    def test_mar_increases_with_opening(self):
        mars = []
        for openness in [0.05, 0.15, 0.3, 0.45]:
            landmarks = _make_landmarks()
            _set_mouth_landmarks(landmarks, openness)
            mars.append(compute_mar(landmarks))
        for i in range(len(mars) - 1):
            assert mars[i] < mars[i + 1], f"MAR should increase: {mars}"


# ---------------------------------------------------------------------------
# Gaze Tests
# ---------------------------------------------------------------------------

class TestGaze:
    def test_engaged_gaze_high_score(self):
        face = make_engaged_face()
        score, h, v = compute_gaze(face.blendshapes)
        assert score > 0.9, f"Engaged student should have gaze_score > 0.9, got {score:.3f}"

    def test_disengaged_gaze_low_score(self):
        face = make_disengaged_face()
        score, h, v = compute_gaze(face.blendshapes)
        assert score < 0.5, f"Disengaged student should have gaze_score < 0.5, got {score:.3f}"

    def test_looking_down_negative_vertical(self):
        face = make_disengaged_face()
        _, _, v = compute_gaze(face.blendshapes)
        assert v < 0, f"Looking down should give negative gaze_vertical, got {v:.3f}"

    def test_passive_moderate_gaze(self):
        face = make_passive_face()
        score, _, _ = compute_gaze(face.blendshapes)
        assert 0.5 < score < 0.9, f"Passive should give moderate gaze, got {score:.3f}"


# ---------------------------------------------------------------------------
# Head Pose Tests
# ---------------------------------------------------------------------------

class TestHeadPose:
    def test_engaged_small_angles(self):
        face = make_engaged_face()
        pitch, yaw, roll = compute_head_pose(face.transformation_matrix)
        assert abs(pitch) < 10, f"Engaged pitch should be small, got {pitch:.1f}"
        assert abs(yaw) < 10, f"Engaged yaw should be small, got {yaw:.1f}"

    def test_disengaged_large_yaw(self):
        face = make_disengaged_face()
        pitch, yaw, roll = compute_head_pose(face.transformation_matrix)
        assert abs(yaw) > 30, f"Disengaged yaw should be large (turned away), got {yaw:.1f}"

    def test_identity_matrix_zero_angles(self):
        mat = np.eye(4)
        pitch, yaw, roll = compute_head_pose(mat)
        assert abs(pitch) < 0.1
        assert abs(yaw) < 0.1
        assert abs(roll) < 0.1

    def test_known_rotation(self):
        mat = _rotation_matrix(pitch_deg=0.0, yaw_deg=30.0, roll_deg=0.0)
        pitch, yaw, roll = compute_head_pose(mat)
        assert abs(yaw - 30.0) < 1.0, f"Expected yaw ~30, got {yaw:.1f}"


# ---------------------------------------------------------------------------
# Expression Variance Tests
# ---------------------------------------------------------------------------

class TestExpressionVariance:
    def test_constant_expression_low_variance(self):
        tracker = ExpressionVarianceTracker(window_size=10)
        bs = make_engaged_face().blendshapes
        for _ in range(10):
            var = tracker.update(bs)
        assert var < 0.01, f"Constant expression should have near-zero variance, got {var:.4f}"

    def test_changing_expression_higher_variance(self):
        tracker = ExpressionVarianceTracker(window_size=10)
        engaged_bs = make_engaged_face().blendshapes
        disengaged_bs = make_disengaged_face().blendshapes
        # Alternate between two very different expressions
        for i in range(10):
            bs = engaged_bs if i % 2 == 0 else disengaged_bs
            var = tracker.update(bs)
        assert var > 0.05, f"Alternating expressions should have higher variance, got {var:.4f}"

    def test_single_frame_returns_zero(self):
        tracker = ExpressionVarianceTracker(window_size=10)
        var = tracker.update(make_engaged_face().blendshapes)
        assert var == 0.0

    def test_reset_clears_buffer(self):
        tracker = ExpressionVarianceTracker(window_size=10)
        for _ in range(5):
            tracker.update(make_engaged_face().blendshapes)
        tracker.reset()
        var = tracker.update(make_engaged_face().blendshapes)
        assert var == 0.0, "After reset, single frame should return 0"


# ---------------------------------------------------------------------------
# Full FeatureExtractor integration tests
# ---------------------------------------------------------------------------

class TestFeatureExtractor:
    def test_engaged_features(self):
        extractor = FeatureExtractor(expression_window=5)
        face = make_engaged_face()
        # Feed a few frames to build up expression variance
        for i in range(5):
            result = extractor.extract(face, timestamp=i * 0.1)

        assert result.ear_avg > 0.2
        assert result.mar < 0.3
        assert result.gaze_score > 0.9
        assert abs(result.head_yaw) < 10
        assert abs(result.head_pitch) < 10

    def test_disengaged_features(self):
        extractor = FeatureExtractor(expression_window=5)
        face = make_disengaged_face()
        for i in range(5):
            result = extractor.extract(face, timestamp=i * 0.1)

        assert result.ear_avg < 0.1
        assert result.mar > 0.4
        assert result.gaze_score < 0.5
        assert abs(result.head_yaw) > 30

    def test_feature_vector_has_timestamp(self):
        extractor = FeatureExtractor()
        face = make_engaged_face()
        result = extractor.extract(face, timestamp=5.5)
        assert result.timestamp == 5.5

    def test_simulated_session_sequence(self):
        """Simulate a short session: engaged → passive → disengaged."""
        extractor = FeatureExtractor(expression_window=3)
        faces = {
            "engaged": make_engaged_face(),
            "passive": make_passive_face(),
            "disengaged": make_disengaged_face(),
        }

        results = {}
        t = 0.0
        for state_name, face in faces.items():
            for _ in range(3):
                result = extractor.extract(face, timestamp=t)
                t += 0.1
            results[state_name] = result

        # Engaged should have best scores
        assert results["engaged"].ear_avg > results["disengaged"].ear_avg
        assert results["engaged"].gaze_score > results["disengaged"].gaze_score
        assert results["engaged"].mar < results["disengaged"].mar
        assert abs(results["engaged"].head_yaw) < abs(results["disengaged"].head_yaw)
