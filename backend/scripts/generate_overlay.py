#!/usr/bin/env python3
"""Generate a landmarks overlay video for an existing session.

Usage: PYTHONPATH=. python scripts/generate_overlay.py <session_id>
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from app.engine.overlay import render_annotated_video
from app.engine.pipeline import Pipeline
from app.core.config import settings

session_id = sys.argv[1] if len(sys.argv) > 1 else None
if not session_id:
    print("Usage: python scripts/generate_overlay.py <session_id>")
    sys.exit(1)

videos_dir = Path(settings.sessions_dir) / "videos"
input_path = None
for ext in (".mp4", ".webm", ".mov"):
    p = videos_dir / f"{session_id}{ext}"
    if p.exists():
        input_path = p
        break

if not input_path:
    print(f"No video found for session {session_id} in {videos_dir}")
    sys.exit(1)

output_path = videos_dir / f"{session_id}_landmarks.mp4"
print(f"Input:  {input_path}")
print(f"Output: {output_path}")
print("Generating overlay video...")

pipeline = Pipeline()
try:
    render_annotated_video(str(input_path), str(output_path), pipeline)
finally:
    pipeline.close()

print(f"Done. Output: {output_path}")
