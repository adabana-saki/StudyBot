/**
 * PhoneLockScreen - Phone lock configuration and activation.
 * Three levels: Nudge (reminder only), Lock (overlay + coin bet), Shield (max restriction).
 */
import React, { useState, useCallback, useEffect, useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  TextInput,
} from "react-native";
import { Colors } from "../constants/colors";
import { LOCK_LEVELS } from "../constants/config";
import {
  getPhoneLockConfig,
  setPhoneLockConfig,
  PhoneLockConfig,
} from "../lib/storage";
import LockOverlay from "../components/LockOverlay";

type LockLevel = 1 | 2 | 3;

const LEVEL_DETAILS: Record<
  LockLevel,
  {
    name: string;
    icon: string;
    color: string;
    description: string;
    features: string[];
  }
> = {
  [LOCK_LEVELS.NUDGE]: {
    name: "Nudge",
    icon: "\u{1F514}",
    color: Colors.lockNudge,
    description: "Gentle reminders to keep you on track.",
    features: [
      "Periodic reminder notifications",
      "Dismissable overlay message",
      "No penalties",
    ],
  },
  [LOCK_LEVELS.LOCK]: {
    name: "Lock",
    icon: "\u{1F512}",
    color: Colors.lockLock,
    description: "Full-screen lock with coin stakes.",
    features: [
      "Full-screen lock overlay",
      "Coin bet for accountability",
      "Break penalty deduction",
      "Emergency unlock available",
    ],
  },
  [LOCK_LEVELS.SHIELD]: {
    name: "Shield",
    icon: "\u{1F6E1}\u{FE0F}",
    color: Colors.lockShield,
    description: "Maximum focus protection.",
    features: [
      "Everything in Lock mode",
      "Encouragement messages",
      "Higher stakes and penalties",
      "App blocking (requires native setup)",
    ],
  },
};

const DURATION_OPTIONS = [15, 25, 30, 45, 60, 90, 120];

export default function PhoneLockScreen() {
  const [level, setLevel] = useState<LockLevel>(1);
  const [duration, setDuration] = useState(25);
  const [coinBet, setCoinBet] = useState("10");
  const [isLockActive, setIsLockActive] = useState(false);
  const [lockRemaining, setLockRemaining] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load saved config
  useEffect(() => {
    (async () => {
      const config = await getPhoneLockConfig();
      if (config) {
        setLevel(config.level);
        setDuration(config.duration);
        setCoinBet(config.coinBet.toString());
      }
    })();
  }, []);

  const breakPenalty = Math.ceil(parseInt(coinBet || "0", 10) * 0.5);

  const activateLock = useCallback(async () => {
    const bet = parseInt(coinBet || "0", 10);

    if (level >= 2 && bet <= 0) {
      Alert.alert(
        "Set a Coin Bet",
        "Lock and Shield modes require a coin bet to keep you accountable."
      );
      return;
    }

    // Save config
    await setPhoneLockConfig({
      level,
      coinBet: bet,
      duration,
      breakPenalty,
    });

    setLockRemaining(duration * 60);
    setIsLockActive(true);

    // Start countdown
    timerRef.current = setInterval(() => {
      setLockRemaining((prev) => {
        if (prev <= 1) {
          if (timerRef.current) clearInterval(timerRef.current);
          setIsLockActive(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }, [level, duration, coinBet, breakPenalty]);

  const handleDismissNudge = useCallback(() => {
    setIsLockActive(false);
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const handleEmergencyUnlock = useCallback(() => {
    Alert.alert(
      "Emergency Unlock",
      `This will end your focus session and deduct ${breakPenalty} coins. Continue?`,
      [
        { text: "Stay Locked", style: "cancel" },
        {
          text: "Unlock",
          style: "destructive",
          onPress: () => {
            setIsLockActive(false);
            if (timerRef.current) {
              clearInterval(timerRef.current);
              timerRef.current = null;
            }
          },
        },
      ]
    );
  }, [breakPenalty]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  return (
    <View style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* Level Selection */}
        <Text style={styles.sectionTitle}>Lock Level</Text>
        <View style={styles.levelGrid}>
          {([1, 2, 3] as LockLevel[]).map((lvl) => {
            const detail = LEVEL_DETAILS[lvl];
            const isSelected = level === lvl;

            return (
              <TouchableOpacity
                key={lvl}
                style={[
                  styles.levelCard,
                  isSelected && {
                    borderColor: detail.color,
                    backgroundColor: detail.color + "10",
                  },
                ]}
                onPress={() => setLevel(lvl)}
                activeOpacity={0.7}
              >
                <Text style={styles.levelIcon}>{detail.icon}</Text>
                <Text
                  style={[
                    styles.levelName,
                    isSelected && { color: detail.color },
                  ]}
                >
                  {detail.name}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>

        {/* Level description */}
        <View style={styles.descriptionCard}>
          <Text style={styles.descriptionText}>
            {LEVEL_DETAILS[level].description}
          </Text>
          {LEVEL_DETAILS[level].features.map((feature, i) => (
            <View key={i} style={styles.featureRow}>
              <Text
                style={[
                  styles.featureBullet,
                  { color: LEVEL_DETAILS[level].color },
                ]}
              >
                {"\u2022"}
              </Text>
              <Text style={styles.featureText}>{feature}</Text>
            </View>
          ))}
        </View>

        {/* Duration */}
        <Text style={styles.sectionTitle}>Duration</Text>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.durationScroll}
          contentContainerStyle={styles.durationContent}
        >
          {DURATION_OPTIONS.map((mins) => (
            <TouchableOpacity
              key={mins}
              style={[
                styles.durationChip,
                duration === mins && {
                  backgroundColor: LEVEL_DETAILS[level].color + "20",
                  borderColor: LEVEL_DETAILS[level].color,
                },
              ]}
              onPress={() => setDuration(mins)}
              activeOpacity={0.7}
            >
              <Text
                style={[
                  styles.durationText,
                  duration === mins && {
                    color: LEVEL_DETAILS[level].color,
                  },
                ]}
              >
                {mins}m
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Coin Bet (for Lock and Shield) */}
        {level >= 2 && (
          <>
            <Text style={styles.sectionTitle}>Coin Bet</Text>
            <View style={styles.betInputContainer}>
              <Text style={styles.betIcon}>{"\u{1FA99}"}</Text>
              <TextInput
                style={styles.betInput}
                value={coinBet}
                onChangeText={(text) =>
                  setCoinBet(text.replace(/[^0-9]/g, ""))
                }
                keyboardType="numeric"
                placeholder="10"
                placeholderTextColor={Colors.textDisabled}
                maxLength={5}
              />
              <Text style={styles.betHint}>
                Penalty: -{breakPenalty} coins
              </Text>
            </View>
          </>
        )}

        {/* Activate Button */}
        <TouchableOpacity
          style={[
            styles.activateButton,
            { backgroundColor: LEVEL_DETAILS[level].color },
          ]}
          onPress={activateLock}
          activeOpacity={0.8}
        >
          <Text style={styles.activateIcon}>
            {LEVEL_DETAILS[level].icon}
          </Text>
          <Text style={styles.activateText}>
            Activate {LEVEL_DETAILS[level].name} Mode
          </Text>
        </TouchableOpacity>

        {/* Info */}
        <View style={styles.infoCard}>
          <Text style={styles.infoTitle}>About Phone Lock</Text>
          <Text style={styles.infoText}>
            Phone Lock helps you stay focused by restricting phone usage during
            study sessions. Higher levels provide stronger accountability
            through coin stakes and app blocking.
          </Text>
          <Text style={styles.infoText}>
            Note: Full app blocking requires additional native module setup.
            See the native module README for instructions.
          </Text>
        </View>
      </ScrollView>

      {/* Lock Overlay */}
      <LockOverlay
        visible={isLockActive}
        level={level}
        remainingSeconds={lockRemaining}
        coinBet={parseInt(coinBet || "0", 10)}
        breakPenalty={breakPenalty}
        onDismiss={
          level === LOCK_LEVELS.NUDGE ? handleDismissNudge : undefined
        }
        onEmergencyUnlock={
          level >= 2 ? handleEmergencyUnlock : undefined
        }
      />
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
    paddingBottom: 40,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: Colors.textPrimary,
    marginBottom: 12,
    marginTop: 8,
  },
  levelGrid: {
    flexDirection: "row",
    gap: 10,
    marginBottom: 16,
  },
  levelCard: {
    flex: 1,
    backgroundColor: Colors.card,
    borderRadius: 12,
    padding: 16,
    alignItems: "center",
    borderWidth: 2,
    borderColor: Colors.border,
  },
  levelIcon: {
    fontSize: 28,
    marginBottom: 8,
  },
  levelName: {
    fontSize: 14,
    fontWeight: "700",
    color: Colors.textSecondary,
  },
  descriptionCard: {
    backgroundColor: Colors.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  descriptionText: {
    fontSize: 14,
    color: Colors.textSecondary,
    marginBottom: 12,
    lineHeight: 20,
  },
  featureRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: 6,
  },
  featureBullet: {
    fontSize: 16,
    marginRight: 8,
    lineHeight: 20,
  },
  featureText: {
    fontSize: 13,
    color: Colors.textMuted,
    flex: 1,
    lineHeight: 20,
  },
  durationScroll: {
    marginBottom: 20,
  },
  durationContent: {
    gap: 8,
  },
  durationChip: {
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 20,
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  durationText: {
    fontSize: 15,
    fontWeight: "600",
    color: Colors.textSecondary,
  },
  betInputContainer: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.card,
    borderRadius: 12,
    padding: 14,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  betIcon: {
    fontSize: 22,
    marginRight: 10,
  },
  betInput: {
    flex: 1,
    fontSize: 20,
    fontWeight: "700",
    color: Colors.textPrimary,
  },
  betHint: {
    fontSize: 12,
    color: Colors.error,
    fontWeight: "600",
  },
  activateButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 14,
    paddingVertical: 18,
    marginBottom: 24,
  },
  activateIcon: {
    fontSize: 22,
    marginRight: 10,
  },
  activateText: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "700",
  },
  infoCard: {
    backgroundColor: Colors.card,
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  infoTitle: {
    fontSize: 14,
    fontWeight: "700",
    color: Colors.textPrimary,
    marginBottom: 8,
  },
  infoText: {
    fontSize: 13,
    color: Colors.textMuted,
    lineHeight: 20,
    marginBottom: 8,
  },
});
