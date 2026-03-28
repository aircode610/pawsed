# Step 8b: Teaching Coach Chat

> Paste this into Lovable **after Step 8 is done**. This adds a chat interface below the section scoring on the same page. **Do not modify the section scoring cards or any other pages.**

---

Add a conversational teaching coach chat interface to the bottom of the AI Insights page at `/session/:id/insights`. This lets the lecturer ask follow-up questions about their lecture data. The chat sits below the section scoring cards.

## Mock behavior

Create a `useMockChat` hook in `hooks/use-mock-chat.ts` that simulates a streaming AI response:

```typescript
const mockResponses: Record<string, string> = {
  "where did i lose the class":
    "The biggest drop happened between minutes 12–18. Engagement fell from 72% to 38% — nearly half the class was disengaged by minute 15. There were 2 yawns, a 45-second zone-out, and 4 look-away events concentrated in that window.\n\nBefore that, you had a steady decline starting around minute 7, but students were still in 'passive' territory — drifting but recoverable. The hard cliff came at minute 12.",

  "what should i change for next time":
    "Three concrete options:\n\n**1. Insert a 90-second activity at minute 12.** Right before the danger zone. A think-pair-share question, a quick poll, or even 'turn to your neighbor and explain X.' This resets the attention clock.\n\n**2. Split the theory block.** If minutes 12–18 were all conceptual, try interleaving a worked example or short demo at minute 14. Your class re-engaged strongly after the danger zone — if that was a demo, move it earlier.\n\n**3. Shorten the block.** Research shows attention drops sharply after 10–15 minutes of passive listening. Your class tracked this almost exactly — strong for 12 minutes, then a cliff.",

  "compare to my last lecture":
    "Last Tuesday (Session sess-002) you scored 71.8% overall — almost identical to today's 72.5%. But the pattern was different:\n\n• Tuesday had a more gradual decline (no single danger zone)\n• Today had a sharper crash but a better recovery\n• Tuesday's most common issue was 'looked away' (distributed evenly)\n• Today's issue was concentrated in one bad 6-minute stretch\n\nThis suggests Tuesday's content was more uniformly paced, while today had a specific problem section. Today is actually easier to fix — you just need to address that one block.",

  default:
    "Based on your session data, I can see a few patterns worth discussing. Your overall engagement was 72.5%, with the main drop happening between minutes 12–18. The class responded well to your opening and closing sections. Would you like me to dig into a specific part of the lecture, or suggest strategies for the weaker sections?",
};
```

The hook should:
- Accept a message string
- Find the best matching mock response (check if the message includes any of the keys, otherwise use `default`)
- Return the response **character by character** with a 15ms delay to simulate streaming
- Track conversation history as an array of `{ role: "user" | "assistant", content: string }`

## Layout

### Section divider
- A subtle horizontal line separating the section cards from the chat
- Heading: "Teaching Coach" with a Lucide `MessageSquare` icon
- Subtext: "Ask questions about your lecture — your coach has full context of this session"

### Suggested questions (chips)
- Show 4 clickable pill/chip buttons above the chat:
  - "Where did I lose the class?"
  - "What should I change for next time?"
  - "Compare to my last lecture"
  - "Give me a 3-point action plan"
- Clicking a chip sends that text as a message (same as typing and hitting send)
- Chips disappear after the first message is sent (they're just conversation starters)

### Chat messages area
- Scrollable area, max height ~400px (scrolls when conversation gets long)
- **User messages:** aligned right, indigo background, white text, rounded bubble with rounded bottom-right corner slightly less rounded (chat bubble style)
- **Assistant messages:** aligned left, surface/card background, regular text color, rounded bubble
- Assistant messages should support **markdown rendering** — bold, bullet lists, numbered lists, paragraphs
- When the assistant is "typing" (streaming), show an animated 3-dot indicator that transitions into the actual text as characters arrive
- Each assistant message has a small "Powered by Claude" label in muted text below it

### Input bar
- Fixed at the bottom of the chat section (not the page)
- Text input with placeholder: "Ask about your lecture..."
- Send button on the right (Lucide `Send` icon, indigo)
- Send on Enter key press
- Disable the input and show a subtle loading state while the assistant is responding
- Clear the input after sending

### Empty state
- Before any messages are sent, the chat area shows a centered message:
  - Lucide `MessageSquare` icon (large, muted)
  - "Your teaching coach is ready"
  - "Ask a question or tap a suggestion above to get started"

## Interactions
- Sending a message adds it to the chat, then triggers the mock streaming response
- The chat auto-scrolls to the bottom when new content arrives
- The suggested question chips are only visible when there are zero messages
- If a message contains a time reference like "minute 12" or "12:00–18:00", render it as a clickable link styled in indigo (for now, clicking does nothing — we'll wire it to the timeline later)

## Style
- The chat should feel like a real messaging interface — not a form
- Generous padding inside message bubbles
- Smooth scroll behavior
- The streaming text effect should feel natural — not jarring
- Keep the overall page scrollable: section cards at top, chat at bottom
- The chat section should feel integrated with the rest of the page, not like a separate widget bolted on
- Subtle rounded corners on the chat container matching the card styling elsewhere
