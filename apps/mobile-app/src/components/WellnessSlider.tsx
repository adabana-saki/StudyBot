/**
 * WellnessSlider - A 1-5 rating selector for mood, energy, and stress levels.
 * Displays as a row of tappable circles with labels.
 */
import React from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";
import { Colors } from "../constants/colors";

interface WellnessSliderProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  labels?: string[];
  color?: string;
  icon?: string;
}

const DEFAULT_LABELS = ["1", "2", "3", "4", "5"];

const MOOD_LABELS = [
  "\u{1F61E}", // Sad
  "\u{1F615}", // Confused
  "\u{1F610}", // Neutral
  "\u{1F642}", // Slightly Smiling
  "\u{1F604}", // Grinning
];

const ENERGY_LABELS = [
  "\u{1F634}", // Sleeping
  "\u{1F971}", // Yawning
  "\u{1F610}", // Neutral
  "\u{26A1}", // Lightning
  "\u{1F525}", // Fire
];

const STRESS_LABELS = [
  "\u{1F60C}", // Relieved
  "\u{1F642}", // Slightly Smiling
  "\u{1F610}", // Neutral
  "\u{1F630}", // Cold Sweat
  "\u{1F4A5}", // Explosion
];

export const WELLNESS_LABEL_PRESETS = {
  mood: MOOD_LABELS,
  energy: ENERGY_LABELS,
  stress: STRESS_LABELS,
};

export default function WellnessSlider({
  label,
  value,
  onChange,
  labels = DEFAULT_LABELS,
  color = Colors.primary,
  icon,
}: WellnessSliderProps) {
  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        {icon && <Text style={styles.headerIcon}>{icon}</Text>}
        <Text style={styles.label}>{label}</Text>
        <Text style={[styles.valueText, { color }]}>{value}/5</Text>
      </View>

      <View style={styles.sliderRow}>
        {[1, 2, 3, 4, 5].map((level) => {
          const isSelected = level === value;
          const isBelow = level <= value;

          return (
            <TouchableOpacity
              key={level}
              style={[
                styles.option,
                isBelow && { borderColor: color + "60" },
                isSelected && {
                  backgroundColor: color + "20",
                  borderColor: color,
                },
              ]}
              onPress={() => onChange(level)}
              activeOpacity={0.6}
            >
              <Text
                style={[
                  styles.optionLabel,
                  isSelected && { color: Colors.textPrimary },
                ]}
              >
                {labels[level - 1] || level.toString()}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      <View style={styles.descriptionRow}>
        <Text style={styles.descriptionText}>Low</Text>
        <Text style={styles.descriptionText}>High</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 20,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 10,
  },
  headerIcon: {
    fontSize: 18,
    marginRight: 8,
  },
  label: {
    fontSize: 16,
    fontWeight: "600",
    color: Colors.textPrimary,
    flex: 1,
  },
  valueText: {
    fontSize: 14,
    fontWeight: "700",
  },
  sliderRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 8,
  },
  option: {
    flex: 1,
    height: 56,
    borderRadius: 12,
    backgroundColor: Colors.card,
    borderWidth: 2,
    borderColor: Colors.border,
    justifyContent: "center",
    alignItems: "center",
  },
  optionLabel: {
    fontSize: 22,
    color: Colors.textMuted,
  },
  descriptionRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 4,
    paddingHorizontal: 4,
  },
  descriptionText: {
    fontSize: 11,
    color: Colors.textDisabled,
  },
});
