"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getToken } from "@/lib/auth";
import type { StudyBotEvent } from "@/lib/events";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type EventCallback = (event: StudyBotEvent) => void;

interface UseEventStreamOptions {
  guildId: string | null;
  enabled?: boolean;
}

export function useEventStream({ guildId, enabled = true }: UseEventStreamOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const listenersRef = useRef<Map<string, Set<EventCallback>>>(new Map());
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelayRef = useRef(1000);

  const on = useCallback((eventType: string, callback: EventCallback) => {
    if (!listenersRef.current.has(eventType)) {
      listenersRef.current.set(eventType, new Set());
    }
    listenersRef.current.get(eventType)!.add(callback);
    return () => {
      listenersRef.current.get(eventType)?.delete(callback);
    };
  }, []);

  const off = useCallback((eventType: string, callback?: EventCallback) => {
    if (callback) {
      listenersRef.current.get(eventType)?.delete(callback);
    } else {
      listenersRef.current.delete(eventType);
    }
  }, []);

  useEffect(() => {
    if (!enabled || !guildId) return;

    const token = getToken();
    if (!token) return;

    function connect() {
      const url = `${API_URL}/api/events/stream?guild_id=${guildId}&token=${token}`;
      const es = new EventSource(url);
      eventSourceRef.current = es;

      es.onopen = () => {
        setIsConnected(true);
        reconnectDelayRef.current = 1000;
      };

      es.onerror = () => {
        setIsConnected(false);
        es.close();
        eventSourceRef.current = null;

        // Exponential backoff reconnect
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, reconnectDelayRef.current);
        reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 2, 30000);
      };

      // Listen for all known event types
      const eventTypes = [
        "study_start", "study_end", "pomodoro_complete", "study_log",
        "xp_gain", "level_up", "achievement_unlock", "todo_complete",
        "focus_start", "focus_end", "lock_start", "lock_end",
        "raid_join", "raid_complete", "flashcard_review",
        "buddy_match", "challenge_join", "challenge_checkin",
        "session_sync", "insights_ready",
        // Phase 8
        "social_reaction", "social_comment",
        "battle_start", "battle_score_update", "battle_complete",
        "room_join", "room_leave", "room_goal_reached",
      ];

      for (const type of eventTypes) {
        es.addEventListener(type, (e: MessageEvent) => {
          try {
            const parsed = JSON.parse(e.data) as StudyBotEvent;
            const callbacks = listenersRef.current.get(type);
            if (callbacks) {
              callbacks.forEach((cb) => cb(parsed));
            }
            // Also notify wildcard listeners
            const wildcardCallbacks = listenersRef.current.get("*");
            if (wildcardCallbacks) {
              wildcardCallbacks.forEach((cb) => cb(parsed));
            }
          } catch {
            // ignore parse errors
          }
        });
      }
    }

    connect();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      setIsConnected(false);
    };
  }, [guildId, enabled]);

  return { isConnected, on, off };
}
