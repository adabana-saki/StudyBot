/**
 * AsyncStorage helpers for persisting non-sensitive app data.
 * For sensitive data (tokens), use SecureStore via auth.ts instead.
 */
import AsyncStorage from "@react-native-async-storage/async-storage";

const KEYS = {
  POMODORO_SETTINGS: "studybot:pomodoro_settings",
  NOTIFICATION_PREFS: "studybot:notification_prefs",
  ONBOARDING_COMPLETE: "studybot:onboarding_complete",
  LAST_ACTIVE_DECK: "studybot:last_active_deck",
  PHONE_LOCK_CONFIG: "studybot:phone_lock_config",
  CACHED_PROFILE: "studybot:cached_profile",
} as const;

export type StorageKey = (typeof KEYS)[keyof typeof KEYS];

/**
 * Store a JSON-serializable value.
 */
export async function setItem<T>(key: StorageKey, value: T): Promise<void> {
  try {
    const json = JSON.stringify(value);
    await AsyncStorage.setItem(key, json);
  } catch (error) {
    console.error(`[Storage] Failed to set ${key}:`, error);
  }
}

/**
 * Retrieve a stored value, returning null if not found.
 */
export async function getItem<T>(key: StorageKey): Promise<T | null> {
  try {
    const json = await AsyncStorage.getItem(key);
    if (json === null) return null;
    return JSON.parse(json) as T;
  } catch (error) {
    console.error(`[Storage] Failed to get ${key}:`, error);
    return null;
  }
}

/**
 * Remove a stored value.
 */
export async function removeItem(key: StorageKey): Promise<void> {
  try {
    await AsyncStorage.removeItem(key);
  } catch (error) {
    console.error(`[Storage] Failed to remove ${key}:`, error);
  }
}

/**
 * Clear all StudyBot-related storage.
 */
export async function clearAll(): Promise<void> {
  try {
    const allKeys = Object.values(KEYS);
    await AsyncStorage.multiRemove(allKeys);
  } catch (error) {
    console.error("[Storage] Failed to clear all:", error);
  }
}

// Typed helpers for common data

export interface PomodoroSettings {
  workDuration: number;
  shortBreak: number;
  longBreak: number;
  cyclesBeforeLongBreak: number;
  autoStartBreaks: boolean;
  autoStartWork: boolean;
}

export interface NotificationPrefs {
  studyReminders: boolean;
  achievementAlerts: boolean;
  streakReminders: boolean;
  wellnessCheckins: boolean;
  reminderTime: string; // HH:MM format
}

export interface PhoneLockConfig {
  level: 1 | 2 | 3;
  coinBet: number;
  duration: number; // minutes
  breakPenalty: number; // coins deducted
}

export async function getPomodoroSettings(): Promise<PomodoroSettings | null> {
  return getItem<PomodoroSettings>(KEYS.POMODORO_SETTINGS);
}

export async function setPomodoroSettings(
  settings: PomodoroSettings
): Promise<void> {
  return setItem(KEYS.POMODORO_SETTINGS, settings);
}

export async function getNotificationPrefs(): Promise<NotificationPrefs | null> {
  return getItem<NotificationPrefs>(KEYS.NOTIFICATION_PREFS);
}

export async function setNotificationPrefs(
  prefs: NotificationPrefs
): Promise<void> {
  return setItem(KEYS.NOTIFICATION_PREFS, prefs);
}

export async function getPhoneLockConfig(): Promise<PhoneLockConfig | null> {
  return getItem<PhoneLockConfig>(KEYS.PHONE_LOCK_CONFIG);
}

export async function setPhoneLockConfig(
  config: PhoneLockConfig
): Promise<void> {
  return setItem(KEYS.PHONE_LOCK_CONFIG, config);
}

export async function isOnboardingComplete(): Promise<boolean> {
  const result = await getItem<boolean>(KEYS.ONBOARDING_COMPLETE);
  return result === true;
}

export async function setOnboardingComplete(): Promise<void> {
  return setItem(KEYS.ONBOARDING_COMPLETE, true);
}

export { KEYS };
