import { useState, useCallback, useRef } from "react";
import { useParams } from "react-router-dom";
import { Play, Eye, Moon, CircleDot, ArrowLeft, ArrowRight, AlertCircle } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { SessionSubNav } from "@/components/SessionSubNav";
import { useSessionData } from "@/hooks/use-session-data";
import type { EventType } from "@/lib/mock-data";

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

const stateColor: Record<string, string> = {
  engaged: "bg-engage-engaged",
  passive: "bg-engage-passive",
  disengaged: "bg-engage-disengaged",
};

function EventIcon({ type, direction }: { type: EventType; direction?: string }) {
  const cls = "h-3 w-3";
  switch (type) {
    case "eyes_closed":
      return <Eye className={cls} />;
    case "yawn":
      return <CircleDot className={cls} />;
    case "looked_away":
      return direction === "right" ? <ArrowRight className={cls} /> : <ArrowLeft className={cls} />;
    case "zoned_out":
      return <Moon className={cls} />;
    default:
      return <CircleDot className={cls} />;
  }
}

function eventLabel(type: string): string {
  return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const TimelinePage = () => {
  const { id } = useParams();
  const { data: session, isLoading, isUsingMock } = useSessionData(id);
  const [currentTime, setCurrentTime] = useState(0);
  const timelineRef = useRef<HTMLDivElement>(null);
  const { duration, analytics, events, engagement_states } = session;

  const handleTimelineClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const pct = (e.clientX - rect.left) / rect.width;
      setCurrentTime(Math.max(0, Math.min(duration, pct * duration)));
    },
    [duration]
  );

  const activeEventIdx = events.reduce((closest, ev, idx) => {
    const diff = Math.abs(ev.timestamp - currentTime);
    const closestDiff = Math.abs(events[closest].timestamp - currentTime);
    return diff < closestDiff ? idx : closest;
  }, 0);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <SessionSubNav />
        <div className="grid grid-cols-3 gap-3">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-20 rounded-lg" />)}
        </div>
        <Skeleton className="aspect-video rounded-lg" />
        <Skeleton className="h-10 rounded-lg" />
        <Skeleton className="h-60 rounded-lg" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <SessionSubNav />

      {isUsingMock && (
        <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-xs text-muted-foreground">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          Using demo data — backend not connected
        </div>
      )}

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-3">
        <Card className="bg-card border-border p-4 text-center">
          <p className="text-xs text-muted-foreground mb-1">Focus</p>
          <p className="text-xl font-bold text-engage-engaged">
            {analytics.focus_time_pct}%
          </p>
        </Card>
        <Card className="bg-card border-border p-4 text-center">
          <p className="text-xs text-muted-foreground mb-1">Duration</p>
          <p className="text-xl font-bold text-foreground">
            {formatTime(duration)}
          </p>
        </Card>
        <Card className="bg-card border-border p-4 text-center">
          <p className="text-xs text-muted-foreground mb-1">Events</p>
          <p className="text-xl font-bold text-foreground">{events.length}</p>
        </Card>
      </div>

      {/* Video Player Placeholder */}
      <Card className="bg-card border-border overflow-hidden">
        <div className="relative aspect-video bg-background flex items-center justify-center">
          <div className="text-center text-muted-foreground">
            <Play className="h-12 w-12 mx-auto mb-2 opacity-40" />
            <p className="text-sm">Video playback — connect to upload</p>
          </div>
        </div>
        {/* Scrub bar */}
        <div className="px-4 py-2 flex items-center gap-3">
          <span className="text-xs text-muted-foreground font-mono w-12">
            {formatTime(currentTime)}
          </span>
          <div
            className="flex-1 h-1.5 bg-secondary rounded-full cursor-pointer relative"
            onClick={handleTimelineClick}
          >
            <div
              className="absolute inset-y-0 left-0 bg-primary rounded-full"
              style={{ width: `${(currentTime / duration) * 100}%` }}
            />
          </div>
          <span className="text-xs text-muted-foreground font-mono w-12 text-right">
            {formatTime(duration)}
          </span>
        </div>
      </Card>

      {/* Engagement Timeline */}
      <Card className="bg-card border-border p-4">
        <h3 className="text-sm font-medium text-foreground mb-3">
          Engagement Timeline
        </h3>
        <div
          ref={timelineRef}
          className="relative h-10 rounded-lg overflow-hidden cursor-pointer border border-border"
          onClick={handleTimelineClick}
        >
          {/* State segments */}
          <div className="absolute inset-0 flex">
            {engagement_states.map((seg, i) => (
              <div
                key={i}
                className={`h-full ${stateColor[seg.state]} opacity-80`}
                style={{ width: `${((seg.end - seg.start) / duration) * 100}%` }}
              />
            ))}
          </div>

          {/* Danger zone overlay */}
          {analytics.danger_zones.map((zone, i) => (
            <div
              key={`dz-${i}`}
              className="absolute inset-y-0 bg-destructive/20 border-x border-destructive/30"
              style={{
                left: `${(zone.start / duration) * 100}%`,
                width: `${((zone.end - zone.start) / duration) * 100}%`,
              }}
            />
          ))}

          {/* Event markers */}
          {events.map((ev, i) => (
            <Tooltip key={i}>
              <TooltipTrigger asChild>
                <div
                  className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 h-5 w-5 rounded-full bg-background/90 border border-border flex items-center justify-center text-foreground hover:scale-125 transition-transform z-10"
                  style={{ left: `${(ev.timestamp / duration) * 100}%` }}
                >
                  <EventIcon
                    type={ev.event_type as EventType}
                    direction={(ev.metadata as { direction?: string })?.direction}
                  />
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p className="text-xs">
                  {eventLabel(ev.event_type)} at {formatTime(ev.timestamp)} —{" "}
                  {ev.duration}s
                </p>
              </TooltipContent>
            </Tooltip>
          ))}

          {/* Cursor */}
          <div
            className="absolute inset-y-0 w-0.5 bg-foreground z-20 pointer-events-none"
            style={{ left: `${(currentTime / duration) * 100}%` }}
          />
        </div>

        {/* Legend */}
        <div className="flex gap-4 mt-3">
          {(["engaged", "passive", "disengaged"] as const).map((s) => (
            <div key={s} className="flex items-center gap-1.5">
              <div className={`h-2.5 w-2.5 rounded-full ${stateColor[s]}`} />
              <span className="text-xs text-muted-foreground capitalize">{s}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Event List */}
      <Card className="bg-card border-border overflow-hidden">
        <div className="px-4 py-3 border-b border-border">
          <h3 className="text-sm font-medium text-foreground">Events</h3>
        </div>
        <div className="divide-y divide-border max-h-80 overflow-y-auto">
          {events.map((ev, i) => {
            const isActive = i === activeEventIdx;
            const dotColor =
              ev.event_type === "looked_away" || ev.event_type === "zoned_out"
                ? "bg-engage-passive"
                : "bg-engage-disengaged";
            return (
              <button
                key={i}
                onClick={() => setCurrentTime(ev.timestamp)}
                className={`w-full flex items-center gap-4 px-4 py-2.5 text-left text-sm transition-colors hover:bg-accent/50 ${
                  isActive ? "bg-primary/10" : i % 2 === 0 ? "bg-transparent" : "bg-accent/20"
                }`}
              >
                <span className="font-mono text-muted-foreground w-12">
                  {formatTime(ev.timestamp)}
                </span>
                <span className="flex items-center gap-2 flex-1 min-w-0">
                  <span className={`h-2 w-2 rounded-full shrink-0 ${dotColor}`} />
                  <span className="text-foreground truncate">
                    {eventLabel(ev.event_type)}
                  </span>
                </span>
                <span className="text-muted-foreground w-14 text-right">
                  {ev.duration}s
                </span>
                <span className="text-muted-foreground w-12 text-right">
                  {Math.round(ev.confidence * 100)}%
                </span>
              </button>
            );
          })}
        </div>
      </Card>
    </div>
  );
};

export default TimelinePage;
