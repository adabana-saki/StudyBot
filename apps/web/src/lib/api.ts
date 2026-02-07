import {
  getToken,
  setToken,
  getRefreshToken,
  setRefreshToken,
  logout,
} from "./auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UserProfile {
  user_id: string;
  username: string;
  display_name: string;
  avatar_url: string;
  xp: number;
  level: number;
  streak_days: number;
  coins: number;
  rank: number;
}

export interface StudyStats {
  total_minutes: number;
  session_count: number;
  avg_minutes: number;
}

export interface DailyStudy {
  day: string;
  total_minutes: number;
}

export interface LeaderboardEntry {
  rank: number;
  user_id: string;
  username: string;
  display_name: string;
  avatar_url: string;
  value: number;
  level: number;
}

export interface Achievement {
  id: string;
  name: string;
  description: string;
  emoji: string;
  category: string;
  threshold: number;
}

export interface UserAchievement {
  achievement: Achievement;
  progress: number;
  unlocked: boolean;
  unlocked_at: string | null;
}

export interface FlashcardDeck {
  id: string;
  name: string;
  description: string;
  card_count: number;
  due_count: number;
  created_at: string;
}

export interface Flashcard {
  id: string;
  front: string;
  back: string;
  deck_id: string;
  ease_factor: number;
  interval: number;
  due_at: string;
}

export interface DeckStats {
  total_cards: number;
  due_cards: number;
  new_cards: number;
  learning_cards: number;
  mature_cards: number;
  average_ease: number;
}

export interface WellnessLog {
  id: string;
  mood: number;
  energy: number;
  stress: number;
  note: string;
  logged_at: string;
}

export interface WellnessAverages {
  avg_mood: number;
  avg_energy: number;
  avg_stress: number;
}

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const res = await fetch(`${API_URL}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) return false;

    const data = await res.json();
    setToken(data.access_token);
    setRefreshToken(data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

export async function fetchAPI<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  // If 401, try to refresh token and retry
  if (res.status === 401 && token) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      const newToken = getToken();
      headers["Authorization"] = `Bearer ${newToken}`;
      res = await fetch(`${API_URL}${path}`, {
        ...options,
        headers,
      });
    } else {
      logout();
      throw new Error("セッションの有効期限が切れました。再ログインしてください。");
    }
  }

  if (!res.ok) {
    const errorText = await res.text().catch(() => "Unknown error");
    throw new Error(`API Error ${res.status}: ${errorText}`);
  }

  return res.json();
}

// Profile
export function getProfile(): Promise<UserProfile> {
  return fetchAPI<UserProfile>("/api/stats/me");
}

// Study Stats
export function getStudyStats(
  period: string = "weekly"
): Promise<StudyStats> {
  return fetchAPI<StudyStats>(`/api/stats/me/study?period=${period}`);
}

export function getDailyStudy(days: number = 14): Promise<DailyStudy[]> {
  return fetchAPI<DailyStudy[]>(`/api/stats/me/daily?days=${days}`);
}

// Leaderboard
export function getLeaderboard(
  guildId: string,
  category: string = "xp",
  period: string = "all_time",
  limit: number = 20,
  offset: number = 0
): Promise<LeaderboardEntry[]> {
  return fetchAPI<LeaderboardEntry[]>(
    `/api/leaderboard/${guildId}?category=${category}&period=${period}&limit=${limit}&offset=${offset}`
  );
}

// Achievements
export function getAchievements(): Promise<Achievement[]> {
  return fetchAPI<Achievement[]>("/api/achievements/all");
}

export function getMyAchievements(): Promise<UserAchievement[]> {
  return fetchAPI<UserAchievement[]>("/api/achievements/me");
}

// Flashcards
export function getDecks(): Promise<FlashcardDeck[]> {
  return fetchAPI<FlashcardDeck[]>("/api/flashcards/decks");
}

export function getDeckCards(deckId: string): Promise<Flashcard[]> {
  return fetchAPI<Flashcard[]>(`/api/flashcards/decks/${deckId}/cards`);
}

export function getReviewCards(
  deckId: string,
  limit: number = 10
): Promise<Flashcard[]> {
  return fetchAPI<Flashcard[]>(
    `/api/flashcards/decks/${deckId}/review?limit=${limit}`
  );
}

export function submitReview(
  cardId: string,
  quality: number
): Promise<void> {
  return fetchAPI<void>("/api/flashcards/review", {
    method: "POST",
    body: JSON.stringify({ card_id: cardId, quality }),
  });
}

export function getDeckStats(deckId: string): Promise<DeckStats> {
  return fetchAPI<DeckStats>(`/api/flashcards/decks/${deckId}/stats`);
}

// Wellness
export function getWellness(days: number = 14): Promise<WellnessLog[]> {
  return fetchAPI<WellnessLog[]>(`/api/wellness/me?days=${days}`);
}

export function getWellnessAverages(
  days: number = 7
): Promise<WellnessAverages> {
  return fetchAPI<WellnessAverages>(`/api/wellness/me/averages?days=${days}`);
}

export function logWellness(data: {
  mood: number;
  energy: number;
  stress: number;
  note: string;
}): Promise<WellnessLog> {
  return fetchAPI<WellnessLog>("/api/wellness/me", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
