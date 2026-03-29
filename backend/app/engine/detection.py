"""Layer 1: MediaPipe FaceLandmarker detection engine.

Wraps MediaPipe's FaceLandmarker to extract 478 landmarks,
52 blendshapes, and a 4x4 facial transformation matrix per frame.

Uses a tiled detection strategy for video-call layouts (Zoom/Teams):
splits the frame into a grid and detects faces per tile, then maps
coordinates back to the full frame. This handles small faces that
the full-frame detector would miss.
"""

import os

import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision

from app.models.schemas import BlendshapeScores, FaceData, Landmark

# Map MediaPipe ARKit blendshape names → our BlendshapeScores fields
_BLENDSHAPE_MAP = {
    "eyeLookDownLeft": "eye_look_down_left",
    "eyeLookDownRight": "eye_look_down_right",
    "eyeLookUpLeft": "eye_look_up_left",
    "eyeLookUpRight": "eye_look_up_right",
    "eyeLookInLeft": "eye_look_in_left",
    "eyeLookInRight": "eye_look_in_right",
    "eyeLookOutLeft": "eye_look_out_left",
    "eyeLookOutRight": "eye_look_out_right",
    "eyeBlinkLeft": "eye_blink_left",
    "eyeBlinkRight": "eye_blink_right",
    "jawOpen": "jaw_open",
    "mouthSmileLeft": "mouth_smile_left",
    "mouthSmileRight": "mouth_smile_right",
    "browDownLeft": "brow_down_left",
    "browDownRight": "brow_down_right",
    "browInnerUp": "brow_inner_up",
}

_DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "models", "face_landmarker.task"
)

# Minimum face tile size in pixels — below this, tiled detection is used
_MIN_FACE_TILE_PX = 300


class DetectionEngine:
    """MediaPipe FaceLandmarker wrapper with tiled detection for small faces.

    For single-face or large-face scenarios, runs detection on the full frame.
    For multi-face grids (Zoom/Teams), splits the frame into tiles and detects
    on each tile independently, then maps landmarks back to full-frame coords.
    """

    def __init__(
        self,
        model_path: str | None = None,
        running_mode: str = "VIDEO",
        num_faces: int = 10,
        tile_grid: tuple[int, int] = (3, 3),
        tile_overlap: int = 20,
        min_detection_confidence: float = 0.5,
        min_presence_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ):
        """
        Args:
            model_path: Path to face_landmarker.task file.
            running_mode: "VIDEO" or "IMAGE".
            num_faces: Max faces per tile during tiled detection.
            tile_grid: (rows, cols) for tiled detection grid.
            tile_overlap: Pixel overlap between tiles to catch border faces.
            min_detection_confidence: MediaPipe detection threshold.
            min_presence_confidence: MediaPipe presence threshold.
            min_tracking_confidence: MediaPipe tracking threshold.
        """
        resolved_path = model_path or _DEFAULT_MODEL_PATH
        resolved_path = os.path.abspath(resolved_path)

        if not os.path.exists(resolved_path):
            raise FileNotFoundError(
                f"MediaPipe model not found at {resolved_path}. "
                f"Download it with:\n"
                f"  mkdir -p models && curl -L -o models/face_landmarker.task "
                f"'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task'"
            )

        self._resolved_path = resolved_path
        self._tile_grid = tile_grid
        self._tile_overlap = tile_overlap
        self._num_faces_per_tile = max(2, num_faces // (tile_grid[0] * tile_grid[1]) + 1)

        mode = (
            vision.RunningMode.VIDEO
            if running_mode == "VIDEO"
            else vision.RunningMode.IMAGE
        )
        self._running_mode = mode

        # Full-frame detector (for VIDEO mode with timestamp tracking)
        base_options = mp.tasks.BaseOptions(
            model_asset_path=resolved_path,
            delegate=mp.tasks.BaseOptions.Delegate.CPU,
        )
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=mode,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
            num_faces=num_faces,
            min_face_detection_confidence=min_detection_confidence,
            min_face_presence_confidence=min_presence_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._detector = vision.FaceLandmarker.create_from_options(options)

        # Tile detector (always IMAGE mode, lower confidence for small faces in tiles)
        tile_conf = min(0.3, min_detection_confidence)
        tile_options = vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(
                model_asset_path=resolved_path,
                delegate=mp.tasks.BaseOptions.Delegate.CPU,
            ),
            running_mode=vision.RunningMode.IMAGE,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
            num_faces=self._num_faces_per_tile,
            min_face_detection_confidence=tile_conf,
            min_face_presence_confidence=tile_conf,
        )
        self._tile_detector = vision.FaceLandmarker.create_from_options(tile_options)

    def detect(self, frame_bgr: np.ndarray, timestamp_ms: int = 0) -> FaceData | None:
        """Detect first face (backward compat)."""
        faces = self.detect_multi(frame_bgr, timestamp_ms)
        return faces[0] if faces else None

    def detect_multi(self, frame_bgr: np.ndarray, timestamp_ms: int = 0) -> list[FaceData]:
        """Detect all faces, using tiled detection for small-face scenarios.

        First tries full-frame detection. If it finds any faces, returns those
        (avoids false positives from tiled detection on single-person videos).
        Only falls back to tiled detection when full-frame finds nothing,
        which indicates faces are too small for the full-frame detector.
        """
        # Try full-frame first
        full_faces = self._detect_full(frame_bgr, timestamp_ms)

        if len(full_faces) > 0:
            return full_faces

        # Full-frame found nothing — faces are likely too small (video-call grid).
        # Fall back to tiled detection.
        return self._detect_tiled(frame_bgr)

    def _detect_full(self, frame_bgr: np.ndarray, timestamp_ms: int = 0) -> list[FaceData]:
        """Standard full-frame detection."""
        frame_rgb = frame_bgr[:, :, ::-1].copy()
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        if self._running_mode == vision.RunningMode.VIDEO:
            result = self._detector.detect_for_video(mp_image, timestamp_ms)
        else:
            result = self._detector.detect(mp_image)

        return self._parse_result(result)

    def _detect_tiled(self, frame_bgr: np.ndarray) -> list[FaceData]:
        """Split frame into tiles and detect on each independently."""
        h, w = frame_bgr.shape[:2]
        rows, cols = self._tile_grid
        tile_h, tile_w = h // rows, w // cols
        overlap = self._tile_overlap

        all_faces: list[FaceData] = []
        seen_centroids: list[tuple[float, float]] = []

        for r in range(rows):
            for c in range(cols):
                y1 = max(0, r * tile_h - overlap)
                y2 = min(h, (r + 1) * tile_h + overlap)
                x1 = max(0, c * tile_w - overlap)
                x2 = min(w, (c + 1) * tile_w + overlap)
                tile = frame_bgr[y1:y2, x1:x2]

                tile_rgb = tile[:, :, ::-1].copy()
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=tile_rgb)
                result = self._tile_detector.detect(mp_image)

                if not result.face_landmarks:
                    continue

                tile_faces = self._parse_result(result)
                tile_h_actual = y2 - y1
                tile_w_actual = x2 - x1

                for face in tile_faces:
                    # Remap landmarks from tile coords to full-frame coords
                    remapped_landmarks = []
                    for lm in face.landmarks:
                        remapped_landmarks.append(Landmark(
                            x=(x1 + lm.x * tile_w_actual) / w,
                            y=(y1 + lm.y * tile_h_actual) / h,
                            z=lm.z,
                        ))

                    # Deduplicate: skip if centroid is too close to an existing face
                    nose = remapped_landmarks[1]
                    cx, cy = nose.x, nose.y
                    is_dup = False
                    for sx, sy in seen_centroids:
                        if abs(cx - sx) < 0.05 and abs(cy - sy) < 0.05:
                            is_dup = True
                            break
                    if is_dup:
                        continue

                    seen_centroids.append((cx, cy))
                    all_faces.append(FaceData(
                        landmarks=remapped_landmarks,
                        blendshapes=face.blendshapes,
                        transformation_matrix=face.transformation_matrix,
                    ))

        return all_faces

    def _parse_result(self, result) -> list[FaceData]:
        """Convert MediaPipe FaceLandmarkerResult to list of FaceData."""
        if not result.face_landmarks:
            return []

        faces = []
        for i in range(len(result.face_landmarks)):
            raw_landmarks = result.face_landmarks[i]
            raw_blendshapes = (
                result.face_blendshapes[i]
                if result.face_blendshapes and i < len(result.face_blendshapes)
                else []
            )
            raw_matrix = (
                result.facial_transformation_matrixes[i]
                if result.facial_transformation_matrixes is not None
                and i < len(result.facial_transformation_matrixes)
                else np.eye(4)
            )

            landmarks = [Landmark(x=lm.x, y=lm.y, z=lm.z) for lm in raw_landmarks]

            bs_kwargs = {}
            for category in raw_blendshapes:
                field_name = _BLENDSHAPE_MAP.get(category.category_name)
                if field_name:
                    bs_kwargs[field_name] = category.score
            blendshapes = BlendshapeScores(**bs_kwargs)

            matrix = np.array(raw_matrix, dtype=np.float64)
            if matrix.shape != (4, 4):
                matrix = np.eye(4)

            faces.append(FaceData(
                landmarks=landmarks,
                blendshapes=blendshapes,
                transformation_matrix=matrix,
            ))

        return faces

    def close(self):
        """Release resources."""
        self._detector.close()
        self._tile_detector.close()
