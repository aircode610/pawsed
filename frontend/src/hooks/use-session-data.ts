import { useQuery } from "@tanstack/react-query";
import { getSession } from "@/lib/api";
import type { SessionData } from "@/lib/types";

const EMPTY_SESSION: SessionData = {
  session_id: "",
  created_at: "",
  duration: 0,
  video_filename: "",
  analytics: {
    focus_time_pct: 0,
    distraction_time_pct: 0,
    longest_focus_streak: 0,
    distraction_breakdown: {},
    engagement_curve: [],
    danger_zones: [],
  },
  events: [],
  engagement_states: [],
  has_landmarks: false,
};

export function useSessionData(id: string | undefined) {
  const query = useQuery<SessionData>({
    queryKey: ["session", id],
    queryFn: () => getSession(id!),
    enabled: !!id,
    retry: 1,
  });

  return {
    data: query.data ?? EMPTY_SESSION,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
