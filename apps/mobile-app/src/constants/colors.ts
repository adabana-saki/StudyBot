/**
 * Theme colors for the StudyBot mobile app.
 * Dark mode by default, matching the web UI design system.
 */
export const Colors = {
  // Backgrounds
  background: "#111827", // gray-900
  card: "#1F2937", // gray-800
  cardAlt: "#374151", // gray-700
  surface: "#4B5563", // gray-600
  border: "#374151", // gray-700

  // Primary & Accent
  primary: "#5865F2", // Discord blurple
  primaryLight: "#7289DA",
  primaryDark: "#4752C4",
  accent: "#22C55E", // Green for success
  accentDark: "#16A34A",

  // Semantic
  warning: "#F59E0B", // Amber
  warningDark: "#D97706",
  error: "#EF4444", // Red
  errorDark: "#DC2626",
  info: "#3B82F6", // Blue

  // Text
  textPrimary: "#F9FAFB", // gray-50
  textSecondary: "#D1D5DB", // gray-300
  textMuted: "#9CA3AF", // gray-400
  textDisabled: "#6B7280", // gray-500

  // Specific UI
  xpBar: "#8B5CF6", // Purple for XP
  xpBarBackground: "#374151",
  streak: "#F59E0B", // Amber for streaks
  coins: "#EAB308", // Yellow for coins
  timer: "#5865F2",
  timerBreak: "#22C55E",

  // Lock levels
  lockNudge: "#F59E0B",
  lockLock: "#EF4444",
  lockShield: "#DC2626",

  // Overlay
  overlay: "rgba(0, 0, 0, 0.7)",
  overlayDark: "rgba(0, 0, 0, 0.85)",
} as const;

export type ColorKey = keyof typeof Colors;
