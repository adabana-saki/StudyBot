/**
 * SettingsScreen - App settings, notification preferences, and logout.
 */
import React, { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
  Image,
  Linking,
} from "react-native";
import { Colors } from "../constants/colors";
import { useAuth } from "../hooks/useAuth";
import {
  getNotificationPrefs,
  setNotificationPrefs,
  NotificationPrefs,
  getPomodoroSettings,
  setPomodoroSettings,
  PomodoroSettings,
  clearAll as clearStorage,
} from "../lib/storage";
import { POMODORO } from "../constants/config";

const DEFAULT_NOTIFICATION_PREFS: NotificationPrefs = {
  studyReminders: true,
  achievementAlerts: true,
  streakReminders: true,
  wellnessCheckins: true,
  reminderTime: "09:00",
};

const DEFAULT_POMODORO_SETTINGS: PomodoroSettings = {
  workDuration: POMODORO.WORK_DURATION / 60,
  shortBreak: POMODORO.SHORT_BREAK / 60,
  longBreak: POMODORO.LONG_BREAK / 60,
  cyclesBeforeLongBreak: POMODORO.CYCLES_BEFORE_LONG_BREAK,
  autoStartBreaks: false,
  autoStartWork: false,
};

export default function SettingsScreen() {
  const { user, logout } = useAuth();
  const [notifPrefs, setNotifPrefs] = useState<NotificationPrefs>(
    DEFAULT_NOTIFICATION_PREFS
  );
  const [pomodoroSettings, setPomodoroSettingsState] =
    useState<PomodoroSettings>(DEFAULT_POMODORO_SETTINGS);

  // Load saved preferences
  useEffect(() => {
    (async () => {
      const savedNotifs = await getNotificationPrefs();
      if (savedNotifs) setNotifPrefs(savedNotifs);

      const savedPomodoro = await getPomodoroSettings();
      if (savedPomodoro) setPomodoroSettingsState(savedPomodoro);
    })();
  }, []);

  const updateNotifPref = useCallback(
    async (key: keyof NotificationPrefs, value: boolean) => {
      const updated = { ...notifPrefs, [key]: value };
      setNotifPrefs(updated);
      await setNotificationPrefs(updated);
    },
    [notifPrefs]
  );

  const updatePomodoroPref = useCallback(
    async (key: keyof PomodoroSettings, value: boolean) => {
      const updated = { ...pomodoroSettings, [key]: value };
      setPomodoroSettingsState(updated);
      await setPomodoroSettings(updated);
    },
    [pomodoroSettings]
  );

  const handleLogout = useCallback(() => {
    Alert.alert("Log Out", "Are you sure you want to log out?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Log Out",
        style: "destructive",
        onPress: async () => {
          await clearStorage();
          await logout();
        },
      },
    ]);
  }, [logout]);

  const handleClearCache = useCallback(() => {
    Alert.alert(
      "Clear Cache",
      "This will clear locally cached data. Your account data is safe on the server.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Clear",
          onPress: async () => {
            await clearStorage();
            Alert.alert("Done", "Cache cleared successfully.");
          },
        },
      ]
    );
  }, []);

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
    >
      {/* Profile Section */}
      <View style={styles.profileSection}>
        <View style={styles.profileRow}>
          {user?.avatar_url ? (
            <Image source={{ uri: user.avatar_url }} style={styles.avatar} />
          ) : (
            <View style={styles.avatarPlaceholder}>
              <Text style={styles.avatarInitial}>
                {user?.username?.charAt(0).toUpperCase() || "?"}
              </Text>
            </View>
          )}
          <View style={styles.profileInfo}>
            <Text style={styles.username}>{user?.username || "Student"}</Text>
            <Text style={styles.userId}>ID: {user?.user_id || "N/A"}</Text>
          </View>
        </View>
      </View>

      {/* Notifications */}
      <Text style={styles.sectionTitle}>Notifications</Text>
      <View style={styles.settingsGroup}>
        <SettingToggle
          label="Study Reminders"
          description="Daily reminders to study"
          value={notifPrefs.studyReminders}
          onToggle={(v) => updateNotifPref("studyReminders", v)}
        />
        <Divider />
        <SettingToggle
          label="Achievement Alerts"
          description="Get notified when you unlock achievements"
          value={notifPrefs.achievementAlerts}
          onToggle={(v) => updateNotifPref("achievementAlerts", v)}
        />
        <Divider />
        <SettingToggle
          label="Streak Reminders"
          description="Remind you before your streak resets"
          value={notifPrefs.streakReminders}
          onToggle={(v) => updateNotifPref("streakReminders", v)}
        />
        <Divider />
        <SettingToggle
          label="Wellness Check-ins"
          description="Periodic wellness logging reminders"
          value={notifPrefs.wellnessCheckins}
          onToggle={(v) => updateNotifPref("wellnessCheckins", v)}
        />
      </View>

      {/* Timer Settings */}
      <Text style={styles.sectionTitle}>Timer</Text>
      <View style={styles.settingsGroup}>
        <SettingToggle
          label="Auto-start Breaks"
          description="Automatically begin break after work session"
          value={pomodoroSettings.autoStartBreaks}
          onToggle={(v) => updatePomodoroPref("autoStartBreaks", v)}
        />
        <Divider />
        <SettingToggle
          label="Auto-start Work"
          description="Automatically begin work after break"
          value={pomodoroSettings.autoStartWork}
          onToggle={(v) => updatePomodoroPref("autoStartWork", v)}
        />
        <Divider />
        <View style={styles.settingRow}>
          <View style={styles.settingInfo}>
            <Text style={styles.settingLabel}>Work Duration</Text>
          </View>
          <Text style={styles.settingValue}>
            {pomodoroSettings.workDuration}min
          </Text>
        </View>
        <Divider />
        <View style={styles.settingRow}>
          <View style={styles.settingInfo}>
            <Text style={styles.settingLabel}>Short Break</Text>
          </View>
          <Text style={styles.settingValue}>
            {pomodoroSettings.shortBreak}min
          </Text>
        </View>
        <Divider />
        <View style={styles.settingRow}>
          <View style={styles.settingInfo}>
            <Text style={styles.settingLabel}>Long Break</Text>
          </View>
          <Text style={styles.settingValue}>
            {pomodoroSettings.longBreak}min
          </Text>
        </View>
      </View>

      {/* Data & Privacy */}
      <Text style={styles.sectionTitle}>Data & Privacy</Text>
      <View style={styles.settingsGroup}>
        <TouchableOpacity
          style={styles.settingRow}
          onPress={handleClearCache}
          activeOpacity={0.7}
        >
          <View style={styles.settingInfo}>
            <Text style={styles.settingLabel}>Clear Cache</Text>
            <Text style={styles.settingDescription}>
              Remove locally stored data
            </Text>
          </View>
          <Text style={styles.chevron}>{"\u203A"}</Text>
        </TouchableOpacity>
        <Divider />
        <TouchableOpacity
          style={styles.settingRow}
          onPress={() =>
            Linking.openURL("https://studybot.example.com/privacy")
          }
          activeOpacity={0.7}
        >
          <View style={styles.settingInfo}>
            <Text style={styles.settingLabel}>Privacy Policy</Text>
          </View>
          <Text style={styles.chevron}>{"\u203A"}</Text>
        </TouchableOpacity>
        <Divider />
        <TouchableOpacity
          style={styles.settingRow}
          onPress={() =>
            Linking.openURL("https://studybot.example.com/terms")
          }
          activeOpacity={0.7}
        >
          <View style={styles.settingInfo}>
            <Text style={styles.settingLabel}>Terms of Service</Text>
          </View>
          <Text style={styles.chevron}>{"\u203A"}</Text>
        </TouchableOpacity>
      </View>

      {/* Logout */}
      <TouchableOpacity
        style={styles.logoutButton}
        onPress={handleLogout}
        activeOpacity={0.7}
      >
        <Text style={styles.logoutText}>Log Out</Text>
      </TouchableOpacity>

      {/* App version */}
      <Text style={styles.version}>StudyBot Mobile v1.0.0</Text>
    </ScrollView>
  );
}

function SettingToggle({
  label,
  description,
  value,
  onToggle,
}: {
  label: string;
  description?: string;
  value: boolean;
  onToggle: (value: boolean) => void;
}) {
  return (
    <View style={styles.settingRow}>
      <View style={styles.settingInfo}>
        <Text style={styles.settingLabel}>{label}</Text>
        {description && (
          <Text style={styles.settingDescription}>{description}</Text>
        )}
      </View>
      <Switch
        value={value}
        onValueChange={onToggle}
        trackColor={{
          false: Colors.cardAlt,
          true: Colors.primary + "60",
        }}
        thumbColor={value ? Colors.primary : Colors.textDisabled}
      />
    </View>
  );
}

function Divider() {
  return <View style={styles.divider} />;
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
  profileSection: {
    backgroundColor: Colors.card,
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  profileRow: {
    flexDirection: "row",
    alignItems: "center",
  },
  avatar: {
    width: 52,
    height: 52,
    borderRadius: 26,
    marginRight: 14,
    borderWidth: 2,
    borderColor: Colors.primary,
  },
  avatarPlaceholder: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: Colors.primary + "30",
    justifyContent: "center",
    alignItems: "center",
    marginRight: 14,
    borderWidth: 2,
    borderColor: Colors.primary,
  },
  avatarInitial: {
    fontSize: 20,
    fontWeight: "700",
    color: Colors.primary,
  },
  profileInfo: {
    flex: 1,
  },
  username: {
    fontSize: 18,
    fontWeight: "700",
    color: Colors.textPrimary,
  },
  userId: {
    fontSize: 12,
    color: Colors.textDisabled,
    marginTop: 2,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: "700",
    color: Colors.textMuted,
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: 8,
    marginTop: 4,
    paddingLeft: 4,
  },
  settingsGroup: {
    backgroundColor: Colors.card,
    borderRadius: 14,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: Colors.border,
    overflow: "hidden",
  },
  settingRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 16,
  },
  settingInfo: {
    flex: 1,
    marginRight: 12,
  },
  settingLabel: {
    fontSize: 15,
    color: Colors.textPrimary,
    fontWeight: "500",
  },
  settingDescription: {
    fontSize: 12,
    color: Colors.textMuted,
    marginTop: 2,
  },
  settingValue: {
    fontSize: 15,
    color: Colors.textSecondary,
    fontWeight: "600",
  },
  chevron: {
    fontSize: 22,
    color: Colors.textDisabled,
    fontWeight: "300",
  },
  divider: {
    height: 1,
    backgroundColor: Colors.border,
    marginLeft: 16,
  },
  logoutButton: {
    backgroundColor: Colors.error + "15",
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: "center",
    borderWidth: 1,
    borderColor: Colors.error + "30",
    marginBottom: 16,
  },
  logoutText: {
    color: Colors.error,
    fontSize: 16,
    fontWeight: "700",
  },
  version: {
    fontSize: 12,
    color: Colors.textDisabled,
    textAlign: "center",
    marginBottom: 16,
  },
});
