"""Layer 1: Face detection using MediaPipe Face Mesh.

Uses refine_landmarks=True to get iris landmarks (468-477) which enable
accurate iris-based gaze tracking in features.py.

Returns FaceData with raw MediaPipe landmarks for downstream processing.
"""

import cv2
import mediapipe as mp

from app.models.schemas import FaceData, Landmark


class DetectionEngine:
    """Detects faces in video frames using MediaPipe Face Mesh."""

    def __init__(self):
        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            static_image_mode=False,
            refine_landmarks=True,        # enables iris landmarks 468-477
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def detect(self, frame_bgr, timestamp: float) -> FaceData | None:
        """Run face detection on one BGR frame.

        Returns FaceData if a face is found, None otherwise.
        """
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self._face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return None

        face_landmarks = results.multi_face_landmarks[0]

        landmarks = [
            Landmark(x=lm.x, y=lm.y, z=lm.z)
            for lm in face_landmarks.landmark
        ]

        return FaceData(
            landmarks=landmarks,
            raw_mp_landmarks=face_landmarks,
            frame_shape=frame_bgr.shape,
        )

    def close(self):
        self._face_mesh.close()
