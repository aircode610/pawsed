"""Audio transcription using faster-whisper.

Extracts audio from a video file and transcribes it to timestamped segments.
Provides content context for the AI insights pipeline so Claude knows WHAT
was being taught during each engagement dip — not just when it happened.

Falls back gracefully (returns []) if faster-whisper is not installed.
"""

import logging

logger = logging.getLogger(__name__)


def transcribe_video(video_path: str, model_size: str = "tiny") -> list[dict]:
    """Transcribe the audio track of a video file.

    Returns a list of dicts: [{start: float, end: float, text: str}, ...]
    with one entry per speech segment (natural speech pauses as boundaries).
    Returns [] if faster-whisper is unavailable or transcription fails.

    Args:
        video_path: Path to the video file.
        model_size: "tiny" (~75 MB) is fastest; "base" is more accurate.
                    First call downloads the model (~HuggingFace cache).
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        logger.warning(
            "faster-whisper not installed — transcription skipped. "
            "Install with: pip install faster-whisper"
        )
        return []

    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments_iter, _ = model.transcribe(
            video_path,
            beam_size=1,       # faster decode at slight accuracy cost
            vad_filter=True,   # skip silent stretches
        )
        result = [
            {"start": seg.start, "end": seg.end, "text": seg.text.strip()}
            for seg in segments_iter
            if seg.text.strip()
        ]
        logger.info("Transcribed %d segments from %s", len(result), video_path)
        return result
    except Exception as exc:
        logger.warning("Transcription failed for %s: %s", video_path, exc)
        return []


def get_transcript_for_window(
    segments: list[dict],
    start: float,
    end: float,
) -> str:
    """Return concatenated transcript text for a given time window [start, end)."""
    parts = [
        seg["text"]
        for seg in segments
        if seg["end"] > start and seg["start"] < end
    ]
    return " ".join(parts).strip()


def build_topic_map(
    sections: list[dict],
) -> str:
    """Build a compact topic map string from scored sections for the chat system prompt.

    Expects each section dict to have: label, start, end, engagement_pct, topic (optional).
    """
    if not sections:
        return ""

    def _fmt(s: float) -> str:
        m, sec = divmod(int(s), 60)
        return f"{m}:{sec:02d}"

    lines = ["LECTURE TOPIC MAP:"]
    for sec in sections:
        topic_str = f": {sec['topic']}" if sec.get("topic") else ""
        lines.append(
            f"  {_fmt(sec['start'])}–{_fmt(sec['end'])}  {sec['label']}{topic_str}"
            f"  ({sec['engagement_pct']:.0f}% engagement)"
        )
    return "\n".join(lines)
