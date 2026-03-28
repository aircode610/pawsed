#!/usr/bin/env python3
"""Test the full L1→L2→L3→L4 pipeline on a video file.

Usage:
    # First, download the MediaPipe model (one-time):
    mkdir -p models
    curl -L -o models/face_landmarker.task \
      'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task'

    # Then run on a video:
    PYTHONPATH=. python scripts/test_video.py path/to/video.mp4
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.engine.pipeline import Pipeline


def fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_video.py <video_path> [model_path]")
        print("\nFirst download the model:")
        print("  mkdir -p models")
        print("  curl -L -o models/face_landmarker.task \\")
        print("    'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task'")
        sys.exit(1)

    video_path = sys.argv[1]
    model_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(video_path):
        print(f"Error: Video not found: {video_path}")
        sys.exit(1)

    print(f"Processing: {video_path}")
    print("-" * 60)

    pipeline = Pipeline(model_path=model_path)

    try:
        results, events, duration = pipeline.process_video(video_path)
    finally:
        pipeline.close()

    # --- Summary ---
    total_frames = len(results)
    frames_with_faces = sum(1 for r in results if r.face_detected)
    max_faces = max((r.total_faces for r in results), default=0)
    engaged = sum(1 for r in results if r.state.value == "engaged")
    passive = sum(1 for r in results if r.state.value == "passive")
    disengaged = sum(1 for r in results if r.state.value == "disengaged")

    # Risk summary
    risk_counts = {}
    for r in results:
        risk_counts[r.risk_level.value] = risk_counts.get(r.risk_level.value, 0) + 1

    print(f"\nDuration:         {fmt_time(duration)} ({duration:.1f}s)")
    print(f"Frames sampled:   {total_frames}")
    print(f"Frames with face: {frames_with_faces}/{total_frames} ({frames_with_faces/max(total_frames,1)*100:.0f}%)")
    print(f"Max faces seen:   {max_faces}")
    print(f"\nEngagement (aggregate):")
    print(f"  Engaged:     {engaged:4d} frames ({engaged/max(total_frames,1)*100:.1f}%)")
    print(f"  Passive:     {passive:4d} frames ({passive/max(total_frames,1)*100:.1f}%)")
    print(f"  Disengaged:  {disengaged:4d} frames ({disengaged/max(total_frames,1)*100:.1f}%)")
    print(f"\nClassroom risk levels:")
    for level in ["low", "moderate", "high", "critical"]:
        count = risk_counts.get(level, 0)
        if count > 0:
            print(f"  {level.capitalize():10s} {count:4d} frames ({count/max(total_frames,1)*100:.1f}%)")

    # --- Multi-face samples ---
    print(f"\n{'='*70}")
    print("Sample frames (every ~10s):")
    print(f"{'='*70}")
    sample_interval = max(1, int(10 * len(results) / max(duration, 1)))
    for i in range(0, len(results), sample_interval):
        r = results[i]
        print(f"\n  {fmt_time(r.timestamp)} | {r.total_faces} faces | risk: {r.risk_level.value} | {r.disengaged_count} disengaged ({r.disengaged_pct:.0f}%)")
        for face in r.faces:
            f = face.features
            print(
                f"    Face {face.face_id:2d}: {face.state.value:>12} "
                f"EAR={f.ear_avg:.2f} MAR={f.mar:.2f} Gaze={f.gaze_score:.2f} "
                f"Yaw={f.head_yaw:.0f} Pitch={f.head_pitch:.0f}"
            )
        if not r.faces:
            print("    (no faces detected)")

    # --- Events ---
    if events:
        print(f"\n{'='*60}")
        print(f"Distraction events ({len(events)} total):")
        print(f"{'='*60}")
        print(f"{'Time':>6} {'Type':<15} {'Duration':>8} {'Confidence':>10} {'Metadata'}")
        print("-" * 65)
        for e in events:
            meta = ""
            if e.metadata:
                meta = str(e.metadata)
            print(
                f"{fmt_time(e.timestamp):>6} "
                f"{e.event_type:<15} "
                f"{e.duration:7.1f}s "
                f"{e.confidence:10.0%} "
                f"{meta}"
            )
    else:
        print("\nNo distraction events detected.")

    print(f"\nDone.")


if __name__ == "__main__":
    main()
