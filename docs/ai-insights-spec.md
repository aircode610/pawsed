# AI Insights Specification

## Overview

The AI insights layer transforms raw engagement data into actionable teaching intelligence. Two core features: **Lecture Section Scoring** (automated analysis) and **Conversational Teaching Coach** (interactive Q&A with lecture data).

Both features target the **lecturer** — language, recommendations, and framing are all from the perspective of "how can I improve my teaching."

---

## Feature 1: Lecture Section Scoring

### What It Does

Automatically breaks a lecture into time segments and scores each one. The lecturer sees at a glance which parts of their lecture worked and which didn't — with specific, pedagogy-informed advice for each segment.

### Example Output

```json
{
  "session_id": "abc123",
  "sections": [
    {
      "label": "Introduction",
      "start": 0,
      "end": 300,
      "engagement_pct": 89.2,
      "state_breakdown": { "engaged": 82, "passive": 14, "disengaged": 4 },
      "top_event": null,
      "ai_note": "Strong opening — students were attentive. Whatever you did here (greeting, agenda, hook question), keep doing it."
    },
    {
      "label": "Segment 2",
      "start": 300,
      "end": 720,
      "engagement_pct": 71.5,
      "state_breakdown": { "engaged": 60, "passive": 28, "disengaged": 12 },
      "top_event": "looked_away (4 times)",
      "ai_note": "Gradual drift starting around minute 7. Students were passive but not fully disengaged — a mid-point check-in question or quick poll could reset attention here."
    },
    {
      "label": "Danger Zone",
      "start": 720,
      "end": 1080,
      "engagement_pct": 38.4,
      "state_breakdown": { "engaged": 25, "passive": 30, "disengaged": 45 },
      "top_event": "zoned_out (45s), yawn (2 times)",
      "ai_note": "This was the lowest-engagement section. 45% of the time was spent disengaged. This often happens during extended theory without interaction. Consider breaking this into two shorter blocks with an active learning exercise (think-pair-share, quick problem) in between."
    },
    {
      "label": "Recovery",
      "start": 1080,
      "end": 1500,
      "engagement_pct": 74.8,
      "state_breakdown": { "engaged": 65, "passive": 25, "disengaged": 10 },
      "top_event": "looked_away (3 times)",
      "ai_note": "Engagement recovered here — the class re-engaged. If this section involved a demo, example, or change of pace, that's likely what worked. Try to bring that energy earlier next time."
    },
    {
      "label": "Wrap-up",
      "start": 1500,
      "end": 1800,
      "engagement_pct": 80.1,
      "state_breakdown": { "engaged": 72, "passive": 22, "disengaged": 6 },
      "top_event": null,
      "ai_note": "Solid finish. Students were mostly attentive through the closing."
    }
  ],
  "overall_summary": "Your lecture had a strong open and close, but lost the class between minutes 12–18. That 6-minute danger zone brought your overall score down from what could have been 80%+ to 72.5%. The fix is structural — break that middle section with an interactive moment."
}
```

### How It Works

**Step 1: Segment the lecture**
- Default: split into 5-minute segments
- Smarter: detect natural breakpoints where engagement shifts significantly (>15% change sustained for >30s) and use those as segment boundaries
- Label segments automatically: "Introduction" (first segment), "Wrap-up" (last segment), "Danger Zone" (any segment below 50% engagement), generic labels for the rest

**Step 2: Compute per-segment analytics**
For each segment, calculate from the existing event log and engagement states:
- Engagement percentage (time in engaged state / segment duration)
- State breakdown (% time in each of the three states)
- Most frequent distraction event type
- Event count and notable events (long duration events, clusters)

**Step 3: Generate AI notes per segment**
Send the segment data to Claude with a teaching-focused prompt:

```
You are a pedagogy expert analyzing a lecture for the instructor.
For each lecture segment, provide a 1-2 sentence observation and
one specific, actionable teaching suggestion.

Use evidence-based teaching strategies: active learning breaks,
think-pair-share, polling, worked examples, scaffolding, varied
modality. Reference the actual data (timestamps, percentages,
event types).

Tone: supportive coach, not critical. The goal is to help the
lecturer improve, not to judge them.
```

**Step 4: Generate overall summary**
One paragraph that tells the story of the lecture: what worked, what didn't, and the single most impactful change to make.

### API

**Endpoint:** `GET /session/{id}/insights/sections`

**Response:** The JSON structure shown above.

**Implementation notes:**
- Segmentation + analytics computation happens in Python (no LLM needed)
- Only the AI note generation requires a Claude API call
- Send all segments in a single API call to Claude for consistency
- Cache the result — don't regenerate on every request
- Use `claude-sonnet-4-6` for speed

### Frontend

- Render as a vertical list of section cards
- Each card shows: time range, engagement percentage (color-coded), state breakdown as a tiny horizontal stacked bar, the AI note
- Danger zone cards have a red left border accent
- The overall summary sits at the top in a highlighted card
- Clicking a section card could navigate to that time range in the timeline view

---

## Feature 2: Conversational Teaching Coach

### What It Does

The lecturer can chat with an AI coach that has full context of their session data. Instead of reading static recommendations, they ask questions and get targeted answers. This is the "wow factor" for the demo.

### Example Conversation

```
Lecturer: At what point did I lose the class?

Coach: The biggest drop happened between minutes 12–18. Engagement fell
from 72% to 38% — nearly half the class was disengaged by minute 15.
There were 2 yawns, a 45-second zone-out, and 4 look-away events
concentrated in that window.

Before that, you had a steady decline starting around minute 7, but
students were still in "passive" territory — drifting but recoverable.

Lecturer: What was I probably doing wrong in that section?

Coach: Based on the pattern — steady passive drift into hard
disengagement with yawning — this is classic "lecture fatigue." It
usually happens during extended one-directional talking without
interaction, especially with abstract or theory-heavy content.

The key signal is the 45-second zone-out at minute 16:20. That's not
a momentary distraction — that's a student who mentally checked out.
When you see that alongside yawning, the issue is usually pacing, not
content.

Lecturer: How do I fix it for next time?

Coach: Three concrete options:

1. **Insert a 90-second activity at minute 12.** Right before the
   danger zone. A think-pair-share question, a quick poll, or even
   "turn to your neighbor and explain X." This resets the attention
   clock.

2. **Split the theory block.** If minutes 12-18 are all conceptual,
   try interleaving a worked example or short demo at minute 14.
   Your class re-engaged strongly after the danger zone — if that
   was a demo or example, move it earlier.

3. **Shorten the block.** Research shows attention drops sharply
   after 10-15 minutes of passive listening. Your class tracked
   this almost exactly — strong for 12 minutes, then a cliff.

Lecturer: Compare this to last Tuesday's lecture.

Coach: Last Tuesday (Session sess-002) you scored 71.8% overall —
almost identical to today's 72.5%. But the pattern was different:

- Tuesday had a more gradual decline (no single danger zone)
- Today had a sharper crash but better recovery
- Tuesday's most common issue was "looked away" (distributed)
- Today's issue was concentrated in one bad stretch

This suggests Tuesday's content was more uniformly dry, while today
had a specific problem section. Today is actually easier to fix —
you just need to address that one 6-minute block.
```

### How It Works

**System prompt structure:**

```
You are a teaching coach for university lecturers. You have access
to engagement analytics from a lecture session recorded via webcam.

Your role:
- Help the lecturer understand WHERE and WHY they lost student
  attention
- Provide specific, evidence-based teaching strategies to improve
- Reference actual data (timestamps, percentages, events) in your
  answers — don't be vague
- Be supportive and constructive — you're a coach, not a critic
- When comparing sessions, highlight both improvements and areas
  to work on

Tone: warm, direct, practical. Like a experienced colleague giving
feedback over coffee. Avoid academic jargon about pedagogy — use
plain language.

SESSION DATA:
{full session JSON — events, analytics, engagement_states, sections}

HISTORICAL DATA (if available):
{summary of past sessions — dates, scores, key patterns}
```

**Conversation flow:**
- Each message from the lecturer is sent to Claude along with the full system prompt + conversation history
- The session data is injected once in the system prompt, not repeated per message
- Stream the response token-by-token for a live typing effect
- Historical session data is included as a summary (not full events) to stay within context limits

### API

**Endpoint:** `POST /session/{id}/insights/chat`

**Request:**
```json
{
  "messages": [
    { "role": "user", "content": "At what point did I lose the class?" }
  ]
}
```

**Response (streamed):**
```json
{
  "role": "assistant",
  "content": "The biggest drop happened between minutes 12–18..."
}
```

Or via **WebSocket** for streaming: `WS /session/{id}/insights/chat`
- Client sends: `{ "content": "At what point did I lose the class?" }`
- Server streams back tokens as they arrive from Claude

**Implementation notes:**
- Use `claude-sonnet-4-6` for fast responses
- Stream the response (Anthropic SDK supports this natively)
- Keep conversation history on the server (keyed by session ID) or pass it from the client
- Limit context: include full event log for the current session, but only summary stats for historical sessions
- Set `max_tokens` to ~500 per response to keep answers focused

### Frontend

- Chat interface below or beside the section scoring cards
- Message bubbles: user on the right (indigo), coach on the left (surface color)
- Typing indicator while streaming (animated dots that transition into actual text)
- Suggested starter questions as clickable chips above the input:
  - "Where did I lose the class?"
  - "What should I change for next time?"
  - "Compare to my last lecture"
  - "Give me a 3-point action plan"
- Input bar at the bottom with send button
- Messages can reference timestamps — these should be clickable and jump to the timeline view
- Small "Powered by Claude" label at the bottom

---

## How They Work Together

The section scoring is the **starting point** — the lecturer sees the automated breakdown when they open the insights page. The conversational coach is the **follow-up** — they can dig deeper into anything the section scoring surfaced.

### Page Layout (`/session/:id/insights`)

```
┌─────────────────────────────────────────────┐
│  Session Sub-Nav (Timeline | Analytics | ... │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─ Overall Summary Card ─────────────────┐ │
│  │ "Your lecture had a strong open..."     │ │
│  └────────────────────────────────────────┘ │
│                                             │
│  ┌─ Section Cards (scrollable) ───────────┐ │
│  │ Introduction    89% ████████░░ ...     │ │
│  │ Segment 2       71% ██████░░░░ ...     │ │
│  │ Danger Zone     38% ███░░░░░░░ ...     │ │
│  │ Recovery         74% ██████░░░░ ...     │ │
│  │ Wrap-up         80% ███████░░░ ...     │ │
│  └────────────────────────────────────────┘ │
│                                             │
│  ┌─ Teaching Coach Chat ──────────────────┐ │
│  │                                        │ │
│  │ [Where did I lose the class?]          │ │
│  │ [What should I change?]  [Compare]     │ │
│  │                                        │ │
│  │ ┌────────────────────────────────────┐ │ │
│  │ │ Ask your teaching coach...    Send │ │ │
│  │ └────────────────────────────────────┘ │ │
│  └────────────────────────────────────────┘ │
│                                             │
└─────────────────────────────────────────────┘
```

---

## Implementation Priority

| Task | Effort | Demo Impact |
|------|--------|-------------|
| Segment computation (Python, no LLM) | Small | Medium |
| AI notes per segment (single Claude call) | Small | High |
| Section scoring frontend cards | Medium | High |
| Chat backend (Claude streaming) | Medium | Very High |
| Chat frontend (message UI + streaming) | Medium | Very High |
| Cross-session comparison in chat | Small | Medium |
| Clickable timestamps in chat | Small | Nice polish |

**Suggested order:**
1. Segment computation + AI notes + section cards (get something visible fast)
2. Chat backend with streaming
3. Chat frontend
4. Cross-session context + polish
