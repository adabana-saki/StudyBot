/**
 * App configuration constants.
 * In production, these would be sourced from environment variables
 * or a build configuration system.
 */

/** Base URL for the StudyBot API. */
export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL || "http://localhost:8000";

/** Discord OAuth configuration. */
export const DISCORD_CLIENT_ID =
  process.env.EXPO_PUBLIC_DISCORD_CLIENT_ID || "";

/** Deep link scheme for OAuth callback. */
export const APP_SCHEME = "studybot";

/** OAuth callback URL the backend redirects to after Discord auth. */
export const OAUTH_REDIRECT_URI = `${APP_SCHEME}://auth/callback`;

/** Backend endpoint that initiates Discord OAuth flow. */
export const DISCORD_AUTH_URL = `${API_BASE_URL}/api/auth/discord/login?redirect_uri=${encodeURIComponent(OAUTH_REDIRECT_URI)}`;

/** Default Pomodoro timer durations (in seconds). */
export const POMODORO = {
  WORK_DURATION: 25 * 60,
  SHORT_BREAK: 5 * 60,
  LONG_BREAK: 15 * 60,
  CYCLES_BEFORE_LONG_BREAK: 4,
} as const;

/** Flashcard quality ratings. */
export const FLASHCARD_QUALITY = {
  AGAIN: 1,
  HARD: 2,
  GOOD: 3,
  EASY: 4,
  PERFECT: 5,
} as const;

/** Phone lock levels. */
export const LOCK_LEVELS = {
  NUDGE: 1,
  LOCK: 2,
  SHIELD: 3,
} as const;

/** Wellness rating range. */
export const WELLNESS_RANGE = {
  MIN: 1,
  MAX: 5,
} as const;
