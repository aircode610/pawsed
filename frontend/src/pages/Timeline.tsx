import { useState, useCallback, useRef, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Play, Eye, Moon, CircleDot, ArrowLeft, ArrowRight, ArrowDown, AlertCircle, Scan, Zap, BedDouble } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { SessionSubNav } from "@/components/SessionSubNav";
import { useSessionData } from "@/hooks/use-session-data";
import { getToken } from "@/lib/api";
import type { EventType, SessionEvent } from "@/lib/types";

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

const stateColor: Record<string, string> = {
  engaged: "bg-engage-engaged",
  passive: "bg-engage-engaged",
  disengaged: "bg-engage-disengaged",
};

interface EventCluster {
  position: number; // 0-100 percentage
  events: SessionEvent[];
}

function clusterEvents(events: SessionEvent[], duration: number): EventCluster[] {
  if (!duration) return [];
  const CLUSTER_PCT = 1.5; // events within 1.5% of timeline width are merged
  const threshold = (CLUSTER_PCT / 100) * duration;
  const clusters: { timestamp: number; events: SessionEvent[] }[] = [];
  for (const ev of [...events].sort((a, b) => a.timestamp - b.timestamp)) {
    const last = clusters[clusters.length - 1];
    if (last && ev.timestamp - last.timestamp < threshold) {
      last.events.push(ev);
    } else {
      clusters.push({ timestamp: ev.timestamp, events: [ev] });
    }
  }
  return clusters.map((c) => ({
    position: (c.timestamp / duration) * 100,
    events: c.events,
  }));
}

function EventIcon({ type, direction, className }: { type: EventType; direction?: string; className?: string }) {
  const cls = className ?? "h-3 w-3";
  switch (type) {
    case "eyes_closed":
      return <Eye className={cls} />;
    case "yawn":
      return <CircleDot className={cls} />;
    case "looked_away":
      return direction === "right" ? <ArrowRight className={cls} /> : <ArrowLeft className={cls} />;
    case "looked_down":
      return <ArrowDown className={cls} />;
    case "drowsy":
      return <BedDouble className={cls} />;
    case "distracted":
      return <Zap className={cls} />;
    case "zoned_out":
      return <Moon className={cls} />;
    default:
      return <CircleDot className={cls} />;
  }
}

function eventLabel(type: string): string {
  return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TimelinePage = () => {
  const { id } = useParams();
  const { data: session, isLoading, isError } = useSessionData(id);
  const [currentTime, setCurrentTime] = useState(0);
  const timelineRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoError, setVideoError] = useState(false);
  const [showLandmarks, setShowLandmarks] = useState(false);
  const { duration, analytics, events, engagement_states, has_landmarks } = session;
  const significantEvents = events.filter((e) => e.severity === "significant");
  const briefEvents = events.filter((e) => e.severity === "brief" || !e.severity);
  const sigClusters = clusterEvents(significantEvents, duration);

  const token = getToken();
  const videoUrl = id && token
    ? `${API_BASE}/session/${id}/video?token=${encodeURIComponent(token)}${showLandmarks ? "&landmarks=true" : ""}`
    : "";

  // Reset error state whenever the video URL changes (e.g. landmarks toggle)
  // so a failed landmarks load doesn't permanently hide the original video.
  useEffect(() => {
    setVideoError(false);
  }, [videoUrl]);

  // Sync video playback position → currentTime state using rAF for smooth updates
  useEffect(() => {
    let rafId: number;
    const tick = () => {
      const video = videoRef.current;
      if (video && !video.paused && !video.ended) {
        setCurrentTime(video.currentTime);
      }
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafId);
  }, []);

  const seekTo = useCallback(
    (time: number) => {
      const clamped = Math.max(0, Math.min(duration, time));
      setCurrentTime(clamped);
      if (videoRef.current) {
        videoRef.current.currentTime = clamped;
      }
    },
    [duration]
  );

  const handleTimelineClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const pct = (e.clientX - rect.left) / rect.width;
      seekTo(pct * duration);
    },
    [duration, seekTo]
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

      {isError && (
        <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-xs text-muted-foreground">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          Could not load session data
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
          <p className="text-xl font-bold text-foreground">{significantEvents.length}</p>
          <p className="text-[10px] text-muted-foreground mt-0.5">{briefEvents.length} brief</p>
        </Card>
      </div>

      {/* Video Player */}
      <Card className="bg-card border-border overflow-hidden">
        <div className="relative aspect-video bg-background">
          {!videoError && videoUrl ? (
            <video
              ref={videoRef}
              key={videoUrl}
              src={videoUrl}
              className="w-full h-full object-contain bg-black"
              controls
              onLoadedMetadata={() => {
                // Restore playback position after source switch
                if (videoRef.current && currentTime > 0) {
                  videoRef.current.currentTime = currentTime;
                }
              }}
              onError={() => setVideoError(true)}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <div className="text-center text-muted-foreground">
                <Play className="h-12 w-12 mx-auto mb-2 opacity-40" />
                <p className="text-sm">
                  Video not available
                </p>
              </div>
            </div>
          )}
          {/* Landmarks toggle — only shown when overlay is available */}
          {!videoError && videoUrl && has_landmarks && (
            <Button
              variant={showLandmarks ? "default" : "secondary"}
              size="sm"
              className="absolute top-2 right-2 z-10 gap-1.5 opacity-90 hover:opacity-100"
              onClick={() => setShowLandmarks((v) => !v)}
            >
              <Scan className="h-3.5 w-3.5" />
              {showLandmarks ? "Landmarks On" : "Landmarks Off"}
            </Button>
          )}
        </div>
        {/* Scrub bar (always visible — syncs with video when available) */}
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
        <h3 className="text-sm font-medium text-foreground mb-3">Engagement Timeline</h3>

        {/* Row 1: engagement color band — no event dots, keeps it clean */}
        <div
          className="relative h-8 rounded-t-lg overflow-hidden cursor-pointer border border-border border-b-0"
          onClick={handleTimelineClick}
        >
          <div className="absolute inset-0 flex">
            {engagement_states.map((seg, i) => (
              <div
                key={i}
                className={`h-full ${stateColor[seg.state]} opacity-80`}
                style={{ width: `${((seg.end - seg.start) / duration) * 100}%` }}
              />
            ))}
          </div>
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
          <div
            className="absolute inset-y-0 w-0.5 bg-foreground z-20 pointer-events-none"
            style={{ left: `${(currentTime / duration) * 100}%` }}
          />
        </div>

        {/* Row 2: significant-event strip with clustering */}
        <div
          ref={timelineRef}
          className="relative h-6 rounded-b-lg overflow-hidden cursor-pointer border border-border border-t border-t-border/40 bg-background/40"
          onClick={handleTimelineClick}
        >
          <div
            className="absolute inset-y-0 w-0.5 bg-foreground/40 z-20 pointer-events-none"
            style={{ left: `${(currentTime / duration) * 100}%` }}
          />
          {sigClusters.map((cluster, i) => (
            <Tooltip key={i}>
              <TooltipTrigger asChild>
                <div
                  className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 flex items-center justify-center z-10 cursor-pointer"
                  style={{ left: `${cluster.position}%` }}
                >
                  {cluster.events.length === 1 ? (
                    <div className="h-4 w-4 rounded-full bg-engage-disengaged/90 border border-engage-disengaged flex items-center justify-center text-white hover:scale-125 transition-transform">
                      <EventIcon
                        type={cluster.events[0].event_type as EventType}
                        direction={(cluster.events[0].metadata as { direction?: string })?.direction}
                        className="h-2.5 w-2.5"
                      />
                    </div>
                  ) : (
                    <div className="h-5 px-1.5 rounded-full bg-engage-disengaged/90 border border-engage-disengaged flex items-center justify-center text-white text-[9px] font-bold hover:scale-110 transition-transform">
                      {cluster.events.length}
                    </div>
                  )}
                </div>
              </TooltipTrigger>
              <TooltipContent>
                {cluster.events.length === 1 ? (
                  <p className="text-xs">
                    {eventLabel(cluster.events[0].event_type)} at {formatTime(cluster.events[0].timestamp)} — {cluster.events[0].duration.toFixed(1)}s
                  </p>
                ) : (
                  <div className="text-xs space-y-0.5">
                    {cluster.events.map((ev, j) => (
                      <p key={j}>{eventLabel(ev.event_type)} — {ev.duration.toFixed(1)}s</p>
                    ))}
                  </div>
                )}
              </TooltipContent>
            </Tooltip>
          ))}
        </div>

        {/* Legend */}
        <div className="flex gap-4 mt-3">
          {(["engaged", "disengaged"] as const).map((s) => (
            <div key={s} className="flex items-center gap-1.5">
              <div className={`h-2.5 w-2.5 rounded-full ${stateColor[s]}`} />
              <span className="text-xs text-muted-foreground capitalize">{s}</span>
            </div>
          ))}
          <div className="flex items-center gap-1.5 ml-auto">
            <div className="h-2.5 w-2.5 rounded-full bg-engage-disengaged/90" />
            <span className="text-xs text-muted-foreground">significant event</span>
          </div>
        </div>
      </Card>

      {/* Event List — tabbed */}
      <Card className="bg-card border-border overflow-hidden">
        <Tabs defaultValue="significant">
          <div className="px-4 pt-3 pb-0 border-b border-border flex items-center justify-between">
            <h3 className="text-sm font-medium text-foreground">Distraction Events</h3>
            <TabsList className="h-7 mb-2">
              <TabsTrigger value="significant" className="text-xs h-6 px-3">
                Significant
                {significantEvents.length > 0 && (
                  <span className="ml-1.5 bg-engage-disengaged/20 text-engage-disengaged text-[10px] font-semibold rounded-full px-1.5 py-0">
                    {significantEvents.length}
                  </span>
                )}
              </TabsTrigger>
              <TabsTrigger value="brief" className="text-xs h-6 px-3">
                Brief
                {briefEvents.length > 0 && (
                  <span className="ml-1.5 bg-muted text-muted-foreground text-[10px] font-semibold rounded-full px-1.5 py-0">
                    {briefEvents.length}
                  </span>
                )}
              </TabsTrigger>
            </TabsList>
          </div>

          {/* Column headers */}
          <div className="flex items-center gap-4 px-4 py-1.5 text-[10px] uppercase tracking-wider text-muted-foreground/60 border-b border-border">
            <span className="w-12">Time</span>
            <span className="flex-1">Event</span>
            <span className="w-14 text-right">Duration</span>
            <span className="w-16 text-right">Confidence</span>
          </div>

          <TabsContent value="significant" className="mt-0">
            <div className="divide-y divide-border max-h-72 overflow-y-auto">
              {significantEvents.length === 0 ? (
                <div className="px-4 py-8 text-center text-sm text-muted-foreground">No significant events</div>
              ) : (
                significantEvents.map((ev, i) => {
                  const isActive = events.indexOf(ev) === activeEventIdx;
                  return (
                    <button
                      key={i}
                      onClick={() => seekTo(ev.timestamp)}
                      className={`w-full flex items-center gap-4 px-4 py-2.5 text-left text-sm transition-colors hover:bg-accent/50 ${isActive ? "bg-primary/10" : ""}`}
                    >
                      <span className="font-mono text-muted-foreground w-12">{formatTime(ev.timestamp)}</span>
                      <span className="flex items-center gap-2 flex-1 min-w-0">
                        <span className="h-2 w-2 rounded-full shrink-0 bg-engage-disengaged" />
                        <span className="text-foreground truncate">{eventLabel(ev.event_type)}</span>
                      </span>
                      <span className="text-muted-foreground w-14 text-right">{ev.duration.toFixed(1)}s</span>
                      <span className="text-muted-foreground w-16 text-right">{Math.round(ev.confidence * 100)}%</span>
                    </button>
                  );
                })
              )}
            </div>
          </TabsContent>

          <TabsContent value="brief" className="mt-0">
            <div className="divide-y divide-border max-h-72 overflow-y-auto">
              {briefEvents.length === 0 ? (
                <div className="px-4 py-8 text-center text-sm text-muted-foreground">No brief events</div>
              ) : (
                briefEvents.map((ev, i) => (
                  <button
                    key={i}
                    onClick={() => seekTo(ev.timestamp)}
                    className="w-full flex items-center gap-4 px-4 py-2 text-left text-xs transition-colors hover:bg-accent/50"
                  >
                    <span className="font-mono text-muted-foreground/70 w-12">{formatTime(ev.timestamp)}</span>
                    <span className="flex items-center gap-2 flex-1 min-w-0">
                      <span className="h-1.5 w-1.5 rounded-full shrink-0 bg-muted-foreground/40" />
                      <span className="text-muted-foreground truncate">{eventLabel(ev.event_type)}</span>
                    </span>
                    <span className="text-muted-foreground/60 w-14 text-right">{ev.duration.toFixed(1)}s</span>
                    <span className="text-muted-foreground/60 w-16 text-right">{Math.round(ev.confidence * 100)}%</span>
                  </button>
                ))
              )}
            </div>
          </TabsContent>
        </Tabs>
      </Card>
    </div>
  );
};

export default TimelinePage;
