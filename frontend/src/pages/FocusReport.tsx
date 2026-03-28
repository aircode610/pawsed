import { useParams } from "react-router-dom";
import { Eye, ArrowRight, CircleDot, Zap, AlertTriangle, TrendingUp, Share2, Download } from "lucide-react";
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
  yawn: { label: "Yawn", icon: CircleDot },
  eyes_closed: { label: "Eyes Closed", icon: Eye },
  zoned_out: { label: "Zoned Out", icon: Eye },
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
      </div>
    </div>
  );
}

const FocusReportPage = () => {
  const { id } = useParams();
  const { data: session } = useSessionData(id);
  const { toast } = useToast();
  const { analytics, duration } = session;

  const distractions = Object.entries(analytics.distraction_breakdown)
    .map(([type, count]) => ({ type, count, ...(DISTRACTION_META[type] || { label: type, icon: Eye }) }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 3);

  const sessionDate = new Date(session.created_at).toLocaleDateString("en-US", {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  });

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
          <p className="text-sm text-muted-foreground">{Math.round(duration / 60)} minutes</p>
        </div>

        {/* Hero ring */}
        <div className="flex flex-col items-center gap-2">
          <FocusRing pct={analytics.focus_time_pct} />
          <p className="text-sm font-medium text-muted-foreground">Focus Score</p>
        </div>

        {/* Top distractions */}
        <div>
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3 text-center">
            Top Distraction Patterns
          </h3>
          <div className="grid grid-cols-3 gap-3">
            {distractions.map((d) => (
              <Card key={d.type} className="bg-background/50 border-border p-4 text-center space-y-2">
                <d.icon className="h-5 w-5 mx-auto text-muted-foreground" />
                <p className="text-xs text-muted-foreground">{d.label}</p>
                <p className="text-lg font-bold text-foreground">{d.count}×</p>
              </Card>
            ))}
          </div>
        </div>

        {/* Highlights */}
        <div className="grid grid-cols-2 gap-3">
          <Card className="bg-background/50 border-border p-4 flex gap-3 items-start">
            <Zap className="h-5 w-5 text-primary shrink-0 mt-0.5" />
            <div>
              <p className="text-xs text-muted-foreground">Longest Focus Streak</p>
              <p className="text-xl font-bold text-foreground">
                {Math.round(analytics.longest_focus_streak / 60)} min
              </p>
            </div>
          </Card>
          <Card className="bg-background/50 border-border p-4 flex gap-3 items-start">
            <AlertTriangle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
            <div>
              <p className="text-xs text-muted-foreground">Biggest Danger Zone</p>
              {analytics.danger_zones[0] ? (
                <p className="text-xl font-bold text-foreground">
                  {formatTime(analytics.danger_zones[0].start)}–{formatTime(analytics.danger_zones[0].end)}
                </p>
              ) : (
                <p className="text-sm text-muted-foreground">None 🎉</p>
              )}
            </div>
          </Card>
        </div>

        {/* Comparison */}
        <Card className="bg-background/50 border-border p-4 flex items-center justify-center gap-2">
          <TrendingUp className="h-4 w-4 text-engage-engaged" />
          <span className="text-sm text-muted-foreground">vs. Your Average:</span>
          <span className="text-sm font-bold text-engage-engaged">+5.2%</span>
        </Card>

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
