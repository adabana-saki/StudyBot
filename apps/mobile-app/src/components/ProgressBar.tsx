/**
 * ProgressBar - Animated horizontal progress bar.
 * Used for XP progress, flashcard progress, and other indicators.
 */
import React, { useEffect, useRef } from "react";
import { View, Text, StyleSheet, Animated, ViewStyle } from "react-native";
import { Colors } from "../constants/colors";

interface ProgressBarProps {
  /** Current progress value. */
  current: number;
  /** Maximum value (100% completion). */
  max: number;
  /** Color of the filled portion. */
  color?: string;
  /** Background color of the track. */
  trackColor?: string;
  /** Height of the bar in pixels. */
  height?: number;
  /** Whether to show the label (e.g., "75%"). */
  showLabel?: boolean;
  /** Custom label text. Overrides the default percentage. */
  label?: string;
  /** Whether to animate the progress on change. */
  animated?: boolean;
  /** Container style overrides. */
  style?: ViewStyle;
}

export default function ProgressBar({
  current,
  max,
  color = Colors.xpBar,
  trackColor = Colors.xpBarBackground,
  height = 8,
  showLabel = false,
  label,
  animated = true,
  style,
}: ProgressBarProps) {
  const progress = max > 0 ? Math.min(current / max, 1) : 0;
  const percentage = Math.round(progress * 100);
  const animatedWidth = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (animated) {
      Animated.timing(animatedWidth, {
        toValue: progress,
        duration: 600,
        useNativeDriver: false,
      }).start();
    } else {
      animatedWidth.setValue(progress);
    }
  }, [progress, animated, animatedWidth]);

  const widthInterpolation = animatedWidth.interpolate({
    inputRange: [0, 1],
    outputRange: ["0%", "100%"],
  });

  return (
    <View style={style}>
      {showLabel && (
        <View style={styles.labelContainer}>
          <Text style={styles.labelText}>
            {label || `${percentage}%`}
          </Text>
          <Text style={styles.labelDetail}>
            {current.toLocaleString()} / {max.toLocaleString()}
          </Text>
        </View>
      )}
      <View
        style={[
          styles.track,
          { height, backgroundColor: trackColor, borderRadius: height / 2 },
        ]}
      >
        <Animated.View
          style={[
            styles.fill,
            {
              width: widthInterpolation,
              height,
              backgroundColor: color,
              borderRadius: height / 2,
            },
          ]}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  track: {
    width: "100%",
    overflow: "hidden",
  },
  fill: {
    position: "absolute",
    left: 0,
    top: 0,
  },
  labelContainer: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 4,
  },
  labelText: {
    fontSize: 12,
    fontWeight: "600",
    color: Colors.textSecondary,
  },
  labelDetail: {
    fontSize: 12,
    color: Colors.textMuted,
  },
});
