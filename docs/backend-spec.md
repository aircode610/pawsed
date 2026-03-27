# Backend Specification

## Overview
Python + FastAPI backend. Processes video frames through a 6-layer pipeline, stores session data, serves results via REST + WebSocket.

## Layer 1: Detection Engine (`app/engine/detection.py`)

**Input:** Video frame (numpy array)
**Output:** MediaPipe FaceLandmarkerResult — 478 landmarks, 52 blendshapes, transformation matrix

```python
# Key setup
from mediapipe.tasks.vision import FaceLandmarker, FaceLandmarkerOptions

options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path="models/face_landmarker.task"),
    output_face_blendshapes=True,
    output_facial_transformation_matrixes=True,
    num_faces=1
)
```

**Notes:**
- Download `face_landmarker.task` from MediaPipe's model hub
- Process frames at ~10 FPS (skip frames from 30fps video for performance)
- Handle "no face detected" gracefully — log as `face_lost` event

## Layer 2: Feature Extractor (`app/engine/features.py`)

**Input:** FaceLandmarkerResult
**Output:** FeatureVector dataclass

### EAR (Eye Aspect Ratio)
```
EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
```
- Right eye landmarks: 33, 160, 158, 133, 153, 144
- Left eye landmarks: 362, 385, 387, 263, 373, 380
- EAR < 0.2 for >0.5s = eyes closed
- Track blink rate (EAR dips per minute)

### MAR (Mouth Aspect Ratio)
```
MAR = (||p2-p8|| + ||p3-p7|| + ||p4-p6||) / (2 * ||p1-p5||)
```
- Upper lip: 13, 14 | Lower lip: 17, 18 | Corners: 78, 308
- MAR > 0.6 for >2s = yawn

### Gaze Direction
Use blendshapes:
- `eyeLookDown_L`, `eyeLookDown_R`
- `eyeLookUp_L`, `eyeLookUp_R`
- `eyeLookIn_L`, `eyeLookIn_R`
- `eyeLookOut_L`, `eyeLookOut_R`

Compute gaze score: high `lookDown` + `lookOut` = looking away from screen.

### Head Pose
Extract pitch, yaw, roll from the facial transformation matrix.
- Yaw > 30° = looking left/right
- Pitch > 20° = looking up/down
- Sustained off-center (>5s) = distraction event

### Expression Variance
- Compute std deviation of all 52 blendshape scores over a sliding window (30 frames)
- Low variance (<0.02) = "frozen face" = zoned out

## Layer 3: Engagement Classifier (`app/engine/classifier.py`)

**Input:** FeatureVector
**Output:** EngagementState enum — `engaged`, `passive`, `disengaged`

### Rules (all thresholds should be configurable):

**Engaged:**
- EAR > 0.2 (eyes open)
- Gaze score indicates on-screen
- Head yaw < 15°, pitch < 10°
- Expression variance > 0.02

**Passive:**
- EAR > 0.2 (eyes open)
- Gaze drifting OR low expression variance
- Head slightly off-center (15° < yaw < 30°)

**Disengaged:**
- EAR < 0.2 for >0.5s (eyes closed) OR
- MAR > 0.6 for >2s (yawning) OR
- Gaze away for >5s OR
- Head yaw > 30° sustained

## Layer 4: Timeline Event Logger (`app/analytics/events.py`)

**Input:** Stream of (timestamp, EngagementState, FeatureVector)
**Output:** List of Event objects

```python
@dataclass
class Event:
    timestamp: float        # seconds from start
    event_type: str         # "yawn", "eyes_closed", "looked_away", "zoned_out", "face_lost"
    duration: float         # seconds
    confidence: float       # 0-1
    metadata: dict          # direction, angle, etc.
```

**State machine:** Track when distraction starts/ends. Only emit event when distraction ends (so we have duration). For ongoing distractions during live mode, emit partial events every 2s.

## Layer 5: Session Analytics (`app/analytics/session.py`)

**Input:** List of Events + total session duration
**Output:** SessionAnalytics

```python
@dataclass
class SessionAnalytics:
    total_duration: float
    focus_time_pct: float
    distraction_time_pct: float
    longest_focus_streak: float      # seconds
    distraction_breakdown: dict      # {type: count}
    engagement_curve: list[float]    # per-minute engagement scores
    danger_zones: list[tuple]        # (start, end) time ranges
```

## Layer 6: LLM Recommendations (`app/analytics/recommendations.py`)

**Input:** SessionAnalytics + Events summary
**Output:** List of recommendation strings

Use Claude API (`claude-sonnet-4-6`) with a prompt that includes:
- Session duration and focus percentage
- Top distraction types and when they occurred
- Danger zone time ranges
- Ask for 3-5 actionable, specific, friendly study tips

## Dependencies (`requirements.txt`)
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
mediapipe>=0.10.8
opencv-python>=4.8.0
numpy>=1.24.0
pydantic>=2.0
pydantic-settings>=2.0
anthropic>=0.39.0
python-multipart>=0.0.6
websockets>=12.0
aiofiles>=23.0
```
