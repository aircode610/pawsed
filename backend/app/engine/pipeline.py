"""Pipeline orchestrator — wires L1 → L2 → L3 for each video frame.

Supports multi-face detection: processes all visible faces per frame,
tracks them across frames with stable IDs, and computes classroom-level
risk based on how many students are disengaged simultaneously.
"""

import os

from app.analytics.events import Event, EventLogger
from app.engine.classifier import ClassifierConfig, EngagementClassifier
from app.engine.detection import DetectionEngine
from app.engine.features import FeatureExtractor
from app.engine.tracker import FaceTracker
from app.models.schemas import (
    EngagementState,
    FaceResult,
    FeatureVector,
    FrameResult,
    RiskLevel,
)


def _process_chunk_worker(
    args: tuple,
) -> tuple[list[FrameResult], list[Event]]:
    """Top-level worker function for parallel video processing.

    Processes a contiguous range of frames [start_frame, end_frame) from
    a video file. Each worker creates its own Pipeline so MediaPipe state
    is fully isolated. Seeks once to start_frame then reads sequentially
    (one seek per chunk is fine; per-frame seeking would be slow for H.264).

    Args:
        args: (video_path, start_frame, end_frame, fps, processing_fps,
               model_path, config)
    """
    import cv2

    video_path, start_frame, end_frame, fps, processing_fps, model_path, config = args

    pipeline = Pipeline(config=config, model_path=model_path)
    detector = pipeline._get_detector(running_mode="VIDEO")

    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    sample_every = max(1, int(fps / processing_fps))
    results: list[FrameResult] = []
    frame_idx = start_frame

    while frame_idx < end_frame:
        ret, frame_bgr = cap.read()
        if not ret:
            break
        # Sample relative to chunk start so the first frame of every chunk
        # is always processed regardless of global frame offset.
        if (frame_idx - start_frame) % sample_every == 0:
            timestamp = frame_idx / fps
            timestamp_ms = int(timestamp * 1000)
            result = pipeline._process_frame_multi(frame_bgr, timestamp, timestamp_ms, detector)
            results.append(result)
            pipeline.event_logger.process(result)
        frame_idx += 1

    cap.release()

    chunk_end_time = end_frame / fps
    pipeline.event_logger.flush(chunk_end_time)
    events = pipeline.event_logger.events
    pipeline.close()

    return results, events


def _compute_risk_level(disengaged_pct: float, total_faces: int) -> RiskLevel:
    """Compute classroom risk level from percentage of disengaged students.

    Risk thresholds:
        LOW:      <20% disengaged — class is mostly engaged
        MODERATE: 20-40% disengaged — some students drifting
        HIGH:     40-60% disengaged — significant portion lost
        CRITICAL: >60% disengaged — majority checked out
    """
    if total_faces == 0:
        return RiskLevel.LOW
    if disengaged_pct >= 60:
        return RiskLevel.CRITICAL
    if disengaged_pct >= 40:
        return RiskLevel.HIGH
    if disengaged_pct >= 20:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


class Pipeline:
    """Processes video frames and produces per-face + classroom-level results.

    Usage (video file):
        pipeline = Pipeline(num_faces=10)
        results, events, duration = pipeline.process_video(video_path)

    Usage (single frame, live mode):
        pipeline = Pipeline(num_faces=10)
        result = pipeline.process_frame(frame_bgr, timestamp)
    """

    def __init__(
        self,
        config: ClassifierConfig | None = None,
        model_path: str | None = None,
        num_faces: int = 10,
    ):
        self.num_faces = num_faces
        self._model_path = model_path
        self._detector: DetectionEngine | None = None

        # Per-face state: feature extractors and classifiers keyed by face_id
        self._feature_extractors: dict[int, FeatureExtractor] = {}
        self._classifiers: dict[int, EngagementClassifier] = {}
        self._config = config or ClassifierConfig()

        # Face tracker for stable IDs across frames
        self.tracker = FaceTracker()

        # Event logger (uses aggregate state for backward compat)
        cfg = self._config
        self.event_logger = EventLogger(
            thresholds={
                "mar_yawn": cfg.mar_yawn,
                "ear_open": cfg.ear_open,
                "gaze_passive": cfg.gaze_passive,
                "head_pitch_disengaged": cfg.head_pitch_disengaged,
                "drowsiness_disengaged": cfg.drowsiness_disengaged,
                "head_motion_distracted": cfg.head_motion_distracted,
            }
        )

    def _get_or_create_face_pipeline(self, face_id: int) -> tuple[FeatureExtractor, EngagementClassifier]:
        """Get or create per-face feature extractor and classifier."""
        if face_id not in self._feature_extractors:
            self._feature_extractors[face_id] = FeatureExtractor()
            self._classifiers[face_id] = EngagementClassifier(self._config)
        return self._feature_extractors[face_id], self._classifiers[face_id]

    def _get_detector(self, running_mode: str = "VIDEO") -> DetectionEngine:
        if self._detector is None:
            self._detector = DetectionEngine(
                model_path=self._model_path,
                running_mode=running_mode,
                num_faces=self.num_faces,
            )
        return self._detector

    def process_video(self, video_path: str) -> tuple[list[FrameResult], list[Event], float]:
        """Process a video file end-to-end."""
        import cv2
        from app.core.config import settings

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps

        sample_every = max(1, int(fps / settings.processing_fps))
        detector = self._get_detector(running_mode="VIDEO")

        results: list[FrameResult] = []
        frame_idx = 0

        while True:
            ret, frame_bgr = cap.read()
            if not ret:
                break

            if frame_idx % sample_every == 0:
                timestamp = frame_idx / fps
                timestamp_ms = int(timestamp * 1000)
                result = self._process_frame_multi(frame_bgr, timestamp, timestamp_ms, detector)
                results.append(result)
                self.event_logger.process(result)

            frame_idx += 1

        cap.release()

        self.event_logger.flush(duration)
        events = self.event_logger.events

        return results, events, duration

    def process_video_parallel(
        self,
        video_path: str,
        workers: int | None = None,
    ) -> tuple[list[FrameResult], list[Event], float]:
        """Process a video file using parallel workers — one per CPU chunk.

        Splits the video into equal frame ranges and processes each chunk in
        a separate process. Roughly N× faster than process_video() on N cores.
        Each worker owns its own Pipeline + MediaPipe detector so there is no
        shared state. Events at chunk boundaries may be slightly shorter than
        reality (an ongoing distraction at the boundary is closed with the
        chunk's end timestamp), but this is imperceptible for lecture videos.

        Args:
            video_path: Path to the video file.
            workers: Number of parallel processes. Defaults to half the CPU
                count (capped at 8) to leave headroom for MediaPipe's internal
                threading.
        """
        import cv2
        from concurrent.futures import ProcessPoolExecutor
        from app.core.config import settings

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        cap.release()

        if workers is None:
            workers = min(max(1, (os.cpu_count() or 4) - 2), 8)

        # Build frame ranges — last chunk absorbs any remainder
        chunk_size = total_frames // workers
        ranges: list[tuple[int, int]] = []
        for i in range(workers):
            start = i * chunk_size
            end = total_frames if i == workers - 1 else (i + 1) * chunk_size
            ranges.append((start, end))

        chunk_args = [
            (video_path, start, end, fps, settings.processing_fps, self._model_path, self._config)
            for start, end in ranges
        ]

        with ProcessPoolExecutor(max_workers=workers) as executor:
            chunk_outputs = list(executor.map(_process_chunk_worker, chunk_args))

        # Merge — chunks are already time-ordered so extend in order
        all_results: list[FrameResult] = []
        all_events: list[Event] = []
        for results, events in chunk_outputs:
            all_results.extend(results)
            all_events.extend(events)

        all_events.sort(key=lambda e: e.timestamp)

        return all_results, all_events, duration

    def process_frame(self, frame_bgr, timestamp: float) -> tuple[FrameResult, Event | None]:
        """Process a single frame (live mode)."""
        detector = self._get_detector(running_mode="IMAGE")
        timestamp_ms = int(timestamp * 1000)
        result = self._process_frame_multi(frame_bgr, timestamp, timestamp_ms, detector)
        event = self.event_logger.process(result)
        return result, event

    def _process_frame_multi(
        self,
        frame_bgr,
        timestamp: float,
        timestamp_ms: int,
        detector: DetectionEngine,
    ) -> FrameResult:
        """Process one frame for all detected faces."""
        # L1: Detect all faces
        all_face_data = detector.detect_multi(frame_bgr, timestamp_ms)

        if not all_face_data:
            return FrameResult(
                timestamp=timestamp,
                faces=[],
                risk_level=RiskLevel.LOW,
                disengaged_count=0,
                total_faces=0,
                disengaged_pct=0.0,
            )

        # Track faces across frames
        assignments = self.tracker.update(all_face_data, timestamp)

        # Process each face through L2 + L3
        face_results: list[FaceResult] = []

        for i, face_data in enumerate(all_face_data):
            face_id, cx, cy = assignments[i]
            extractor, classifier = self._get_or_create_face_pipeline(face_id)

            # L2: Feature extraction
            features = extractor.extract(face_data, timestamp)

            # L3: Classification
            state, confidence = classifier.classify(features)

            face_results.append(FaceResult(
                face_id=face_id,
                features=features,
                state=state,
                confidence=confidence,
                face_detected=True,
                face_data=face_data,
                centroid_x=cx,
                centroid_y=cy,
            ))

        # Compute classroom-level metrics
        total = len(face_results)
        disengaged = sum(1 for f in face_results if f.state == EngagementState.DISENGAGED)
        disengaged_pct = (disengaged / total * 100) if total > 0 else 0.0
        risk_level = _compute_risk_level(disengaged_pct, total)

        return FrameResult(
            timestamp=timestamp,
            faces=face_results,
            risk_level=risk_level,
            disengaged_count=disengaged,
            total_faces=total,
            disengaged_pct=round(disengaged_pct, 1),
        )

    def reset(self) -> None:
        """Reset all state between sessions."""
        self._feature_extractors.clear()
        self._classifiers.clear()
        self.tracker.reset()
        self.event_logger.reset()

    def close(self) -> None:
        if self._detector:
            self._detector.close()
