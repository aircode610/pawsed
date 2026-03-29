"""Standalone visualizer — generates Matplotlib figures from a processed session.

Reads the session pickle (saved by /analyze) and outputs four plots:

  1. Engagement timeline — color-coded band over time
  2. Per-minute engagement score — line chart
  3. Event type distribution — horizontal bar chart
  4. Event duration distribution — histogram (brief vs significant)

Usage:
    cd backend
    PYTHONPATH=. python scripts/visualize.py <session_id>

    # or point directly at a pickle file:
    PYTHONPATH=. python scripts/visualize.py --pickle sessions/results/<id>_results.pkl

Outputs are saved to scripts/output/<session_id>_*.png and also displayed
interactively if a display is available.
"""

import argparse
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Use non-interactive backend when running headless
try:
    matplotlib.use("TkAgg")
except Exception:
    matplotlib.use("Agg")


COLORS = {
    "engaged":    "#4ade80",   # green
    "passive":    "#facc15",   # yellow
    "disengaged": "#f87171",   # red
}

EVENT_COLORS = {
    "yawn":               "#f97316",
    "eyes_closed":        "#a78bfa",
    "looked_away":        "#60a5fa",
    "looked_down":        "#fb7185",
    "drowsy":             "#c084fc",
    "distracted":         "#fbbf24",
    "zoned_out":          "#94a3b8",
    "face_lost":          "#6b7280",
    "prolonged_inactivity": "#f43f5e",
}


def load_results(session_id: str | None, pickle_path: str | None):
    """Load FrameResult list from pickle."""
    import pickle

    if pickle_path:
        p = Path(pickle_path)
    else:
        p = Path("sessions/results") / f"{session_id}_results.pkl"

    if not p.exists():
        print(f"ERROR: pickle not found at {p}", file=sys.stderr)
        print("Run /analyze first or check the session_id.", file=sys.stderr)
        sys.exit(1)

    with open(p, "rb") as f:
        results = pickle.load(f)
    print(f"Loaded {len(results)} frames from {p}")
    return results


def load_events_from_results(results):
    """Re-derive events from results for standalone use."""
    from app.analytics.events import EventLogger
    from app.models.schemas import EngagementState

    logger = EventLogger()
    for r in results:
        logger.process(r)
    if results:
        logger.flush(results[-1].timestamp)
    return logger.events


def plot_engagement_timeline(results, ax):
    """Color-coded horizontal engagement band."""
    from app.models.schemas import EngagementState

    if not results:
        return

    duration = results[-1].timestamp
    ax.set_xlim(0, duration)
    ax.set_ylim(0, 1)

    state_map = {"engaged": 1.0, "passive": 0.5, "disengaged": 0.0}
    prev_t = results[0].timestamp
    prev_state = results[0].state.value

    for r in results[1:]:
        color = COLORS.get(prev_state, "#94a3b8")
        ax.barh(0, r.timestamp - prev_t, left=prev_t, height=1,
                color=color, align="edge", linewidth=0)
        prev_t = r.timestamp
        prev_state = r.state.value

    # Final segment
    ax.barh(0, duration - prev_t, left=prev_t, height=1,
            color=COLORS.get(prev_state, "#94a3b8"), align="edge", linewidth=0)

    ax.set_yticks([])
    ax.set_xlabel("Time (seconds)")
    ax.set_title("Engagement Timeline")

    patches = [mpatches.Patch(color=c, label=l) for l, c in COLORS.items()]
    ax.legend(handles=patches, loc="upper right", fontsize=8)

    # Minute tick marks
    minute_marks = range(0, int(duration) + 60, 60)
    ax.set_xticks(list(minute_marks))
    ax.set_xticklabels([f"{t//60}m" for t in minute_marks], fontsize=8)
    ax.grid(axis="x", linestyle="--", alpha=0.3)


def plot_per_minute_score(results, ax):
    """Line chart — per-minute average engagement score."""
    if not results:
        return

    duration = results[-1].timestamp
    bin_size = 60.0
    num_bins = max(1, int(duration / bin_size) + 1)
    bins = [[] for _ in range(num_bins)]

    score_map = {"engaged": 1.0, "passive": 0.5, "disengaged": 0.0}
    for r in results:
        idx = min(int(r.timestamp / bin_size), num_bins - 1)
        bins[idx].append(score_map.get(r.state.value, 0.0))

    scores = [sum(b) / len(b) if b else 0.0 for b in bins]
    minutes = [i for i in range(len(scores))]

    ax.plot(minutes, scores, color="#60a5fa", linewidth=2, marker="o", markersize=5)
    ax.fill_between(minutes, scores, alpha=0.15, color="#60a5fa")
    ax.axhline(0.6, linestyle="--", color="#4ade80", linewidth=1, alpha=0.6, label="High engagement")
    ax.axhline(0.4, linestyle="--", color="#f87171", linewidth=1, alpha=0.6, label="Low engagement")

    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Minute")
    ax.set_ylabel("Engagement score")
    ax.set_title("Per-minute Engagement Score")
    ax.set_xticks(minutes)
    ax.legend(fontsize=8)
    ax.grid(axis="y", linestyle="--", alpha=0.3)


def plot_event_distribution(events, ax):
    """Horizontal bar chart of event type counts."""
    if not events:
        ax.text(0.5, 0.5, "No events detected", ha="center", va="center",
                transform=ax.transAxes, color="gray")
        ax.set_title("Event Type Distribution")
        return

    from collections import Counter
    counts = Counter(e.event_type for e in events)
    labels = list(counts.keys())
    values = [counts[l] for l in labels]
    colors = [EVENT_COLORS.get(l, "#94a3b8") for l in labels]

    y = np.arange(len(labels))
    bars = ax.barh(y, values, color=colors, height=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Count")
    ax.set_title("Event Type Distribution")

    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=9)
    ax.grid(axis="x", linestyle="--", alpha=0.3)


def plot_event_duration_histogram(events, ax):
    """Histogram of event durations, split by brief vs significant."""
    if not events:
        ax.text(0.5, 0.5, "No events detected", ha="center", va="center",
                transform=ax.transAxes, color="gray")
        ax.set_title("Event Duration Distribution")
        return

    brief = [e.duration for e in events if e.severity == "brief"]
    significant = [e.duration for e in events if e.severity == "significant"]

    bins = np.linspace(0, max(e.duration for e in events) + 1, 20)
    if brief:
        ax.hist(brief, bins=bins, alpha=0.7, color="#60a5fa", label=f"Brief (<5s)  n={len(brief)}")
    if significant:
        ax.hist(significant, bins=bins, alpha=0.7, color="#f87171",
                label=f"Significant (≥5s)  n={len(significant)}")

    ax.axvline(5.0, linestyle="--", color="white", linewidth=1, alpha=0.5)
    ax.set_xlabel("Duration (seconds)")
    ax.set_ylabel("Count")
    ax.set_title("Event Duration Distribution")
    ax.legend(fontsize=8)
    ax.grid(axis="y", linestyle="--", alpha=0.3)


def main():
    parser = argparse.ArgumentParser(description="Visualize a Pawsed session from its pickle file")
    parser.add_argument("session_id", nargs="?", help="Session ID (looks up sessions/results/<id>_results.pkl)")
    parser.add_argument("--pickle", help="Direct path to a _results.pkl file")
    args = parser.parse_args()

    if not args.session_id and not args.pickle:
        parser.print_help()
        sys.exit(1)

    results = load_results(args.session_id, args.pickle)
    events = load_events_from_results(results)

    duration = results[-1].timestamp if results else 0
    total_engaged = sum(1 for r in results if r.state.value == "engaged")
    focus_pct = round(total_engaged / len(results) * 100, 1) if results else 0

    print(f"Duration:   {duration:.1f}s  ({duration/60:.1f} min)")
    print(f"Frames:     {len(results)}")
    print(f"Focus:      {focus_pct}%")
    print(f"Events:     {len(events)}")

    # Dark style
    plt.style.use("dark_background")
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    fig.patch.set_facecolor("#0f172a")
    for ax in axes.flat:
        ax.set_facecolor("#1e293b")
        ax.tick_params(colors="white")
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.title.set_color("white")
        for spine in ax.spines.values():
            spine.set_edgecolor("#334155")

    session_label = args.session_id or Path(args.pickle).stem
    fig.suptitle(f"Pawsed — Session Analysis: {session_label}  |  Focus: {focus_pct}%",
                 fontsize=13, color="white", y=0.98)

    plot_engagement_timeline(results, axes[0, 0])
    plot_per_minute_score(results, axes[0, 1])
    plot_event_distribution(events, axes[1, 0])
    plot_event_duration_histogram(events, axes[1, 1])

    plt.tight_layout(rect=[0, 0, 1, 0.96])

    # Save output
    out_dir = Path("scripts/output")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{session_label}_analysis.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\nSaved to {out_path}")

    try:
        plt.show()
    except Exception:
        pass


if __name__ == "__main__":
    main()
