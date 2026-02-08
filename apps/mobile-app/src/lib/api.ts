/**
 * API client for communicating with the StudyBot FastAPI backend.
 * Handles authentication headers, token refresh on 401, and typed responses.
 */
import { API_BASE_URL } from "../constants/config";
import {
  getAccessToken,
  getRefreshToken,
  storeTokens,
  clearTokens,
  isTokenExpired,
} from "./auth";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface UserProfile {
  user_id: string;
  username: string;
  avatar_url: string | null;
  xp: number;
  level: number;
  xp_to_next_level: number;
  streak: number;
  coins: number;
  rank: number;
  guild_id: string;
}

export interface StudyStats {
  total_minutes: number;
  total_sessions: number;
  average_session: number;
  most_productive_day: string;
  period: string;
}

export interface DailyStudy {
  date: string;
  minutes: number;
}

export interface LeaderboardEntry {
  rank: number;
  user_id: string;
  username: string;
  avatar_url: string | null;
  value: number;
}

export interface Achievement {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  tier: "bronze" | "silver" | "gold" | "platinum";
  unlocked: boolean;
  unlocked_at: string | null;
  progress: number;
  target: number;
}

export interface FlashcardDeck {
  id: string;
  name: string;
  description: string;
  card_count: number;
  due_count: number;
  last_reviewed: string | null;
}

export interface Flashcard {
  id: string;
  deck_id: string;
  front: string;
  back: string;
  due_at: string;
  ease_factor: number;
  interval: number;
  repetitions: number;
}

export interface ReviewResult {
  card_id: string;
  next_due: string;
  new_interval: number;
  new_ease: number;
}

export interface WellnessEntry {
  id: string;
  mood: number;
  energy: number;
  stress: number;
  note: string | null;
  created_at: string;
}

export interface ApiError {
  detail: string;
  status: number;
}

// ─── Token refresh logic ──────────────────────────────────────────────────────

let refreshPromise: Promise<boolean> | null = null;

/**
 * Attempt to refresh the access token using the stored refresh token.
 * Returns true if refresh succeeded, false otherwise.
 * Deduplicates concurrent refresh attempts.
 */
async function refreshAccessToken(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const refreshToken = await getRefreshToken();
      if (!refreshToken) return false;

      const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        await clearTokens();
        return false;
      }

      const data = await response.json();
      await storeTokens(data.access_token, data.refresh_token);
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

// ─── Core fetch wrapper ───────────────────────────────────────────────────────

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
  skipAuth?: boolean;
}

/**
 * Make an authenticated API request. Automatically retries once on 401
 * after refreshing the access token.
 */
async function apiRequest<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = "GET", body, headers = {}, skipAuth = false } = options;

  // Check if token needs proactive refresh
  if (!skipAuth) {
    const token = await getAccessToken();
    if (token && isTokenExpired(token)) {
      await refreshAccessToken();
    }
  }

  const makeRequest = async (): Promise<Response> => {
    const requestHeaders: Record<string, string> = {
      "Content-Type": "application/json",
      ...headers,
    };

    if (!skipAuth) {
      const token = await getAccessToken();
      if (token) {
        requestHeaders["Authorization"] = `Bearer ${token}`;
      }
    }

    const config: RequestInit = {
      method,
      headers: requestHeaders,
    };

    if (body !== undefined) {
      config.body = JSON.stringify(body);
    }

    return fetch(`${API_BASE_URL}${path}`, config);
  };

  let response = await makeRequest();

  // On 401, try refreshing the token and retry once
  if (response.status === 401 && !skipAuth) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      response = await makeRequest();
    } else {
      throw {
        detail: "Authentication expired. Please log in again.",
        status: 401,
      } as ApiError;
    }
  }

  if (!response.ok) {
    let detail = "An unexpected error occurred.";
    try {
      const errorData = await response.json();
      detail = errorData.detail || detail;
    } catch {
      // response body was not JSON
    }
    throw { detail, status: response.status } as ApiError;
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ─── API methods ──────────────────────────────────────────────────────────────

/** Fetch the authenticated user's profile. */
export function getProfile(): Promise<UserProfile> {
  return apiRequest<UserProfile>("/api/stats/me");
}

/** Fetch study statistics for a given period. */
export function getStudyStats(
  period: "daily" | "weekly" | "monthly" | "all" = "weekly"
): Promise<StudyStats> {
  return apiRequest<StudyStats>(`/api/stats/me/study?period=${period}`);
}

/** Fetch daily study minutes for the last N days. */
export function getDailyStudy(days: number = 14): Promise<DailyStudy[]> {
  return apiRequest<DailyStudy[]>(`/api/stats/me/daily?days=${days}`);
}

/** Fetch leaderboard for a guild. */
export function getLeaderboard(
  guildId: string,
  category: "xp" | "streak" | "study_time" = "xp",
  period: "weekly" | "monthly" | "all" = "weekly"
): Promise<LeaderboardEntry[]> {
  return apiRequest<LeaderboardEntry[]>(
    `/api/leaderboard/${guildId}?category=${category}&period=${period}`
  );
}

/** Fetch all available achievements. */
export function getAllAchievements(): Promise<Achievement[]> {
  return apiRequest<Achievement[]>("/api/achievements/all");
}

/** Fetch the current user's achievements. */
export function getMyAchievements(): Promise<Achievement[]> {
  return apiRequest<Achievement[]>("/api/achievements/me");
}

/** Fetch all flashcard decks. */
export function getFlashcardDecks(): Promise<FlashcardDeck[]> {
  return apiRequest<FlashcardDeck[]>("/api/flashcards/decks");
}

/** Fetch cards due for review in a deck. */
export function getReviewCards(deckId: string): Promise<Flashcard[]> {
  return apiRequest<Flashcard[]>(`/api/flashcards/decks/${deckId}/review`);
}

/** Submit a flashcard review. */
export function submitReview(
  cardId: string,
  quality: number
): Promise<ReviewResult> {
  return apiRequest<ReviewResult>("/api/flashcards/review", {
    method: "POST",
    body: { card_id: cardId, quality },
  });
}

/** Fetch wellness entries for the current user. */
export function getWellnessEntries(): Promise<WellnessEntry[]> {
  return apiRequest<WellnessEntry[]>("/api/wellness/me");
}

/** Submit a new wellness entry. */
export function submitWellnessEntry(entry: {
  mood: number;
  energy: number;
  stress: number;
  note?: string;
}): Promise<WellnessEntry> {
  return apiRequest<WellnessEntry>("/api/wellness/me", {
    method: "POST",
    body: entry,
  });
}

/** Register a device push notification token. */
export function registerPushToken(
  deviceToken: string,
  platform: "ios" | "android"
): Promise<void> {
  return apiRequest<void>("/api/notifications/register", {
    method: "POST",
    body: { device_token: deviceToken, platform },
  });
}

export default {
  getProfile,
  getStudyStats,
  getDailyStudy,
  getLeaderboard,
  getAllAchievements,
  getMyAchievements,
  getFlashcardDecks,
  getReviewCards,
  submitReview,
  getWellnessEntries,
  submitWellnessEntry,
  registerPushToken,
};
