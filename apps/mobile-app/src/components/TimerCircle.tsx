/**
 * TimerCircle - Circular timer display with animated progress ring.
 * Used in the Study Timer screen for Pomodoro sessions.
 */
import React, { useEffect, useRef } from "react";
import { View, Text, StyleSheet, Animated, Dimensions } from "react-native";
import { Colors } from "../constants/colors";

const SCREEN_WIDTH = Dimensions.get("window").width;
const CIRCLE_SIZE = Math.min(SCREEN_WIDTH - 80, 280);

interface TimerCircleProps {
  /** Remaining time in seconds. */
  remainingSeconds: number;
  /** Total duration in seconds. */
  totalSeconds: number;
  /** Whether the timer is in a break session. */
  isBreak: boolean;
  /** Whether the timer is currently running. */
  isRunning: boolean;
  /** Current Pomodoro cycle number. */
  cycle: number;
  /** Total cycles before long break. */
  totalCycles: number;
}

/**
 * Format seconds into MM:SS display.
 */
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

export default function TimerCircle({
  remainingSeconds,
  totalSeconds,
  isBreak,
  isRunning,
  cycle,
  totalCycles,
}: TimerCircleProps) {
  const progress =
    totalSeconds > 0 ? 1 - remainingSeconds / totalSeconds : 0;
  const pulseAnimation = useRef(new Animated.Value(1)).current;
  const color = isBreak ? Colors.timerBreak : Colors.timer;

  // Pulse animation when running
  useEffect(() => {
    if (isRunning) {
      const pulse = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnimation, {
            toValue: 1.05,
            duration: 1000,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnimation, {
            toValue: 1,
            duration: 1000,
            useNativeDriver: true,
          }),
        ])
      );
      pulse.start();
      return () => pulse.stop();
    } else {
      pulseAnimation.setValue(1);
    }
  }, [isRunning, pulseAnimation]);

  // Create SVG-like circle segments using views
  const progressDegrees = progress * 360;

  return (
    <Animated.View
      style={[styles.container, { transform: [{ scale: pulseAnimation }] }]}
    >
      {/* Background circle */}
      <View style={[styles.circle, styles.backgroundCircle]}>
        {/* Progress ring - using a simple approach with background + overlay */}
        <View style={styles.progressContainer}>
          {/* Left half */}
          <View style={styles.halfContainer}>
            <View
              style={[
                styles.halfCircle,
                styles.leftHalf,
                {
                  backgroundColor:
                    progressDegrees > 180 ? color : "transparent",
                  transform: [
                    {
                      rotate:
                        progressDegrees > 180
                          ? `${progressDegrees - 180}deg`
                          : "0deg",
                    },
                  ],
                },
              ]}
            />
          </View>
          {/* Right half */}
          <View style={[styles.halfContainer, styles.rightContainer]}>
            <View
              style={[
                styles.halfCircle,
                styles.rightHalf,
                {
                  backgroundColor: color,
                  transform: [
                    {
                      rotate:
                        progressDegrees <= 180
                          ? `${progressDegrees}deg`
                          : "180deg",
                    },
                  ],
                },
              ]}
            />
          </View>
        </View>

        {/* Inner circle (makes it a ring) */}
        <View style={styles.innerCircle}>
          {/* Timer text */}
          <Text style={[styles.timeText, { color }]}>
            {formatTime(remainingSeconds)}
          </Text>

          {/* Session label */}
          <Text style={styles.sessionLabel}>
            {isBreak ? "BREAK" : "FOCUS"}
          </Text>

          {/* Cycle indicator */}
          <View style={styles.cycleContainer}>
            {Array.from({ length: totalCycles }, (_, i) => (
              <View
                key={i}
                style={[
                  styles.cycleDot,
                  {
                    backgroundColor:
                      i < cycle ? color : Colors.cardAlt,
                  },
                ]}
              />
            ))}
          </View>
        </View>
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    justifyContent: "center",
  },
  circle: {
    width: CIRCLE_SIZE,
    height: CIRCLE_SIZE,
    borderRadius: CIRCLE_SIZE / 2,
    justifyContent: "center",
    alignItems: "center",
  },
  backgroundCircle: {
    backgroundColor: Colors.cardAlt + "40",
    borderWidth: 3,
    borderColor: Colors.border,
  },
  progressContainer: {
    position: "absolute",
    width: CIRCLE_SIZE,
    height: CIRCLE_SIZE,
    borderRadius: CIRCLE_SIZE / 2,
    overflow: "hidden",
    flexDirection: "row",
  },
  halfContainer: {
    width: CIRCLE_SIZE / 2,
    height: CIRCLE_SIZE,
    overflow: "hidden",
  },
  rightContainer: {
    // Right side
  },
  halfCircle: {
    width: CIRCLE_SIZE,
    height: CIRCLE_SIZE,
    borderRadius: CIRCLE_SIZE / 2,
    position: "absolute",
  },
  leftHalf: {
    left: 0,
    transformOrigin: `${CIRCLE_SIZE / 2}px ${CIRCLE_SIZE / 2}px`,
  },
  rightHalf: {
    right: 0,
    transformOrigin: `0px ${CIRCLE_SIZE / 2}px`,
  },
  innerCircle: {
    width: CIRCLE_SIZE - 24,
    height: CIRCLE_SIZE - 24,
    borderRadius: (CIRCLE_SIZE - 24) / 2,
    backgroundColor: Colors.background,
    justifyContent: "center",
    alignItems: "center",
    zIndex: 10,
  },
  timeText: {
    fontSize: 48,
    fontWeight: "200",
    fontVariant: ["tabular-nums"],
  },
  sessionLabel: {
    fontSize: 14,
    fontWeight: "700",
    letterSpacing: 3,
    color: Colors.textMuted,
    marginTop: 4,
  },
  cycleContainer: {
    flexDirection: "row",
    gap: 8,
    marginTop: 16,
  },
  cycleDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
});
