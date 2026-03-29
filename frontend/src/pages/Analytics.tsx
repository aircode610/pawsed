import { useMemo } from "react";
import { useParams } from "react-router-dom";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as ReTooltip,
  ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar, ReferenceArea,
  Legend,
} from "recharts";
import { Zap, AlertTriangle, AlertCircle } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { SessionSubNav } from "@/components/SessionSubNav";
import { useSessionData } from "@/hooks/use-session-data";

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

const STATE_COLORS: Record<string, string> = {
  engaged: "#22c55e",
  passive: "#eab308",
  disengaged: "#ef4444",
};

const AnalyticsPage = () => {
  const { id } = useParams();
  const { data: session, isLoading } = useSessionData(id);
  const { analytics, engagement_states, duration } = session;
  const focusPct = analytics.focus_time_pct;

  const curveData = useMemo(
    () => analytics.engagement_curve.map((score, i) => ({ minute: i + 1, score })),
    [analytics.engagement_curve]
  );

  const stateDistribution = useMemo(() => {
    const totals: Record<string, number> = { engaged: 0, passive: 0, disengaged: 0 };
    engagement_states.forEach((s) => {
      totals[s.state] += s.end - s.start;
    });
    return Object.entries(totals).map(([state, seconds]) => ({
      name: state.charAt(0).toUpperCase() + state.slice(1),
      value: Math.round((seconds / duration) * 100),
      seconds,
      color: STATE_COLORS[state],
    }));
  }, [engagement_states, duration]);

  const distractionData = useMemo(() => {
    const labels: Record<string, string> = {
      yawn: "Yawn",
      looked_away: "Looked Away",
      eyes_closed: "Eyes Closed",
      zoned_out: "Zoned Out",
    };
    return Object.entries(analytics.distraction_breakdown).map(([key, count]) => ({
      name: labels[key] || key,
      count,
    }));
  }, [analytics.distraction_breakdown]);

  const pctColor = focusPct >= 70 ? "text-engage-engaged" : focusPct >= 50 ? "text-engage-passive" : "text-engage-disengaged";

  if (isLoading) {
    return (
      <div className="space-y-4">
        <SessionSubNav />
        <Skeleton className="h-32 rounded-lg" />
        <Skeleton className="h-80 rounded-lg" />
        <div className="grid md:grid-cols-2 gap-4">
          <Skeleton className="h-80 rounded-lg" />
          <Skeleton className="h-80 rounded-lg" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <SessionSubNav />

      {/* Headline */}
      <Card className="bg-card border-border p-6 text-center">
        <p className="text-muted-foreground mb-1">You were focused</p>
        <p className={`text-5xl font-bold ${pctColor}`}>{focusPct}%</p>
        <p className="text-muted-foreground text-sm mt-1">of this session</p>
        <p className="text-xs text-muted-foreground mt-3">
          {new Date(session.created_at).toLocaleDateString()} · {formatTime(duration)}
        </p>
      </Card>

      {/* Engagement Over Time */}
      <Card className="bg-card border-border p-4">
        <h3 className="text-sm font-medium text-foreground mb-4">Engagement Over Time</h3>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={curveData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="engGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#22c55e" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(215 19.3% 34.5%)" />
            <XAxis dataKey="minute" tick={{ fill: "#94a3b8", fontSize: 12 }} tickLine={false} axisLine={false} />
            <YAxis domain={[0, 1]} tick={{ fill: "#94a3b8", fontSize: 12 }} tickLine={false} axisLine={false} />
            <ReTooltip
              contentStyle={{ backgroundColor: "#1e293b", border: "1px solid hsl(215 19.3% 34.5%)", borderRadius: 8 }}
              labelStyle={{ color: "#f8fafc" }}
              itemStyle={{ color: "#22c55e" }}
              formatter={(value: number) => [`${(value * 100).toFixed(0)}%`, "Engagement"]}
              labelFormatter={(label) => `Minute ${label}`}
            />
            {analytics.danger_zones.map((z, i) => (
              <ReferenceArea
                key={i}
                x1={z.start / 60}
                x2={z.end / 60}
                fill="#ef4444"
                fillOpacity={0.1}
                stroke="#ef4444"
                strokeOpacity={0.3}
              />
            ))}
            <Area type="monotone" dataKey="score" stroke="#22c55e" strokeWidth={2} fill="url(#engGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </Card>

      {/* Row 2 */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* Pie */}
        <Card className="bg-card border-border p-4">
          <h3 className="text-sm font-medium text-foreground mb-4">Time Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={stateDistribution}
                dataKey="value"
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={3}
                label={({ name, value }) => `${name} ${value}%`}
              >
                {stateDistribution.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Legend
                formatter={(value) => <span className="text-xs text-muted-foreground">{value}</span>}
              />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        {/* Bar */}
        <Card className="bg-card border-border p-4">
          <h3 className="text-sm font-medium text-foreground mb-4">Distraction Types</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={distractionData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(215 19.3% 34.5%)" />
              <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} tickLine={false} axisLine={false} />
              <YAxis allowDecimals={false} tick={{ fill: "#94a3b8", fontSize: 12 }} tickLine={false} axisLine={false} />
              <ReTooltip
                contentStyle={{ backgroundColor: "#1e293b", border: "1px solid hsl(215 19.3% 34.5%)", borderRadius: 8 }}
                labelStyle={{ color: "#f8fafc" }}
                itemStyle={{ color: "#f87171" }}
              />
              <Bar dataKey="count" fill="#f87171" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Row 3 */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card className="bg-card border-border p-5 flex gap-4 items-start">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
            <Zap className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Longest Focus Streak</p>
            <p className="text-2xl font-bold text-foreground">
              {Math.round(analytics.longest_focus_streak / 60)} min
            </p>
            <p className="text-xs text-muted-foreground mt-1">Without any distraction events</p>
          </div>
        </Card>

        <Card className="bg-card border-border p-5 flex gap-4 items-start">
          <div className="h-10 w-10 rounded-lg bg-destructive/10 flex items-center justify-center shrink-0">
            <AlertTriangle className="h-5 w-5 text-destructive" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Danger Zones</p>
            {analytics.danger_zones.map((z, i) => (
              <p key={i} className="text-foreground font-medium">
                {formatTime(z.start)} — {formatTime(z.end)}{" "}
                <span className="text-muted-foreground font-normal">
                  (avg score: {Math.round(z.avg_score * 100)}%)
                </span>
              </p>
            ))}
            <p className="text-xs text-muted-foreground mt-1">
              Time ranges where engagement dropped significantly
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default AnalyticsPage;
