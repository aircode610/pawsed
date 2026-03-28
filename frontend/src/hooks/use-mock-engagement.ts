import { useState, useEffect, useRef, useCallback } from "react";

type EngagementState = "engaged" | "passive" | "disengaged";

interface MockMetrics {
  state: EngagementState;
  ear: number;
  gaze: string;
  head: string;
}

const CYCLE: { state: EngagementState; duration: number; metrics: Omit<MockMetrics, "state"> }[] = [
  { state: "engaged", duration: 5000, metrics: { ear: 0.28, gaze: "On screen", head: "Forward" } },
  { state: "passive", duration: 3000, metrics: { ear: 0.24, gaze: "Drifting", head: "Tilted 12°" } },
  { state: "disengaged", duration: 2000, metrics: { ear: 0.12, gaze: "Away", head: "Turned 35°" } },
];

export function useMockEngagement() {
  const [metrics, setMetrics] = useState<MockMetrics>({
    state: "engaged",
    ...CYCLE[0].metrics,
  });
  const idx = useRef(0);

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>;

    const next = () => {
      idx.current = (idx.current + 1) % CYCLE.length;
      const c = CYCLE[idx.current];
      setMetrics({ state: c.state, ...c.metrics });
      timeout = setTimeout(next, c.duration);
    };

    timeout = setTimeout(next, CYCLE[0].duration);
    return () => clearTimeout(timeout);
  }, []);

  return metrics;
}
