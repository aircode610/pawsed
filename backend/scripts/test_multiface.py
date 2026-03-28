#!/usr/bin/env python3
"""Test multi-face detection by creating a frame with duplicated faces.

Creates a wider canvas with the original face + a mirrored copy to verify
the pipeline detects, tracks, and classifies multiple faces independently.

Usage: PYTHONPATH=. python scripts/test_multiface.py /path/to/video.mp4
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from app.engine.detection import DetectionEngine
from app.engine.features import FeatureExtractor
from app.engine.classifier import EngagementClassifier
from app.engine.tracker import FaceTracker
from app.engine.overlay import draw_landmarks_on_frame
from app.models.schemas import EngagementState


def main():
    video_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not video_path:
        print("Usage: python scripts/test_multiface.py <video_path>")
        sys.exit(1)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # Skip to a frame with a visible face (~3s in)
    target_frame = int(3 * fps)
    for _ in range(target_frame):
        cap.read()
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Could not read frame")
        sys.exit(1)

    h, w = frame.shape[:2]
    print(f"Original frame: {w}x{h}")

    # Create a synthetic 2-person frame: original + mirror side by side
    canvas = np.zeros((h, w * 2, 3), dtype=np.uint8)
    canvas[:, :w] = frame
    canvas[:, w:] = cv2.flip(frame, 1)
    print(f"Multi-face canvas: {canvas.shape[1]}x{canvas.shape[0]}")

    # --- Detection ---
    print(f"\n--- Detection (num_faces=5) ---")
    det = DetectionEngine(running_mode="IMAGE", num_faces=5)
    faces = det.detect_multi(canvas, 0)
    print(f"Faces detected: {len(faces)}")
    for i, face in enumerate(faces):
        nose = face.landmarks[1]
        print(f"  Face {i}: nose=({nose.x:.3f}, {nose.y:.3f}) jawOpen={face.blendshapes.jaw_open:.3f}")

    # --- Tracking ---
    print(f"\n--- Tracking ---")
    tracker = FaceTracker()
    assignments = tracker.update(faces, timestamp=0.0)
    for i, (fid, cx, cy) in enumerate(assignments):
        print(f"  Detection {i} -> Face ID {fid} at ({cx:.3f}, {cy:.3f})")

    # --- Per-face classification ---
    print(f"\n--- Per-face engagement ---")
    face_results = []
    for i, face in enumerate(faces):
        fid = assignments[i][0]
        fe = FeatureExtractor()
        clf = EngagementClassifier()
        features = fe.extract(face, 0.0)
        state, conf = clf.classify(features)
        face_results.append((face, state, conf, features, fid))
        print(
            f"  Face {fid}: {state.value} ({conf:.0%}) "
            f"EAR={features.ear_avg:.2f} MAR={features.mar:.2f} "
            f"Gaze={features.gaze_score:.2f} Yaw={features.head_yaw:.0f} Pitch={features.head_pitch:.0f}"
        )

    # --- Classroom risk ---
    total = len(face_results)
    disengaged = sum(1 for _, s, *_ in face_results if s == EngagementState.DISENGAGED)
    pct = (disengaged / total * 100) if total > 0 else 0
    print(f"\n--- Classroom ---")
    print(f"  Total faces: {total}")
    print(f"  Disengaged: {disengaged} ({pct:.0f}%)")
    print(f"  Risk: {'CRITICAL' if pct >= 60 else 'HIGH' if pct >= 40 else 'MODERATE' if pct >= 20 else 'LOW'}")

    # --- Draw overlay and save ---
    annotated = canvas.copy()
    for face, state, conf, features, fid in face_results:
        feat_text = [
            f"Face {fid} | EAR:{features.ear_avg:.2f} MAR:{features.mar:.2f}",
            f"Gaze:{features.gaze_score:.2f} Yaw:{features.head_yaw:.0f} [{conf:.0%}]",
        ]
        draw_landmarks_on_frame(annotated, face, state, feat_text)

    out_dir = os.path.dirname(video_path)
    out_path = os.path.join(out_dir, "multiface_overlay.jpg")
    cv2.imwrite(out_path, annotated)
    print(f"\nSaved overlay to: {out_path}")

    det.close()
    print("Done.")


if __name__ == "__main__":
    main()
