/**
 * LockOverlay - Full-screen modal overlay for phone lock mode.
 * Covers the entire app with a lock screen based on the lock level.
 */
import React, { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  Modal,
  Animated,
  TouchableOpacity,
  Dimensions,
} from "react-native";
import { Colors } from "../constants/colors";
import { LOCK_LEVELS } from "../constants/config";

const { height: SCREEN_HEIGHT } = Dimensions.get("window");

interface LockOverlayProps {
  visible: boolean;
  level: 1 | 2 | 3;
  remainingSeconds: number;
  coinBet: number;
  breakPenalty: number;
  onDismiss?: () => void;
  onEmergencyUnlock?: () => void;
}

const ENCOURAGEMENT_MESSAGES = [
  "You are doing great! Stay focused.",
  "Every minute of focus counts toward your goals.",
  "Your future self will thank you.",
  "Discipline is the bridge between goals and accomplishment.",
  "Small consistent actions create extraordinary results.",
  "Stay with it. The discomfort is temporary.",
  "Focus is your superpower. Use it wisely.",
  "You chose to study. Honor that decision.",
];

function formatCountdown(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

export default function LockOverlay({
  visible,
  level,
  remainingSeconds,
  coinBet,
  breakPenalty,
  onDismiss,
  onEmergencyUnlock,
}: LockOverlayProps) {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const [messageIndex, setMessageIndex] = useState(0);
  const messageOpacity = useRef(new Animated.Value(1)).current;

  // Fade in/out animation
  useEffect(() => {
    if (visible) {
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
      }).start();
    } else {
      Animated.timing(fadeAnim, {
        toValue: 0,
        duration: 200,
        useNativeDriver: true,
      }).start();
    }
  }, [visible, fadeAnim]);

  // Rotate encouragement messages (Shield level only)
  useEffect(() => {
    if (!visible || level !== LOCK_LEVELS.SHIELD) return;

    const interval = setInterval(() => {
      // Fade out current message
      Animated.timing(messageOpacity, {
        toValue: 0,
        duration: 400,
        useNativeDriver: true,
      }).start(() => {
        setMessageIndex(
          (prev) => (prev + 1) % ENCOURAGEMENT_MESSAGES.length
        );
        // Fade in new message
        Animated.timing(messageOpacity, {
          toValue: 1,
          duration: 400,
          useNativeDriver: true,
        }).start();
      });
    }, 8000);

    return () => clearInterval(interval);
  }, [visible, level, messageOpacity]);

  const getLevelConfig = () => {
    switch (level) {
      case LOCK_LEVELS.NUDGE:
        return {
          title: "Study Reminder",
          subtitle: "Time to get back to studying!",
          color: Colors.lockNudge,
          icon: "\u{1F4DA}",
          showDismiss: true,
          showTimer: false,
          showBet: false,
        };
      case LOCK_LEVELS.LOCK:
        return {
          title: "Phone Locked",
          subtitle: "Focus mode is active. Stay committed!",
          color: Colors.lockLock,
          icon: "\u{1F512}",
          showDismiss: false,
          showTimer: true,
          showBet: true,
        };
      case LOCK_LEVELS.SHIELD:
        return {
          title: "Maximum Focus Shield",
          subtitle: "Your phone is shielded. You got this!",
          color: Colors.lockShield,
          icon: "\u{1F6E1}\u{FE0F}",
          showDismiss: false,
          showTimer: true,
          showBet: true,
        };
      default:
        return {
          title: "Focus Mode",
          subtitle: "",
          color: Colors.primary,
          icon: "\u{1F4DA}",
          showDismiss: true,
          showTimer: false,
          showBet: false,
        };
    }
  };

  const config = getLevelConfig();

  return (
    <Modal
      visible={visible}
      animationType="none"
      transparent
      statusBarTranslucent
      onRequestClose={() => {
        // Only allow dismissing for nudge level
        if (level === LOCK_LEVELS.NUDGE && onDismiss) {
          onDismiss();
        }
      }}
    >
      <Animated.View style={[styles.overlay, { opacity: fadeAnim }]}>
        <View style={styles.content}>
          {/* Lock icon */}
          <Text style={styles.lockIcon}>{config.icon}</Text>

          {/* Title */}
          <Text style={[styles.title, { color: config.color }]}>
            {config.title}
          </Text>
          <Text style={styles.subtitle}>{config.subtitle}</Text>

          {/* Timer countdown */}
          {config.showTimer && remainingSeconds > 0 && (
            <View style={styles.timerContainer}>
              <Text style={styles.timerLabel}>Time remaining</Text>
              <Text style={[styles.timerText, { color: config.color }]}>
                {formatCountdown(remainingSeconds)}
              </Text>
            </View>
          )}

          {/* Coin bet info */}
          {config.showBet && coinBet > 0 && (
            <View style={styles.betContainer}>
              <View style={styles.betRow}>
                <Text style={styles.betLabel}>Coins at stake</Text>
                <Text style={styles.betValue}>
                  {"\u{1FA99}"} {coinBet}
                </Text>
              </View>
              <View style={styles.betRow}>
                <Text style={styles.betLabel}>Early break penalty</Text>
                <Text style={[styles.betValue, { color: Colors.error }]}>
                  -{breakPenalty}
                </Text>
              </View>
            </View>
          )}

          {/* Encouragement (Shield level) */}
          {level === LOCK_LEVELS.SHIELD && (
            <Animated.View
              style={[styles.encouragement, { opacity: messageOpacity }]}
            >
              <Text style={styles.encouragementText}>
                {ENCOURAGEMENT_MESSAGES[messageIndex]}
              </Text>
            </Animated.View>
          )}

          {/* Dismiss button (Nudge only) */}
          {config.showDismiss && onDismiss && (
            <TouchableOpacity
              style={[styles.dismissButton, { borderColor: config.color }]}
              onPress={onDismiss}
              activeOpacity={0.7}
            >
              <Text style={[styles.dismissText, { color: config.color }]}>
                Got it, back to studying!
              </Text>
            </TouchableOpacity>
          )}

          {/* Emergency unlock (Lock and Shield only) */}
          {!config.showDismiss && onEmergencyUnlock && (
            <View style={styles.emergencyContainer}>
              <Text style={styles.emergencyWarning}>
                Emergency unlock will forfeit your coin bet
              </Text>
              <TouchableOpacity
                style={styles.emergencyButton}
                onPress={onEmergencyUnlock}
                activeOpacity={0.7}
              >
                <Text style={styles.emergencyText}>Emergency Unlock</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      </Animated.View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: Colors.overlayDark,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 24,
  },
  content: {
    width: "100%",
    alignItems: "center",
    paddingVertical: 40,
  },
  lockIcon: {
    fontSize: 64,
    marginBottom: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: "800",
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: Colors.textSecondary,
    textAlign: "center",
    lineHeight: 24,
    marginBottom: 32,
    paddingHorizontal: 20,
  },
  timerContainer: {
    alignItems: "center",
    marginBottom: 28,
  },
  timerLabel: {
    fontSize: 12,
    fontWeight: "600",
    color: Colors.textMuted,
    letterSpacing: 1,
    textTransform: "uppercase",
    marginBottom: 8,
  },
  timerText: {
    fontSize: 56,
    fontWeight: "200",
    fontVariant: ["tabular-nums"],
  },
  betContainer: {
    backgroundColor: Colors.card,
    borderRadius: 12,
    padding: 16,
    width: "100%",
    marginBottom: 24,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  betRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 6,
  },
  betLabel: {
    fontSize: 14,
    color: Colors.textSecondary,
  },
  betValue: {
    fontSize: 16,
    fontWeight: "700",
    color: Colors.coins,
  },
  encouragement: {
    paddingHorizontal: 20,
    marginBottom: 32,
  },
  encouragementText: {
    fontSize: 16,
    color: Colors.textSecondary,
    textAlign: "center",
    fontStyle: "italic",
    lineHeight: 24,
  },
  dismissButton: {
    borderWidth: 2,
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 32,
    marginTop: 8,
  },
  dismissText: {
    fontSize: 16,
    fontWeight: "700",
  },
  emergencyContainer: {
    alignItems: "center",
    marginTop: 40,
  },
  emergencyWarning: {
    fontSize: 12,
    color: Colors.textDisabled,
    marginBottom: 12,
    textAlign: "center",
  },
  emergencyButton: {
    paddingVertical: 10,
    paddingHorizontal: 24,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: Colors.error + "40",
  },
  emergencyText: {
    fontSize: 13,
    color: Colors.error,
    fontWeight: "600",
  },
});
