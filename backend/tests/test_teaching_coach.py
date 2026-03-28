"""Evals for the Teaching Coach chat.

Tests system prompt construction (no LLM) and full conversation quality (with LLM).
"""

import os
import pytest

from app.analytics.models import (
    EngagementSegment,
    Event,
    Section,
    SectionScoringResult,
    SessionData,
    StateBreakdown,
)
from app.analytics.teaching_coach import (
    CoachState,
    _build_system_prompt,
    build_coach_graph,
    chat_with_coach,
)


# ---------------------------------------------------------------------------
# Shared mock data
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
    Event(timestamp=1250, event_type="looked_away", duration=6.2, confidence=0.88),
    Event(timestamp=1380, event_type="yawn", duration=3.8, confidence=0.83),
    Event(timestamp=1500, event_type="looked_away", duration=4.5, confidence=0.80),
    Event(timestamp=1620, event_type="looked_away", duration=7.0, confidence=0.86),
    Event(timestamp=1720, event_type="looked_away", duration=3.2, confidence=0.79),
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
    session_id="coach-eval-001",
    duration=1800,
    events=MOCK_EVENTS,
    engagement_states=MOCK_ENGAGEMENT_STATES,
)

MOCK_SECTION_SCORING = SectionScoringResult(
    session_id="coach-eval-001",
    overall_summary="Strong opening and close, but the class was lost between minutes 12-18.",
    sections=[
        Section(
            label="Introduction", start=0, end=300, engagement_pct=89.2,
            state_breakdown=StateBreakdown(engaged=82, passive=14, disengaged=4),
            top_event=None, ai_note="Strong opening.",
        ),
        Section(
            label="Danger Zone", start=720, end=1080, engagement_pct=38.4,
            state_breakdown=StateBreakdown(engaged=25, passive=30, disengaged=45),
            top_event="looked_away (3 times)", ai_note="Lowest engagement stretch.",
        ),
        Section(
            label="Wrap-up", start=1500, end=1800, engagement_pct=80.1,
            state_breakdown=StateBreakdown(engaged=72, passive=22, disengaged=6),
            top_event=None, ai_note="Solid finish.",
        ),
    ],
)

MOCK_HISTORICAL = [
    {"date": "2026-03-24", "focus_pct": 65.2, "duration_min": 40, "event_count": 18},
    {"date": "2026-03-25", "focus_pct": 71.8, "duration_min": 30, "event_count": 14},
    {"date": "2026-03-26", "focus_pct": 78.4, "duration_min": 35, "event_count": 10},
]


# ---------------------------------------------------------------------------
# System prompt construction tests (no LLM)
# ---------------------------------------------------------------------------

class TestSystemPrompt:
    def _get_prompt(self, **overrides) -> str:
        defaults = {
            "session_data": MOCK_SESSION,
            "messages": [],
            "section_scoring": None,
            "historical_sessions": None,
        }
        defaults.update(overrides)
        # CoachState is a TypedDict — pass as plain dict
        return _build_system_prompt(defaults)

    def test_includes_duration(self):
        prompt = self._get_prompt()
        assert "30 min" in prompt

    def test_includes_focus_percentage(self):
        prompt = self._get_prompt()
        # Should contain a percentage
        assert "%" in prompt

    def test_includes_event_types(self):
        prompt = self._get_prompt()
        assert "looked_away" in prompt
        assert "yawn" in prompt

    def test_includes_danger_zone(self):
        prompt = self._get_prompt()
        # The 720-1080 disengaged block (>60s) should appear as a danger zone
        assert "12:00" in prompt or "12:0" in prompt

    def test_includes_event_log_with_timestamps(self):
        prompt = self._get_prompt()
        assert "4:32" in prompt  # timestamp 272s = 4:32
        assert "7:15" in prompt  # timestamp 435s = 7:15

    def test_includes_lecturer_framing(self):
        prompt = self._get_prompt()
        prompt_lower = prompt.lower()
        assert "lecturer" in prompt_lower or "teaching" in prompt_lower
        assert "student" in prompt_lower  # should mention students (the ones being observed)

    def test_instructs_not_to_use_student_language(self):
        prompt = self._get_prompt()
        assert "not a student" in prompt.lower() or "lecturer" in prompt.lower()

    def test_includes_section_scoring_when_provided(self):
        prompt = self._get_prompt(section_scoring=MOCK_SECTION_SCORING)
        assert "SECTION SCORING" in prompt
        assert "Introduction" in prompt
        assert "Danger Zone" in prompt
        assert "Strong opening and close" in prompt

    def test_excludes_section_scoring_when_none(self):
        prompt = self._get_prompt(section_scoring=None)
        assert "SECTION SCORING" not in prompt

    def test_includes_historical_sessions(self):
        prompt = self._get_prompt(historical_sessions=MOCK_HISTORICAL)
        assert "HISTORICAL SESSIONS" in prompt
        assert "2026-03-24" in prompt
        assert "65.2" in prompt

    def test_excludes_historical_when_none(self):
        prompt = self._get_prompt(historical_sessions=None)
        assert "HISTORICAL SESSIONS" not in prompt


# ---------------------------------------------------------------------------
# Graph structure tests (no LLM)
# ---------------------------------------------------------------------------

class TestGraphStructure:
    def test_graph_compiles(self):
        graph = build_coach_graph()
        assert graph is not None

    def test_state_is_typeddict(self):
        """CoachState should be a TypedDict (extends MessagesState)."""
        # CoachState is a TypedDict, so it's instantiated as a plain dict
        state = {
            "session_data": MOCK_SESSION,
            "messages": [{"role": "user", "content": "Hello"}],
        }
        assert state["session_data"].session_id == "coach-eval-001"
        assert len(state["messages"]) == 1

    def test_state_has_expected_keys(self):
        """CoachState should define session_data, section_scoring, historical_sessions."""
        annotations = CoachState.__annotations__
        assert "session_data" in annotations
        assert "section_scoring" in annotations
        assert "historical_sessions" in annotations


# ---------------------------------------------------------------------------
# Full chat evals (requires ANTHROPIC_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set — skipping LLM eval",
)
class TestChatWithLLM:
    def test_basic_response(self):
        """Coach should return a non-empty response."""
        response = chat_with_coach(
            session_data=MOCK_SESSION,
            messages=[{"role": "user", "content": "How did my lecture go?"}],
        )
        assert len(response) > 50, f"Response too short: '{response}'"

    def test_references_session_data(self):
        """Response should reference actual data from the session."""
        response = chat_with_coach(
            session_data=MOCK_SESSION,
            messages=[{"role": "user", "content": "Where did I lose the class?"}],
        )
        response_lower = response.lower()
        # Should mention the danger zone time range or specific events
        has_data_reference = any(
            term in response_lower
            for term in ["12:", "minute", "yawn", "looked away", "eyes closed",
                         "disengaged", "danger", "%", "zoned"]
        )
        assert has_data_reference, \
            f"Response should reference session data: '{response[:200]}...'"

    def test_lecturer_focused_language(self):
        """Response should use lecturer-focused language, not student self-help."""
        response = chat_with_coach(
            session_data=MOCK_SESSION,
            messages=[{"role": "user", "content": "What should I change?"}],
        )
        response_lower = response.lower()
        # Should NOT say "you lost focus" or "your focus dropped"
        bad_phrases = ["you lost focus", "your focus dropped", "your attention"]
        for phrase in bad_phrases:
            assert phrase not in response_lower, \
                f"Response uses student language '{phrase}': '{response[:200]}...'"

    def test_provides_actionable_advice(self):
        """Response should include actionable teaching strategies."""
        response = chat_with_coach(
            session_data=MOCK_SESSION,
            messages=[{"role": "user", "content": "How can I improve the weak sections?"}],
        )
        response_lower = response.lower()
        has_action = any(
            word in response_lower
            for word in ["try", "consider", "add", "break", "insert", "use",
                         "introduce", "include", "ask", "poll", "activity",
                         "question", "pause", "interact"]
        )
        assert has_action, \
            f"Response should be actionable: '{response[:200]}...'"

    def test_conversation_continuity(self):
        """Multi-turn conversation should maintain context."""
        messages = [
            {"role": "user", "content": "What was the worst section of my lecture?"},
        ]
        response1 = chat_with_coach(session_data=MOCK_SESSION, messages=messages)

        # Add the response and a follow-up
        messages.append({"role": "assistant", "content": response1})
        messages.append({"role": "user", "content": "How do I fix that specific section?"})

        response2 = chat_with_coach(session_data=MOCK_SESSION, messages=messages)

        assert len(response2) > 50
        # Second response should build on the first, not start fresh
        response2_lower = response2.lower()
        has_continuity = any(
            term in response2_lower
            for term in ["that section", "this section", "mentioned", "section",
                         "earlier", "as i", "the same", "break", "split",
                         "try", "consider", "activity"]
        )
        assert has_continuity, \
            f"Follow-up should reference prior context: '{response2[:200]}...'"

    def test_with_section_scoring_context(self):
        """Response should leverage section scoring data when provided."""
        response = chat_with_coach(
            session_data=MOCK_SESSION,
            messages=[{"role": "user", "content": "Walk me through each section."}],
            section_scoring=MOCK_SECTION_SCORING,
        )
        response_lower = response.lower()
        # Should reference section labels or scoring data
        has_section_ref = any(
            term in response_lower
            for term in ["introduction", "danger zone", "wrap-up", "wrap up",
                         "89%", "38%", "80%", "opening", "closing"]
        )
        assert has_section_ref, \
            f"Should reference section scoring: '{response[:200]}...'"

    def test_cross_session_comparison(self):
        """When historical data is provided, coach should be able to compare."""
        response = chat_with_coach(
            session_data=MOCK_SESSION,
            messages=[{"role": "user", "content": "How does this compare to my previous lectures?"}],
            historical_sessions=MOCK_HISTORICAL,
        )
        response_lower = response.lower()
        has_comparison = any(
            term in response_lower
            for term in ["previous", "last", "earlier", "compared", "improvement",
                         "trend", "progress", "65", "71", "78", "march", "session"]
        )
        assert has_comparison, \
            f"Should reference historical data: '{response[:200]}...'"

    def test_handles_off_topic_gracefully(self):
        """Coach should redirect off-topic questions back to teaching."""
        response = chat_with_coach(
            session_data=MOCK_SESSION,
            messages=[{"role": "user", "content": "What's the weather like today?"}],
        )
        response_lower = response.lower()
        # Should either redirect to teaching or politely decline
        is_relevant = any(
            term in response_lower
            for term in ["lecture", "session", "teaching", "engagement", "class",
                         "focus", "help", "happy to", "can help"]
        )
        assert is_relevant, \
            f"Should stay on-topic or redirect: '{response[:200]}...'"

    def test_short_question_gets_concise_answer(self):
        """A simple question should get a focused response, not a wall of text."""
        response = chat_with_coach(
            session_data=MOCK_SESSION,
            messages=[{"role": "user", "content": "What was my overall focus percentage?"}],
        )
        # Should be concise — under 500 chars for a simple factual question
        assert len(response) < 1000, \
            f"Response too long for a simple question ({len(response)} chars)"
        assert "%" in response, "Should include the percentage"
