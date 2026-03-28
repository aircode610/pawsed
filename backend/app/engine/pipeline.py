"""Pipeline orchestrator — wires L1 → L2 → L3 for each video frame.

Detection (L1) is plugged in here. When your teammate finishes detection.py,
import DetectionEngine and replace the TODO stub below.
"""

from app.analytics.events import Event, EventLogger
from app.engine.classifier import ClassifierConfig, EngagementClassifier
from app.engine.detection import DetectionEngine
from app.engine.features import FeatureExtractor
from app.models.schemas import EngagementState, FrameResult


class Pipeline:
    """Processes a stream of video frames and produces FrameResults + Events.

    Usage (video file):
        pipeline = Pipeline()
        results, events, duration = pipeline.process_video(video_path)

    Usage (single frame, live mode):
        pipeline = Pipeline()
        result = pipeline.process_frame(frame_bgr, timestamp)
    """

    def __init__(self, config: ClassifierConfig | None = None):
        self.feature_extractor = FeatureExtractor()
        self.classifier = EngagementClassifier(config)
        self.event_logger = EventLogger(
            thresholds={
                "mar_yawn": (config or ClassifierConfig()).mar_yawn,
                "ear_open": (config or ClassifierConfig()).ear_open,
                "gaze_passive": (config or ClassifierConfig()).gaze_passive,
            }
        )
        self.detector = DetectionEngine()

    def process_video(self, video_path: str) -> tuple[list[FrameResult], list[Event], float]:
        """Process a video file end-to-end.

        Returns:
            results: per-frame FrameResults
            events: completed distraction events
            duration: total video duration in seconds
        """
        import cv2

        from app.core.config import settings

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps

        # Sample every Nth frame to hit target processing FPS
        sample_every = max(1, int(fps / settings.processing_fps))

        results: list[FrameResult] = []
        frame_idx = 0

        while True:
            ret, frame_bgr = cap.read()
            if not ret:
                break

            if frame_idx % sample_every == 0:
                timestamp = frame_idx / fps
                result = self._process_frame_bgr(frame_bgr, timestamp)
                results.append(result)
                self.event_logger.process(result)

            frame_idx += 1

        cap.release()

        # Close any open distraction at session end
        self.event_logger.flush(duration)
        events = self.event_logger.events

        return results, events, duration

    def process_frame(self, frame_bgr, timestamp: float) -> tuple[FrameResult, Event | None]:
        """Process a single frame (live mode).

        Returns the FrameResult and an Event if one just completed.
        """
        result = self._process_frame_bgr(frame_bgr, timestamp)
        event = self.event_logger.process(result)
        return result, event

    def _process_frame_bgr(self, frame_bgr, timestamp: float) -> FrameResult:
        """Internal: run L1 → L2 → L3 on one frame."""
        # --- L1: Detection ---
        face_data = self.detector.detect(frame_bgr, timestamp)

        if face_data is None:
            # No face in frame
            from app.models.schemas import FeatureVector
            return FrameResult(
                timestamp=timestamp,
                features=FeatureVector(
                    ear_left=0.0, ear_right=0.0, ear_avg=0.0,
                    mar=0.0, gaze_score=0.0,
                    gaze_horizontal=0.0, gaze_vertical=0.0,
                    head_pitch=0.0, head_yaw=0.0, head_roll=0.0,
                    expression_variance=0.0,
                    timestamp=timestamp,
                ),
                state=EngagementState.DISENGAGED,
                face_detected=False,
            )

        # --- L2: Feature extraction (pass frame for face crop → ParaNet) ---
        features = self.feature_extractor.extract(face_data, timestamp, frame_bgr=frame_bgr)

        # --- L3: Classification ---
        state, _confidence = self.classifier.classify(features)

        return FrameResult(
            timestamp=timestamp,
            features=features,
            state=state,
            face_detected=True,
        )

    def reset(self) -> None:
        """Reset all state between sessions."""
        self.feature_extractor.reset()
        self.classifier.reset()
        self.event_logger.reset()


