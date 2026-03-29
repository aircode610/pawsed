import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Sparkles, AlertTriangle, Eye, ChevronRight, AlertCircle } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { SessionSubNav } from "@/components/SessionSubNav";
import { TeachingCoachChat } from "@/components/TeachingCoachChat";
import { useSessionData } from "@/hooks/use-session-data";
import { getSectionScoring } from "@/lib/api";
import type { SectionScoringData } from "@/lib/types";

const fmt = (s: number) => {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, "0")}`;
};

const scoreColor = (pct: number) => {
  if (pct >= 70) return "text-engage-engaged";
  if (pct >= 50) return "text-engage-passive";
  return "text-engage-disengaged";
};

const AICoachPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: session } = useSessionData(id);
  const [scoring, setScoring] = useState<SectionScoringData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!id) return;
    getSectionScoring(id)
      .then((data) => setScoring(data))
      .catch(() => setError(true))
      .finally(() => setIsLoading(false));
  }, [id]);

  if (error) {
    return (
      <div className="space-y-4">
        <SessionSubNav />
        <Card className="bg-card border-border p-8 text-center">
          <AlertCircle className="h-8 w-8 text-muted-foreground/40 mx-auto mb-3" />
          <p className="text-muted-foreground">Could not generate AI insights. Make sure ANTHROPIC_API_KEY is set.</p>
        </Card>
        <TeachingCoachChat sessionId={id} />
      </div>
    );
  }

  if (isLoading || !scoring) {
    return (
      <div className="space-y-4">
        <SessionSubNav />
        <Skeleton className="h-32 rounded-lg" />
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-40 rounded-lg" />)}
      </div>
    );
  }

  const { sections, overall_summary } = scoring;
  const dangerCount = session.analytics.danger_zones.length;

  return (
    <div className="space-y-4">
      <SessionSubNav />

      {/* Overall Summary */}
      <Card className="bg-card border-border border-l-[3px] border-l-primary p-6 space-y-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          <h1 className="text-lg font-semibold text-foreground">Lecture Summary</h1>
        </div>
        <p className="text-sm text-muted-foreground leading-relaxed">{overall_summary}</p>
        <div className="flex gap-6 pt-1 text-sm">
          <span className="text-muted-foreground">
            Overall: <span className="font-semibold text-foreground">{session.analytics.focus_time_pct}%</span> engaged
          </span>
          <span className="text-muted-foreground">
            Danger zones: <span className="font-semibold text-foreground">{dangerCount}</span>
          </span>
        </div>
      </Card>

      {/* Section Cards */}
      <div className="space-y-4">
        {sections.map((sec) => {
          const isDanger = sec.engagement_pct < 50;
          return (
            <Card
              key={sec.label}
              onClick={() => navigate(`/session/${id}/timeline`)}
              className={`bg-card border-border p-5 space-y-3 cursor-pointer transition-transform hover:scale-[1.01] ${
                isDanger
                  ? "border-l-[3px] border-l-engage-disengaged bg-engage-disengaged/[0.03]"
                  : ""
              }`}
            >
              {/* Header */}
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-foreground">{sec.label}</h3>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>{fmt(sec.start)} – {fmt(sec.end)}</span>
                  <ChevronRight className="h-3.5 w-3.5" />
                </div>
              </div>

              {/* Score */}
              <span className={`text-3xl font-bold ${scoreColor(sec.engagement_pct)}`}>
                {sec.engagement_pct}%
              </span>

              {/* State breakdown bar */}
              <div className="flex h-2 w-full rounded-full overflow-hidden">
                <div
                  className="bg-engage-engaged"
                  style={{ width: `${sec.state_breakdown.engaged}%` }}
                />
                <div
                  className="bg-engage-passive"
                  style={{ width: `${sec.state_breakdown.passive}%` }}
                />
                <div
                  className="bg-engage-disengaged"
                  style={{ width: `${sec.state_breakdown.disengaged}%` }}
                />
              </div>

              {/* Top event */}
              {sec.top_event && (
                <div className="flex items-center gap-1.5">
                  {sec.top_event.includes("looked") ? (
                    <Eye className="h-3.5 w-3.5 text-muted-foreground" />
                  ) : (
                    <AlertTriangle className="h-3.5 w-3.5 text-muted-foreground" />
                  )}
                  <span className="text-xs text-muted-foreground bg-muted/50 rounded-full px-2 py-0.5">
                    {sec.top_event}
                  </span>
                </div>
              )}

              {/* AI note */}
              <p className="text-sm text-muted-foreground leading-relaxed">{sec.ai_note}</p>
            </Card>
          );
        })}
      </div>

      <p className="text-[10px] text-muted-foreground text-center pt-2">
        Analysis powered by Claude AI
      </p>

      {/* Teaching Coach Chat */}
      <TeachingCoachChat sessionId={id} />
    </div>
  );
};

export default AICoachPage;
