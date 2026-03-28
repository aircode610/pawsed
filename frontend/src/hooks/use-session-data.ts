import { useQuery } from "@tanstack/react-query";
import { getSession } from "@/lib/api";
import { mockSession } from "@/lib/mock-data";
import type { SessionData } from "@/lib/types";

export function useSessionData(id: string | undefined) {
  const query = useQuery<SessionData>({
    queryKey: ["session", id],
    queryFn: () => getSession(id!),
    enabled: !!id,
    retry: false,
  });

  const isUsingMock = query.isError || !id;
  const data: SessionData = query.data ?? (mockSession as unknown as SessionData);

  return {
    data,
    isLoading: query.isLoading && !isUsingMock,
    isUsingMock,
  };
}
