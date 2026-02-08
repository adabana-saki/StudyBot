/**
 * AchievementsScreen - Displays the achievement grid with filter tabs.
 * Shows unlocked/locked achievements with progress indicators.
 */
import React, { useState, useMemo } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Modal,
  RefreshControl,
} from "react-native";
import { Colors } from "../constants/colors";
import { useApiQuery } from "../hooks/useApi";
import { getMyAchievements, Achievement } from "../lib/api";
import AchievementBadge from "../components/AchievementBadge";
import ProgressBar from "../components/ProgressBar";

type FilterTab = "all" | "unlocked" | "locked";

const TIER_ORDER: Record<string, number> = {
  platinum: 0,
  gold: 1,
  silver: 2,
  bronze: 3,
};

export default function AchievementsScreen() {
  const [filter, setFilter] = useState<FilterTab>("all");
  const [selectedAchievement, setSelectedAchievement] =
    useState<Achievement | null>(null);

  const {
    data: achievements,
    isLoading,
    error,
    refetch,
  } = useApiQuery<Achievement[]>(() => getMyAchievements(), []);

  const filteredAchievements = useMemo(() => {
    if (!achievements) return [];
    let filtered = [...achievements];

    if (filter === "unlocked") {
      filtered = filtered.filter((a) => a.unlocked);
    } else if (filter === "locked") {
      filtered = filtered.filter((a) => !a.unlocked);
    }

    // Sort: unlocked first, then by tier
    filtered.sort((a, b) => {
      if (a.unlocked !== b.unlocked) return a.unlocked ? -1 : 1;
      return (TIER_ORDER[a.tier] ?? 4) - (TIER_ORDER[b.tier] ?? 4);
    });

    return filtered;
  }, [achievements, filter]);

  const stats = useMemo(() => {
    if (!achievements) return { total: 0, unlocked: 0, byTier: {} as Record<string, number> };
    const unlocked = achievements.filter((a) => a.unlocked);
    const byTier: Record<string, number> = {};
    for (const a of unlocked) {
      byTier[a.tier] = (byTier[a.tier] || 0) + 1;
    }
    return { total: achievements.length, unlocked: unlocked.length, byTier };
  }, [achievements]);

  // Group by category
  const categories = useMemo(() => {
    const cats: Record<string, Achievement[]> = {};
    for (const a of filteredAchievements) {
      const cat = a.category || "General";
      if (!cats[cat]) cats[cat] = [];
      cats[cat].push(a);
    }
    return cats;
  }, [filteredAchievements]);

  return (
    <View style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={isLoading}
            onRefresh={refetch}
            tintColor={Colors.primary}
            colors={[Colors.primary]}
          />
        }
      >
        {/* Summary */}
        <View style={styles.summaryCard}>
          <Text style={styles.summaryTitle}>Your Achievements</Text>
          <ProgressBar
            current={stats.unlocked}
            max={stats.total}
            color={Colors.coins}
            height={8}
            showLabel
            label={`${stats.unlocked} / ${stats.total} Unlocked`}
            style={{ marginTop: 8 }}
          />
          <View style={styles.tierRow}>
            <TierCount label="Platinum" count={stats.byTier["platinum"] || 0} color="#E5E4E2" />
            <TierCount label="Gold" count={stats.byTier["gold"] || 0} color="#FFD700" />
            <TierCount label="Silver" count={stats.byTier["silver"] || 0} color="#C0C0C0" />
            <TierCount label="Bronze" count={stats.byTier["bronze"] || 0} color="#CD7F32" />
          </View>
        </View>

        {/* Filter Tabs */}
        <View style={styles.filterRow}>
          {(["all", "unlocked", "locked"] as FilterTab[]).map((tab) => (
            <TouchableOpacity
              key={tab}
              style={[
                styles.filterTab,
                filter === tab && styles.filterTabActive,
              ]}
              onPress={() => setFilter(tab)}
              activeOpacity={0.7}
            >
              <Text
                style={[
                  styles.filterTabText,
                  filter === tab && styles.filterTabTextActive,
                ]}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Loading */}
        {isLoading && !achievements && (
          <ActivityIndicator
            size="large"
            color={Colors.primary}
            style={styles.loader}
          />
        )}

        {/* Error */}
        {error && (
          <View style={styles.errorContainer}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        {/* Achievement Grid by Category */}
        {Object.entries(categories).map(([category, items]) => (
          <View key={category}>
            <Text style={styles.categoryTitle}>{category}</Text>
            <View style={styles.grid}>
              {items.map((achievement) => (
                <AchievementBadge
                  key={achievement.id}
                  name={achievement.name}
                  description={achievement.description}
                  icon={achievement.icon}
                  tier={achievement.tier}
                  unlocked={achievement.unlocked}
                  progress={achievement.progress}
                  target={achievement.target}
                  onPress={() => setSelectedAchievement(achievement)}
                />
              ))}
            </View>
          </View>
        ))}

        {/* Empty state */}
        {filteredAchievements.length === 0 && !isLoading && (
          <View style={styles.emptyState}>
            <Text style={styles.emptyIcon}>{"\u{1F3C6}"}</Text>
            <Text style={styles.emptyTitle}>
              {filter === "unlocked"
                ? "No Achievements Unlocked Yet"
                : "No Achievements Found"}
            </Text>
            <Text style={styles.emptyText}>
              Keep studying to unlock achievements!
            </Text>
          </View>
        )}
      </ScrollView>

      {/* Achievement Detail Modal */}
      <Modal
        visible={selectedAchievement !== null}
        animationType="fade"
        transparent
        onRequestClose={() => setSelectedAchievement(null)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setSelectedAchievement(null)}
        >
          <View style={styles.modalCard}>
            {selectedAchievement && (
              <>
                <Text style={styles.modalIcon}>
                  {selectedAchievement.unlocked
                    ? selectedAchievement.icon
                    : "\u{1F512}"}
                </Text>
                <Text style={styles.modalName}>
                  {selectedAchievement.name}
                </Text>
                <Text style={styles.modalTier}>
                  {selectedAchievement.tier.toUpperCase()}
                </Text>
                <Text style={styles.modalDescription}>
                  {selectedAchievement.description}
                </Text>

                {selectedAchievement.unlocked ? (
                  <Text style={styles.modalUnlocked}>
                    Unlocked{" "}
                    {selectedAchievement.unlocked_at
                      ? new Date(
                          selectedAchievement.unlocked_at
                        ).toLocaleDateString()
                      : ""}
                  </Text>
                ) : (
                  <View style={styles.modalProgress}>
                    <ProgressBar
                      current={selectedAchievement.progress}
                      max={selectedAchievement.target}
                      color={Colors.primary}
                      height={6}
                      showLabel
                    />
                  </View>
                )}

                <TouchableOpacity
                  style={styles.modalClose}
                  onPress={() => setSelectedAchievement(null)}
                >
                  <Text style={styles.modalCloseText}>Close</Text>
                </TouchableOpacity>
              </>
            )}
          </View>
        </TouchableOpacity>
      </Modal>
    </View>
  );
}

function TierCount({
  label,
  count,
  color,
}: {
  label: string;
  count: number;
  color: string;
}) {
  return (
    <View style={styles.tierCount}>
      <View style={[styles.tierDot, { backgroundColor: color }]} />
      <Text style={styles.tierCountText}>
        {count} {label}
      </Text>
    </View>
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
  summaryCard: {
    backgroundColor: Colors.card,
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  summaryTitle: {
    fontSize: 20,
    fontWeight: "800",
    color: Colors.textPrimary,
  },
  tierRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
    marginTop: 12,
  },
  tierCount: {
    flexDirection: "row",
    alignItems: "center",
  },
  tierDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 6,
  },
  tierCountText: {
    fontSize: 12,
    color: Colors.textMuted,
  },
  filterRow: {
    flexDirection: "row",
    gap: 8,
    marginBottom: 20,
  },
  filterTab: {
    paddingVertical: 8,
    paddingHorizontal: 18,
    borderRadius: 20,
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  filterTabActive: {
    backgroundColor: Colors.primary + "20",
    borderColor: Colors.primary,
  },
  filterTabText: {
    fontSize: 13,
    fontWeight: "600",
    color: Colors.textMuted,
  },
  filterTabTextActive: {
    color: Colors.primary,
  },
  loader: {
    marginTop: 40,
  },
  errorContainer: {
    padding: 16,
    backgroundColor: Colors.error + "15",
    borderRadius: 12,
  },
  errorText: {
    color: Colors.error,
    textAlign: "center",
  },
  categoryTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: Colors.textSecondary,
    marginBottom: 12,
    marginTop: 4,
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    marginBottom: 16,
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
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: Colors.overlay,
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  modalCard: {
    backgroundColor: Colors.card,
    borderRadius: 20,
    padding: 28,
    width: "100%",
    maxWidth: 340,
    alignItems: "center",
    borderWidth: 1,
    borderColor: Colors.border,
  },
  modalIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  modalName: {
    fontSize: 20,
    fontWeight: "800",
    color: Colors.textPrimary,
    textAlign: "center",
    marginBottom: 4,
  },
  modalTier: {
    fontSize: 11,
    fontWeight: "700",
    color: Colors.textMuted,
    letterSpacing: 2,
    marginBottom: 12,
  },
  modalDescription: {
    fontSize: 14,
    color: Colors.textSecondary,
    textAlign: "center",
    lineHeight: 22,
    marginBottom: 16,
  },
  modalUnlocked: {
    fontSize: 13,
    color: Colors.accent,
    fontWeight: "600",
    marginBottom: 16,
  },
  modalProgress: {
    width: "100%",
    marginBottom: 16,
  },
  modalClose: {
    paddingVertical: 10,
    paddingHorizontal: 24,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  modalCloseText: {
    fontSize: 14,
    color: Colors.textSecondary,
    fontWeight: "600",
  },
});
