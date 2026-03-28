"""Layer 6 — Lecture Section Scoring via LangGraph.

Pipeline:
  1. segment_lecture — split the session into time-based sections
  2. compute_section_analytics — calculate engagement metrics per section
  3. generate_ai_notes — call Claude to produce teaching advice per section + overall summary

Uses LangGraph StateGraph with Pydantic state for validation.
"""

from collections import Counter
from typing import Annotated

import operator
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic

from app.analytics.prompts import SECTION_SCORING_PROMPT
from app.models.analytics import (
    Event,
    EngagementSegment,
    Section,
    SectionScoringResult,
    SessionData,
    StateBreakdown,
)


# ---------------------------------------------------------------------------
# Graph State
# ---------------------------------------------------------------------------

class ScoringState(BaseModel):
    """State that flows through the LangGraph pipeline."""

    # Input
    session: SessionData

    # Intermediate — built by segment_lecture
    sections: list[Section] = Field(default_factory=list)

    # Output — built by generate_ai_notes
    overall_summary: str = ""

    # Config
    segment_duration: float = Field(default=300.0, description="Target section length in seconds")
    engagement_shift_threshold: float = Field(
        default=0.15, description="Min engagement change to force a segment boundary"
    )


# ---------------------------------------------------------------------------
# Node 1: Segment the lecture
# ---------------------------------------------------------------------------

def segment_lecture(state: ScoringState) -> dict:
    """Split the session into sections based on time intervals and engagement shifts.

    Uses fixed-duration segments as a base, then adjusts boundaries where
    engagement shifts significantly (>threshold sustained for >30s).
    """
    session = state.session
    duration = session.duration
    seg_dur = state.segment_duration

    # Build an engagement score per second from engagement_states
    scores_per_second = _build_per_second_scores(session.engagement_states, duration)

    # Start with fixed boundaries
    boundaries = list(range(0, int(duration), int(seg_dur)))
    if boundaries[-1] != int(duration):
        boundaries.append(int(duration))

    # Detect significant shifts and insert boundaries
    shift_threshold = state.engagement_shift_threshold
    window = 30  # seconds
    for t in range(window, int(duration) - window):
        before = sum(scores_per_second[t - window:t]) / window
        after = sum(scores_per_second[t:t + window]) / window
        if abs(after - before) >= shift_threshold:
            # Only insert if not too close to an existing boundary
            if all(abs(t - b) > 60 for b in boundaries):
                boundaries.append(t)

    boundaries = sorted(set(boundaries))

    # Build sections
    sections = []
    for i in range(len(boundaries) - 1):
        start = float(boundaries[i])
        end = float(boundaries[i + 1])
        label = _auto_label(i, len(boundaries) - 1, scores_per_second, start, end)
        sections.append(Section(
            label=label,
            start=start,
            end=end,
            engagement_pct=0.0,
            state_breakdown=StateBreakdown(engaged=0, passive=0, disengaged=0),
        ))

    return {"sections": sections}


# ---------------------------------------------------------------------------
# Node 2: Compute per-section analytics
# ---------------------------------------------------------------------------

def compute_section_analytics(state: ScoringState) -> dict:
    """Calculate engagement percentage, state breakdown, and top event for each section."""
    session = state.session
    sections = state.sections
    updated = []

    for section in sections:
        s_start = section.start
        s_end = section.end
        s_duration = s_end - s_start

        if s_duration == 0:
            updated.append(section)
            continue

        # Calculate time in each state
        time_in_state = {"engaged": 0.0, "passive": 0.0, "disengaged": 0.0}
        for seg in session.engagement_states:
            overlap_start = max(seg.start, s_start)
            overlap_end = min(seg.end, s_end)
            if overlap_start < overlap_end:
                time_in_state[seg.state] += overlap_end - overlap_start

        total_time = sum(time_in_state.values()) or 1.0
        breakdown = StateBreakdown(
            engaged=round(time_in_state["engaged"] / total_time * 100, 1),
            passive=round(time_in_state["passive"] / total_time * 100, 1),
            disengaged=round(time_in_state["disengaged"] / total_time * 100, 1),
        )
        engagement_pct = round(breakdown.engaged + breakdown.passive * 0.5, 1)

        # Find events in this section
        events_in_section = [
            e for e in session.events
            if s_start <= e.timestamp < s_end
        ]

        # Top event type
        top_event = None
        if events_in_section:
            counts = Counter(e.event_type for e in events_in_section)
            top_type, top_count = counts.most_common(1)[0]
            top_event = f"{top_type} ({top_count} {'time' if top_count == 1 else 'times'})"

        updated.append(section.model_copy(update={
            "engagement_pct": engagement_pct,
            "state_breakdown": breakdown,
            "top_event": top_event,
            "events_in_section": events_in_section,
        }))

    return {"sections": updated}


# ---------------------------------------------------------------------------
# Node 3: Generate AI notes via Claude
# ---------------------------------------------------------------------------

def generate_ai_notes(state: ScoringState) -> dict:
    """Call Claude to generate per-section teaching advice and an overall summary."""
    model = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=2000)

    sections_text = _format_sections_for_prompt(state.sections)

    prompt = SECTION_SCORING_PROMPT.format(
        duration_min=state.session.duration / 60,
        sections_text=sections_text,
    )

    response = model.invoke([{"role": "user", "content": prompt}])
    content = response.content

    # Parse the response
    updated_sections = list(state.sections)
    overall_summary = ""

    lines = content.strip().split("\n")
    current_section_idx = -1
    current_text = []

    for line in lines:
        line_stripped = line.strip()
        if line_stripped.upper().startswith("SECTION "):
            # Save previous section's text
            if current_section_idx >= 0 and current_section_idx < len(updated_sections):
                updated_sections[current_section_idx] = updated_sections[current_section_idx].model_copy(
                    update={"ai_note": " ".join(current_text).strip()}
                )
            # Parse section number
            try:
                parts = line_stripped.split(":", 1)
                num = int(parts[0].replace("SECTION", "").strip()) - 1
                current_section_idx = num
                current_text = [parts[1].strip()] if len(parts) > 1 else []
            except (ValueError, IndexError):
                current_text.append(line_stripped)
        elif line_stripped.upper().startswith("OVERALL:"):
            # Save last section
            if current_section_idx >= 0 and current_section_idx < len(updated_sections):
                updated_sections[current_section_idx] = updated_sections[current_section_idx].model_copy(
                    update={"ai_note": " ".join(current_text).strip()}
                )
            current_section_idx = -1
            overall_summary = line_stripped.split(":", 1)[1].strip() if ":" in line_stripped else ""
            current_text = [overall_summary] if overall_summary else []
        else:
            current_text.append(line_stripped)

    # Handle final section or overall
    if current_section_idx >= 0 and current_section_idx < len(updated_sections):
        updated_sections[current_section_idx] = updated_sections[current_section_idx].model_copy(
            update={"ai_note": " ".join(current_text).strip()}
        )
    elif current_section_idx == -1 and current_text:
        overall_summary = " ".join(current_text).strip()

    return {"sections": updated_sections, "overall_summary": overall_summary}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_section_scoring_graph() -> StateGraph:
    """Build and compile the section scoring LangGraph pipeline."""
    builder = StateGraph(ScoringState)

    builder.add_node("segment_lecture", segment_lecture)
    builder.add_node("compute_analytics", compute_section_analytics)
    builder.add_node("generate_ai_notes", generate_ai_notes)

    builder.add_edge(START, "segment_lecture")
    builder.add_edge("segment_lecture", "compute_analytics")
    builder.add_edge("compute_analytics", "generate_ai_notes")
    builder.add_edge("generate_ai_notes", END)

    return builder.compile()


def run_section_scoring(session_data: SessionData, segment_duration: float = 300.0) -> SectionScoringResult:
    """Run the full section scoring pipeline and return the result.

    Args:
        session_data: The session events and engagement states.
        segment_duration: Target section length in seconds (default 5 min).

    Returns:
        SectionScoringResult with scored sections and overall summary.
    """
    graph = build_section_scoring_graph()

    initial_state = ScoringState(
        session=session_data,
        segment_duration=segment_duration,
    )

    result = graph.invoke(initial_state)

    return SectionScoringResult(
        session_id=session_data.session_id,
        overall_summary=result["overall_summary"],
        sections=result["sections"],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_per_second_scores(
    engagement_states: list[EngagementSegment],
    duration: float,
) -> list[float]:
    """Build a per-second engagement score array from engagement segments."""
    score_map = {"engaged": 1.0, "passive": 0.5, "disengaged": 0.0}
    scores = [0.0] * int(duration)
    for seg in engagement_states:
        score = score_map.get(seg.state, 0.0)
        for t in range(int(seg.start), min(int(seg.end), int(duration))):
            scores[t] = score
    return scores


def _auto_label(
    index: int,
    total: int,
    scores: list[float],
    start: float,
    end: float,
) -> str:
    """Generate a label for a section based on position and engagement."""
    if index == 0:
        return "Introduction"
    if index == total - 1:
        return "Wrap-up"

    # Check if this is a danger zone
    section_scores = scores[int(start):int(end)]
    if section_scores:
        avg = sum(section_scores) / len(section_scores)
        if avg < 0.4:
            return "Danger Zone"

    return f"Segment {index + 1}"


def _format_sections_for_prompt(sections: list[Section]) -> str:
    """Format section data as readable text for the LLM prompt."""
    lines = []
    for i, s in enumerate(sections, 1):
        time_range = f"{_fmt_time(s.start)} – {_fmt_time(s.end)}"
        events_desc = ""
        if s.events_in_section:
            counts = Counter(e.event_type for e in s.events_in_section)
            events_desc = ", ".join(f"{t} ({c}x)" for t, c in counts.most_common())

        lines.append(
            f"Section {i}: \"{s.label}\" ({time_range})\n"
            f"  Engagement: {s.engagement_pct:.1f}%\n"
            f"  Breakdown: {s.state_breakdown.engaged:.0f}% engaged, "
            f"{s.state_breakdown.passive:.0f}% passive, "
            f"{s.state_breakdown.disengaged:.0f}% disengaged\n"
            f"  Events: {events_desc or 'none'}"
        )
    return "\n\n".join(lines)


def _fmt_time(seconds: float) -> str:
    """Format seconds as mm:ss."""
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"
