#!/usr/bin/env python3
"""Debug script — dumps raw landmark positions and feature values for a few frames.

Usage: PYTHONPATH=. python scripts/debug_features.py /path/to/video.mp4
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from app.engine.detection import DetectionEngine
from app.engine.features import (
    compute_ear, compute_ear_both, compute_mar, compute_gaze,
    RIGHT_EYE, LEFT_EYE, MOUTH_TOP, MOUTH_BOTTOM, MOUTH_LEFT, MOUTH_RIGHT,
    MOUTH_UPPER_MID, MOUTH_LOWER_MID, _landmark_dist,
)

video_path = sys.argv[1]
detector = DetectionEngine(running_mode="VIDEO")
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

frame_idx = 0
sample_every = max(1, int(fps / 2))  # ~2 fps for debugging
samples = 0

while samples < 10:
    ret, frame = cap.read()
    if not ret:
        break
    if frame_idx % sample_every != 0:
        frame_idx += 1
        continue

    ts_ms = int(frame_idx / fps * 1000)
    face = detector.detect(frame, ts_ms)
    frame_idx += 1

    if face is None:
        print(f"Frame {frame_idx}: no face")
        samples += 1
        continue

    lm = face.landmarks
    samples += 1

    # --- EAR ---
    print(f"\n{'='*60}")
    print(f"Frame {frame_idx} (t={ts_ms}ms)")
    print(f"{'='*60}")

    # Right eye landmarks
    re = RIGHT_EYE
    print(f"\nRight eye landmarks ({re}):")
    for i, idx in enumerate(re):
        print(f"  p{i+1} [idx={idx}]: x={lm[idx].x:.4f} y={lm[idx].y:.4f} z={lm[idx].z:.4f}")
    ear_r = compute_ear(lm, RIGHT_EYE)
    ear_l = compute_ear(lm, LEFT_EYE)
    print(f"  EAR right={ear_r:.4f}  EAR left={ear_l:.4f}  avg={((ear_r+ear_l)/2):.4f}")

    # --- MAR ---
    print(f"\nMouth landmarks:")
    for name, indices in [("top", MOUTH_TOP), ("bottom", MOUTH_BOTTOM),
                          ("left", MOUTH_LEFT), ("right", MOUTH_RIGHT),
                          ("upper_mid", MOUTH_UPPER_MID), ("lower_mid", MOUTH_LOWER_MID)]:
        for idx in indices:
            print(f"  {name} [idx={idx}]: x={lm[idx].x:.4f} y={lm[idx].y:.4f} z={lm[idx].z:.4f}")

    # Manual MAR calc with distances
    top = lm[MOUTH_TOP[0]]
    bottom = lm[MOUTH_BOTTOM[0]]
    left = lm[MOUTH_LEFT[0]]
    right = lm[MOUTH_RIGHT[0]]
    u1 = lm[MOUTH_UPPER_MID[0]]
    u2 = lm[MOUTH_UPPER_MID[1]]
    l1 = lm[MOUTH_LOWER_MID[0]]
    l2 = lm[MOUTH_LOWER_MID[1]]

    v1 = _landmark_dist(top, bottom)
    v2 = _landmark_dist(u1, l1)
    v3 = _landmark_dist(u2, l2)
    h = _landmark_dist(left, right)
    mar = (v1 + v2 + v3) / (2.0 * h) if h > 0 else 0

    print(f"  vertical1 (top-bottom) = {v1:.4f}")
    print(f"  vertical2 (u1-l1) = {v2:.4f}")
    print(f"  vertical3 (u2-l2) = {v3:.4f}")
    print(f"  horizontal (left-right) = {h:.4f}")
    print(f"  MAR = ({v1:.4f} + {v2:.4f} + {v3:.4f}) / (2 * {h:.4f}) = {mar:.4f}")

    # --- Gaze ---
    bs = face.blendshapes
    print(f"\nGaze blendshapes:")
    print(f"  lookDown L={bs.eye_look_down_left:.3f} R={bs.eye_look_down_right:.3f}")
    print(f"  lookUp   L={bs.eye_look_up_left:.3f} R={bs.eye_look_up_right:.3f}")
    print(f"  lookIn   L={bs.eye_look_in_left:.3f} R={bs.eye_look_in_right:.3f}")
    print(f"  lookOut  L={bs.eye_look_out_left:.3f} R={bs.eye_look_out_right:.3f}")
    print(f"  blink    L={bs.eye_blink_left:.3f} R={bs.eye_blink_right:.3f}")
    print(f"  jawOpen={bs.jaw_open:.3f}")

    gaze_score, gaze_h, gaze_v = compute_gaze(bs)
    print(f"  gaze_score={gaze_score:.3f} h={gaze_h:.3f} v={gaze_v:.3f}")

cap.release()
detector.close()
