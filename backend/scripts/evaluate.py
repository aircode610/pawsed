"""Quantitative evaluation of the engagement classifier and event detector.

Builds a synthetic ground-truth dataset from deterministic FeatureVectors,
runs the classifier and event logger against them, and reports:

  - Confusion matrix (Engaged vs Disengaged)
  - Per-class precision, recall, F1
  - Event detection results (each expected event type triggered correctly)

No video or API key required — the rule-based classifier is deterministic.

Usage:
    cd backend
    PYTHONPATH=. python scripts/evaluate.py
"""

import sys
from collections import defaultdict
from dataclasses import dataclass

from app.engine.classifier import ClassifierConfig, EngagementClassifier
from app.analytics.events import EventLogger, EVENT_YAWN, EVENT_EYES_CLOSED, EVENT_LOOKED_AWAY, EVENT_LOOKED_DOWN, EVENT_DROWSY, EVENT_DISTRACTED
from app.models.schemas import EngagementState, FeatureVector, FrameResult, FaceResult


# ---------------------------------------------------------------------------
# Synthetic ground-truth dataset
# ---------------------------------------------------------------------------

def _fv(
    timestamp: float,
    ear_avg: float = 0.28,
    mar: float = 0.10,
    gaze_score: float = 0.85,
    gaze_horizontal: float = 0.0,
    head_yaw: float = 4.0,
    head_pitch: float = 3.0,
    head_roll: float = 1.0,
    expression_variance: float = 0.04,
    drowsiness: float = 0.05,
    head_motion: float = 0.5,
    brow_furrow: float = 0.10,
    brow_raise: float = 0.15,
) -> FeatureVector:
    return FeatureVector(
        ear_left=ear_avg, ear_right=ear_avg, ear_avg=ear_avg,
        mar=mar,
        gaze_score=gaze_score, gaze_horizontal=gaze_horizontal, gaze_vertical=0.0,
        head_pitch=head_pitch, head_yaw=head_yaw, head_roll=head_roll,
        expression_variance=expression_variance,
        drowsiness=drowsiness,
        head_motion=head_motion,
        brow_furrow=brow_furrow,
        brow_raise=brow_raise,
        timestamp=timestamp,
    )


@dataclass
class ClassifierCase:
    name: str
    frames: list[FeatureVector]   # fed in order
    expected_final: str           # "engaged" or "disengaged"


@dataclass
class EventCase:
    name: str
    frames: list[FeatureVector]
    expected_event_type: str      # event type that should fire after frames


def build_classifier_cases() -> list[ClassifierCase]:
    return [
        # --- ENGAGED cases ---
        ClassifierCase("engaged_baseline", [_fv(0.0)], "engaged"),
        ClassifierCase("engaged_slight_head_turn",
                       [_fv(0.0, head_yaw=11.0)], "engaged"),
        ClassifierCase("engaged_low_brow_furrow",
                       [_fv(0.0, brow_furrow=0.25)], "engaged"),
        ClassifierCase("engaged_after_eye_blink_recovery",
                       [_fv(0.0, ear_avg=0.08),           # eyes closed frame 0
                        _fv(0.3, ear_avg=0.08),           # still closed at 0.3s (< 0.5s threshold)
                        _fv(0.35, ear_avg=0.30)],          # opens → resets timer → engaged
                       "engaged"),
        ClassifierCase("engaged_brief_yawn",
                       [_fv(0.0, mar=0.75),
                        _fv(1.5, mar=0.75),               # only 1.5s yawn (< 2.0s threshold)
                        _fv(2.0, mar=0.10)],               # closes
                       "engaged"),
        ClassifierCase("engaged_slight_gaze_drift",
                       [_fv(0.0, gaze_score=0.40)],       # between passive and on-screen thresholds
                       "engaged"),

        # --- DISENGAGED cases ---
        ClassifierCase("disengaged_eyes_closed_sustained",
                       [_fv(0.0, ear_avg=0.08),
                        _fv(0.3, ear_avg=0.08),
                        _fv(0.6, ear_avg=0.08)],          # 0.6s ≥ 0.5s threshold
                       "disengaged"),
        ClassifierCase("disengaged_yawn_sustained",
                       [_fv(0.0, mar=0.75),
                        _fv(1.0, mar=0.75),
                        _fv(2.5, mar=0.75)],              # 2.5s ≥ 2.0s threshold
                       "disengaged"),
        ClassifierCase("disengaged_gaze_away_sustained",
                       [_fv(0.0, gaze_score=0.20),
                        _fv(2.0, gaze_score=0.20),
                        _fv(3.5, gaze_score=0.20)],       # 3.5s ≥ 3.0s threshold
                       "disengaged"),
        ClassifierCase("disengaged_head_turned_immediate",
                       [_fv(0.0, head_yaw=40.0)],         # > 15° → immediate
                       "disengaged"),
        ClassifierCase("disengaged_drowsy_sustained",
                       [_fv(0.0, drowsiness=0.65),
                        _fv(1.0, drowsiness=0.65),
                        _fv(2.5, drowsiness=0.65)],       # 2.5s ≥ 2.0s threshold
                       "disengaged"),
        ClassifierCase("disengaged_fidgeting_sustained",
                       [_fv(0.0, head_motion=4.0),
                        _fv(1.0, head_motion=4.0),
                        _fv(2.5, head_motion=4.0)],       # 2.5s ≥ 2.0s threshold
                       "disengaged"),
        ClassifierCase("disengaged_head_pitched_down",
                       [_fv(0.0, head_pitch=25.0),
                        _fv(2.0, head_pitch=25.0),
                        _fv(3.5, head_pitch=25.0)],       # 3.5s ≥ 3.0s threshold
                       "disengaged"),
    ]


def build_event_cases() -> list[EventCase]:
    """Each case produces exactly one disengagement event of the expected type."""
    engaged = _fv(99.0)   # recovery frame

    def case(name, disengage_frames, expected):
        return EventCase(name, disengage_frames + [engaged], expected)

    return [
        case("event_yawn",
             [_fv(0.0, mar=0.75), _fv(1.0, mar=0.75), _fv(2.5, mar=0.75)],
             EVENT_YAWN),
        case("event_eyes_closed",
             [_fv(0.0, ear_avg=0.08), _fv(0.3, ear_avg=0.08), _fv(0.6, ear_avg=0.08)],
             EVENT_EYES_CLOSED),
        case("event_looked_away",
             [_fv(0.0, gaze_score=0.20), _fv(2.0, gaze_score=0.20), _fv(3.5, gaze_score=0.20)],
             EVENT_LOOKED_AWAY),
        case("event_looked_down",
             [_fv(0.0, head_pitch=25.0), _fv(2.0, head_pitch=25.0), _fv(3.5, head_pitch=25.0)],
             EVENT_LOOKED_DOWN),
        case("event_drowsy",
             [_fv(0.0, drowsiness=0.65), _fv(1.0, drowsiness=0.65), _fv(2.5, drowsiness=0.65)],
             EVENT_DROWSY),
        case("event_distracted",
             [_fv(0.0, head_motion=4.0), _fv(1.0, head_motion=4.0), _fv(2.5, head_motion=4.0)],
             EVENT_DISTRACTED),
    ]


# ---------------------------------------------------------------------------
# Evaluation runners
# ---------------------------------------------------------------------------

def run_classifier_evaluation(cases: list[ClassifierCase]):
    """Run all classifier cases and return (predictions, actuals) lists."""
    predictions = []
    actuals = []

    print("\n── Classifier Evaluation ─────────────────────────────────────────")
    print(f"{'Case':<45} {'Expected':<12} {'Predicted':<12} {'✓/✗'}")
    print("─" * 75)

    for case in cases:
        clf = EngagementClassifier()
        state = EngagementState.ENGAGED
        for fv in case.frames:
            state, _ = clf.classify(fv)

        predicted = state.value
        correct = predicted == case.expected_final
        mark = "✓" if correct else "✗"

        print(f"{case.name:<45} {case.expected_final:<12} {predicted:<12} {mark}")
        predictions.append(predicted)
        actuals.append(case.expected_final)

    return predictions, actuals


def run_event_evaluation(cases: list[EventCase]):
    """Run all event cases and check that the right event type fires."""
    print("\n── Event Detection Evaluation ────────────────────────────────────")
    print(f"{'Case':<35} {'Expected event':<22} {'Detected event':<22} {'✓/✗'}")
    print("─" * 85)

    tp = fp = fn = 0

    for case in cases:
        clf = EngagementClassifier()
        logger = EventLogger()
        detected_type = None

        for fv in case.frames:
            state, confidence = clf.classify(fv)
            fr = _make_frame_result(fv, state, confidence)
            event = logger.process(fr)
            if event:
                detected_type = event.event_type

        correct = detected_type == case.expected_event_type
        mark = "✓" if correct else "✗"
        if correct:
            tp += 1
        elif detected_type is None:
            fn += 1
        else:
            fp += 1

        det_str = detected_type or "(none)"
        print(f"{case.name:<35} {case.expected_event_type:<22} {det_str:<22} {mark}")

    return tp, fp, fn


def _make_frame_result(fv: FeatureVector, state: EngagementState, confidence: float) -> FrameResult:
    """Wrap a FeatureVector in a minimal FrameResult for the event logger."""
    from app.models.schemas import FrameResult, FaceResult, RiskLevel
    face = FaceResult(
        face_id=0, features=fv, state=state, confidence=confidence,
        face_detected=True, centroid_x=0.5, centroid_y=0.5,
    )
    return FrameResult(
        timestamp=fv.timestamp,
        faces=[face],
        total_faces=1,
        disengaged_pct=100.0 if state == EngagementState.DISENGAGED else 0.0,
        risk_level=RiskLevel.HIGH if state == EngagementState.DISENGAGED else RiskLevel.LOW,
    )


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def confusion_matrix(predictions: list[str], actuals: list[str]):
    labels = ["engaged", "disengaged"]
    matrix = defaultdict(lambda: defaultdict(int))
    for pred, actual in zip(predictions, actuals):
        matrix[actual][pred] += 1

    print("\n── Confusion Matrix ──────────────────────────────────────────────")
    header = f"{'':>14}" + "".join(f"{'pred:' + l:>16}" for l in labels)
    print(header)
    for actual in labels:
        row = f"{'actual:' + actual:>14}" + "".join(f"{matrix[actual][pred]:>16}" for pred in labels)
        print(row)


def prf(predictions: list[str], actuals: list[str], label: str) -> tuple[float, float, float]:
    tp = sum(1 for p, a in zip(predictions, actuals) if p == label and a == label)
    fp = sum(1 for p, a in zip(predictions, actuals) if p == label and a != label)
    fn = sum(1 for p, a in zip(predictions, actuals) if p != label and a == label)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall    = tp / (tp + fn) if (tp + fn) else 0.0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def print_metrics(predictions: list[str], actuals: list[str]):
    confusion_matrix(predictions, actuals)

    acc = sum(p == a for p, a in zip(predictions, actuals)) / len(actuals)
    print(f"\n── Per-class Metrics ─────────────────────────────────────────────")
    print(f"{'Class':<16} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    print("─" * 50)
    for label in ["engaged", "disengaged"]:
        p, r, f = prf(predictions, actuals, label)
        print(f"{label:<16} {p:>10.2f} {r:>10.2f} {f:>10.2f}")
    print(f"\n  Overall accuracy: {acc:.2f}  ({sum(p == a for p, a in zip(predictions, actuals))}/{len(actuals)} correct)")


def print_event_summary(tp: int, fp: int, fn: int):
    total = tp + fp + fn
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall    = tp / (tp + fn) if (tp + fn) else 0.0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    print(f"\n── Event Detection Summary ───────────────────────────────────────")
    print(f"  Correct: {tp}/{tp + fn}  |  Precision: {precision:.2f}  Recall: {recall:.2f}  F1: {f1:.2f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 75)
    print("  Pawsed — Engagement Classifier & Event Detector Evaluation")
    print("=" * 75)

    clf_cases = build_classifier_cases()
    predictions, actuals = run_classifier_evaluation(clf_cases)
    print_metrics(predictions, actuals)

    event_cases = build_event_cases()
    tp, fp, fn = run_event_evaluation(event_cases)
    print_event_summary(tp, fp, fn)

    print("\n" + "=" * 75)
    # Exit non-zero if any case failed (useful in CI)
    total_wrong = sum(p != a for p, a in zip(predictions, actuals)) + fp + fn
    sys.exit(0 if total_wrong == 0 else 1)
