import { useState, useCallback, useRef } from "react";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

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

function findResponse(message: string): string {
  const lower = message.toLowerCase();
  for (const key of Object.keys(mockResponses)) {
    if (key !== "default" && lower.includes(key)) return mockResponses[key];
  }
  return mockResponses.default;
}

export function useMockChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const cancelRef = useRef(false);

  const sendMessage = useCallback((text: string) => {
    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setIsStreaming(true);
    cancelRef.current = false;

    const fullResponse = findResponse(text);
    let index = 0;

    // Add empty assistant message
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    const interval = setInterval(() => {
      if (cancelRef.current) {
        clearInterval(interval);
        setIsStreaming(false);
        return;
      }
      index++;
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: fullResponse.slice(0, index),
        };
        return updated;
      });
      if (index >= fullResponse.length) {
        clearInterval(interval);
        setIsStreaming(false);
      }
    }, 15);
  }, []);

  return { messages, isStreaming, sendMessage };
}
