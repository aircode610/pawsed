import { useParams } from "react-router-dom";
import {
  Eye, ArrowRight, ArrowDown, CircleDot, Zap, AlertTriangle, TrendingUp,
  Share2, Download, Clock, Users, BedDouble, Moon, Activity,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { SessionSubNav } from "@/components/SessionSubNav";
import { useSessionData } from "@/hooks/use-session-data";

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

const DISTRACTION_META: Record<string, { label: string; icon: typeof Eye }> = {
  looked_away: { label: "Looked Away", icon: ArrowRight },
  looked_down: { label: "Looked Down", icon: ArrowDown },
  yawn: { label: "Yawning", icon: CircleDot },
  eyes_closed: { label: "Eyes Closed", icon: Eye },
  drowsy: { label: "Drowsy", icon: BedDouble },
  distracted: { label: "Distracted", icon: Zap },
  zoned_out: { label: "Zoned Out", icon: Moon },
  face_lost: { label: "Not Visible", icon: Users },
};

function FocusRing({ pct }: { pct: number }) {
  const r = 90;
  const circumference = 2 * Math.PI * r;
  const filled = (pct / 100) * circumference;
  const color = pct >= 70 ? "#22c55e" : pct >= 50 ? "#eab308" : "#ef4444";

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width="220" height="220" viewBox="0 0 220 220">
        <circle cx="110" cy="110" r={r} fill="none" stroke="hsl(217.2 32.6% 17.5%)" strokeWidth="14" />
        <circle
          cx="110" cy="110" r={r}
          fill="none" stroke={color} strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - filled}
          transform="rotate(-90 110 110)"
          style={{ filter: `drop-shadow(0 0 8px ${color}40)` }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-5xl font-bold text-foreground">{pct}%</span>
        <span className="text-xs text-muted-foreground">Engagement</span>
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, sub }: { icon: typeof Eye; label: string; value: string; sub?: string }) {
  return (
    <Card className="bg-background/50 border-border p-4 flex gap-3 items-start">
      <Icon className="h-5 w-5 text-primary shrink-0 mt-0.5" />
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-xl font-bold text-foreground">{value}</p>
        {sub && <p className="text-[10px] text-muted-foreground">{sub}</p>}
      </div>
    </Card>
  );
}

const FocusReportPage = () => {
  const { id } = useParams();
  const { data: session } = useSessionData(id);
  const { toast } = useToast();
  const { analytics, duration, events } = session;

  // Top distractions sorted by count
  const distractions = Object.entries(analytics.distraction_breakdown)
    .map(([type, count]) => ({ type, count, ...(DISTRACTION_META[type] || { label: type, icon: Eye }) }))
    .sort((a, b) => b.count - a.count);

  const topDistractions = distractions.slice(0, 3);

  const sessionDate = new Date(session.created_at).toLocaleDateString("en-US", {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  });

  // Compute additional stats
  const totalEvents = events.length;
  const totalDistractionTime = events.reduce((sum, e) => sum + e.duration, 0);
  const avgEventDuration = totalEvents > 0 ? totalDistractionTime / totalEvents : 0;
  const maxFaces = (analytics as any).max_faces_detected || 1;
  const peakRisk = ((analytics as any).peak_risk_moments || []) as Array<{ start: number; end: number }>;

  // Engagement time breakdown
  const engagedPct = analytics.focus_time_pct;
  const distractedPct = analytics.distraction_time_pct;
  const passivePct = Math.max(0, 100 - engagedPct - distractedPct);

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    toast({ title: "Link copied!", description: "Share this report with anyone." });
  };

  return (
    <div className="space-y-4">
      <SessionSubNav />

      <div className="mx-auto max-w-[600px] rounded-2xl border border-border p-8 space-y-8"
        style={{ background: "linear-gradient(180deg, hsl(222.2 47.4% 11.2%) 0%, hsl(217.2 32.6% 17.5%) 100%)" }}
      >
        {/* Header */}
        <div className="text-center space-y-1">
          <p className="text-xs text-muted-foreground tracking-widest uppercase">Pawsed</p>
          <p className="text-sm text-muted-foreground">{sessionDate}</p>
          <p className="text-sm text-muted-foreground">
            {Math.round(duration / 60)} minutes · {maxFaces > 1 ? `${maxFaces} students detected` : "1 student"}
          </p>
        </div>

        {/* Hero ring */}
        <div className="flex flex-col items-center gap-2">
          <FocusRing pct={engagedPct} />
        </div>

        {/* Time breakdown bar */}
        <div className="space-y-2">
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider text-center">
            Time Distribution
          </h3>
          <div className="flex h-3 w-full rounded-full overflow-hidden">
            <div className="bg-engage-engaged" style={{ width: `${engagedPct}%` }} />
            <div className="bg-engage-passive" style={{ width: `${passivePct}%` }} />
            <div className="bg-engage-disengaged" style={{ width: `${distractedPct}%` }} />
          </div>
          <div className="flex justify-between text-[10px] text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-engage-engaged" /> Engaged {engagedPct}%
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-engage-passive" /> Passive {passivePct.toFixed(0)}%
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-engage-disengaged" /> Disengaged {distractedPct}%
            </span>
          </div>
        </div>

        {/* Key metrics */}
        <div className="grid grid-cols-2 gap-3">
          <StatCard icon={Zap} label="Longest Focus Streak" value={`${Math.round(analytics.longest_focus_streak / 60)} min`} />
          <StatCard icon={Clock} label="Total Distraction Time" value={`${Math.round(totalDistractionTime)}s`} sub={`across ${totalEvents} events`} />
          <StatCard icon={Activity} label="Avg Distraction Length" value={`${avgEventDuration.toFixed(1)}s`} sub="per event" />
          <StatCard
            icon={AlertTriangle}
            label="Danger Zones"
            value={analytics.danger_zones.length > 0
              ? `${formatTime(analytics.danger_zones[0].start)}–${formatTime(analytics.danger_zones[0].end)}`
              : "None"
            }
            sub={analytics.danger_zones.length > 1 ? `+${analytics.danger_zones.length - 1} more` : undefined}
          />
        </div>

        {/* Peak risk moments */}
        {peakRisk.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider text-center">
              Peak Risk Moments
            </h3>
            <div className="flex flex-wrap gap-2 justify-center">
              {peakRisk.slice(0, 5).map((pr, i) => (
                <span key={i} className="text-xs bg-engage-disengaged/20 text-engage-disengaged border border-engage-disengaged/30 rounded-full px-3 py-1">
                  {formatTime(pr.start)}–{formatTime(pr.end)}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Distraction breakdown */}
        <div>
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3 text-center">
            Distraction Breakdown
          </h3>
          <div className="grid grid-cols-3 gap-3">
            {topDistractions.map((d) => (
              <Card key={d.type} className="bg-background/50 border-border p-4 text-center space-y-2">
                <d.icon className="h-5 w-5 mx-auto text-muted-foreground" />
                <p className="text-xs text-muted-foreground">{d.label}</p>
                <p className="text-lg font-bold text-foreground">{d.count}×</p>
              </Card>
            ))}
          </div>
          {distractions.length > 3 && (
            <div className="flex flex-wrap gap-2 mt-3 justify-center">
              {distractions.slice(3).map((d) => (
                <span key={d.type} className="text-[10px] text-muted-foreground bg-background/50 border border-border rounded-full px-2.5 py-1">
                  {d.label}: {d.count}×
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-3 justify-center">
          <Button onClick={handleShare} variant="outline" size="sm" className="gap-2">
            <Share2 className="h-4 w-4" /> Share Report
          </Button>
          <Button variant="outline" size="sm" className="gap-2">
            <Download className="h-4 w-4" /> Download as Image
          </Button>
        </div>

        <p className="text-center text-[10px] text-muted-foreground">Generated by Pawsed</p>
      </div>
    </div>
  );
};

export default FocusReportPage;
