/**
 * StudyTimerScreen - Pomodoro timer with circular display,
 * start/pause/stop controls, and local notifications.
 */
import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  AppState,
  AppStateStatus,
} from "react-native";
import { Colors } from "../constants/colors";
import { POMODORO } from "../constants/config";
import {
  scheduleLocalNotification,
  cancelNotification,
} from "../lib/notifications";
import TimerCircle from "../components/TimerCircle";

type TimerPhase = "work" | "shortBreak" | "longBreak";

interface TimerState {
  phase: TimerPhase;
  remainingSeconds: number;
  totalSeconds: number;
  isRunning: boolean;
  cycle: number;
  totalCycles: number;
  sessionsCompleted: number;
}

export default function StudyTimerScreen() {
  const [timer, setTimer] = useState<TimerState>({
    phase: "work",
    remainingSeconds: POMODORO.WORK_DURATION,
    totalSeconds: POMODORO.WORK_DURATION,
    isRunning: false,
    cycle: 0,
    totalCycles: POMODORO.CYCLES_BEFORE_LONG_BREAK,
    sessionsCompleted: 0,
  });

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const notificationIdRef = useRef<string | null>(null);
  const backgroundTimeRef = useRef<number>(0);

  // Handle app state changes (background/foreground)
  useEffect(() => {
    const handleAppStateChange = (nextState: AppStateStatus) => {
      if (nextState === "background" && timer.isRunning) {
        backgroundTimeRef.current = Date.now();
      } else if (nextState === "active" && timer.isRunning) {
        const elapsed = Math.floor(
          (Date.now() - backgroundTimeRef.current) / 1000
        );
        if (elapsed > 0) {
          setTimer((prev) => ({
            ...prev,
            remainingSeconds: Math.max(0, prev.remainingSeconds - elapsed),
          }));
        }
      }
    };

    const subscription = AppState.addEventListener(
      "change",
      handleAppStateChange
    );
    return () => subscription.remove();
  }, [timer.isRunning]);

  // Timer countdown logic
  useEffect(() => {
    if (timer.isRunning && timer.remainingSeconds > 0) {
      intervalRef.current = setInterval(() => {
        setTimer((prev) => {
          if (prev.remainingSeconds <= 1) {
            return { ...prev, remainingSeconds: 0 };
          }
          return { ...prev, remainingSeconds: prev.remainingSeconds - 1 };
        });
      }, 1000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [timer.isRunning, timer.remainingSeconds > 0]);

  // Handle timer completion
  useEffect(() => {
    if (timer.remainingSeconds === 0 && timer.isRunning) {
      handleTimerComplete();
    }
  }, [timer.remainingSeconds, timer.isRunning]);

  const handleTimerComplete = useCallback(async () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    // Cancel any pending notification
    if (notificationIdRef.current) {
      await cancelNotification(notificationIdRef.current);
      notificationIdRef.current = null;
    }

    setTimer((prev) => {
      const wasWork = prev.phase === "work";
      const newSessionsCompleted = wasWork
        ? prev.sessionsCompleted + 1
        : prev.sessionsCompleted;
      const newCycle = wasWork ? prev.cycle + 1 : prev.cycle;

      // Determine next phase
      let nextPhase: TimerPhase;
      let nextDuration: number;

      if (wasWork) {
        if (newCycle >= prev.totalCycles) {
          nextPhase = "longBreak";
          nextDuration = POMODORO.LONG_BREAK;
        } else {
          nextPhase = "shortBreak";
          nextDuration = POMODORO.SHORT_BREAK;
        }
      } else {
        nextPhase = "work";
        nextDuration = POMODORO.WORK_DURATION;
      }

      // Reset cycle counter after long break
      const finalCycle =
        prev.phase === "longBreak" ? 0 : newCycle;

      // Send a local notification
      const title = wasWork
        ? "Work session complete!"
        : "Break is over!";
      const body = wasWork
        ? `Great job! Take a ${nextPhase === "longBreak" ? "long" : "short"} break.`
        : "Time to get back to studying!";

      scheduleLocalNotification({
        title,
        body,
        channelId: "timer",
      }).catch(console.error);

      return {
        ...prev,
        phase: nextPhase,
        remainingSeconds: nextDuration,
        totalSeconds: nextDuration,
        isRunning: false,
        cycle: finalCycle,
        sessionsCompleted: newSessionsCompleted,
      };
    });
  }, []);

  const startTimer = useCallback(async () => {
    setTimer((prev) => ({ ...prev, isRunning: true }));

    // Schedule a notification for when the timer ends
    try {
      const id = await scheduleLocalNotification({
        title:
          timer.phase === "work"
            ? "Focus session complete!"
            : "Break is over!",
        body:
          timer.phase === "work"
            ? "Great work! Time for a break."
            : "Ready to focus again?",
        triggerSeconds: timer.remainingSeconds,
        channelId: "timer",
      });
      notificationIdRef.current = id;
    } catch {
      // Notification scheduling failed; timer still works
    }
  }, [timer.phase, timer.remainingSeconds]);

  const pauseTimer = useCallback(async () => {
    setTimer((prev) => ({ ...prev, isRunning: false }));

    // Cancel the scheduled notification
    if (notificationIdRef.current) {
      await cancelNotification(notificationIdRef.current);
      notificationIdRef.current = null;
    }
  }, []);

  const stopTimer = useCallback(() => {
    Alert.alert(
      "Stop Timer",
      "Are you sure you want to stop the current session?",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Stop",
          style: "destructive",
          onPress: async () => {
            if (intervalRef.current) {
              clearInterval(intervalRef.current);
              intervalRef.current = null;
            }
            if (notificationIdRef.current) {
              await cancelNotification(notificationIdRef.current);
              notificationIdRef.current = null;
            }
            setTimer({
              phase: "work",
              remainingSeconds: POMODORO.WORK_DURATION,
              totalSeconds: POMODORO.WORK_DURATION,
              isRunning: false,
              cycle: 0,
              totalCycles: POMODORO.CYCLES_BEFORE_LONG_BREAK,
              sessionsCompleted: timer.sessionsCompleted,
            });
          },
        },
      ]
    );
  }, [timer.sessionsCompleted]);

  const skipPhase = useCallback(() => {
    handleTimerComplete();
  }, [handleTimerComplete]);

  const getPhaseLabel = (): string => {
    switch (timer.phase) {
      case "work":
        return "Focus Time";
      case "shortBreak":
        return "Short Break";
      case "longBreak":
        return "Long Break";
    }
  };

  const getPhaseColor = (): string => {
    return timer.phase === "work" ? Colors.timer : Colors.timerBreak;
  };

  return (
    <View style={styles.container}>
      {/* Phase label */}
      <View style={styles.phaseContainer}>
        <Text style={[styles.phaseLabel, { color: getPhaseColor() }]}>
          {getPhaseLabel()}
        </Text>
        <Text style={styles.sessionCount}>
          Session {timer.sessionsCompleted + (timer.phase === "work" ? 1 : 0)}
        </Text>
      </View>

      {/* Timer circle */}
      <View style={styles.timerContainer}>
        <TimerCircle
          remainingSeconds={timer.remainingSeconds}
          totalSeconds={timer.totalSeconds}
          isBreak={timer.phase !== "work"}
          isRunning={timer.isRunning}
          cycle={timer.cycle}
          totalCycles={timer.totalCycles}
        />
      </View>

      {/* Controls */}
      <View style={styles.controls}>
        {/* Stop button */}
        <TouchableOpacity
          style={styles.secondaryButton}
          onPress={stopTimer}
          activeOpacity={0.7}
        >
          <Text style={styles.secondaryButtonIcon}>{"\u{23F9}\u{FE0F}"}</Text>
          <Text style={styles.secondaryButtonText}>Stop</Text>
        </TouchableOpacity>

        {/* Start/Pause button */}
        <TouchableOpacity
          style={[styles.primaryButton, { backgroundColor: getPhaseColor() }]}
          onPress={timer.isRunning ? pauseTimer : startTimer}
          activeOpacity={0.8}
        >
          <Text style={styles.primaryButtonIcon}>
            {timer.isRunning ? "\u{23F8}\u{FE0F}" : "\u{25B6}\u{FE0F}"}
          </Text>
          <Text style={styles.primaryButtonText}>
            {timer.isRunning ? "Pause" : "Start"}
          </Text>
        </TouchableOpacity>

        {/* Skip button */}
        <TouchableOpacity
          style={styles.secondaryButton}
          onPress={skipPhase}
          activeOpacity={0.7}
        >
          <Text style={styles.secondaryButtonIcon}>{"\u{23ED}\u{FE0F}"}</Text>
          <Text style={styles.secondaryButtonText}>Skip</Text>
        </TouchableOpacity>
      </View>

      {/* Today's stats */}
      <View style={styles.todayStats}>
        <View style={styles.todayStat}>
          <Text style={styles.todayStatValue}>
            {timer.sessionsCompleted}
          </Text>
          <Text style={styles.todayStatLabel}>Sessions</Text>
        </View>
        <View style={styles.todayStatDivider} />
        <View style={styles.todayStat}>
          <Text style={styles.todayStatValue}>
            {timer.sessionsCompleted * 25}m
          </Text>
          <Text style={styles.todayStatLabel}>Total Focus</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
    paddingHorizontal: 24,
    paddingTop: 20,
  },
  phaseContainer: {
    alignItems: "center",
    marginBottom: 20,
  },
  phaseLabel: {
    fontSize: 22,
    fontWeight: "700",
  },
  sessionCount: {
    fontSize: 13,
    color: Colors.textMuted,
    marginTop: 4,
  },
  timerContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  controls: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 16,
    paddingVertical: 24,
  },
  primaryButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 16,
    paddingHorizontal: 36,
    borderRadius: 28,
    minWidth: 140,
  },
  primaryButtonIcon: {
    fontSize: 18,
    marginRight: 8,
  },
  primaryButtonText: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "700",
  },
  secondaryButton: {
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  secondaryButtonIcon: {
    fontSize: 22,
    marginBottom: 4,
  },
  secondaryButtonText: {
    fontSize: 12,
    color: Colors.textMuted,
    fontWeight: "600",
  },
  todayStats: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: Colors.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  todayStat: {
    alignItems: "center",
    paddingHorizontal: 24,
  },
  todayStatValue: {
    fontSize: 20,
    fontWeight: "700",
    color: Colors.textPrimary,
  },
  todayStatLabel: {
    fontSize: 12,
    color: Colors.textMuted,
    marginTop: 2,
  },
  todayStatDivider: {
    width: 1,
    height: 30,
    backgroundColor: Colors.border,
  },
});
