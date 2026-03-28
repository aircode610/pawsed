"""Face tracker — assigns stable IDs to faces across frames.

Uses spatial proximity (centroid distance) to match faces between
consecutive frames. Handles faces appearing, disappearing, and swapping.
"""

from dataclasses import dataclass, field

from app.models.schemas import FaceData, Landmark


@dataclass
class TrackedFace:
    face_id: int
    centroid_x: float
    centroid_y: float
    last_seen_timestamp: float = 0.0
    frames_missing: int = 0


def _face_centroid(face_data: FaceData) -> tuple[float, float]:
    """Compute the centroid of a face from its nose tip landmark (index 1)."""
    if len(face_data.landmarks) > 1:
        nose = face_data.landmarks[1]
        return nose.x, nose.y
    # Fallback: average all landmarks
    xs = [lm.x for lm in face_data.landmarks]
    ys = [lm.y for lm in face_data.landmarks]
    return sum(xs) / len(xs), sum(ys) / len(ys)


class FaceTracker:
    """Matches detected faces to tracked IDs using spatial proximity.

    Args:
        max_distance: Maximum centroid distance (normalized coords) to match a face.
            Faces beyond this distance are considered new.
        max_missing_frames: How many consecutive frames a face can be absent
            before its ID is retired.
    """

    def __init__(self, max_distance: float = 0.15, max_missing_frames: int = 15):
        self._max_distance = max_distance
        self._max_missing = max_missing_frames
        self._tracked: list[TrackedFace] = []
        self._next_id = 0

    def update(self, faces: list[FaceData], timestamp: float = 0.0) -> list[tuple[int, float, float]]:
        """Match detected faces to tracked IDs.

        Args:
            faces: List of FaceData detected in the current frame.
            timestamp: Current frame timestamp.

        Returns:
            List of (face_id, centroid_x, centroid_y) in same order as input faces.
        """
        # Compute centroids for detected faces
        centroids = [_face_centroid(f) for f in faces]

        # Match each detected face to the nearest tracked face
        used_tracked = set()
        assignments: list[tuple[int, float, float]] = [(-1, 0.0, 0.0)] * len(faces)

        # Compute all pairwise distances
        pairs = []
        for di, (dx, dy) in enumerate(centroids):
            for ti, tracked in enumerate(self._tracked):
                dist = ((dx - tracked.centroid_x) ** 2 + (dy - tracked.centroid_y) ** 2) ** 0.5
                pairs.append((dist, di, ti))

        # Greedy nearest-neighbor matching
        pairs.sort(key=lambda p: p[0])
        used_detected = set()

        for dist, di, ti in pairs:
            if di in used_detected or ti in used_tracked:
                continue
            if dist > self._max_distance:
                break
            # Match
            tracked = self._tracked[ti]
            tracked.centroid_x, tracked.centroid_y = centroids[di]
            tracked.last_seen_timestamp = timestamp
            tracked.frames_missing = 0
            assignments[di] = (tracked.face_id, centroids[di][0], centroids[di][1])
            used_detected.add(di)
            used_tracked.add(ti)

        # Assign new IDs to unmatched detections
        for di in range(len(faces)):
            if di not in used_detected:
                cx, cy = centroids[di]
                new_id = self._next_id
                self._next_id += 1
                self._tracked.append(TrackedFace(
                    face_id=new_id,
                    centroid_x=cx,
                    centroid_y=cy,
                    last_seen_timestamp=timestamp,
                ))
                assignments[di] = (new_id, cx, cy)

        # Age out unmatched tracked faces
        for ti in range(len(self._tracked) - 1, -1, -1):
            if ti not in used_tracked and self._tracked[ti].last_seen_timestamp < timestamp:
                self._tracked[ti].frames_missing += 1
                if self._tracked[ti].frames_missing > self._max_missing:
                    self._tracked.pop(ti)

        return assignments

    @property
    def active_face_count(self) -> int:
        return len(self._tracked)

    def reset(self):
        self._tracked.clear()
        self._next_id = 0
