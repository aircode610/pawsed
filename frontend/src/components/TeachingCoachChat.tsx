import { useState, useRef, useEffect } from "react";
import { MessageSquare, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { useMockChat } from "@/hooks/use-mock-chat";
import ReactMarkdown from "react-markdown";

const SUGGESTIONS = [
  "Where did I lose the class?",
  "What should I change for next time?",
  "Compare to my last lecture",
  "Give me a 3-point action plan",
];

// Render time references like "minute 12" or "12:00–18:00" as styled spans
function renderWithTimeLinks(text: string) {
  return text.replace(
    /(\b(?:minutes?\s+\d+(?:–\d+)?|\d{1,2}:\d{2}(?:\s*–\s*\d{1,2}:\d{2})?))/g,
    "**$1**"
  );
}

export function TeachingCoachChat() {
  const { messages, isStreaming, sendMessage } = useMockChat();
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const hasMessages = messages.length > 0;

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    setInput("");
    sendMessage(trimmed);
  };

  // Auto-scroll on new content
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="space-y-4">
      <Separator className="bg-border" />

      {/* Header */}
      <div className="flex items-center gap-2">
        <MessageSquare className="h-5 w-5 text-primary" />
        <div>
          <h2 className="text-base font-semibold text-foreground">Teaching Coach</h2>
          <p className="text-xs text-muted-foreground">
            Ask questions about your lecture — your coach has full context of this session
          </p>
        </div>
      </div>

      {/* Suggestion chips */}
      {!hasMessages && (
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => sendMessage(s)}
              className="text-xs px-3 py-1.5 rounded-full border border-border bg-card text-muted-foreground hover:text-foreground hover:border-primary/50 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Chat area */}
      <div
        ref={scrollRef}
        className="rounded-lg border border-border bg-background/50 overflow-y-auto scroll-smooth"
        style={{ maxHeight: 400, minHeight: 200 }}
      >
        {!hasMessages ? (
          <div className="flex flex-col items-center justify-center h-48 text-center gap-2">
            <MessageSquare className="h-10 w-10 text-muted-foreground/40" />
            <p className="text-sm font-medium text-muted-foreground">Your teaching coach is ready</p>
            <p className="text-xs text-muted-foreground/70">
              Ask a question or tap a suggestion above to get started
            </p>
          </div>
        ) : (
          <div className="p-4 space-y-4">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div className="space-y-1 max-w-[85%]">
                  <div
                    className={`px-4 py-3 text-sm leading-relaxed ${
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground rounded-2xl rounded-br-md"
                        : "bg-card border border-border text-foreground rounded-2xl rounded-bl-md"
                    }`}
                  >
                    {msg.role === "assistant" ? (
                      msg.content ? (
                        <div className="prose prose-sm prose-invert max-w-none [&_strong]:text-primary [&_p]:mb-2 [&_ul]:mb-2 [&_ol]:mb-2 [&_li]:mb-0.5">
                          <ReactMarkdown>{renderWithTimeLinks(msg.content)}</ReactMarkdown>
                        </div>
                      ) : (
                        <span className="flex gap-1 items-center h-5">
                          <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:0ms]" />
                          <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:150ms]" />
                          <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:300ms]" />
                        </span>
                      )
                    ) : (
                      msg.content
                    )}
                  </div>
                  {msg.role === "assistant" && msg.content && (
                    <p className="text-[9px] text-muted-foreground/50 pl-1">Powered by Claude</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask about your lecture..."
          disabled={isStreaming}
          className="bg-card border-border"
        />
        <Button
          size="icon"
          onClick={handleSend}
          disabled={isStreaming || !input.trim()}
          className="shrink-0"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
