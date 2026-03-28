"""Layer 2: Feature extraction from MediaPipe Face Mesh output.

Integrates two approaches for maximum accuracy:
- Iris-based gaze  (Amir's implementation) — more accurate than blendshape gaze
- solvePnP head pose (Amir's implementation) — more accurate than matrix decomposition
- EAR / MAR from landmarks (unchanged)
- Expression variance from landmark stability over sliding window
"""

import math
from collections import deque

import cv2
import numpy as np

from app.models.schemas import FaceData, FeatureVector, Landmark

# ── Landmark indices ──────────────────────────────────────────────────────────
RIGHT_EYE   = (33, 160, 158, 133, 153, 144)
LEFT_EYE    = (362, 385, 387, 263, 373, 380)

MOUTH_TOP        = 13
MOUTH_BOTTOM     = 14
MOUTH_LEFT       = 78
MOUTH_RIGHT      = 308
MOUTH_UPPER_MID  = (12, 11)
MOUTH_LOWER_MID  = (16, 17)

# Iris landmarks (requires refine_landmarks=True)
IRIS_LEFT        = 468
IRIS_RIGHT       = 473
LEFT_EYE_TOP     = 159
LEFT_EYE_BOTTOM  = 145
RIGHT_EYE_TOP    = 386
RIGHT_EYE_BOTTOM = 374

# Head pose — 3D model points (average face proportions)
HEAD_POSE_3D = np.array([
    (0.0,    0.0,    0.0),      # Nose tip
    (0.0,   -330.0, -65.0),     # Chin
    (-225.0, 170.0, -135.0),    # Left eye left corner
    (225.0,  170.0, -135.0),    # Right eye right corner
    (-150.0,-150.0, -125.0),    # Left mouth corner
    (150.0, -150.0, -125.0),    # Right mouth corner
], dtype=np.float64)

# Landmark indices for the 6 head pose reference points (matching 3D model above)
HEAD_POSE_INDICES = [1, 152, 33, 263, 61, 291]

# Key landmarks used for expression variance (stability proxy)
STABILITY_INDICES = [1, 33, 61, 199, 263, 291]


# ── EAR ───────────────────────────────────────────────────────────────────────

def _dist(a: Landmark, b: Landmark) -> float:
    return ((a.x - b.x)**2 + (a.y - b.y)**2 + (a.z - b.z)**2) ** 0.5


def _ear(landmarks: list[Landmark], indices: tuple) -> float:
    p1, p2, p3, p4, p5, p6 = [landmarks[i] for i in indices]
    v1 = _dist(p2, p6)
    v2 = _dist(p3, p5)
    h  = _dist(p1, p4)
    return (v1 + v2) / (2.0 * h) if h > 0 else 0.0


def compute_ear_both(landmarks: list[Landmark]) -> tuple[float, float, float]:
    ear_r = _ear(landmarks, RIGHT_EYE)
    ear_l = _ear(landmarks, LEFT_EYE)
    return ear_l, ear_r, (ear_l + ear_r) / 2.0


# ── MAR ───────────────────────────────────────────────────────────────────────

def compute_mar(landmarks: list[Landmark]) -> float:
    top    = landmarks[MOUTH_TOP]
    bottom = landmarks[MOUTH_BOTTOM]
    left   = landmarks[MOUTH_LEFT]
    right  = landmarks[MOUTH_RIGHT]
    u1     = landmarks[MOUTH_UPPER_MID[0]]
    u2     = landmarks[MOUTH_UPPER_MID[1]]
    l1     = landmarks[MOUTH_LOWER_MID[0]]
    l2     = landmarks[MOUTH_LOWER_MID[1]]

    v1 = _dist(top, bottom)
    v2 = _dist(u1, l1)
    v3 = _dist(u2, l2)
    h  = _dist(left, right)
    return (v1 + v2 + v3) / (2.0 * h) if h > 0 else 0.0


# ── Iris-based gaze (Amir's implementation) ───────────────────────────────────

def compute_gaze_iris(raw_mp_landmarks, frame_w: int, frame_h: int) -> tuple[float, float, float]:
    """Compute gaze from iris position relative to eye boundaries.

    More accurate than blendshape-based gaze.

    Returns:
        gaze_score:      0.0 (looking away) to 1.0 (on screen)
        gaze_horizontal: negative = left, positive = right
        gaze_vertical:   negative = down, positive = up
    """
    lm = raw_mp_landmarks.landmark

    TOP_CAMERA_BIAS = 0.5   # compensate for typical top-mounted webcam

    def safe_div(a, b, default=0.5):
        return a / b if b != 0 else default

    # Horizontal gaze
    left_w  = max(lm[133].x - lm[33].x,  0.01)
    right_w = max(lm[263].x - lm[362].x, 0.01)

    l_gaze_x = safe_div(lm[IRIS_LEFT].x  - lm[33].x,  left_w)
    r_gaze_x = safe_div(lm[IRIS_RIGHT].x - lm[362].x, right_w)

    # Vertical gaze
    left_h  = max(lm[LEFT_EYE_BOTTOM].y  - lm[LEFT_EYE_TOP].y,  0.01)
    right_h = max(lm[RIGHT_EYE_BOTTOM].y - lm[RIGHT_EYE_TOP].y, 0.01)

    l_gaze_y = safe_div(lm[IRIS_LEFT].y  - lm[LEFT_EYE_TOP].y,  left_h) - 0.5
    r_gaze_y = safe_div(lm[IRIS_RIGHT].y - lm[RIGHT_EYE_TOP].y, right_h) - 0.5

    gaze_x = np.clip((l_gaze_x + r_gaze_x) / 2.0, 0.0, 1.0)
    gaze_y = (l_gaze_y + r_gaze_y) / 2.0 + TOP_CAMERA_BIAS
    gaze_y = np.clip((gaze_y + 1.0) / 2.0, 0.0, 1.0)

    # gaze_score: 1.0 when iris centered, drops toward edges
    center_x, center_y = 0.5, 0.45
    deviation = math.hypot(gaze_x - center_x, gaze_y - center_y)
    gaze_score = float(max(0.0, 1.0 - deviation * 2.5))

    # Return horizontal as signed (-0.5..0.5 relative to center)
    gaze_horizontal = float(gaze_x - 0.5)
    gaze_vertical   = float(0.5 - gaze_y)   # positive = looking up

    return gaze_score, gaze_horizontal, gaze_vertical


# ── solvePnP head pose (Amir's implementation) ────────────────────────────────

def compute_head_pose_solvepnp(
    raw_mp_landmarks,
    frame_shape: tuple,
) -> tuple[float, float, float]:
    """Estimate head pitch/yaw/roll using solvePnP.

    More accurate than rotation matrix decomposition.

    Returns: (pitch, yaw, roll) in degrees.
    """
    h, w = frame_shape[:2]
    focal_length = w / (2 * math.tan(math.pi / 6))   # assumes ~60° horizontal FoV
    camera_matrix = np.array([
        [focal_length, 0, w / 2],
        [0, focal_length, h / 2],
        [0, 0, 1],
    ], dtype=np.float64)
    dist_coeffs = np.zeros((4, 1))

    lm = raw_mp_landmarks.landmark
    image_points = np.array([
        (lm[i].x * w, lm[i].y * h) for i in HEAD_POSE_INDICES
    ], dtype=np.float64)

    success, rvec, tvec = cv2.solvePnP(
        HEAD_POSE_3D, image_points, camera_matrix, dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    if not success:
        return 0.0, 0.0, 0.0

    rot_mat, _ = cv2.Rodrigues(rvec)
    pose_mat   = cv2.hconcat((rot_mat, tvec))
    _, _, _, _, _, _, euler = cv2.decomposeProjectionMatrix(pose_mat)
    pitch_raw, yaw_raw, roll_raw = [float(a) for a in euler.flatten()]

    def norm_angle(a):
        while a >  180: a -= 360
        while a < -180: a += 360
        return a

    def norm_pitch(p):
        if p > 180: p -= 360
        p = -p
        if p < -90: p = -(180 + p)
        elif p > 90: p = 180 - p
        return -p

    return norm_pitch(pitch_raw), norm_angle(yaw_raw), norm_angle(roll_raw)


# ── Expression variance (landmark stability proxy) ────────────────────────────

class ExpressionVarianceTracker:
    """Tracks movement variance of key landmarks over a sliding window.

    Used as expression variance proxy when blendshapes are unavailable.
    Low variance = frozen/still face = likely zoned out.
    """

    def __init__(self, window_size: int = 30):
        self._buf: deque[np.ndarray] = deque(maxlen=window_size)

    def update(self, landmarks: list[Landmark], frame_w: int, frame_h: int) -> float:
        pts = np.array([
            [landmarks[i].x * frame_w, landmarks[i].y * frame_h]
            for i in STABILITY_INDICES
        ], dtype=np.float32)
        self._buf.append(pts.flatten())

        if len(self._buf) < 2:
            return 0.0

        stacked = np.stack(list(self._buf))
        return float(np.mean(np.std(stacked, axis=0)))

    def reset(self):
        self._buf.clear()


# ── Face crop for ParaNet ─────────────────────────────────────────────────────

def extract_face_crop(
    landmarks: list[Landmark],
    frame_bgr: np.ndarray,
    size: int = 250,
    padding: float = 0.20,
) -> np.ndarray | None:
    """Crop face region from frame using landmark bounding box → 250×250 grayscale."""
    h, w = frame_bgr.shape[:2]
    xs = [lm.x * w for lm in landmarks]
    ys = [lm.y * h for lm in landmarks]

    px = int((max(xs) - min(xs)) * padding)
    py = int((max(ys) - min(ys)) * padding)

    x1 = max(0, int(min(xs)) - px)
    y1 = max(0, int(min(ys)) - py)
    x2 = min(w, int(max(xs)) + px)
    y2 = min(h, int(max(ys)) + py)

    if x2 <= x1 or y2 <= y1:
        return None

    gray = cv2.cvtColor(frame_bgr[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, (size, size))


# ── Feature extractor ─────────────────────────────────────────────────────────

class FeatureExtractor:
    """Orchestrates all feature extraction for a stream of frames."""

    def __init__(self, expression_window: int = 30):
        self.variance_tracker = ExpressionVarianceTracker(window_size=expression_window)

    def extract(
        self,
        face_data: FaceData,
        timestamp: float = 0.0,
        frame_bgr: np.ndarray | None = None,
    ) -> FeatureVector:
        """Extract all engagement features from one frame's FaceData.

        Args:
            face_data:  Output from DetectionEngine.detect()
            timestamp:  Seconds from session start
            frame_bgr:  Original BGR frame (used for face crop + solvePnP fallback)
        """
        lm = face_data.landmarks
        h, w = face_data.frame_shape[:2]

        ear_l, ear_r, ear_avg = compute_ear_both(lm)
        mar = compute_mar(lm)

        # Iris gaze (primary) — requires raw_mp_landmarks with refine_landmarks=True
        gaze_score, gaze_h, gaze_v = compute_gaze_iris(face_data.raw_mp_landmarks, w, h)

        # Head pose via solvePnP
        pitch, yaw, roll = compute_head_pose_solvepnp(face_data.raw_mp_landmarks, face_data.frame_shape)

        # Expression variance from landmark stability
        expr_var = self.variance_tracker.update(lm, w, h)
        # Normalize to roughly same scale as blendshape variance (0 – 0.1)
        expr_var = min(expr_var / 200.0, 0.1)

        face_crop = (
            extract_face_crop(lm, frame_bgr)
            if frame_bgr is not None
            else None
        )

        return FeatureVector(
            ear_left=ear_l,
            ear_right=ear_r,
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
            face_crop=face_crop,
        )

    def reset(self):
        self.variance_tracker.reset()
