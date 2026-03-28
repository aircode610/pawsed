"""Layer 1: MediaPipe FaceLandmarker detection engine.

Wraps MediaPipe's FaceLandmarker to extract 478 landmarks,
52 blendshapes, and a 4x4 facial transformation matrix per frame.
Converts MediaPipe results into our FaceData dataclass.
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

# Default model path — can be overridden via constructor
_DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "models", "face_landmarker.task"
)


class DetectionEngine:
    """MediaPipe FaceLandmarker wrapper.

    Supports VIDEO running mode (for pre-recorded files with timestamps)
    and IMAGE mode (for single frames without timestamps).
    """

    def __init__(
        self,
        model_path: str | None = None,
        running_mode: str = "VIDEO",
        num_faces: int = 1,
    ):
        resolved_path = model_path or _DEFAULT_MODEL_PATH
        resolved_path = os.path.abspath(resolved_path)

        if not os.path.exists(resolved_path):
            raise FileNotFoundError(
                f"MediaPipe model not found at {resolved_path}. "
                f"Download it with:\n"
                f"  mkdir -p models && curl -L -o models/face_landmarker.task "
                f"'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task'"
            )

        mode = (
            vision.RunningMode.VIDEO
            if running_mode == "VIDEO"
            else vision.RunningMode.IMAGE
        )

        base_options = mp.tasks.BaseOptions(model_asset_path=resolved_path)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=mode,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
            num_faces=num_faces,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._detector = vision.FaceLandmarker.create_from_options(options)
        self._running_mode = mode

    def detect(self, frame_bgr: np.ndarray, timestamp_ms: int = 0) -> FaceData | None:
        """Run face detection on a BGR frame.

        Args:
            frame_bgr: OpenCV BGR image (numpy array).
            timestamp_ms: Frame timestamp in milliseconds (required for VIDEO mode).

        Returns:
            FaceData if a face was detected, None otherwise.
        """
        # Convert BGR → RGB for MediaPipe
        frame_rgb = frame_bgr[:, :, ::-1].copy()
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        if self._running_mode == vision.RunningMode.VIDEO:
            result = self._detector.detect_for_video(mp_image, timestamp_ms)
        else:
            result = self._detector.detect(mp_image)

        if not result.face_landmarks:
            return None

        # Take the first face
        raw_landmarks = result.face_landmarks[0]
        raw_blendshapes = result.face_blendshapes[0] if result.face_blendshapes else []
        raw_matrix = (
            result.facial_transformation_matrixes[0]
            if result.facial_transformation_matrixes is not None
            and len(result.facial_transformation_matrixes) > 0
            else np.eye(4)
        )

        # Convert landmarks
        landmarks = [
            Landmark(x=lm.x, y=lm.y, z=lm.z)
            for lm in raw_landmarks
        ]

        # Convert blendshapes
        bs_kwargs = {}
        for category in raw_blendshapes:
            field_name = _BLENDSHAPE_MAP.get(category.category_name)
            if field_name:
                bs_kwargs[field_name] = category.score
        blendshapes = BlendshapeScores(**bs_kwargs)

        # Transformation matrix
        matrix = np.array(raw_matrix, dtype=np.float64)
        if matrix.shape != (4, 4):
            matrix = np.eye(4)

        return FaceData(
            landmarks=landmarks,
            blendshapes=blendshapes,
            transformation_matrix=matrix,
        )

    def close(self):
        """Release the MediaPipe detector resources."""
        self._detector.close()
