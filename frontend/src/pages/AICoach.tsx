import { useState, useEffect, useCallback } from "react";
import { Bot, RefreshCw } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { SessionSubNav } from "@/components/SessionSubNav";
import { mockInsights } from "@/lib/mock-data";

const CATEGORY_STYLE: Record<string, { border: string; badge: string; label: string }> = {
  timing:        { border: "border-l-blue-500",   badge: "bg-blue-500/15 text-blue-400",   label: "Timing" },
  technique:     { border: "border-l-purple-500", badge: "bg-purple-500/15 text-purple-400", label: "Technique" },
  encouragement: { border: "border-l-engage-engaged", badge: "bg-engage-engaged/15 text-engage-engaged", label: "Encouragement" },
};

const AICoachPage = () => {
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 1500);
    return () => clearTimeout(t);
  }, []);

  const handleRegenerate = useCallback(() => {
    setRegenerating(true);
    setTimeout(() => setRegenerating(false), 2000);
  }, []);

  const showSkeleton = loading || regenerating;

  return (
    <div className="space-y-4">
      <SessionSubNav />

      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
          <Bot className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-foreground">Your AI Study Coach</h1>
          <p className="text-sm text-muted-foreground">Personalized recommendations based on your session data</p>
        </div>
      </div>

      {/* Cards */}
      {showSkeleton ? (
        <div className="space-y-4">
          <p className="text-xs text-muted-foreground animate-pulse text-center">
            Your AI coach is analyzing your session...
          </p>
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32 rounded-lg" />
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {mockInsights.recommendations.map((rec, i) => {
            const style = CATEGORY_STYLE[rec.category] || CATEGORY_STYLE.technique;
            return (
              <Card
                key={i}
                className={`bg-card border-border border-l-[3px] ${style.border} p-5 space-y-2`}
              >
                <span className={`inline-block text-[10px] font-semibold uppercase tracking-wider rounded-full px-2 py-0.5 ${style.badge}`}>
                  {style.label}
                </span>
                <h3 className="text-base font-semibold text-foreground">{rec.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{rec.body}</p>
              </Card>
            );
          })}
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-col items-center gap-3 pt-2">
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={handleRegenerate}
          disabled={showSkeleton}
        >
          <RefreshCw className={`h-4 w-4 ${regenerating ? "animate-spin" : ""}`} />
          Regenerate Suggestions
        </Button>
        <p className="text-[10px] text-muted-foreground">Powered by Claude AI</p>
      </div>
    </div>
  );
};

export default AICoachPage;
