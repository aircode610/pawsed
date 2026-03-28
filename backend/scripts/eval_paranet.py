"""Evaluate ParaNet model accuracy on the Student-engagement-dataset.

Dataset structure:
    Student-engagement-dataset/
        Engaged/confused/
        Engaged/engaged/
        Engaged/frustrated/
        Not engaged/Looking Away/
        Not engaged/bored/
        Not engaged/drowsy/

Run from the backend/ directory:
    python -m scripts.eval_paranet [--dataset PATH] [--weights PATH]
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

# Allow imports from backend/app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engine.paranet_classifier import ParaNet, CLASS_MAP
from app.models.schemas import EngagementState

# ── Label mapping: folder path → class index ─────────────────────────────────
# LabelEncoder sorts alphabetically across ALL subfolders:
#   Engaged/confused      → 0
#   Engaged/engaged       → 1
#   Engaged/frustrated    → 2
#   Not engaged/Looking Away → 3
#   Not engaged/bored     → 4
#   Not engaged/drowsy    → 5
FOLDER_TO_IDX: dict[str, int] = {
    "confused":      0,
    "engaged":       1,
    "frustrated":    2,
    "Looking Away":  3,
    "bored":         4,
    "drowsy":        5,
}

_STATE_IDX = {
    EngagementState.ENGAGED:    0,
    EngagementState.PASSIVE:    1,
    EngagementState.DISENGAGED: 2,
}

THREE_CLASS_NAMES = ["engaged", "passive", "disengaged"]
SIX_CLASS_NAMES   = [
    "confused (→passive)",
    "engaged (→engaged)",
    "frustrated (→passive)",
    "Looking Away (→disengaged)",
    "bored (→disengaged)",
    "drowsy (→disengaged)",
]


_face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def load_image(path: Path, size: int = 250) -> np.ndarray | None:
    """Replicate the notebook's process_imgs: Haar Cascade crop → 250×250 grayscale."""
    img = cv2.imread(str(path))
    if img is None:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = _face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    if len(faces) > 0:
        x, y, w, h = faces[0]
        pad_x, pad_y = int(w * 0.15), int(h * 0.15)
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(img.shape[1], x + w + pad_x)
        y2 = min(img.shape[0], y + h + pad_y)
        crop = gray[y1:y2, x1:x2]
        if crop.size > 0:
            return cv2.resize(crop, (size, size))
    # Fallback: no face detected → resize whole image
    return cv2.resize(gray, (size, size))


def preprocess(img: np.ndarray) -> torch.Tensor:
    # Notebook trains with raw uint8 values cast to float (no /255 normalization)
    x = img.astype(np.float32)
    return torch.tensor(x).unsqueeze(0).unsqueeze(0)  # (1, 1, 250, 250)


def eval_model(dataset_root: Path, weights_path: Path, num_classes: int = 6):
    print(f"Loading weights from: {weights_path}")
    model = ParaNet(num_classes=num_classes)
    state_dict = torch.load(weights_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()

    # Per-class counters for 6-class accuracy
    six_correct   = np.zeros(num_classes, dtype=int)
    six_total     = np.zeros(num_classes, dtype=int)
    # Per-class counters for 3-class accuracy
    three_correct = np.zeros(3, dtype=int)
    three_total   = np.zeros(3, dtype=int)

    skipped = 0

    for subfolder, class_idx in FOLDER_TO_IDX.items():
        # Find this subfolder anywhere under dataset_root
        matches = list(dataset_root.rglob(subfolder))
        dirs = [p for p in matches if p.is_dir()]
        if not dirs:
            print(f"  WARNING: subfolder '{subfolder}' not found under {dataset_root}")
            continue
        folder = dirs[0]

        images = sorted(folder.glob("*.jpg")) + sorted(folder.glob("*.png"))
        if not images:
            print(f"  WARNING: no images in {folder}")
            continue

        true_3class = _STATE_IDX[CLASS_MAP[class_idx]]

        for img_path in images:
            img = load_image(img_path)
            if img is None:
                skipped += 1
                continue

            x = preprocess(img)
            with torch.no_grad():
                _, probs = model(x)
            raw_probs = probs.squeeze(0).numpy()

            # 6-class prediction
            pred_6 = int(np.argmax(raw_probs))
            six_total[class_idx]   += 1
            six_correct[class_idx] += int(pred_6 == class_idx)

            # 3-class prediction (aggregate probabilities)
            three_probs = np.zeros(3, dtype=np.float32)
            for i, p in enumerate(raw_probs):
                three_probs[_STATE_IDX[CLASS_MAP[i]]] += p
            pred_3 = int(np.argmax(three_probs))
            three_total[true_3class]   += 1
            three_correct[true_3class] += int(pred_3 == true_3class)

    # ── Print results ──────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  6-CLASS ACCURACY (original labels)")
    print(f"{'='*60}")
    for i, name in enumerate(SIX_CLASS_NAMES):
        if six_total[i] == 0:
            continue
        acc = six_correct[i] / six_total[i]
        print(f"  {name:<35} {six_correct[i]:>4}/{six_total[i]:<4}  {acc:.1%}")
    total_6 = six_total.sum()
    correct_6 = six_correct.sum()
    if total_6 > 0:
        print(f"  {'OVERALL':<35} {correct_6:>4}/{total_6:<4}  {correct_6/total_6:.1%}")

    print(f"\n{'='*60}")
    print("  3-CLASS ACCURACY (engaged / passive / disengaged)")
    print(f"{'='*60}")
    for i, name in enumerate(THREE_CLASS_NAMES):
        if three_total[i] == 0:
            continue
        acc = three_correct[i] / three_total[i]
        print(f"  {name:<35} {three_correct[i]:>4}/{three_total[i]:<4}  {acc:.1%}")
    total_3 = three_total.sum()
    correct_3 = three_correct.sum()
    if total_3 > 0:
        print(f"  {'OVERALL':<35} {correct_3:>4}/{total_3:<4}  {correct_3/total_3:.1%}")

    if skipped:
        print(f"\n  (skipped {skipped} unreadable images)")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Evaluate ParaNet on the engagement dataset")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "Student-engagement-dataset",
        help="Path to the dataset root",
    )
    parser.add_argument(
        "--weights",
        type=Path,
        default=Path("models/paranet.pt"),
        help="Path to paranet weights file",
    )
    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"ERROR: dataset not found at {args.dataset}")
        sys.exit(1)
    if not args.weights.exists():
        print(f"ERROR: weights not found at {args.weights}")
        print("Available models:", list(Path("models").glob("*.pt")))
        sys.exit(1)

    eval_model(args.dataset, args.weights)


if __name__ == "__main__":
    main()
