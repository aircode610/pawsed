"""WebSocket endpoint for live webcam engagement streaming.

Flow:
  1. Frontend connects to /ws/live
  2. Server creates a session and waits for frames
  3. Frontend sends frames as base64 JPEG + timestamp
  4. Server runs each frame through the pipeline and sends back state
  5. When a distraction event completes, server sends an event message
  6. When frontend disconnects, server saves the session and sends session_end
"""

import base64
import json

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.engine.pipeline import Pipeline
from app.models.schemas import EngagementState
from app.storage.sessions import create_session, save_session_results

router = APIRouter()


@router.websocket("/ws/live")
async def live_session(websocket: WebSocket):
    await websocket.accept()

    session_id = create_session("live_webcam")
    pipeline = Pipeline()

    all_results = []
    session_start: float | None = None

    try:
        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)

            if message.get("type") != "frame":
                continue

            # Decode base64 JPEG frame
            frame_bytes = base64.b64decode(message["data"])
            np_arr = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame_bgr is None:
                continue

            timestamp: float = message.get("timestamp", 0.0)
            if session_start is None:
                session_start = timestamp

            # Relative timestamp from session start
            rel_ts = timestamp - session_start

            # Run through pipeline
            result, completed_event = pipeline.process_frame(frame_bgr, rel_ts)
            all_results.append(result)

            # Send per-frame state back to frontend
            state_msg = {
                "type": "state",
                "data": {
                    "state": result.state.value,
                    "features": {
                        "ear": round(result.features.ear_avg, 3),
                        "mar": round(result.features.mar, 3),
                        "gaze_score": round(result.features.gaze_score, 3),
                        "head_yaw": round(result.features.head_yaw, 2),
                        "head_pitch": round(result.features.head_pitch, 2),
                        "expression_variance": round(result.features.expression_variance, 4),
                    },
                    "event": None,
                },
            }
            await websocket.send_text(json.dumps(state_msg))

            # If a distraction event just completed, send it separately
            if completed_event:
                event_msg = {
                    "type": "event",
                    "data": {
                        "timestamp": completed_event.timestamp,
                        "event_type": completed_event.event_type,
                        "duration": completed_event.duration,
                        "confidence": completed_event.confidence,
                        "metadata": completed_event.metadata,
                    },
                }
                await websocket.send_text(json.dumps(event_msg))

            # Also check for partial events (ongoing distractions every 2s)
            partial = pipeline.event_logger.partial_event(rel_ts)
            if partial:
                partial_msg = {
                    "type": "event",
                    "data": {
                        "timestamp": partial.timestamp,
                        "event_type": partial.event_type,
                        "duration": partial.duration,
                        "confidence": partial.confidence,
                        "metadata": partial.metadata,
                    },
                }
                await websocket.send_text(json.dumps(partial_msg))

    except WebSocketDisconnect:
        pass
    finally:
        # Close any open distraction and save the session
        duration = (
            all_results[-1].timestamp if all_results else 0.0
        )
        pipeline.event_logger.flush(duration)
        events = pipeline.event_logger.events

        if all_results:
            save_session_results(session_id, all_results, events, duration)

        # Send session_end so frontend knows the session_id to fetch results
        try:
            await websocket.send_text(
                json.dumps({"type": "session_end", "data": {"session_id": session_id}})
            )
        except Exception:
            pass
