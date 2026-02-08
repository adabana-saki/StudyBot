/**
 * AchievementBadge - Displays a single achievement in a compact badge format.
 * Shows locked/unlocked state, tier color, and progress.
 */
import React from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";
import { Colors } from "../constants/colors";

interface AchievementBadgeProps {
  name: string;
  description: string;
  icon: string;
  tier: "bronze" | "silver" | "gold" | "platinum";
  unlocked: boolean;
  progress: number;
  target: number;
  onPress?: () => void;
}

const TIER_COLORS: Record<string, string> = {
  bronze: "#CD7F32",
  silver: "#C0C0C0",
  gold: "#FFD700",
  platinum: "#E5E4E2",
};

const TIER_GLOW: Record<string, string> = {
  bronze: "#CD7F3230",
  silver: "#C0C0C030",
  gold: "#FFD70030",
  platinum: "#E5E4E230",
};

export default function AchievementBadge({
  name,
  description,
  icon,
  tier,
  unlocked,
  progress,
  target,
  onPress,
}: AchievementBadgeProps) {
  const tierColor = TIER_COLORS[tier] || TIER_COLORS.bronze;
  const tierGlow = TIER_GLOW[tier] || TIER_GLOW.bronze;
  const progressPercent = target > 0 ? Math.min(progress / target, 1) : 0;

  return (
    <TouchableOpacity
      style={[
        styles.container,
        unlocked && { borderColor: tierColor + "60" },
      ]}
      onPress={onPress}
      activeOpacity={0.7}
      disabled={!onPress}
    >
      {/* Icon */}
      <View
        style={[
          styles.iconContainer,
          unlocked
            ? { backgroundColor: tierGlow, borderColor: tierColor }
            : styles.iconLocked,
        ]}
      >
        <Text style={[styles.icon, !unlocked && styles.iconLockedText]}>
          {unlocked ? icon : "\u{1F512}"}
        </Text>
      </View>

      {/* Name */}
      <Text
        style={[styles.name, !unlocked && styles.textLocked]}
        numberOfLines={2}
      >
        {name}
      </Text>

      {/* Progress bar (shown when not yet unlocked) */}
      {!unlocked && target > 0 && (
        <View style={styles.progressContainer}>
          <View style={styles.progressTrack}>
            <View
              style={[
                styles.progressFill,
                {
                  width: `${progressPercent * 100}%`,
                  backgroundColor: tierColor,
                },
              ]}
            />
          </View>
          <Text style={styles.progressText}>
            {progress}/{target}
          </Text>
        </View>
      )}

      {/* Unlocked indicator */}
      {unlocked && (
        <View style={[styles.unlockedBadge, { backgroundColor: tierColor }]}>
          <Text style={styles.checkmark}>{"\u2713"}</Text>
        </View>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    width: "30%",
    backgroundColor: Colors.card,
    borderRadius: 12,
    padding: 12,
    alignItems: "center",
    borderWidth: 1,
    borderColor: Colors.border,
    marginBottom: 12,
    position: "relative",
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 8,
    borderWidth: 2,
    borderColor: "transparent",
  },
  iconLocked: {
    backgroundColor: Colors.cardAlt,
    borderColor: Colors.border,
  },
  icon: {
    fontSize: 22,
  },
  iconLockedText: {
    opacity: 0.5,
    fontSize: 18,
  },
  name: {
    fontSize: 11,
    fontWeight: "600",
    color: Colors.textPrimary,
    textAlign: "center",
    lineHeight: 14,
  },
  textLocked: {
    color: Colors.textDisabled,
  },
  progressContainer: {
    width: "100%",
    marginTop: 6,
    alignItems: "center",
  },
  progressTrack: {
    width: "100%",
    height: 3,
    backgroundColor: Colors.cardAlt,
    borderRadius: 2,
    overflow: "hidden",
  },
  progressFill: {
    height: 3,
    borderRadius: 2,
  },
  progressText: {
    fontSize: 9,
    color: Colors.textMuted,
    marginTop: 2,
  },
  unlockedBadge: {
    position: "absolute",
    top: 6,
    right: 6,
    width: 18,
    height: 18,
    borderRadius: 9,
    justifyContent: "center",
    alignItems: "center",
  },
  checkmark: {
    fontSize: 11,
    color: "#000",
    fontWeight: "bold",
  },
});
