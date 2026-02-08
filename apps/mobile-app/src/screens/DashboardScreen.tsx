/**
 * DashboardScreen - Main dashboard showing user stats, level, streak,
 * quick actions, and recent activity.
 */
import React, { useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  Image,
} from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { Colors } from "../constants/colors";
import { useAuth } from "../hooks/useAuth";
import { useApiQuery } from "../hooks/useApi";
import { getStudyStats, getDailyStudy, StudyStats, DailyStudy } from "../lib/api";
import StatsCard from "../components/StatsCard";
import ProgressBar from "../components/ProgressBar";

type RootStackParamList = {
  Dashboard: undefined;
  StudyTimer: undefined;
  Flashcards: undefined;
  Wellness: undefined;
  Achievements: undefined;
  PhoneLock: undefined;
};

type NavigationProp = NativeStackNavigationProp<RootStackParamList>;

export default function DashboardScreen() {
  const navigation = useNavigation<NavigationProp>();
  const { user, refreshProfile } = useAuth();

  const {
    data: studyStats,
    isLoading: statsLoading,
    refetch: refetchStats,
  } = useApiQuery<StudyStats>(() => getStudyStats("weekly"), []);

  const {
    data: dailyStudy,
    refetch: refetchDaily,
  } = useApiQuery<DailyStudy[]>(() => getDailyStudy(7), []);

  const onRefresh = useCallback(async () => {
    await Promise.all([refreshProfile(), refetchStats(), refetchDaily()]);
  }, [refreshProfile, refetchStats, refetchDaily]);

  const formatStudyTime = (minutes: number): string => {
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={statsLoading}
          onRefresh={onRefresh}
          tintColor={Colors.primary}
          colors={[Colors.primary]}
        />
      }
    >
      {/* Profile Card */}
      <View style={styles.profileCard}>
        <View style={styles.profileHeader}>
          <View style={styles.avatarContainer}>
            {user?.avatar_url ? (
              <Image
                source={{ uri: user.avatar_url }}
                style={styles.avatar}
              />
            ) : (
              <View style={styles.avatarPlaceholder}>
                <Text style={styles.avatarInitial}>
                  {user?.username?.charAt(0).toUpperCase() || "?"}
                </Text>
              </View>
            )}
            <View style={styles.levelBadge}>
              <Text style={styles.levelBadgeText}>{user?.level || 0}</Text>
            </View>
          </View>

          <View style={styles.profileInfo}>
            <Text style={styles.username}>{user?.username || "Student"}</Text>
            <Text style={styles.rankText}>
              Rank #{user?.rank || "-"} in server
            </Text>
          </View>
        </View>

        {/* XP Progress */}
        <View style={styles.xpContainer}>
          <ProgressBar
            current={user?.xp || 0}
            max={user?.xp_to_next_level || 100}
            color={Colors.xpBar}
            height={10}
            showLabel
            label={`Level ${user?.level || 0}`}
          />
        </View>
      </View>

      {/* Stats Row */}
      <View style={styles.statsRow}>
        <StatsCard
          label="Study"
          value={formatStudyTime(studyStats?.total_minutes || 0)}
          icon={"\u{23F1}\u{FE0F}"}
          color={Colors.primary}
        />
        <StatsCard
          label="Sessions"
          value={studyStats?.total_sessions || 0}
          icon={"\u{1F4CA}"}
          color={Colors.info}
          style={{ marginHorizontal: 8 }}
        />
        <StatsCard
          label="Streak"
          value={`${user?.streak || 0}d`}
          icon={"\u{1F525}"}
          color={Colors.streak}
        />
        <StatsCard
          label="Coins"
          value={user?.coins || 0}
          icon={"\u{1FA99}"}
          color={Colors.coins}
          style={{ marginLeft: 8 }}
        />
      </View>

      {/* Quick Actions */}
      <Text style={styles.sectionTitle}>Quick Actions</Text>
      <View style={styles.actionsGrid}>
        <QuickAction
          icon={"\u{23F1}\u{FE0F}"}
          label="Start Timer"
          color={Colors.primary}
          onPress={() => navigation.navigate("StudyTimer")}
        />
        <QuickAction
          icon={"\u{1F0CF}"}
          label="Review Cards"
          color={Colors.accent}
          onPress={() => navigation.navigate("Flashcards")}
        />
        <QuickAction
          icon={"\u{1F49A}"}
          label="Wellness"
          color="#EC4899"
          onPress={() => navigation.navigate("Wellness")}
        />
        <QuickAction
          icon={"\u{1F512}"}
          label="Phone Lock"
          color={Colors.warning}
          onPress={() => navigation.navigate("PhoneLock")}
        />
      </View>

      {/* Weekly Activity */}
      <Text style={styles.sectionTitle}>This Week</Text>
      <View style={styles.weekChart}>
        {dailyStudy && dailyStudy.length > 0 ? (
          <View style={styles.chartBars}>
            {dailyStudy.slice(-7).map((day, index) => {
              const maxMinutes = Math.max(
                ...dailyStudy.slice(-7).map((d) => d.minutes),
                1
              );
              const barHeight = Math.max(
                (day.minutes / maxMinutes) * 100,
                4
              );
              const dayName = new Date(day.date).toLocaleDateString("en", {
                weekday: "short",
              });

              return (
                <View key={index} style={styles.chartBarContainer}>
                  <Text style={styles.chartMinutes}>
                    {day.minutes > 0 ? `${day.minutes}m` : ""}
                  </Text>
                  <View
                    style={[
                      styles.chartBar,
                      {
                        height: barHeight,
                        backgroundColor:
                          day.minutes > 0
                            ? Colors.primary
                            : Colors.cardAlt,
                      },
                    ]}
                  />
                  <Text style={styles.chartDay}>{dayName}</Text>
                </View>
              );
            })}
          </View>
        ) : (
          <View style={styles.emptyChart}>
            <Text style={styles.emptyChartText}>
              No study data yet this week.
            </Text>
            <Text style={styles.emptyChartHint}>
              Start a study session to see your progress!
            </Text>
          </View>
        )}
      </View>

      {/* Best Day */}
      {studyStats?.most_productive_day && (
        <View style={styles.insightCard}>
          <Text style={styles.insightIcon}>{"\u{2B50}"}</Text>
          <View style={styles.insightContent}>
            <Text style={styles.insightTitle}>Most Productive Day</Text>
            <Text style={styles.insightValue}>
              {studyStats.most_productive_day}
            </Text>
          </View>
        </View>
      )}
    </ScrollView>
  );
}

function QuickAction({
  icon,
  label,
  color,
  onPress,
}: {
  icon: string;
  label: string;
  color: string;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      style={styles.actionCard}
      onPress={onPress}
      activeOpacity={0.7}
    >
      <View
        style={[styles.actionIcon, { backgroundColor: color + "20" }]}
      >
        <Text style={styles.actionIconText}>{icon}</Text>
      </View>
      <Text style={styles.actionLabel}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  content: {
    padding: 16,
    paddingBottom: 32,
  },
  profileCard: {
    backgroundColor: Colors.card,
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  profileHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 16,
  },
  avatarContainer: {
    position: "relative",
    marginRight: 14,
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    borderWidth: 2,
    borderColor: Colors.primary,
  },
  avatarPlaceholder: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: Colors.primary + "30",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 2,
    borderColor: Colors.primary,
  },
  avatarInitial: {
    fontSize: 22,
    fontWeight: "700",
    color: Colors.primary,
  },
  levelBadge: {
    position: "absolute",
    bottom: -4,
    right: -4,
    backgroundColor: Colors.primary,
    borderRadius: 10,
    width: 24,
    height: 24,
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 2,
    borderColor: Colors.card,
  },
  levelBadgeText: {
    color: "#fff",
    fontSize: 11,
    fontWeight: "800",
  },
  profileInfo: {
    flex: 1,
  },
  username: {
    fontSize: 20,
    fontWeight: "700",
    color: Colors.textPrimary,
    marginBottom: 2,
  },
  rankText: {
    fontSize: 13,
    color: Colors.textMuted,
  },
  xpContainer: {
    marginTop: 4,
  },
  statsRow: {
    flexDirection: "row",
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: Colors.textPrimary,
    marginBottom: 12,
  },
  actionsGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
    marginBottom: 24,
  },
  actionCard: {
    width: "48%",
    flexGrow: 1,
    backgroundColor: Colors.card,
    borderRadius: 12,
    padding: 16,
    alignItems: "center",
    borderWidth: 1,
    borderColor: Colors.border,
  },
  actionIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 8,
  },
  actionIconText: {
    fontSize: 24,
  },
  actionLabel: {
    fontSize: 13,
    fontWeight: "600",
    color: Colors.textSecondary,
  },
  weekChart: {
    backgroundColor: Colors.card,
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: Colors.border,
    minHeight: 160,
  },
  chartBars: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
    height: 120,
  },
  chartBarContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "flex-end",
  },
  chartMinutes: {
    fontSize: 10,
    color: Colors.textMuted,
    marginBottom: 4,
  },
  chartBar: {
    width: 24,
    borderRadius: 4,
    minHeight: 4,
  },
  chartDay: {
    fontSize: 11,
    color: Colors.textDisabled,
    marginTop: 6,
  },
  emptyChart: {
    justifyContent: "center",
    alignItems: "center",
    paddingVertical: 20,
  },
  emptyChartText: {
    fontSize: 14,
    color: Colors.textMuted,
    marginBottom: 4,
  },
  emptyChartHint: {
    fontSize: 12,
    color: Colors.textDisabled,
  },
  insightCard: {
    backgroundColor: Colors.card,
    borderRadius: 12,
    padding: 16,
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: Colors.border,
  },
  insightIcon: {
    fontSize: 28,
    marginRight: 14,
  },
  insightContent: {
    flex: 1,
  },
  insightTitle: {
    fontSize: 12,
    color: Colors.textMuted,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  insightValue: {
    fontSize: 18,
    fontWeight: "700",
    color: Colors.textPrimary,
    marginTop: 2,
  },
});
