import { useState, useEffect, useMemo } from "react";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts";
import { BookOpen, TrendingUp, TrendingDown, Target, Clock, AlertTriangle, Trophy } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getSessions } from "@/lib/api";
import { mockSessionList } from "@/lib/mock-data";
import type { SessionSummary } from "@/lib/types";

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function scoreColor(pct: number) {
  if (pct >= 70) return "text-engage-engaged";
  if (pct >= 50) return "text-engage-passive";
  return "text-engage-disengaged";
}

const ProfilePage = () => {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    getSessions()
      .then((data) => setSessions(data.length > 0 ? data : mockSessionList as any))
      .catch(() => setSessions(mockSessionList as any))
      .finally(() => setIsLoading(false));
  }, []);

  const stats = useMemo(() => {
    if (sessions.length === 0) return null;

    const sorted = [...sessions].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    );
    const scores = sorted.map((s) => s.focus_time_pct);
    const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
    const best = Math.max(...scores);
    const worst = Math.min(...scores);
    const latest = scores[scores.length - 1];
    const first = scores[0];
    const trend = latest - first;
    const totalMinutes = sessions.reduce((a, s) => a + s.duration / 60, 0);

    const trendData = sorted.map((s) => ({
      date: fmtDate(s.created_at),
      score: s.focus_time_pct,
    }));

    // Weekly heatmap — last 7 days
    const now = new Date();
    const weekMap = new Map<string, number>();
    for (const s of sessions) {
      const d = new Date(s.created_at).toISOString().slice(0, 10);
      weekMap.set(d, Math.max(weekMap.get(d) ?? 0, s.focus_time_pct));
    }
    const weekDays = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      const key = d.toISOString().slice(0, 10);
      weekDays.push({
        label: d.toLocaleDateString("en-US", { weekday: "short" }).charAt(0),
        score: weekMap.get(key) ?? null,
      });
    }

    return { avg, best, worst, trend, totalMinutes, trendData, weekDays, lectureCount: sessions.length };
  }, [sessions]);

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-2xl mx-auto">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24 rounded-lg" />)}
        </div>
        <Skeleton className="h-48 rounded-lg" />
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-foreground mb-4">Teaching Dashboard</h1>
        <Card className="bg-card border-border p-8 text-center">
          <BookOpen className="h-10 w-10 text-muted-foreground/40 mx-auto mb-3" />
          <p className="text-muted-foreground">No lectures analyzed yet. Upload a recording to see your teaching analytics.</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-2xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Teaching Dashboard</h1>
        <p className="text-sm text-muted-foreground">Your lecture engagement overview</p>
      </div>

      {/* Top stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="bg-card border-border p-4 text-center">
          <BookOpen className="h-5 w-5 text-primary mx-auto mb-1" />
          <p className="text-2xl font-bold text-foreground">{stats.lectureCount}</p>
          <p className="text-xs text-muted-foreground">Lectures</p>
        </Card>
        <Card className="bg-card border-border p-4 text-center">
          <Target className="h-5 w-5 text-primary mx-auto mb-1" />
          <p className={`text-2xl font-bold ${scoreColor(stats.avg)}`}>{stats.avg.toFixed(1)}%</p>
          <p className="text-xs text-muted-foreground">Avg Engagement</p>
        </Card>
        <Card className="bg-card border-border p-4 text-center">
          <Trophy className="h-5 w-5 text-engage-engaged mx-auto mb-1" />
          <p className="text-2xl font-bold text-engage-engaged">{stats.best.toFixed(1)}%</p>
          <p className="text-xs text-muted-foreground">Best Lecture</p>
        </Card>
        <Card className="bg-card border-border p-4 text-center">
          <Clock className="h-5 w-5 text-muted-foreground mx-auto mb-1" />
          <p className="text-2xl font-bold text-foreground">{Math.round(stats.totalMinutes)}</p>
          <p className="text-xs text-muted-foreground">Minutes Analyzed</p>
        </Card>
      </div>

      {/* Trend */}
      <Card className="bg-card border-border p-5">
        <div className="flex items-end justify-between mb-4">
          <div>
            <h3 className="text-sm font-medium text-foreground">Engagement Trend</h3>
            <div className="flex items-center gap-1.5 mt-0.5">
              {stats.trend >= 0 ? (
                <TrendingUp className="h-3.5 w-3.5 text-engage-engaged" />
              ) : (
                <TrendingDown className="h-3.5 w-3.5 text-engage-disengaged" />
              )}
              <p className={`text-xs ${stats.trend >= 0 ? "text-engage-engaged" : "text-engage-disengaged"}`}>
                {stats.trend >= 0 ? "+" : ""}{stats.trend.toFixed(1)}% from first lecture
              </p>
            </div>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={stats.trendData}>
            <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false} />
            <YAxis domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false} width={35} />
            <Tooltip
              contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: "#94a3b8" }}
            />
            <Line type="monotone" dataKey="score" stroke="#22c55e" strokeWidth={2} dot={{ r: 4, fill: "#22c55e" }} name="Engagement %" />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      {/* Weekly heatmap */}
      <Card className="bg-card border-border p-5">
        <h3 className="text-sm font-medium text-foreground mb-4">This Week</h3>
        <div className="flex justify-between gap-2">
          {stats.weekDays.map((day, i) => (
            <div key={i} className="flex flex-col items-center gap-1.5 flex-1">
              <div
                className={`w-full aspect-square rounded-md flex items-center justify-center text-[10px] font-medium ${
                  day.score === null
                    ? "bg-secondary text-muted-foreground/30"
                    : day.score >= 70
                    ? "bg-engage-engaged/70 text-white"
                    : day.score >= 50
                    ? "bg-engage-passive/70 text-white"
                    : "bg-engage-disengaged/70 text-white"
                }`}
              >
                {day.score !== null ? `${Math.round(day.score)}%` : "—"}
              </div>
              <span className="text-[10px] text-muted-foreground">{day.label}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Teaching insights */}
      <Card className="bg-card border-border p-5 space-y-3">
        <h3 className="text-sm font-medium text-foreground">Quick Insights</h3>
        <div className="space-y-2 text-sm text-muted-foreground">
          {stats.best === stats.worst ? (
            <p>You've analyzed one lecture so far. Upload more to see trends and comparisons.</p>
          ) : (
            <>
              <div className="flex items-start gap-2">
                <Trophy className="h-4 w-4 text-engage-engaged shrink-0 mt-0.5" />
                <p>Your best lecture scored <span className="text-foreground font-medium">{stats.best.toFixed(1)}%</span> engagement. Review what worked in that session.</p>
              </div>
              {stats.worst < 60 && (
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-engage-disengaged shrink-0 mt-0.5" />
                  <p>Your lowest scoring lecture was <span className="text-foreground font-medium">{stats.worst.toFixed(1)}%</span>. Check the AI insights for that session for specific advice.</p>
                </div>
              )}
              <div className="flex items-start gap-2">
                {stats.trend >= 0 ? (
                  <TrendingUp className="h-4 w-4 text-engage-engaged shrink-0 mt-0.5" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-engage-passive shrink-0 mt-0.5" />
                )}
                <p>
                  {stats.trend >= 0
                    ? `Your engagement is trending up by ${stats.trend.toFixed(1)}% — your teaching adjustments are working.`
                    : `Your engagement has dipped ${Math.abs(stats.trend).toFixed(1)}% — check the AI coach for suggestions on recent lectures.`
                  }
                </p>
              </div>
            </>
          )}
        </div>
      </Card>
    </div>
  );
};

export default ProfilePage;
