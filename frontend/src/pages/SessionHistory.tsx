import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { LineChart, Line, ResponsiveContainer } from "recharts";
import { ArrowUpDown, TrendingUp, TrendingDown } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { mockSessionList } from "@/lib/mock-data";

type SortKey = "date" | "focus";

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

function fmtDuration(s: number) {
  return `${Math.round(s / 60)} min`;
}

function scoreColor(pct: number) {
  if (pct >= 70) return "text-engage-engaged";
  if (pct >= 50) return "text-engage-passive";
  return "text-engage-disengaged";
}

const SessionHistoryPage = () => {
  const navigate = useNavigate();
  const [sortBy, setSortBy] = useState<SortKey>("date");
  const [compareIds, setCompareIds] = useState<Set<string>>(new Set());

  const sorted = useMemo(() => {
    const list = [...mockSessionList];
    if (sortBy === "date") list.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    else list.sort((a, b) => b.focus_time_pct - a.focus_time_pct);
    return list;
  }, [sortBy]);

  const toggleCompare = (id: string) => {
    setCompareIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < 2) next.add(id);
      return next;
    });
  };

  const compareArr = Array.from(compareIds);
  const showCompare = compareArr.length === 2;
  const compA = showCompare ? mockSessionList.find((s) => s.session_id === compareArr[0]) : null;
  const compB = showCompare ? mockSessionList.find((s) => s.session_id === compareArr[1]) : null;
  const delta = compA && compB ? compB.focus_time_pct - compA.focus_time_pct : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Session History</h1>
          <p className="text-sm text-muted-foreground">Track your progress across sessions</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={() => setSortBy((s) => (s === "date" ? "focus" : "date"))}
        >
          <ArrowUpDown className="h-3.5 w-3.5" />
          {sortBy === "date" ? "Date" : "Focus Score"}
        </Button>
      </div>

      {/* Grid */}
      <div className="grid md:grid-cols-2 gap-4">
        {sorted.map((sess) => (
          <Card
            key={sess.session_id}
            className="bg-card border-border p-4 cursor-pointer hover:scale-[1.02] transition-transform relative group"
            onClick={() => navigate(`/session/${sess.session_id}/timeline`)}
          >
            <div
              className="absolute top-3 right-3 z-10"
              onClick={(e) => e.stopPropagation()}
            >
              <Checkbox
                checked={compareIds.has(sess.session_id)}
                onCheckedChange={() => toggleCompare(sess.session_id)}
                disabled={!compareIds.has(sess.session_id) && compareIds.size >= 2}
              />
            </div>

            <div className="flex justify-between items-start gap-4">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-foreground truncate">{sess.video_filename}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {fmtDate(sess.created_at)} · {fmtDuration(sess.duration)}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">{sess.event_count} events</p>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <ResponsiveContainer width={80} height={30}>
                  <LineChart data={sess.engagement_curve.map((v, i) => ({ i, v }))}>
                    <Line type="monotone" dataKey="v" stroke="#22c55e" strokeWidth={1.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
                <span className={`text-2xl font-bold ${scoreColor(sess.focus_time_pct)}`}>
                  {sess.focus_time_pct}%
                </span>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Compare panel */}
      {showCompare && compA && compB && (
        <Card className="bg-card border-border p-5 animate-in slide-in-from-bottom-4 duration-300">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-6">
              <div className="text-center">
                <p className="text-xs text-muted-foreground truncate max-w-[140px]">{compA.video_filename}</p>
                <p className={`text-xl font-bold ${scoreColor(compA.focus_time_pct)}`}>{compA.focus_time_pct}%</p>
              </div>
              <span className="text-muted-foreground">vs</span>
              <div className="text-center">
                <p className="text-xs text-muted-foreground truncate max-w-[140px]">{compB.video_filename}</p>
                <p className={`text-xl font-bold ${scoreColor(compB.focus_time_pct)}`}>{compB.focus_time_pct}%</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {delta >= 0 ? (
                <TrendingUp className="h-4 w-4 text-engage-engaged" />
              ) : (
                <TrendingDown className="h-4 w-4 text-engage-disengaged" />
              )}
              <span className={`font-bold ${delta >= 0 ? "text-engage-engaged" : "text-engage-disengaged"}`}>
                {delta >= 0 ? "+" : ""}{delta.toFixed(1)}%
              </span>
              <span className="text-sm text-muted-foreground">
                {delta >= 0 ? "improvement" : "decline"}
              </span>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};

export default SessionHistoryPage;
