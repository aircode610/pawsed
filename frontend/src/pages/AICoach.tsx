import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Sparkles,
  AlertTriangle,
  Eye,
  ChevronDown,
  ChevronUp,
  Clock,
  BookOpen,
  MessageSquare,
  AlertCircle,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SessionSubNav } from "@/components/SessionSubNav";
import { TeachingCoachChat } from "@/components/TeachingCoachChat";
import { useSessionData } from "@/hooks/use-session-data";
import { getSectionScoring } from "@/lib/api";
import type { LectureSection, SectionScoringData } from "@/lib/types";

const fmt = (s: number) => {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, "0")}`;
};

const engagementColor = (pct: number) => {
  if (pct >= 70) return { text: "text-engage-engaged", bg: "bg-engage-engaged", label: "Strong" };
  if (pct >= 50) return { text: "text-yellow-400", bg: "bg-yellow-400", label: "Moderate" };
  return { text: "text-engage-disengaged", bg: "bg-engage-disengaged", label: "Weak" };
};

function SectionRow({ sec, index }: { sec: LectureSection; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const navigate = useNavigate();
  const { id } = useParams();
  const color = engagementColor(sec.engagement_pct);
  const isDanger = sec.engagement_pct < 50;

  return (
    <div
      className={`border border-border rounded-lg overflow-hidden transition-all ${
        isDanger ? "border-engage-disengaged/40 bg-engage-disengaged/[0.03]" : "bg-card"
      }`}
    >
      {/* Row header — always visible */}
      <button
        className="w-full text-left p-4"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-center gap-3">
          {/* Index pill */}
          <span className="text-xs font-mono text-muted-foreground w-5 shrink-0">
            {String(index + 1).padStart(2, "0")}
          </span>

          {/* Label + time */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-foreground truncate">{sec.label}</span>
              {isDanger && (
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-engage-disengaged/15 text-engage-disengaged">
                  ⚠ danger zone
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5 mt-0.5">
              <Clock className="h-3 w-3 text-muted-foreground/60" />
              <span className="text-xs text-muted-foreground">{fmt(sec.start)} – {fmt(sec.end)}</span>
              {sec.topic && (
                <>
                  <span className="text-muted-foreground/40">·</span>
                  <BookOpen className="h-3 w-3 text-muted-foreground/60" />
                  <span className="text-xs text-muted-foreground truncate max-w-[240px]">{sec.topic}</span>
                </>
              )}
            </div>
          </div>

          {/* Engagement score */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="text-right">
              <span className={`text-xl font-bold ${color.text}`}>{sec.engagement_pct.toFixed(0)}%</span>
              <div className="text-[10px] text-muted-foreground">{color.label}</div>
            </div>

            {/* Mini engagement bar */}
            <div className="w-16 h-2 rounded-full bg-muted overflow-hidden hidden sm:block">
              <div
                className={`h-full rounded-full ${color.bg}`}
                style={{ width: `${sec.engagement_pct}%` }}
              />
            </div>

            {expanded ? (
              <ChevronUp className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            )}
          </div>
        </div>

        {/* State breakdown strip */}
        <div className="flex h-1.5 w-full rounded-full overflow-hidden mt-3 gap-0.5">
          <div className="bg-engage-engaged rounded-l-full" style={{ width: `${sec.state_breakdown.engaged}%` }} />
          <div className="bg-engage-passive" style={{ width: `${sec.state_breakdown.passive}%` }} />
          <div className="bg-engage-disengaged rounded-r-full" style={{ width: `${sec.state_breakdown.disengaged}%` }} />
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-border bg-background/40 px-4 pb-4 pt-3 space-y-3">
          {/* Top event badge */}
          {sec.top_event && (
            <div className="flex items-center gap-1.5">
              {sec.top_event.includes("looked") ? (
                <Eye className="h-3.5 w-3.5 text-muted-foreground" />
              ) : (
                <AlertTriangle className="h-3.5 w-3.5 text-muted-foreground" />
              )}
              <span className="text-xs text-muted-foreground">
                Most common: <span className="font-medium text-foreground">{sec.top_event}</span>
              </span>
            </div>
          )}

          {/* AI note */}
          {sec.ai_note && (
            <div className="flex gap-2">
              <Sparkles className="h-3.5 w-3.5 text-primary shrink-0 mt-0.5" />
              <p className="text-sm text-muted-foreground leading-relaxed">{sec.ai_note}</p>
            </div>
          )}

          {/* Jump to timeline */}
          <button
            onClick={(e) => { e.stopPropagation(); navigate(`/session/${id}/timeline`); }}
            className="text-xs text-primary hover:underline"
          >
            View in timeline →
          </button>
        </div>
      )}
    </div>
  );
}

const AICoachPage = () => {
  const { id } = useParams();
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

  const dangerCount = session.analytics.danger_zones.length;
  const bestSection = scoring?.sections.reduce(
    (best, s) => (s.engagement_pct > (best?.engagement_pct ?? 0) ? s : best),
    null as LectureSection | null,
  );
  const worstSection = scoring?.sections.reduce(
    (worst, s) => (s.engagement_pct < (worst?.engagement_pct ?? 101) ? s : worst),
    null as LectureSection | null,
  );

  return (
    <div className="space-y-4">
      <SessionSubNav />

      <Tabs defaultValue="insights">
        <TabsList className="bg-card border border-border">
          <TabsTrigger value="insights" className="gap-1.5">
            <Sparkles className="h-3.5 w-3.5" />
            Insights
          </TabsTrigger>
          <TabsTrigger value="chat" className="gap-1.5">
            <MessageSquare className="h-3.5 w-3.5" />
            Teaching Coach
          </TabsTrigger>
        </TabsList>

        {/* ── Insights tab ── */}
        <TabsContent value="insights" className="mt-4 space-y-4">
          {error ? (
            <Card className="bg-card border-border p-8 text-center">
              <AlertCircle className="h-8 w-8 text-muted-foreground/40 mx-auto mb-3" />
              <p className="text-muted-foreground">
                Could not generate AI insights. Make sure <code className="text-xs">ANTHROPIC_API_KEY</code> is set.
              </p>
            </Card>
          ) : isLoading || !scoring ? (
            <>
              <Skeleton className="h-32 rounded-lg" />
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 rounded-lg" />)}
            </>
          ) : (
            <>
              {/* Overall summary card */}
              <Card className="bg-card border-border border-l-[3px] border-l-primary p-5 space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-primary shrink-0" />
                    <h1 className="text-base font-semibold text-foreground">Lecture Summary</h1>
                  </div>
                  <div className="flex gap-3 text-xs shrink-0">
                    <span className="text-muted-foreground">
                      Focus <span className="font-semibold text-foreground">{session.analytics.focus_time_pct}%</span>
                    </span>
                    {dangerCount > 0 && (
                      <span className="text-engage-disengaged font-medium">
                        {dangerCount} danger zone{dangerCount > 1 ? "s" : ""}
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">{scoring.overall_summary}</p>

                {/* Best / worst section badges */}
                {(bestSection || worstSection) && (
                  <div className="flex gap-3 pt-1 flex-wrap">
                    {bestSection && (
                      <div className="flex items-center gap-1.5 text-xs text-engage-engaged">
                        <TrendingUp className="h-3.5 w-3.5" />
                        <span>Best: <strong>{bestSection.label}</strong> ({bestSection.engagement_pct.toFixed(0)}%)</span>
                      </div>
                    )}
                    {worstSection && worstSection !== bestSection && (
                      <div className="flex items-center gap-1.5 text-xs text-engage-disengaged">
                        <TrendingDown className="h-3.5 w-3.5" />
                        <span>Needs work: <strong>{worstSection.label}</strong> ({worstSection.engagement_pct.toFixed(0)}%)</span>
                      </div>
                    )}
                  </div>
                )}
              </Card>

              {/* Section list */}
              <div className="space-y-2">
                {scoring.sections.map((sec, i) => (
                  <SectionRow key={`${sec.label}-${i}`} sec={sec} index={i} />
                ))}
              </div>

              <p className="text-[10px] text-muted-foreground text-center pt-1">
                Analysis powered by Claude AI
              </p>
            </>
          )}
        </TabsContent>

        {/* ── Chat tab ── */}
        <TabsContent value="chat" className="mt-4">
          <TeachingCoachChat sessionId={id} />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AICoachPage;
