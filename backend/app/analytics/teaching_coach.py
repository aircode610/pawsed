"""Teaching Coach Chat — conversational AI for lecturers.

Uses LangGraph MessagesState for conversation management.
Injects session engagement data as system context so the lecturer
can ask questions about their lecture and get data-backed advice.
"""

from collections import Counter

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage
from langchain_core.messages.utils import trim_messages, count_tokens_approximately
from langgraph.graph import StateGraph, START, END, MessagesState

from app.analytics.prompts import TEACHING_COACH_SYSTEM
from app.models.analytics import (
    EngagementSegment,
    Event,
    SectionScoringResult,
    SessionData,
)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class CoachState(MessagesState):
    """Chat state extending MessagesState with session context.

    The `messages` field is managed by LangGraph's built-in add_messages reducer —
    returning {"messages": [response]} appends rather than replaces.
    """

    session_data: SessionData
    section_scoring: SectionScoringResult | None = None
    # Optional: summaries of other sessions for cross-session comparison
    historical_sessions: list[dict] | None = None


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

def _build_system_prompt(state: dict) -> str:
    """Build a system prompt with full session context.

    Note: state is a dict (TypedDict) because MessagesState extends TypedDict,
    not Pydantic BaseModel. All access must use dict syntax.
    """
    session: SessionData = state["session_data"]
    duration_min = session.duration / 60

    # Engagement state summary
    time_in_state = {"engaged": 0.0, "passive": 0.0, "disengaged": 0.0}
    for seg in session.engagement_states:
        time_in_state[seg.state] += seg.end - seg.start
    total = sum(time_in_state.values()) or 1.0
    focus_pct = round((time_in_state["engaged"] + time_in_state["passive"] * 0.5) / total * 100, 1)

    # Event summary
    event_counts = Counter(e.event_type for e in session.events)
    events_desc = ", ".join(f"{t}: {c}" for t, c in event_counts.most_common())

    # Danger zones (segments with >60s of disengaged)
    danger_zones = []
    for seg in session.engagement_states:
        if seg.state == "disengaged" and (seg.end - seg.start) > 60:
            danger_zones.append(f"{_fmt_time(seg.start)}–{_fmt_time(seg.end)}")

    # Section scoring summary (if available)
    sections_text = ""
    section_scoring = state.get("section_scoring")
    if section_scoring:
        sections_text = "\n\nSECTION SCORING:\n"
        for s in section_scoring.sections:
            sections_text += (
                f"- {s.label} ({_fmt_time(s.start)}–{_fmt_time(s.end)}): "
                f"{s.engagement_pct:.0f}% engagement"
            )
            if s.top_event:
                sections_text += f", top event: {s.top_event}"
            sections_text += "\n"
        if section_scoring.overall_summary:
            sections_text += f"\nOverall: {section_scoring.overall_summary}\n"

    # Historical sessions summary
    history_text = ""
    historical_sessions = state.get("historical_sessions")
    if historical_sessions:
        history_text = "\n\nHISTORICAL SESSIONS:\n"
        for h in historical_sessions:
            history_text += (
                f"- {h.get('date', 'Unknown date')}: "
                f"{h.get('focus_pct', 'N/A')}% focus, "
                f"{h.get('duration_min', 'N/A')} min, "
                f"{h.get('event_count', 'N/A')} events\n"
            )

    # Detailed event log (timestamps + types)
    event_log = "\n\nEVENT LOG:\n"
    for e in session.events:
        event_log += f"- {_fmt_time(e.timestamp)}: {e.event_type} ({e.duration:.1f}s, confidence {e.confidence:.0%})"
        if e.metadata:
            event_log += f" — {e.metadata}"
        event_log += "\n"

    return TEACHING_COACH_SYSTEM.format(
        duration_min=duration_min,
        focus_pct=focus_pct,
        time_engaged=time_in_state["engaged"],
        time_passive=time_in_state["passive"],
        time_disengaged=time_in_state["disengaged"],
        events_desc=events_desc,
        danger_zones=", ".join(danger_zones) if danger_zones else "none",
        sections_text=sections_text,
        history_text=history_text,
        event_log=event_log,
    )


# ---------------------------------------------------------------------------
# Chat node
# ---------------------------------------------------------------------------

def coach_respond(state: CoachState) -> dict:
    """Process the conversation and generate a coaching response."""
    model = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=1000)

    system_msg = SystemMessage(_build_system_prompt(state))

    # Trim conversation history to stay within context limits
    trimmed = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=4096,
        start_on="human",
    )

    response = model.invoke([system_msg] + trimmed)

    return {"messages": [response]}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_coach_graph():
    """Build and compile the teaching coach chat graph."""
    builder = StateGraph(CoachState)
    builder.add_node("coach_respond", coach_respond)
    builder.add_edge(START, "coach_respond")
    builder.add_edge("coach_respond", END)
    return builder.compile()


def chat_with_coach(
    session_data: SessionData,
    messages: list[dict],
    section_scoring: SectionScoringResult | None = None,
    historical_sessions: list[dict] | None = None,
) -> str:
    """Send a message to the teaching coach and get a response.

    Args:
        session_data: Current session engagement data.
        messages: Conversation history as list of {"role": "user"|"assistant", "content": str}.
        section_scoring: Optional section scoring result for richer context.
        historical_sessions: Optional list of past session summaries.

    Returns:
        The assistant's response text.
    """
    graph = build_coach_graph()

    result = graph.invoke({
        "session_data": session_data,
        "messages": messages,
        "section_scoring": section_scoring,
        "historical_sessions": historical_sessions,
    })

    # The last message in the list is the assistant's response
    return result["messages"][-1].content


async def stream_coach_response(
    session_data: SessionData,
    messages: list[dict],
    section_scoring: SectionScoringResult | None = None,
    historical_sessions: list[dict] | None = None,
):
    """Stream a teaching coach response token by token.

    Yields string chunks as they arrive from Claude.
    """
    graph = build_coach_graph()

    async for chunk in graph.astream(
        {
            "session_data": session_data,
            "messages": messages,
            "section_scoring": section_scoring,
            "historical_sessions": historical_sessions,
        },
        stream_mode="messages",
        version="v2",
    ):
        if chunk["type"] == "messages":
            message_chunk, metadata = chunk["data"]
            if message_chunk.content:
                yield message_chunk.content


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_time(seconds: float) -> str:
    """Format seconds as mm:ss."""
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"
