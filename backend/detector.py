import cv2
import numpy as np
import json
import math
from collections import deque
from scipy.spatial import distance
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision


# ─────────────────────────────────────────────────────────
# THRESHOLDS
# ─────────────────────────────────────────────────────────

EAR_THRESHOLD        = 0.20    # below - eye considered closed
EYE_CLOSE_MIN_SEC    = 1.5     # sustained closure - log "eyes_closed"

MAR_THRESHOLD        = 0.55    # above - mouth open (yawn candidate)
YAWN_MIN_FRAMES      = 10      # consecutive frames needed to call it a yawn

GAZE_DOWN_THRESHOLD  = 0.35    # eyeLookDown blendshape score
GAZE_AWAY_THRESHOLD  = 0.30    # eyeLookOut / eyeLookIn blendshape score
LOOK_AWAY_MIN_SEC    = 5.0     # must persist this long to log "looked_away"

PITCH_DOWN_THRESH    = 20      # degrees — head bowing down
YAW_AWAY_THRESH      = 25      # degrees — head turned left/right
HEAD_POSE_MIN_SEC    = 3.0

EXPR_WINDOW_SEC      = 10      # sliding window for expression variance
EXPR_VAR_THRESHOLD   = 0.003   # below - "frozen face" - passive/disengaged

INACTIVITY_SEC       = 30      # seconds without nose movement - inactivity
MOVEMENT_PX          = 8       # pixel threshold for "moved"

NO_FACE_MIN_SEC      = 5.0     # seconds without face - log "no_face"

MODEL_PATH           = "face_landmarker.task"


# ─────────────────────────────────────────────────────────
# MEDIAPIPE LANDMARK INDICES  (478-point FaceMesh)
# ─────────────────────────────────────────────────────────

# Left eye (viewer's left = person's right)
LEFT_EYE_TOP    = [159, 160, 161]
LEFT_EYE_BOT    = [145, 144, 163]
LEFT_EYE_L      = 33
LEFT_EYE_R      = 133

# Right eye
RIGHT_EYE_TOP   = [386, 387, 388]
RIGHT_EYE_BOT   = [374, 373, 380]
RIGHT_EYE_L     = 362
RIGHT_EYE_R     = 263

# Mouth (outer lip)
MOUTH_LEFT      = 61
MOUTH_RIGHT     = 291
MOUTH_TOP       = [82, 312]
MOUTH_BOT       = [87, 317]

NOSE_TIP        = 4


# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────

def seconds_to_timestamp(sec: float) -> str:
    h  = int(sec // 3600)
    m  = int((sec % 3600) // 60)
    s  = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def lm_xy(lm, w: int, h: int) -> np.ndarray:
    return np.array([lm.x * w, lm.y * h])


def ear(lms, top_idxs, bot_idxs, l_idx, r_idx, w, h) -> float:
    """Eye Aspect Ratio = vertical / horizontal diameter of the eye."""
    top   = np.mean([lm_xy(lms[i], w, h) for i in top_idxs], axis=0)
    bot   = np.mean([lm_xy(lms[i], w, h) for i in bot_idxs], axis=0)
    left  = lm_xy(lms[l_idx], w, h)
    right = lm_xy(lms[r_idx], w, h)
    horiz = distance.euclidean(left, right)
    return distance.euclidean(top, bot) / horiz if horiz > 0 else 0.0


def mar(lms, w: int, h: int) -> float:
    """Mouth Aspect Ratio = vertical / horizontal opening."""
    top   = np.mean([lm_xy(lms[i], w, h) for i in MOUTH_TOP], axis=0)
    bot   = np.mean([lm_xy(lms[i], w, h) for i in MOUTH_BOT], axis=0)
    left  = lm_xy(lms[MOUTH_LEFT], w, h)
    right = lm_xy(lms[MOUTH_RIGHT], w, h)
    horiz = distance.euclidean(left, right)
    return distance.euclidean(top, bot) / horiz if horiz > 0 else 0.0


def head_pose(transform_matrix) -> tuple[float, float, float]:
    """
    Extract pitch, yaw, roll (degrees) from MediaPipe 4×4 transform matrix.
    pitch > 0 - head down, yaw > 0 - head right.
    """
    if transform_matrix is None:
        return 0.0, 0.0, 0.0
    m = np.array(transform_matrix.data).reshape(4, 4)
    R = m[:3, :3]
    sy = math.sqrt(R[0, 0] ** 2 + R[1, 0] ** 2)
    if sy > 1e-6:
        pitch = math.degrees(math.atan2(-R[2, 0], sy))
        yaw   = math.degrees(math.atan2(R[1, 0], R[0, 0]))
        roll  = math.degrees(math.atan2(R[2, 1], R[2, 2]))
    else:
        pitch = math.degrees(math.atan2(-R[2, 0], sy))
        yaw   = 0.0
        roll  = math.degrees(math.atan2(-R[1, 2], R[1, 1]))
    return pitch, yaw, roll


def blendshape_score(blendshapes, name: str) -> float:
    if not blendshapes:
        return 0.0
    for bs in blendshapes[0]:
        if bs.category_name == name:
            return bs.score
    return 0.0


def gaze_scores(blendshapes) -> tuple[float, float, float]:
    """Returns (gaze_down, gaze_left, gaze_right) as 0-1 scores."""
    down  = max(blendshape_score(blendshapes, "eyeLookDownLeft"),
                blendshape_score(blendshapes, "eyeLookDownRight"))
    left  = max(blendshape_score(blendshapes, "eyeLookOutLeft"),
                blendshape_score(blendshapes, "eyeLookInRight"))
    right = max(blendshape_score(blendshapes, "eyeLookOutRight"),
                blendshape_score(blendshapes, "eyeLookInLeft"))
    return down, left, right


def expression_variance(blendshape_window: deque) -> float:
    """Std dev of blendshape scores across window — low = frozen face."""
    if len(blendshape_window) < 2:
        return 1.0
    arr = np.array(blendshape_window)
    return float(np.mean(np.std(arr, axis=0)))


# ─────────────────────────────────────────────────────────
# LAYER 3 — ENGAGEMENT CLASSIFIER
# ─────────────────────────────────────────────────────────

def classify_engagement(ear_val, mar_val, gaze_down, gaze_left, gaze_right,
                         pitch, yaw, expr_var) -> tuple[str, float]:
    """
    Rule-based. Returns (level, confidence 0-1).
    Engaged / Passive / Disengaged
    """
    score = 100.0

    if ear_val < EAR_THRESHOLD:
        score -= 35
    if mar_val > MAR_THRESHOLD:
        score -= 20
    if gaze_down > GAZE_DOWN_THRESHOLD:
        score -= 25
    if gaze_left > GAZE_AWAY_THRESHOLD or gaze_right > GAZE_AWAY_THRESHOLD:
        score -= 25
    if abs(pitch) > PITCH_DOWN_THRESH:
        score -= 15
    if abs(yaw) > YAW_AWAY_THRESH:
        score -= 15
    if expr_var < EXPR_VAR_THRESHOLD:
        score -= 10

    score = max(0.0, score)

    if score >= 65:
        level = "engaged"
    elif score >= 35:
        level = "passive"
    else:
        level = "disengaged"

    return level, round(score / 100, 2)


# ─────────────────────────────────────────────────────────
# LAYER 4 — EVENT STATE MACHINE
# ─────────────────────────────────────────────────────────

class EventTracker:
    """
    Tracks open events and closes them when conditions change.
    Appends completed events to self.events.
    """
    def __init__(self):
        self.events: list[dict] = []

        # yawn
        self._yawn_counter    = 0
        self._yawn_start_t    = None
        self._yawn_start_f    = None

        # eyes closed
        self._eye_close_start_t = None
        self._eye_close_start_f = None

        # looked away
        self._away_start_t    = None
        self._away_start_f    = None
        self._away_direction  = None

        # head pose
        self._head_off_start_t = None
        self._head_off_start_f = None

        # inactivity (nose movement)
        self._nose_history: list[tuple] = []  # (pos, time, frame)
        self._inact_start_t  = None
        self._inact_start_f  = None

        # no face
        self._no_face_start_t = None
        self._no_face_start_f = None

        # blendshape window for expression variance
        self._expr_window: deque = deque()
        self._expr_window_times: deque = deque()

    # ── internal helpers ──────────────────────────────

    def _log(self, event_type: str, t_start: float, t_end: float,
             f_start: int, f_end: int, confidence: float = 1.0, **extra):
        entry = {
            "event":           event_type,
            "timestamp_start": seconds_to_timestamp(t_start),
            "timestamp_end":   seconds_to_timestamp(t_end),
            "frame_start":     f_start,
            "frame_end":       f_end,
            "duration_sec":    round(t_end - t_start, 3),
            "confidence":      round(confidence, 2),
        }
        entry.update(extra)
        self.events.append(entry)

    # ── public update methods ─────────────────────────

    def update_yawn(self, mar_val: float, t: float, f: int):
        if mar_val > MAR_THRESHOLD:
            if self._yawn_counter == 0:
                self._yawn_start_t = t
                self._yawn_start_f = f
            self._yawn_counter += 1
        else:
            if self._yawn_counter >= YAWN_MIN_FRAMES:
                conf = min(1.0, (self._yawn_counter - YAWN_MIN_FRAMES) / 20 + 0.6)
                self._log("yawn", self._yawn_start_t, t,
                          self._yawn_start_f, f,
                          confidence=conf,
                          mar_peak=round(mar_val, 3))
            self._yawn_counter = 0
            self._yawn_start_t = None

    def update_eye_closure(self, ear_val: float, t: float, f: int):
        if ear_val < EAR_THRESHOLD:
            if self._eye_close_start_t is None:
                self._eye_close_start_t = t
                self._eye_close_start_f = f
        else:
            if self._eye_close_start_t is not None:
                duration = t - self._eye_close_start_t
                if duration >= EYE_CLOSE_MIN_SEC:
                    self._log("eyes_closed",
                              self._eye_close_start_t, t,
                              self._eye_close_start_f, f,
                              confidence=min(1.0, duration / 5.0))
            self._eye_close_start_t = None
            self._eye_close_start_f = None

    def update_gaze(self, gaze_down: float, gaze_left: float,
                    gaze_right: float, t: float, f: int):
        looking_away = (
            gaze_down  > GAZE_DOWN_THRESHOLD or
            gaze_left  > GAZE_AWAY_THRESHOLD or
            gaze_right > GAZE_AWAY_THRESHOLD
        )
        if looking_away:
            if gaze_down > GAZE_DOWN_THRESHOLD:
                direction = "down"
            elif gaze_left > gaze_right:
                direction = "left"
            else:
                direction = "right"

            if self._away_start_t is None:
                self._away_start_t   = t
                self._away_start_f   = f
                self._away_direction = direction
        else:
            if self._away_start_t is not None:
                duration = t - self._away_start_t
                if duration >= LOOK_AWAY_MIN_SEC:
                    self._log("looked_away",
                              self._away_start_t, t,
                              self._away_start_f, f,
                              confidence=min(1.0, duration / 10.0),
                              direction=self._away_direction)
            self._away_start_t = None

    def update_head_pose(self, pitch: float, yaw: float, t: float, f: int):
        head_off = abs(pitch) > PITCH_DOWN_THRESH or abs(yaw) > YAW_AWAY_THRESH
        if head_off:
            if self._head_off_start_t is None:
                self._head_off_start_t = t
                self._head_off_start_f = f
        else:
            if self._head_off_start_t is not None:
                duration = t - self._head_off_start_t
                if duration >= HEAD_POSE_MIN_SEC:
                    self._log("head_pose_off",
                              self._head_off_start_t, t,
                              self._head_off_start_f, f,
                              confidence=min(1.0, duration / 8.0),
                              pitch=round(pitch, 1),
                              yaw=round(yaw, 1))
            self._head_off_start_t = None

    def update_inactivity(self, nose_pos: tuple, t: float, f: int):
        self._nose_history.append((nose_pos, t, f))
        # keep only last INACTIVITY_SEC window
        cutoff = t - INACTIVITY_SEC
        self._nose_history = [(p, ts, fr) for p, ts, fr in self._nose_history
                              if ts >= cutoff]
        if len(self._nose_history) < 2:
            return

        positions = [p for p, _, _ in self._nose_history]
        max_shift = max(
            distance.euclidean(positions[i], positions[j])
            for i in range(len(positions))
            for j in range(i + 1, len(positions))
        )
        if max_shift < MOVEMENT_PX:
            if self._inact_start_t is None:
                self._inact_start_t = self._nose_history[0][1]
                self._inact_start_f = self._nose_history[0][2]
        else:
            if self._inact_start_t is not None:
                duration = t - self._inact_start_t
                if duration >= INACTIVITY_SEC:
                    self._log("inactivity",
                              self._inact_start_t, t,
                              self._inact_start_f, f,
                              confidence=1.0)
            self._inact_start_t = None

    def update_blendshapes(self, scores: list[float], t: float):
        """Feed raw blendshape score vector; prune window by time."""
        self._expr_window.append(scores)
        self._expr_window_times.append(t)
        cutoff = t - EXPR_WINDOW_SEC
        while self._expr_window_times and self._expr_window_times[0] < cutoff:
            self._expr_window.popleft()
            self._expr_window_times.popleft()

    def get_expr_var(self) -> float:
        return expression_variance(self._expr_window)

    def face_detected(self, t: float, f: int):
        """Call this when a face IS detected — closes any open no_face event."""
        if self._no_face_start_t is not None:
            duration = t - self._no_face_start_t
            if duration >= NO_FACE_MIN_SEC:
                self._log("no_face",
                          self._no_face_start_t, t,
                          self._no_face_start_f, f,
                          confidence=1.0)
            self._no_face_start_t = None

    def no_face_detected(self, t: float, f: int):
        """Call this when NO face is detected."""
        if self._no_face_start_t is None:
            self._no_face_start_t = t
            self._no_face_start_f = f

    def flush(self, t: float, f: int):
        """Call at end of video to close any still-open events."""
        if self._yawn_counter >= YAWN_MIN_FRAMES and self._yawn_start_t:
            self._log("yawn", self._yawn_start_t, t, self._yawn_start_f, f)

        if self._eye_close_start_t and (t - self._eye_close_start_t) >= EYE_CLOSE_MIN_SEC:
            self._log("eyes_closed", self._eye_close_start_t, t,
                      self._eye_close_start_f, f, confidence=1.0)

        if self._away_start_t and (t - self._away_start_t) >= LOOK_AWAY_MIN_SEC:
            self._log("looked_away", self._away_start_t, t,
                      self._away_start_f, f,
                      confidence=1.0,
                      direction=self._away_direction)

        if self._head_off_start_t and (t - self._head_off_start_t) >= HEAD_POSE_MIN_SEC:
            self._log("head_pose_off", self._head_off_start_t, t,
                      self._head_off_start_f, f, confidence=1.0)

        if self._inact_start_t and (t - self._inact_start_t) >= INACTIVITY_SEC:
            self._log("inactivity", self._inact_start_t, t,
                      self._inact_start_f, f, confidence=1.0)

        if self._no_face_start_t and (t - self._no_face_start_t) >= NO_FACE_MIN_SEC:
            self._log("no_face", self._no_face_start_t, t,
                      self._no_face_start_f, f, confidence=1.0)


# ─────────────────────────────────────────────────────────
# LAYER 1 — MEDIAPIPE SETUP
# ─────────────────────────────────────────────────────────

def build_landmarker() -> mp_vision.FaceLandmarker:
    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = mp_vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=True,
        output_facial_transformation_matrixes=True,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return mp_vision.FaceLandmarker.create_from_options(options)


# ─────────────────────────────────────────────────────────
# MAIN PROCESSING LOOP
# ─────────────────────────────────────────────────────────

def run(video_path: str, output_path: str = "events.json"):
    """
    Process a video file (or webcam index) and write events to JSON.

    Output format per event:
    {
        "event":           "yawn" | "eyes_closed" | "looked_away" |
                           "head_pose_off" | "inactivity" | "no_face",
        "timestamp_start": "00:04:32.000",
        "timestamp_end":   "00:04:35.200",
        "frame_start":     6480,
        "frame_end":       6576,
        "duration_sec":    3.2,
        "confidence":      0.87,
        ... (event-specific extra fields)
    }
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: cannot open {video_path}")
        return

    fps          = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_id     = 0

    print(f"Video : {video_path}")
    print(f"FPS   : {fps:.1f}  |  total frames: {total_frames}")

    landmarker = build_landmarker()
    tracker    = EventTracker()

    # per-frame engagement state (saved for later analytics layers)
    frame_states: list[dict] = []

    while True:
        ret, bgr = cap.read()
        if not ret:
            break

        t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        h, w = bgr.shape[:2]

        # MediaPipe expects RGB
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # ── Layer 1: run FaceLandmarker ──────────────────
        result = landmarker.detect(mp_image)
        lms    = result.face_landmarks
        bshps  = result.face_blendshapes
        mats   = result.facial_transformation_matrixes

        if not lms:
            # no face in this frame
            tracker.no_face_detected(t, frame_id)
            frame_states.append({
                "frame": frame_id,
                "t": round(t, 3),
                "engagement": "no_face",
                "score": 0.0
            })
            frame_id += 1
            continue

        tracker.face_detected(t, frame_id)
        lm_list = lms[0]  # first (and only) face

        # ── Layer 2: feature extraction ──────────────────

        # EAR — average of both eyes
        ear_l = ear(lm_list, LEFT_EYE_TOP,  LEFT_EYE_BOT,  LEFT_EYE_L,  LEFT_EYE_R,  w, h)
        ear_r = ear(lm_list, RIGHT_EYE_TOP, RIGHT_EYE_BOT, RIGHT_EYE_L, RIGHT_EYE_R, w, h)
        ear_val = (ear_l + ear_r) / 2.0

        # MAR
        mar_val = mar(lm_list, w, h)

        # Gaze from blendshapes
        gaze_down, gaze_left, gaze_right = gaze_scores(bshps)

        # Head pose from transform matrix
        matrix = mats[0] if mats else None
        pitch, yaw, roll = head_pose(matrix)

        # Expression variance
        if bshps:
            scores_vec = [bs.score for bs in bshps[0]]
            tracker.update_blendshapes(scores_vec, t)
        expr_var = tracker.get_expr_var()

        # Nose position for inactivity
        nose_pos = (lm_list[NOSE_TIP].x * w, lm_list[NOSE_TIP].y * h)

        # ── Layer 3: classify engagement ─────────────────
        level, confidence = classify_engagement(
            ear_val, mar_val, gaze_down, gaze_left, gaze_right,
            pitch, yaw, expr_var
        )

        frame_states.append({
            "frame":      frame_id,
            "t":          round(t, 3),
            "engagement": level,
            "score":      confidence,
            "ear":        round(ear_val, 3),
            "mar":        round(mar_val, 3),
            "gaze_down":  round(gaze_down, 3),
            "gaze_left":  round(gaze_left, 3),
            "gaze_right": round(gaze_right, 3),
            "pitch":      round(pitch, 1),
            "yaw":        round(yaw, 1),
            "roll":       round(roll, 1),
            "expr_var":   round(expr_var, 5),
        })

        # ── Layer 4: event detection ──────────────────────
        tracker.update_yawn(mar_val, t, frame_id)
        tracker.update_eye_closure(ear_val, t, frame_id)
        tracker.update_gaze(gaze_down, gaze_left, gaze_right, t, frame_id)
        tracker.update_head_pose(pitch, yaw, t, frame_id)
        tracker.update_inactivity(nose_pos, t, frame_id)

        frame_id += 1

        if frame_id % 100 == 0:
            pct = (frame_id / total_frames * 100) if total_frames > 0 else 0
            print(f"  {frame_id}/{total_frames}  ({pct:.1f}%)  [{level}]")

    cap.release()
    tracker.flush(t, frame_id)

    # ── sort & save ───────────────────────────────────────
    events_sorted = sorted(tracker.events, key=lambda e: e["frame_start"])

    output = {
        "events":       events_sorted,
        "frame_states": frame_states,   # per-frame data for Layer 5 analytics
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # ── summary ───────────────────────────────────────────
    print(f"\n{'─'*40}")
    print(f"Done. Total events: {len(events_sorted)}")
    for etype in ["yawn", "eyes_closed", "looked_away", "head_pose_off", "inactivity", "no_face"]:
        n = sum(1 for e in events_sorted if e["event"] == etype)
        if n:
            print(f"  {etype:<18}: {n}")
    print(f"Results saved - {output_path}")


# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    run(
        video_path=r"C:\Users\662\OneDrive\Рабочий стол\0328(1).mp4",
        output_path="events.json",
    )