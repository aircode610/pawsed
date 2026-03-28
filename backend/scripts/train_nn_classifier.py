"""Train the Lokdin-style neural network engagement classifier.

Generates synthetic training data from known engagement patterns,
trains a small MLP, and saves weights to models/engagement_nn.pt.

Run from the backend/ directory:
    python -m scripts.train_nn_classifier
"""

import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
from torch.utils.data import DataLoader, TensorDataset

from app.engine.nn_classifier import EngagementNet, FEATURE_MEANS, FEATURE_STDS

# ── Config ────────────────────────────────────────────────────────────────────
N_PER_CLASS = 10_000   # synthetic samples per class (30k total)
EPOCHS      = 60
BATCH_SIZE  = 256
LR          = 1e-3
SEED        = 42
MODEL_PATH  = Path("models/engagement_nn.pt")


# ── Synthetic data generator ──────────────────────────────────────────────────

def generate(n: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Generate n samples per class.

    Feature column order must match FEATURE_NAMES in nn_classifier.py:
    ear_left, ear_right, ear_avg, mar,
    gaze_score, gaze_horizontal, gaze_vertical,
    head_pitch, head_yaw, head_roll, expression_variance
    """
    def clip(a, lo, hi): return np.clip(a, lo, hi)
    parts_X, parts_y = [], []

    # ── Class 0: Engaged ──────────────────────────────────────────────────────
    e = n
    X = np.column_stack([
        clip(rng.normal(0.28, 0.025, e), 0.22, 0.40),   # ear_left
        clip(rng.normal(0.28, 0.025, e), 0.22, 0.40),   # ear_right
        clip(rng.normal(0.28, 0.020, e), 0.22, 0.38),   # ear_avg
        clip(rng.normal(0.25, 0.05,  e), 0.10, 0.50),   # mar
        clip(rng.normal(0.82, 0.08,  e), 0.65, 1.00),   # gaze_score
        rng.normal(0.0, 0.08, e),                         # gaze_horizontal
        rng.normal(0.0, 0.08, e),                         # gaze_vertical
        rng.normal(0.0, 4.0,  e),                         # head_pitch
        rng.normal(0.0, 5.0,  e),                         # head_yaw
        rng.normal(0.0, 2.0,  e),                         # head_roll
        clip(rng.normal(0.04, 0.01, e), 0.02, 0.12),    # expression_variance
    ]).astype(np.float32)
    parts_X.append(X)
    parts_y.append(np.zeros(e, dtype=np.int64))

    # ── Class 1: Passive ──────────────────────────────────────────────────────
    p = n
    X = np.column_stack([
        clip(rng.normal(0.23, 0.03,  p), 0.16, 0.32),
        clip(rng.normal(0.23, 0.03,  p), 0.16, 0.32),
        clip(rng.normal(0.23, 0.025, p), 0.16, 0.30),
        clip(rng.normal(0.35, 0.08,  p), 0.15, 0.58),
        clip(rng.normal(0.60, 0.10,  p), 0.40, 0.78),
        rng.normal(0.0, 0.14, p),
        rng.normal(0.0, 0.12, p),
        rng.normal(5.0, 6.0,  p),
        rng.normal(8.0, 7.0,  p),
        rng.normal(0.0, 4.0,  p),
        clip(rng.normal(0.015, 0.006, p), 0.005, 0.025),
    ]).astype(np.float32)
    parts_X.append(X)
    parts_y.append(np.ones(p, dtype=np.int64))

    # ── Class 2: Disengaged (4 sub-patterns) ─────────────────────────────────
    q = n // 4
    r = n - 3 * q   # remainder goes to last sub-pattern

    # Sub A: sleepy / eyes closed
    Xa = np.column_stack([
        clip(rng.normal(0.14, 0.03,  q), 0.05, 0.20),
        clip(rng.normal(0.14, 0.03,  q), 0.05, 0.20),
        clip(rng.normal(0.14, 0.025, q), 0.05, 0.19),
        clip(rng.normal(0.30, 0.08,  q), 0.10, 0.55),
        clip(rng.normal(0.50, 0.12,  q), 0.20, 0.72),
        rng.normal(0.0, 0.10, q),
        rng.normal(0.0, 0.10, q),
        rng.normal(5.0, 5.0,  q),
        rng.normal(5.0, 5.0,  q),
        rng.normal(0.0, 3.0,  q),
        clip(rng.normal(0.010, 0.005, q), 0.003, 0.020),
    ]).astype(np.float32)

    # Sub B: yawning
    Xb = np.column_stack([
        clip(rng.normal(0.22, 0.03,  q), 0.16, 0.32),
        clip(rng.normal(0.22, 0.03,  q), 0.16, 0.32),
        clip(rng.normal(0.22, 0.025, q), 0.16, 0.30),
        clip(rng.normal(0.75, 0.08,  q), 0.60, 0.95),   # high MAR
        clip(rng.normal(0.55, 0.12,  q), 0.30, 0.75),
        rng.normal(0.0, 0.12, q),
        rng.normal(0.0, 0.10, q),
        rng.normal(8.0, 6.0,  q),
        rng.normal(5.0, 5.0,  q),
        rng.normal(0.0, 3.0,  q),
        clip(rng.normal(0.025, 0.008, q), 0.010, 0.050),
    ]).astype(np.float32)

    # Sub C: looking away (low gaze)
    Xc = np.column_stack([
        clip(rng.normal(0.26, 0.03,  q), 0.18, 0.38),
        clip(rng.normal(0.26, 0.03,  q), 0.18, 0.38),
        clip(rng.normal(0.26, 0.025, q), 0.18, 0.36),
        clip(rng.normal(0.28, 0.06,  q), 0.12, 0.50),
        clip(rng.normal(0.25, 0.10,  q), 0.05, 0.45),   # low gaze_score
        rng.normal(0.0, 0.25, q),
        rng.normal(0.0, 0.20, q),
        rng.normal(0.0, 6.0,  q),
        rng.normal(0.0, 8.0,  q),
        rng.normal(0.0, 3.0,  q),
        clip(rng.normal(0.020, 0.008, q), 0.008, 0.040),
    ]).astype(np.float32)

    # Sub D: head turned away
    Xd = np.column_stack([
        clip(rng.normal(0.25, 0.03,  r), 0.17, 0.36),
        clip(rng.normal(0.25, 0.03,  r), 0.17, 0.36),
        clip(rng.normal(0.25, 0.025, r), 0.17, 0.34),
        clip(rng.normal(0.28, 0.06,  r), 0.12, 0.50),
        clip(rng.normal(0.45, 0.12,  r), 0.15, 0.65),
        rng.normal(0.0, 0.18, r),
        rng.normal(0.0, 0.15, r),
        rng.normal(8.0, 5.0,  r),
        clip(rng.normal(28.0, 8.0, r), 15.0, 50.0),     # large head_yaw
        rng.normal(0.0, 4.0,  r),
        clip(rng.normal(0.018, 0.007, r), 0.006, 0.040),
    ]).astype(np.float32)

    parts_X.append(np.vstack([Xa, Xb, Xc, Xd]))
    parts_y.append(np.full(n, 2, dtype=np.int64))

    return np.vstack(parts_X), np.concatenate(parts_y)


def normalize(X: np.ndarray) -> np.ndarray:
    return ((X - FEATURE_MEANS) / (FEATURE_STDS + 1e-8)).astype(np.float32)


# ── Training loop ─────────────────────────────────────────────────────────────

def train():
    rng = np.random.default_rng(SEED)
    print(f"Generating {N_PER_CLASS * 3:,} synthetic samples...")
    X, y = generate(N_PER_CLASS, rng)
    X = normalize(X)

    # 85% train / 15% validation
    idx = rng.permutation(len(X))
    split = int(0.85 * len(X))
    X_tr, X_val = X[idx[:split]], X[idx[split:]]
    y_tr, y_val = y[idx[:split]], y[idx[split:]]

    train_dl = DataLoader(TensorDataset(torch.tensor(X_tr), torch.tensor(y_tr)),
                          batch_size=BATCH_SIZE, shuffle=True)
    val_dl   = DataLoader(TensorDataset(torch.tensor(X_val), torch.tensor(y_val)),
                          batch_size=BATCH_SIZE)

    model     = EngagementNet()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    criterion = nn.CrossEntropyLoss()

    best_val_acc = 0.0
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"Training for {EPOCHS} epochs...\n")
    for epoch in range(1, EPOCHS + 1):
        # Train
        model.train()
        for Xb, yb in train_dl:
            optimizer.zero_grad()
            criterion(model(Xb), yb).backward()
            optimizer.step()
        scheduler.step()

        # Validate
        model.eval()
        correct = total = 0
        with torch.no_grad():
            for Xb, yb in val_dl:
                correct += (model(Xb).argmax(1) == yb).sum().item()
                total   += len(yb)
        val_acc = correct / total

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), MODEL_PATH)

        if epoch % 10 == 0:
            print(f"  Epoch {epoch:3d}/{EPOCHS}  val_acc={val_acc:.4f}  best={best_val_acc:.4f}")

    print(f"\nDone. Best val accuracy: {best_val_acc:.4f}")
    print(f"Weights saved to: {MODEL_PATH}")


if __name__ == "__main__":
    train()
