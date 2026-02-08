/**
 * WellnessScreen - Mood, energy, and stress logging with history view.
 */
import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  RefreshControl,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { Colors } from "../constants/colors";
import { useApiQuery, useApiMutation } from "../hooks/useApi";
import {
  getWellnessEntries,
  submitWellnessEntry,
  WellnessEntry,
} from "../lib/api";
import WellnessSlider, {
  WELLNESS_LABEL_PRESETS,
} from "../components/WellnessSlider";

type ViewMode = "log" | "history";

export default function WellnessScreen() {
  const [viewMode, setViewMode] = useState<ViewMode>("log");
  const [mood, setMood] = useState(3);
  const [energy, setEnergy] = useState(3);
  const [stress, setStress] = useState(3);
  const [note, setNote] = useState("");

  const {
    data: entries,
    isLoading: entriesLoading,
    refetch: refetchEntries,
  } = useApiQuery<WellnessEntry[]>(() => getWellnessEntries(), []);

  const { mutate: submitEntry, isLoading: isSubmitting } = useApiMutation<
    WellnessEntry,
    { mood: number; energy: number; stress: number; note?: string }
  >(
    (data) => submitWellnessEntry(data),
    {
      onSuccess: () => {
        Alert.alert("Logged!", "Your wellness check-in has been saved.", [
          {
            text: "View History",
            onPress: () => {
              setViewMode("history");
              refetchEntries();
            },
          },
          { text: "OK" },
        ]);
        // Reset form
        setMood(3);
        setEnergy(3);
        setStress(3);
        setNote("");
      },
      onError: (error) => {
        Alert.alert("Error", error);
      },
    }
  );

  const handleSubmit = useCallback(() => {
    submitEntry({
      mood,
      energy,
      stress,
      note: note.trim() || undefined,
    });
  }, [mood, energy, stress, note, submitEntry]);

  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

    if (diffHours < 1) return "Just now";
    if (diffHours < 24) return `${diffHours}h ago`;

    return date.toLocaleDateString("en", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };

  const getMoodEmoji = (value: number): string => {
    return WELLNESS_LABEL_PRESETS.mood[value - 1] || "";
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      {/* Tab switcher */}
      <View style={styles.tabRow}>
        <TouchableOpacity
          style={[styles.tab, viewMode === "log" && styles.tabActive]}
          onPress={() => setViewMode("log")}
          activeOpacity={0.7}
        >
          <Text
            style={[
              styles.tabText,
              viewMode === "log" && styles.tabTextActive,
            ]}
          >
            Check-in
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, viewMode === "history" && styles.tabActive]}
          onPress={() => {
            setViewMode("history");
            refetchEntries();
          }}
          activeOpacity={0.7}
        >
          <Text
            style={[
              styles.tabText,
              viewMode === "history" && styles.tabTextActive,
            ]}
          >
            History
          </Text>
        </TouchableOpacity>
      </View>

      {viewMode === "log" ? (
        <ScrollView
          contentContainerStyle={styles.content}
          showsVerticalScrollIndicator={false}
        >
          <Text style={styles.heading}>How are you feeling?</Text>
          <Text style={styles.subheading}>
            Regular check-ins help track your well-being over time.
          </Text>

          {/* Mood */}
          <WellnessSlider
            label="Mood"
            value={mood}
            onChange={setMood}
            labels={WELLNESS_LABEL_PRESETS.mood}
            color="#EC4899"
            icon={"\u{1F60A}"}
          />

          {/* Energy */}
          <WellnessSlider
            label="Energy"
            value={energy}
            onChange={setEnergy}
            labels={WELLNESS_LABEL_PRESETS.energy}
            color={Colors.warning}
            icon={"\u{26A1}"}
          />

          {/* Stress */}
          <WellnessSlider
            label="Stress"
            value={stress}
            onChange={setStress}
            labels={WELLNESS_LABEL_PRESETS.stress}
            color={Colors.error}
            icon={"\u{1F4A7}"}
          />

          {/* Note */}
          <Text style={styles.noteLabel}>Notes (optional)</Text>
          <TextInput
            style={styles.noteInput}
            value={note}
            onChangeText={setNote}
            placeholder="How was your day? Anything on your mind?"
            placeholderTextColor={Colors.textDisabled}
            multiline
            numberOfLines={3}
            maxLength={500}
            textAlignVertical="top"
          />

          {/* Submit */}
          <TouchableOpacity
            style={[
              styles.submitButton,
              isSubmitting && styles.submitButtonDisabled,
            ]}
            onPress={handleSubmit}
            disabled={isSubmitting}
            activeOpacity={0.8}
          >
            <Text style={styles.submitText}>
              {isSubmitting ? "Saving..." : "Log Check-in"}
            </Text>
          </TouchableOpacity>
        </ScrollView>
      ) : (
        <ScrollView
          contentContainerStyle={styles.content}
          refreshControl={
            <RefreshControl
              refreshing={entriesLoading}
              onRefresh={refetchEntries}
              tintColor={Colors.primary}
              colors={[Colors.primary]}
            />
          }
        >
          <Text style={styles.heading}>Wellness History</Text>

          {entries && entries.length > 0 ? (
            entries.map((entry) => (
              <View key={entry.id} style={styles.historyCard}>
                <View style={styles.historyHeader}>
                  <Text style={styles.historyDate}>
                    {formatDate(entry.created_at)}
                  </Text>
                  <Text style={styles.historyMoodEmoji}>
                    {getMoodEmoji(entry.mood)}
                  </Text>
                </View>

                <View style={styles.historyMetrics}>
                  <MetricPill
                    label="Mood"
                    value={entry.mood}
                    color="#EC4899"
                  />
                  <MetricPill
                    label="Energy"
                    value={entry.energy}
                    color={Colors.warning}
                  />
                  <MetricPill
                    label="Stress"
                    value={entry.stress}
                    color={Colors.error}
                  />
                </View>

                {entry.note && (
                  <Text style={styles.historyNote}>{entry.note}</Text>
                )}
              </View>
            ))
          ) : (
            <View style={styles.emptyState}>
              <Text style={styles.emptyIcon}>{"\u{1F49A}"}</Text>
              <Text style={styles.emptyTitle}>No Check-ins Yet</Text>
              <Text style={styles.emptyText}>
                Start logging your mood, energy, and stress to see trends over
                time.
              </Text>
            </View>
          )}
        </ScrollView>
      )}
    </KeyboardAvoidingView>
  );
}

function MetricPill({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <View style={[styles.metricPill, { borderColor: color + "40" }]}>
      <Text style={[styles.metricValue, { color }]}>{value}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  tabRow: {
    flexDirection: "row",
    paddingHorizontal: 16,
    paddingTop: 8,
    gap: 8,
  },
  tab: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: Colors.card,
    alignItems: "center",
    borderWidth: 1,
    borderColor: Colors.border,
  },
  tabActive: {
    backgroundColor: Colors.primary + "20",
    borderColor: Colors.primary,
  },
  tabText: {
    fontSize: 14,
    fontWeight: "600",
    color: Colors.textMuted,
  },
  tabTextActive: {
    color: Colors.primary,
  },
  content: {
    padding: 16,
    paddingBottom: 32,
  },
  heading: {
    fontSize: 24,
    fontWeight: "800",
    color: Colors.textPrimary,
    marginBottom: 4,
    marginTop: 8,
  },
  subheading: {
    fontSize: 14,
    color: Colors.textMuted,
    marginBottom: 24,
    lineHeight: 20,
  },
  noteLabel: {
    fontSize: 16,
    fontWeight: "600",
    color: Colors.textPrimary,
    marginBottom: 8,
  },
  noteInput: {
    backgroundColor: Colors.card,
    borderRadius: 12,
    padding: 14,
    fontSize: 14,
    color: Colors.textPrimary,
    borderWidth: 1,
    borderColor: Colors.border,
    minHeight: 80,
    marginBottom: 24,
  },
  submitButton: {
    backgroundColor: Colors.primary,
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: "center",
  },
  submitButtonDisabled: {
    opacity: 0.6,
  },
  submitText: {
    color: "#fff",
    fontSize: 17,
    fontWeight: "700",
  },
  // History styles
  historyCard: {
    backgroundColor: Colors.card,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  historyHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },
  historyDate: {
    fontSize: 13,
    color: Colors.textMuted,
    fontWeight: "600",
  },
  historyMoodEmoji: {
    fontSize: 22,
  },
  historyMetrics: {
    flexDirection: "row",
    gap: 8,
    marginBottom: 8,
  },
  metricPill: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: Colors.cardAlt + "40",
    borderWidth: 1,
    gap: 6,
  },
  metricValue: {
    fontSize: 16,
    fontWeight: "700",
  },
  metricLabel: {
    fontSize: 11,
    color: Colors.textMuted,
  },
  historyNote: {
    fontSize: 13,
    color: Colors.textSecondary,
    lineHeight: 20,
    marginTop: 4,
    fontStyle: "italic",
  },
  emptyState: {
    alignItems: "center",
    paddingVertical: 60,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: Colors.textPrimary,
    marginBottom: 8,
  },
  emptyText: {
    fontSize: 14,
    color: Colors.textMuted,
    textAlign: "center",
    lineHeight: 20,
    paddingHorizontal: 32,
  },
});
