/**
 * Token management using Expo SecureStore.
 * Handles JWT access/refresh token storage and retrieval.
 */
import * as SecureStore from "expo-secure-store";

const TOKEN_KEYS = {
  ACCESS_TOKEN: "studybot_access_token",
  REFRESH_TOKEN: "studybot_refresh_token",
  USER_ID: "studybot_user_id",
} as const;

/**
 * Store authentication tokens securely.
 */
export async function storeTokens(
  accessToken: string,
  refreshToken: string
): Promise<void> {
  await Promise.all([
    SecureStore.setItemAsync(TOKEN_KEYS.ACCESS_TOKEN, accessToken),
    SecureStore.setItemAsync(TOKEN_KEYS.REFRESH_TOKEN, refreshToken),
  ]);
}

/**
 * Retrieve the stored access token, or null if not present.
 */
export async function getAccessToken(): Promise<string | null> {
  try {
    return await SecureStore.getItemAsync(TOKEN_KEYS.ACCESS_TOKEN);
  } catch {
    return null;
  }
}

/**
 * Retrieve the stored refresh token, or null if not present.
 */
export async function getRefreshToken(): Promise<string | null> {
  try {
    return await SecureStore.getItemAsync(TOKEN_KEYS.REFRESH_TOKEN);
  } catch {
    return null;
  }
}

/**
 * Store the user ID for quick access.
 */
export async function storeUserId(userId: string): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_KEYS.USER_ID, userId);
}

/**
 * Retrieve the stored user ID.
 */
export async function getUserId(): Promise<string | null> {
  try {
    return await SecureStore.getItemAsync(TOKEN_KEYS.USER_ID);
  } catch {
    return null;
  }
}

/**
 * Clear all stored authentication data.
 */
export async function clearTokens(): Promise<void> {
  await Promise.all([
    SecureStore.deleteItemAsync(TOKEN_KEYS.ACCESS_TOKEN),
    SecureStore.deleteItemAsync(TOKEN_KEYS.REFRESH_TOKEN),
    SecureStore.deleteItemAsync(TOKEN_KEYS.USER_ID),
  ]);
}

/**
 * Check if user has stored tokens (may be expired).
 */
export async function hasTokens(): Promise<boolean> {
  const token = await getAccessToken();
  return token !== null;
}

/**
 * Parse a JWT token to extract the payload without verification.
 * Used only for reading expiry client-side; the server always validates.
 */
export function parseJwtPayload(
  token: string
): Record<string, unknown> | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = parts[1];
    const decoded = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(decoded);
  } catch {
    return null;
  }
}

/**
 * Check if an access token is expired (with 60-second buffer).
 */
export function isTokenExpired(token: string): boolean {
  const payload = parseJwtPayload(token);
  if (!payload || typeof payload.exp !== "number") return true;
  const expiresAt = payload.exp * 1000;
  const bufferMs = 60 * 1000;
  return Date.now() >= expiresAt - bufferMs;
}
