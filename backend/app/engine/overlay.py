"""Renders face landmarks and engagement state overlay onto video frames.

Used to generate an annotated version of the uploaded video.
"""

import os
import subprocess
import tempfile

import cv2
import numpy as np

from app.models.schemas import BlendshapeScores, FaceData, Landmark, EngagementState

# MediaPipe face mesh connections for drawing (subset — key contours only)
# Full mesh has 468+ connections; we draw the most visible ones
_FACE_OVAL = [
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
    397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
    172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109, 10,
]
_LEFT_EYE = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398, 362]
_RIGHT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246, 33]
_LIPS_OUTER = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185, 61]
_LIPS_INNER = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78]
_LEFT_EYEBROW = [276, 283, 282, 295, 285, 300, 293, 334, 296, 336]
_RIGHT_EYEBROW = [46, 53, 52, 65, 55, 70, 63, 105, 66, 107]

STATE_COLORS = {
    EngagementState.ENGAGED: (0, 200, 83),      # green (BGR)
    EngagementState.PASSIVE: (0, 180, 235),      # yellow (BGR)
    EngagementState.DISENGAGED: (60, 76, 231),   # red (BGR)
}


def draw_landmarks_on_frame(
    frame: np.ndarray,
    face_data: FaceData | None,
    state: EngagementState,
    features_text: list[str] | None = None,
) -> np.ndarray:
    """Draw face landmarks and engagement info on a frame.

    Args:
        frame: BGR image (modified in place and returned).
        face_data: Detection result (None if no face).
        state: Current engagement state.
        features_text: Optional list of feature strings to display.

    Returns:
        The annotated frame.
    """
    h, w = frame.shape[:2]
    color = STATE_COLORS.get(state, (200, 200, 200))

    if face_data is None:
        # No face — draw border and label
        cv2.rectangle(frame, (0, 0), (w - 1, h - 1), (100, 100, 100), 3)
        cv2.putText(frame, "No face detected", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 2)
        return frame

    lm = face_data.landmarks

    # Draw mesh connections
    for contour, c in [
        (_FACE_OVAL, (180, 180, 180)),
        (_LEFT_EYE, color),
        (_RIGHT_EYE, color),
        (_LIPS_OUTER, color),
        (_LIPS_INNER, (200, 200, 200)),
        (_LEFT_EYEBROW, (180, 180, 180)),
        (_RIGHT_EYEBROW, (180, 180, 180)),
    ]:
        pts = []
        for idx in contour:
            if idx < len(lm):
                pts.append((int(lm[idx].x * w), int(lm[idx].y * h)))
        for i in range(len(pts) - 1):
            cv2.line(frame, pts[i], pts[i + 1], c, 1, cv2.LINE_AA)

    # Draw key landmark dots (eyes, nose tip, mouth corners)
    key_points = [33, 133, 362, 263, 1, 78, 308]  # eye corners, nose, mouth corners
    for idx in key_points:
        if idx < len(lm):
            x, y = int(lm[idx].x * w), int(lm[idx].y * h)
            cv2.circle(frame, (x, y), 2, color, -1, cv2.LINE_AA)

    # State border
    cv2.rectangle(frame, (0, 0), (w - 1, h - 1), color, 3)

    # State label (top-left)
    label = state.value.upper()
    cv2.putText(frame, label, (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)

    # Feature text (bottom-left)
    if features_text:
        y_offset = h - 10 - (len(features_text) - 1) * 20
        for line in features_text:
            cv2.putText(frame, line, (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1, cv2.LINE_AA)
            y_offset += 20

    return frame


def render_annotated_video(
    input_path: str,
    output_path: str,
    pipeline,
) -> None:
    """Process a video and write an annotated copy with landmarks overlaid.

    Args:
        input_path: Path to the original video.
        output_path: Path to write the annotated video.
        pipeline: A Pipeline instance (used for feature extraction and classification).
    """
    from app.core.config import settings
    from app.engine.detection import DetectionEngine

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {input_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Write to a temp file with mp4v codec, then re-encode to H.264 for browser playback
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".mp4")
    os.close(tmp_fd)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(tmp_path, fourcc, fps, (w, h))

    # Create a fresh detector — cannot reuse the pipeline's detector because
    # MediaPipe VIDEO mode requires monotonically increasing timestamps,
    # and the pipeline's detector already consumed timestamps from the first pass.
    detector = DetectionEngine(model_path=pipeline._model_path, running_mode="VIDEO")

    pipeline.feature_extractor.reset()
    pipeline.classifier.reset()
    sample_every = max(1, int(fps / settings.processing_fps))

    frame_idx = 0
    last_face_data: FaceData | None = None
    last_state = EngagementState.DISENGAGED
    last_features_text: list[str] = []

    while True:
        ret, frame_bgr = cap.read()
        if not ret:
            break

        if frame_idx % sample_every == 0:
            timestamp = frame_idx / fps
            timestamp_ms = int(timestamp * 1000)

            face_data = detector.detect(frame_bgr, timestamp_ms)
            if face_data is not None:
                features = pipeline.feature_extractor.extract(face_data, timestamp)
                state, confidence = pipeline.classifier.classify(features)
                last_face_data = face_data
                last_state = state
                last_features_text = [
                    f"EAR: {features.ear_avg:.2f}  MAR: {features.mar:.2f}",
                    f"Gaze: {features.gaze_score:.2f}  Yaw: {features.head_yaw:.0f}",
                    f"Conf: {confidence:.0%}",
                ]
            else:
                last_face_data = None
                last_state = EngagementState.DISENGAGED
                last_features_text = []

        annotated = draw_landmarks_on_frame(
            frame_bgr.copy(), last_face_data, last_state, last_features_text
        )
        writer.write(annotated)
        frame_idx += 1

    cap.release()
    writer.release()
    detector.close()

    # Re-encode to H.264 for browser compatibility
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", tmp_path,
                "-c:v", "libx264", "-preset", "fast",
                "-crf", "23", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                output_path,
            ],
            capture_output=True,
            check=True,
        )
    finally:
        os.unlink(tmp_path)
