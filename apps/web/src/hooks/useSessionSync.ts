"use client";

import { useCallback, useEffect, useState } from "react";
import { getActiveSessions, ActiveSession } from "@/lib/api";
import { useEventStream } from "@/hooks/useEventStream";

interface UseSessionSyncOptions {
  guildId: string | null;
}

export function useSessionSync({ guildId }: UseSessionSyncOptions) {
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [loading, setLoading] = useState(true);
  const { on } = useEventStream({ guildId, enabled: !!guildId });

  const refresh = useCallback(async () => {
    try {
      const data = await getActiveSessions();
      setSessions(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Listen for session sync events
  useEffect(() => {
    const unsub = on("session_sync", () => {
      refresh();
    });
    return unsub;
  }, [on, refresh]);

  return { sessions, loading, refresh };
}
