import { Flame } from "lucide-react";
import { LineChart, Line, XAxis, ResponsiveContainer } from "recharts";
import { Card } from "@/components/ui/card";
import { mockSessionList, mockBadges, mockWeeklyHeatmap } from "@/lib/mock-data";

const DAYS = ["M", "T", "W", "T", "F", "S", "S"];

function heatColor(score: number | null): string {
  if (score === null) return "bg-secondary";
  if (score < 0.5) return "bg-engage-disengaged/70";
  if (score <= 0.7) return "bg-engage-passive/70";
  return "bg-engage-engaged/70";
}

const ProfilePage = () => {
  const streak = 3;
  const trendData = mockSessionList
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
    .map((s) => ({
      date: new Date(s.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      pct: s.focus_time_pct,
    }));
  const firstPct = trendData[0]?.pct ?? 0;
  const lastPct = trendData[trendData.length - 1]?.pct ?? 0;
  const trendDelta = lastPct - firstPct;

  return (
    <div className="space-y-8 max-w-2xl mx-auto">
      {/* Streak */}
      <div className="flex flex-col items-center gap-2 py-4">
        <Flame className="h-10 w-10 text-orange-500 animate-pulse" />
        <p className="text-5xl font-bold text-foreground">{streak}</p>
        <p className="text-sm font-medium text-foreground">Day Streak</p>
        <p className="text-xs text-muted-foreground">Keep it going! 2 more days for the 5-Day Streak badge</p>
      </div>

      {/* Weekly heatmap */}
      <Card className="bg-card border-border p-5">
        <h3 className="text-sm font-medium text-foreground mb-4">This Week</h3>
        <div className="flex justify-between gap-2">
          {mockWeeklyHeatmap.map((day, i) => (
            <div key={i} className="flex flex-col items-center gap-1.5 flex-1">
              <div className={`w-full aspect-square rounded-md ${heatColor(day.score)}`} />
              <span className="text-[10px] text-muted-foreground">{DAYS[i]}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Badges */}
      <div>
        <h3 className="text-sm font-medium text-foreground mb-3">Badges</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {mockBadges.map((badge) => (
            <Card
              key={badge.id}
              className={`bg-card border-border p-4 text-center space-y-1 transition-opacity ${
                badge.earned ? "opacity-100" : "opacity-40"
              } ${badge.earned ? "shadow-[0_0_12px_-2px_hsl(var(--primary)/0.25)]" : ""}`}
            >
              <span className="text-3xl">{badge.icon}</span>
              <p className="text-sm font-semibold text-foreground">{badge.name}</p>
              {badge.earned && badge.date ? (
                <p className="text-[10px] text-muted-foreground">
                  Earned {new Date(badge.date).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                </p>
              ) : (
                <p className="text-[10px] text-muted-foreground">{badge.description}</p>
              )}
            </Card>
          ))}
        </div>
      </div>

      {/* Trend */}
      <Card className="bg-card border-border p-5">
        <div className="flex items-end justify-between mb-4">
          <div>
            <h3 className="text-sm font-medium text-foreground">Your Focus Trend</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              {trendDelta >= 0 ? "+" : ""}{trendDelta.toFixed(1)}% from first session
            </p>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={trendData}>
            <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false} />
            <Line type="monotone" dataKey="pct" stroke="#22c55e" strokeWidth={2} dot={{ r: 4, fill: "#22c55e" }} />
          </LineChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
};

export default ProfilePage;
