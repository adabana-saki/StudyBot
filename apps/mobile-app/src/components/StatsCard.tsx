/**
 * StatsCard - Displays a single statistic with an icon, label, and value.
 * Used in the Dashboard screen stats row.
 */
import React from "react";
import { View, Text, StyleSheet, ViewStyle } from "react-native";
import { Colors } from "../constants/colors";

interface StatsCardProps {
  label: string;
  value: string | number;
  icon: string;
  color?: string;
  style?: ViewStyle;
}

export default function StatsCard({
  label,
  value,
  icon,
  color = Colors.primary,
  style,
}: StatsCardProps) {
  return (
    <View style={[styles.container, style]}>
      <View style={[styles.iconContainer, { backgroundColor: color + "20" }]}>
        <Text style={[styles.icon, { color }]}>{icon}</Text>
      </View>
      <Text style={styles.value}>{value}</Text>
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.card,
    borderRadius: 12,
    padding: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: Colors.border,
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 8,
  },
  icon: {
    fontSize: 20,
  },
  value: {
    fontSize: 20,
    fontWeight: "700",
    color: Colors.textPrimary,
    marginBottom: 2,
  },
  label: {
    fontSize: 11,
    color: Colors.textMuted,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
});
