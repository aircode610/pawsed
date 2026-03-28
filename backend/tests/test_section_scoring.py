"""Evals for the section scoring pipeline.

Tests segmentation logic and analytics computation with mock session data.
The AI note generation test is marked separately since it requires an API key.
"""

import os
import pytest

from langgraph.graph import StateGraph, START, END

from app.analytics.models import (
    EngagementSegment,
    Event,
    SessionData,
    StateBreakdown,
)
from app.analytics.section_scoring import (
    ScoringState,
    _auto_label,
    _build_per_second_scores,
    _fmt_time,
    build_section_scoring_graph,
    compute_section_analytics,
    run_section_scoring,
    segment_lecture,
)


# ---------------------------------------------------------------------------
# Shared mock data — simulates the 30-min session from the frontend
# ---------------------------------------------------------------------------

MOCK_EVENTS = [
    Event(timestamp=272, event_type="yawn", duration=3.2, confidence=0.87),
    Event(timestamp=435, event_type="looked_away", duration=8.1, confidence=0.92, metadata={"direction": "left"}),
    Event(timestamp=620, event_type="eyes_closed", duration=2.1, confidence=0.78),
    Event(timestamp=760, event_type="looked_away", duration=5.5, confidence=0.85, metadata={"direction": "right"}),
    Event(timestamp=850, event_type="yawn", duration=4.0, confidence=0.91),
    Event(timestamp=920, event_type="looked_away", duration=12.3, confidence=0.94, metadata={"direction": "left"}),
    Event(timestamp=980, event_type="zoned_out", duration=45.0, confidence=0.72),
    Event(timestamp=1100, event_type="eyes_closed", duration=5.5, confidence=0.95),
    Event(timestamp=1250, event_type="looked_away", duration=6.2, confidence=0.88, metadata={"direction": "right"}),
    Event(timestamp=1380, event_type="yawn", duration=3.8, confidence=0.83),
    Event(timestamp=1500, event_type="looked_away", duration=4.5, confidence=0.80, metadata={"direction": "left"}),
    Event(timestamp=1620, event_type="looked_away", duration=7.0, confidence=0.86, metadata={"direction": "right"}),
    Event(timestamp=1720, event_type="looked_away", duration=3.2, confidence=0.79, metadata={"direction": "left"}),
]

MOCK_ENGAGEMENT_STATES = [
    EngagementSegment(start=0, end=272, state="engaged"),
    EngagementSegment(start=272, end=280, state="disengaged"),
    EngagementSegment(start=280, end=435, state="engaged"),
    EngagementSegment(start=435, end=445, state="disengaged"),
    EngagementSegment(start=445, end=620, state="passive"),
    EngagementSegment(start=620, end=625, state="disengaged"),
    EngagementSegment(start=625, end=720, state="engaged"),
    EngagementSegment(start=720, end=1080, state="disengaged"),
    EngagementSegment(start=1080, end=1250, state="passive"),
    EngagementSegment(start=1250, end=1380, state="engaged"),
    EngagementSegment(start=1380, end=1500, state="passive"),
    EngagementSegment(start=1500, end=1620, state="engaged"),
    EngagementSegment(start=1620, end=1720, state="passive"),
    EngagementSegment(start=1720, end=1800, state="engaged"),
]

MOCK_SESSION = SessionData(
    session_id="eval-001",
    duration=1800,
    events=MOCK_EVENTS,
    engagement_states=MOCK_ENGAGEMENT_STATES,
)


def _make_state(**overrides) -> ScoringState:
    defaults = {"session": MOCK_SESSION, "segment_duration": 300.0}
    defaults.update(overrides)
    return ScoringState(**defaults)


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_fmt_time(self):
        assert _fmt_time(0) == "0:00"
        assert _fmt_time(90) == "1:30"
        assert _fmt_time(1800) == "30:00"

    def test_build_per_second_scores(self):
        scores = _build_per_second_scores(MOCK_ENGAGEMENT_STATES, 1800)
        assert len(scores) == 1800
        # First 272 seconds should be engaged (1.0)
        assert all(s == 1.0 for s in scores[0:272])
        # 720-1080 should be disengaged (0.0)
        assert all(s == 0.0 for s in scores[720:1080])
        # 445-620 should be passive (0.5)
        assert all(s == 0.5 for s in scores[445:620])

    def test_auto_label_first_is_introduction(self):
        scores = [1.0] * 300
        assert _auto_label(0, 5, scores, 0, 300) == "Introduction"

    def test_auto_label_last_is_wrapup(self):
        scores = [1.0] * 1800
        assert _auto_label(4, 5, scores, 1500, 1800) == "Wrap-up"

    def test_auto_label_low_engagement_is_danger_zone(self):
        scores = [0.0] * 600  # all disengaged
        assert _auto_label(2, 5, scores, 0, 600) == "Danger Zone"

    def test_auto_label_normal_segment(self):
        scores = [1.0] * 600
        label = _auto_label(2, 5, scores, 0, 600)
        assert label == "Segment 3"


# ---------------------------------------------------------------------------
# Segmentation tests
# ---------------------------------------------------------------------------

class TestSegmentation:
    def test_produces_sections(self):
        state = _make_state()
        result = segment_lecture(state)
        sections = result["sections"]
        assert len(sections) >= 3, "Should produce at least 3 sections for a 30-min lecture"

    def test_sections_cover_full_duration(self):
        state = _make_state()
        result = segment_lecture(state)
        sections = result["sections"]
        assert sections[0].start == 0
        assert sections[-1].end == 1800

    def test_sections_are_contiguous(self):
        state = _make_state()
        result = segment_lecture(state)
        sections = result["sections"]
        for i in range(len(sections) - 1):
            assert sections[i].end == sections[i + 1].start, \
                f"Gap between section {i} end={sections[i].end} and section {i+1} start={sections[i+1].start}"

    def test_first_section_labeled_introduction(self):
        state = _make_state()
        result = segment_lecture(state)
        assert result["sections"][0].label == "Introduction"

    def test_last_section_labeled_wrapup(self):
        state = _make_state()
        result = segment_lecture(state)
        assert result["sections"][-1].label == "Wrap-up"

    def test_custom_segment_duration(self):
        state = _make_state(segment_duration=600.0)  # 10-min segments
        result = segment_lecture(state)
        sections = result["sections"]
        # With 10-min segments on a 30-min lecture, should have ~3 base segments
        # (plus possible shift-based splits)
        assert len(sections) >= 3

    def test_short_session(self):
        """A 2-minute session should still produce at least one section."""
        short_session = SessionData(
            session_id="short",
            duration=120,
            events=[],
            engagement_states=[EngagementSegment(start=0, end=120, state="engaged")],
        )
        state = _make_state(session=short_session, segment_duration=300.0)
        result = segment_lecture(state)
        assert len(result["sections"]) >= 1

    def test_danger_zone_detected(self):
        """The 720-1080 disengaged block should produce a Danger Zone label."""
        state = _make_state(segment_duration=300.0)
        result = segment_lecture(state)
        labels = [s.label for s in result["sections"]]
        assert "Danger Zone" in labels, f"Expected a Danger Zone, got labels: {labels}"


# ---------------------------------------------------------------------------
# Analytics computation tests
# ---------------------------------------------------------------------------

class TestAnalyticsComputation:
    def _get_scored_sections(self, **overrides) -> list:
        state = _make_state(**overrides)
        segmented = segment_lecture(state)
        state_with_sections = state.model_copy(update=segmented)
        result = compute_section_analytics(state_with_sections)
        return result["sections"]

    def test_engagement_pct_in_range(self):
        sections = self._get_scored_sections()
        for s in sections:
            assert 0 <= s.engagement_pct <= 100, f"Section '{s.label}' has invalid engagement: {s.engagement_pct}"

    def test_state_breakdown_sums_to_100(self):
        sections = self._get_scored_sections()
        for s in sections:
            total = s.state_breakdown.engaged + s.state_breakdown.passive + s.state_breakdown.disengaged
            assert abs(total - 100.0) < 1.0, \
                f"Section '{s.label}' breakdown sums to {total}, expected ~100"

    def test_introduction_has_high_engagement(self):
        """First 5 minutes are mostly engaged in mock data."""
        sections = self._get_scored_sections()
        intro = sections[0]
        assert intro.engagement_pct > 70, \
            f"Introduction should be highly engaged, got {intro.engagement_pct}%"

    def test_danger_zone_has_low_engagement(self):
        """The section covering 720-1080 should have low engagement."""
        sections = self._get_scored_sections()
        danger = [s for s in sections if s.label == "Danger Zone"]
        assert len(danger) > 0, "Should have a danger zone section"
        for d in danger:
            assert d.engagement_pct < 50, \
                f"Danger zone should have low engagement, got {d.engagement_pct}%"

    def test_events_assigned_to_correct_sections(self):
        sections = self._get_scored_sections()
        for s in sections:
            for e in s.events_in_section:
                assert s.start <= e.timestamp < s.end, \
                    f"Event at {e.timestamp} doesn't belong in section {s.label} ({s.start}-{s.end})"

    def test_top_event_populated(self):
        """Sections with events should have a top_event string."""
        sections = self._get_scored_sections()
        sections_with_events = [s for s in sections if s.events_in_section]
        assert len(sections_with_events) > 0, "Should have sections with events"
        for s in sections_with_events:
            assert s.top_event is not None
            assert "(" in s.top_event  # e.g., "looked_away (3 times)"

    def test_section_with_no_events(self):
        """A fully engaged session with no events should still score correctly."""
        clean_session = SessionData(
            session_id="clean",
            duration=600,
            events=[],
            engagement_states=[EngagementSegment(start=0, end=600, state="engaged")],
        )
        state = _make_state(session=clean_session)
        segmented = segment_lecture(state)
        state_with_sections = state.model_copy(update=segmented)
        result = compute_section_analytics(state_with_sections)
        for s in result["sections"]:
            assert s.engagement_pct == 100.0
            assert s.top_event is None
            assert len(s.events_in_section) == 0


# ---------------------------------------------------------------------------
# LangGraph pipeline integration tests (no LLM — nodes 1-2 only)
# ---------------------------------------------------------------------------

class TestPipelineNoLLM:
    """Test the segmentation + analytics nodes run together via LangGraph."""

    def test_two_node_pipeline(self):
        """Build a graph with just segment + analytics (skip AI notes)."""
        builder = StateGraph(ScoringState)
        builder.add_node("segment_lecture", segment_lecture)
        builder.add_node("compute_analytics", compute_section_analytics)
        builder.add_edge(START, "segment_lecture")
        builder.add_edge("segment_lecture", "compute_analytics")
        builder.add_edge("compute_analytics", END)
        graph = builder.compile()

        result = graph.invoke(ScoringState(session=MOCK_SESSION))

        sections = result["sections"]
        assert len(sections) >= 3
        assert all(s.engagement_pct >= 0 for s in sections)
        assert all(
            abs(s.state_breakdown.engaged + s.state_breakdown.passive + s.state_breakdown.disengaged - 100) < 1
            for s in sections
        )

    def test_pydantic_validation_on_input(self):
        """State validation should reject invalid input."""
        with pytest.raises(Exception):
            ScoringState(session="not a session")

    def test_result_converts_to_scoring_result(self):
        """The pipeline output should be convertible to SectionScoringResult."""
        builder = StateGraph(ScoringState)
        builder.add_node("segment_lecture", segment_lecture)
        builder.add_node("compute_analytics", compute_section_analytics)
        builder.add_edge(START, "segment_lecture")
        builder.add_edge("segment_lecture", "compute_analytics")
        builder.add_edge("compute_analytics", END)
        graph = builder.compile()

        result = graph.invoke(ScoringState(session=MOCK_SESSION))

        from app.analytics.models import SectionScoringResult
        output = SectionScoringResult(
            session_id=MOCK_SESSION.session_id,
            overall_summary="",
            sections=result["sections"],
        )
        assert output.session_id == "eval-001"
        assert len(output.sections) >= 3


# ---------------------------------------------------------------------------
# Full pipeline test (requires ANTHROPIC_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set — skipping LLM eval",
)
class TestFullPipelineWithLLM:
    """End-to-end eval that calls Claude for AI note generation."""

    def test_run_section_scoring(self):
        result = run_section_scoring(MOCK_SESSION)

        # Structure checks
        assert result.session_id == "eval-001"
        assert len(result.sections) >= 3
        assert len(result.overall_summary) > 50, \
            f"Overall summary too short: '{result.overall_summary}'"

        # Every section should have an AI note
        for s in result.sections:
            assert len(s.ai_note) > 20, \
                f"Section '{s.label}' has a too-short AI note: '{s.ai_note}'"

        # Quality checks on AI notes
        danger_sections = [s for s in result.sections if s.engagement_pct < 50]
        for s in danger_sections:
            # Danger zone notes should mention something actionable
            note_lower = s.ai_note.lower()
            has_action = any(
                word in note_lower
                for word in ["try", "consider", "suggest", "break", "add", "insert", "use", "could", "recommend"]
            )
            assert has_action, \
                f"Danger zone note for '{s.label}' should be actionable: '{s.ai_note}'"

    def test_overall_summary_mentions_key_findings(self):
        result = run_section_scoring(MOCK_SESSION)
        summary_lower = result.overall_summary.lower()

        # Should reference the danger zone or low engagement period
        mentions_problem = any(
            term in summary_lower
            for term in ["danger", "drop", "lost", "low", "disengaged", "fell", "declined", "struggled"]
        )
        assert mentions_problem, \
            f"Summary should mention the problem area: '{result.overall_summary}'"

    def test_notes_are_lecturer_focused(self):
        """AI notes should address the lecturer, not the student."""
        result = run_section_scoring(MOCK_SESSION)
        for s in result.sections:
            note_lower = s.ai_note.lower()
            # Should not say "you lost focus" (student language)
            # Should say things like "students", "class", "your lecture"
            student_self_ref = "you lost focus" in note_lower or "your focus" in note_lower
            assert not student_self_ref, \
                f"Note for '{s.label}' uses student-focused language: '{s.ai_note}'"
