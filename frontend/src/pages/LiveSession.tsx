import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, ArrowUpRight, User, Camera, CameraOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useMockEngagement } from "@/hooks/use-mock-engagement";

const BORDER_COLORS: Record<string, string> = {
  engaged: "border-engage-engaged",
  passive: "border-engage-passive",
  disengaged: "border-engage-disengaged",
};

const BADGE_BG: Record<string, string> = {
  engaged: "bg-engage-engaged",
  passive: "bg-engage-passive",
  disengaged: "bg-engage-disengaged",
};

function useElapsed(running: boolean) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!running) return;
    const interval = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(interval);
  }, [running]);
  const m = Math.floor(elapsed / 60);
  const s = elapsed % 60;
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

const LiveSessionPage = () => {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraState, setCameraState] = useState<"loading" | "active" | "denied" | "unavailable">("loading");
  const [stopping, setStopping] = useState(false);
  const { state, ear, gaze, head } = useMockEngagement();
  const elapsed = useElapsed(cameraState === "active" && !stopping);

  useEffect(() => {
    let cancelled = false;
    navigator.mediaDevices
      .getUserMedia({ video: true })
      .then((stream) => {
        if (cancelled) { stream.getTracks().forEach((t) => t.stop()); return; }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setCameraState("active");
      })
      .catch((err) => {
        if (cancelled) return;
        if (err.name === "NotAllowedError") setCameraState("denied");
        else setCameraState("unavailable");
      });
    return () => { cancelled = true; streamRef.current?.getTracks().forEach((t) => t.stop()); };
  }, []);

  const stopSession = useCallback(() => {
    setStopping(true);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    setTimeout(() => navigate("/sessions"), 1500);
  }, [navigate]);

  if (cameraState === "denied") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-6rem)] gap-4 text-center px-4">
        <CameraOff className="h-16 w-16 text-muted-foreground" />
        <h2 className="text-xl font-semibold text-foreground">Camera Access Denied</h2>
        <p className="text-sm text-muted-foreground max-w-sm">
          Pawsed needs camera access to track engagement. Please allow camera permission in your browser settings and reload.
        </p>
        <Button variant="outline" onClick={() => navigate("/")}>Go Back</Button>
      </div>
    );
  }

  if (cameraState === "unavailable") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-6rem)] gap-4 text-center px-4">
        <CameraOff className="h-16 w-16 text-muted-foreground" />
        <h2 className="text-xl font-semibold text-foreground">No Camera Found</h2>
        <p className="text-sm text-muted-foreground max-w-sm">
          We couldn't detect a camera on your device. Please connect a webcam and try again.
        </p>
        <Button variant="outline" onClick={() => navigate("/")}>Go Back</Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-6rem)] gap-6 px-4">
      {/* Video container */}
      <div className="relative w-full max-w-[900px]">
        <div
          className={`rounded-xl border-4 overflow-hidden transition-colors duration-500 ${
            cameraState === "active" ? BORDER_COLORS[state] : "border-border"
          }`}
        >
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            className="w-full aspect-video bg-background object-cover mirror"
            style={{ transform: "scaleX(-1)" }}
          />

          {cameraState === "loading" && (
            <div className="absolute inset-0 flex items-center justify-center bg-background">
              <Camera className="h-12 w-12 text-muted-foreground animate-pulse" />
            </div>
          )}

          {stopping && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm">
              <p className="text-foreground font-medium animate-pulse">Processing session...</p>
            </div>
          )}
        </div>

        {/* Top-left: Timer */}
        {cameraState === "active" && !stopping && (
          <div className="absolute top-3 left-3 flex items-center gap-2 rounded-full bg-background/70 backdrop-blur px-3 py-1.5">
            <span className="h-2 w-2 rounded-full bg-destructive animate-pulse" />
            <span className="text-xs font-mono text-foreground">{elapsed}</span>
          </div>
        )}

        {/* Top-right: State badge */}
        {cameraState === "active" && !stopping && (
          <div
            className={`absolute top-3 right-3 rounded-full px-3 py-1.5 text-xs font-semibold backdrop-blur capitalize transition-colors duration-500 ${BADGE_BG[state]} text-foreground`}
          >
            {state}
          </div>
        )}

        {/* Bottom-left: Metrics */}
        {cameraState === "active" && !stopping && (
          <div className="absolute bottom-3 left-3 rounded-lg bg-background/70 backdrop-blur px-3 py-2 space-y-1">
            <div className="flex items-center gap-2 text-xs text-foreground">
              <Eye className="h-3 w-3 text-muted-foreground" />
              <span className="text-muted-foreground">EAR:</span>
              <span className="font-mono">{ear.toFixed(2)}</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-foreground">
              <ArrowUpRight className="h-3 w-3 text-muted-foreground" />
              <span className="text-muted-foreground">Gaze:</span>
              <span>{gaze}</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-foreground">
              <User className="h-3 w-3 text-muted-foreground" />
              <span className="text-muted-foreground">Head:</span>
              <span>{head}</span>
            </div>
          </div>
        )}
      </div>

      {/* Controls */}
      {cameraState === "active" && !stopping && (
        <Button variant="destructive" size="lg" onClick={stopSession}>
          Stop Session
        </Button>
      )}
    </div>
  );
};

export default LiveSessionPage;
