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

// === Shop ===
export interface ShopItem {
  id: number;
  name: string;
  description: string;
  category: string;
  price: number;
  rarity: string;
  emoji: string;
}

export interface InventoryItem {
  id: number;
  item_id: number;
  name: string;
  emoji: string;
  category: string;
  quantity: number;
  equipped: boolean;
}

export interface CurrencyBalance {
  balance: number;
  total_earned: number;
  total_spent: number;
}

export function getShopItems(category?: string): Promise<ShopItem[]> {
  const params = category ? `?category=${category}` : "";
  return fetchAPI<ShopItem[]>(`/api/shop/items${params}`);
}

export function getInventory(): Promise<InventoryItem[]> {
  return fetchAPI<InventoryItem[]>("/api/shop/inventory");
}

export function purchaseItem(itemId: number): Promise<{ message: string; balance: number }> {
  return fetchAPI("/api/shop/purchase", {
    method: "POST",
    body: JSON.stringify({ item_id: itemId }),
  });
}

export function getCurrencyBalance(): Promise<CurrencyBalance> {
  return fetchAPI<CurrencyBalance>("/api/shop/balance");
}

// === Todos ===
export interface TodoItem {
  id: number;
  title: string;
  priority: number;
  status: string;
  deadline: string | null;
  completed_at: string | null;
  created_at: string;
}

export function getTodos(status?: string): Promise<TodoItem[]> {
  const params = status ? `?status=${status}` : "";
  return fetchAPI<TodoItem[]>(`/api/todos${params}`);
}

export function createTodo(data: {
  title: string;
  priority?: number;
  deadline?: string;
}): Promise<TodoItem> {
  return fetchAPI<TodoItem>("/api/todos", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function completeTodo(id: number): Promise<TodoItem> {
  return fetchAPI<TodoItem>(`/api/todos/${id}/complete`, { method: "POST" });
}

export function deleteTodo(id: number): Promise<void> {
  return fetchAPI(`/api/todos/${id}`, { method: "DELETE" });
}

// === Plans ===
export interface StudyPlanItem {
  id: number;
  subject: string;
  goal: string;
  deadline: string | null;
  status: string;
  ai_feedback: string | null;
  created_at: string;
}

export interface PlanTask {
  id: number;
  title: string;
  description: string;
  order_index: number;
  status: string;
  completed_at: string | null;
}

export interface StudyPlanDetail extends StudyPlanItem {
  tasks: PlanTask[];
}

export function getPlans(): Promise<StudyPlanItem[]> {
  return fetchAPI<StudyPlanItem[]>("/api/plans");
}

export function getPlanDetail(id: number): Promise<StudyPlanDetail> {
  return fetchAPI<StudyPlanDetail>(`/api/plans/${id}`);
}

// === Profile ===
export interface UserPreferences {
  display_name: string | null;
  bio: string;
  timezone: string;
  daily_goal_minutes: number;
  notifications_enabled: boolean;
  theme: string;
  custom_title: string | null;
}

export interface ProfileDetail {
  user_id: number;
  username: string;
  xp: number;
  level: number;
  streak_days: number;
  coins: number;
  rank: number;
  preferences: UserPreferences | null;
}

export function getProfileDetail(): Promise<ProfileDetail> {
  return fetchAPI<ProfileDetail>("/api/profile/me");
}

export function updateProfile(data: {
  display_name?: string;
  bio?: string;
  timezone?: string;
  daily_goal_minutes?: number;
}): Promise<ProfileDetail> {
  return fetchAPI<ProfileDetail>("/api/profile/me", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// === Server Stats ===
export interface ServerStats {
  member_count: number;
  total_minutes: number;
  total_sessions: number;
  weekly_minutes: number;
  weekly_active_members: number;
  tasks_completed: number;
  raids_completed: number;
}

export function getServerStats(guildId: string): Promise<ServerStats> {
  return fetchAPI<ServerStats>(`/api/server/${guildId}/stats`);
}

// === Focus / Lock ===
export interface FocusSession {
  session_id: number;
  lock_type: string;
  duration_minutes: number;
  coins_bet: number;
  unlock_level: number;
  state: string;
  remaining_seconds: number;
  remaining_minutes: number;
  end_time: string | null;
  started_at: string | null;
}

export interface FocusHistoryEntry {
  id: number;
  lock_type: string;
  duration_minutes: number;
  coins_bet: number;
  unlock_level: number;
  state: string;
  started_at: string;
  ended_at: string | null;
}

export interface LockSettings {
  default_unlock_level: number;
  default_duration: number;
  default_coin_bet: number;
  block_categories: string[];
  custom_blocked_urls: string[];
}

export interface UnlockResult {
  success: boolean;
  coins_earned: number;
  coins_returned: number;
  message: string;
}

export function getFocusStatus(): Promise<FocusSession | null> {
  return fetchAPI<FocusSession | null>("/api/focus/status");
}

export function startFocus(data: {
  duration: number;
  unlock_level: number;
  coins_bet: number;
}): Promise<FocusSession> {
  return fetchAPI<FocusSession>("/api/focus/start", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function endFocus(): Promise<UnlockResult> {
  return fetchAPI<UnlockResult>("/api/focus/end", { method: "POST" });
}

export function unlockWithCode(code: string): Promise<UnlockResult> {
  return fetchAPI<UnlockResult>("/api/focus/unlock", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

export function penaltyUnlock(): Promise<{
  success: boolean;
  coins_lost: number;
  penalty_rate: number;
  message: string;
}> {
  return fetchAPI("/api/focus/penalty-unlock", { method: "POST" });
}

export function requestFocusCode(): Promise<{ message: string }> {
  return fetchAPI("/api/focus/request-code", { method: "POST" });
}

export function getLockSettings(): Promise<LockSettings> {
  return fetchAPI<LockSettings>("/api/focus/settings");
}

export function updateLockSettings(data: Partial<LockSettings>): Promise<LockSettings> {
  return fetchAPI<LockSettings>("/api/focus/settings", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function getFocusHistory(limit: number = 20): Promise<FocusHistoryEntry[]> {
  return fetchAPI<FocusHistoryEntry[]>(`/api/focus/history?limit=${limit}`);
}

// === Activity ===
export interface ActivityEvent {
  id: number;
  user_id: number;
  username: string;
  event_type: string;
  event_data: Record<string, unknown>;
  created_at: string;
}

export interface ActiveStudier {
  user_id: number;
  username: string;
  event_type: string;
  event_data: Record<string, unknown>;
  started_at: string;
}

export function getActivityFeed(guildId: string, limit: number = 50): Promise<ActivityEvent[]> {
  return fetchAPI<ActivityEvent[]>(`/api/activity/${guildId}?limit=${limit}`);
}

export function getStudyingNow(guildId: string): Promise<ActiveStudier[]> {
  return fetchAPI<ActiveStudier[]>(`/api/activity/${guildId}/studying-now`);
}

// === Buddy ===
export interface BuddyProfile {
  user_id: number;
  subjects: string[];
  preferred_times: string[];
  study_style: string;
  active: boolean;
  username?: string;
}

export interface BuddyMatch {
  id: number;
  user_a: number;
  user_b: number;
  username_a: string;
  username_b: string;
  guild_id: number;
  subject: string | null;
  compatibility_score: number;
  status: string;
  matched_at: string;
}

export function getBuddyProfile(): Promise<BuddyProfile | null> {
  return fetchAPI<BuddyProfile | null>("/api/buddy/profile");
}

export function updateBuddyProfile(data: {
  subjects?: string[];
  preferred_times?: string[];
  study_style?: string;
}): Promise<BuddyProfile> {
  return fetchAPI<BuddyProfile>("/api/buddy/profile", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function getBuddyMatches(): Promise<BuddyMatch[]> {
  return fetchAPI<BuddyMatch[]>("/api/buddy/matches");
}

export function getAvailableBuddies(): Promise<BuddyProfile[]> {
  return fetchAPI<BuddyProfile[]>("/api/buddy/available");
}

// === Challenges ===
export interface Challenge {
  id: number;
  creator_id: number;
  creator_name: string;
  guild_id: number;
  name: string;
  description: string;
  goal_type: string;
  goal_target: number;
  duration_days: number;
  start_date: string;
  end_date: string;
  xp_multiplier: number;
  status: string;
  participant_count: number;
  created_at: string;
}

export interface ChallengeLeaderboardEntry {
  user_id: number;
  username: string;
  progress: number;
  checkins: number;
  completed: boolean;
}

export interface ChallengeDetail extends Challenge {
  participants: ChallengeLeaderboardEntry[];
}

export function getChallenges(guildId: string = "0", status?: string): Promise<Challenge[]> {
  const params = status ? `&status=${status}` : "";
  return fetchAPI<Challenge[]>(`/api/challenges?guild_id=${guildId}${params}`);
}

export function getChallengeDetail(id: number): Promise<ChallengeDetail> {
  return fetchAPI<ChallengeDetail>(`/api/challenges/${id}`);
}

export function joinChallenge(id: number): Promise<{ message: string }> {
  return fetchAPI(`/api/challenges/${id}/join`, { method: "POST" });
}

export function challengeCheckin(id: number, progress: number, note?: string): Promise<{ message: string }> {
  return fetchAPI(`/api/challenges/${id}/checkin`, {
    method: "POST",
    body: JSON.stringify({ progress, note: note || "" }),
  });
}

export function getChallengeLeaderboard(id: number): Promise<ChallengeLeaderboardEntry[]> {
  return fetchAPI<ChallengeLeaderboardEntry[]>(`/api/challenges/${id}/leaderboard`);
}

// === Sessions ===
export interface ActiveSession {
  id: number;
  user_id: number;
  username: string;
  session_type: string;
  source_platform: string;
  topic: string;
  duration_minutes: number;
  started_at: string;
  end_time: string;
  remaining_seconds: number;
}

export function getActiveSessions(): Promise<ActiveSession[]> {
  return fetchAPI<ActiveSession[]>("/api/sessions/active");
}

export function startSession(data: {
  session_type: string;
  duration_minutes: number;
  topic?: string;
}): Promise<ActiveSession> {
  return fetchAPI<ActiveSession>("/api/sessions/start", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function endSession(): Promise<{ message: string }> {
  return fetchAPI("/api/sessions/end", { method: "POST" });
}

// === Insights ===
export interface UserInsight {
  id: number;
  insight_type: string;
  title: string;
  body: string;
  data: Record<string, unknown>;
  confidence: number;
  generated_at: string;
}

export interface WeeklyReport {
  id: number;
  week_start: string;
  week_end: string;
  summary: string;
  insights: Array<{ type: string; title: string; body: string; confidence: number }>;
  generated_at: string;
  raw_data?: Record<string, unknown>;
}

export function getMyInsights(): Promise<UserInsight[]> {
  return fetchAPI<UserInsight[]>("/api/insights/me");
}

export function getMyReports(): Promise<WeeklyReport[]> {
  return fetchAPI<WeeklyReport[]>("/api/insights/me/reports");
}

export function getReportDetail(id: number): Promise<WeeklyReport> {
  return fetchAPI<WeeklyReport>(`/api/insights/me/reports/${id}`);
}

// === Timeline ===
export interface TimelineEvent {
  id: number;
  user_id: number;
  username: string;
  event_type: string;
  event_data: Record<string, unknown>;
  created_at: string;
  reaction_counts: Record<string, number>;
  my_reactions: string[];
  comment_count: number;
}

export interface CommentResponse {
  id: number;
  user_id: number;
  username: string;
  body: string;
  created_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}

export function getTimeline(guildId: string, offset = 0, limit = 30): Promise<PaginatedResponse<TimelineEvent>> {
  return fetchAPI<PaginatedResponse<TimelineEvent>>(
    `/api/timeline/${guildId}?offset=${offset}&limit=${limit}`
  );
}

export function addReaction(eventId: number, type: string): Promise<void> {
  return fetchAPI("/api/timeline/" + eventId + "/reactions", {
    method: "POST",
    body: JSON.stringify({ reaction_type: type }),
  });
}

export function removeReaction(eventId: number, type: string): Promise<void> {
  return fetchAPI(`/api/timeline/${eventId}/reactions/${type}`, {
    method: "DELETE",
  });
}

export function getComments(eventId: number): Promise<CommentResponse[]> {
  return fetchAPI<CommentResponse[]>(`/api/timeline/${eventId}/comments`);
}

export function addComment(eventId: number, body: string): Promise<CommentResponse> {
  return fetchAPI<CommentResponse>(`/api/timeline/${eventId}/comments`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
}

export function deleteComment(commentId: number): Promise<void> {
  return fetchAPI(`/api/timeline/comments/${commentId}`, { method: "DELETE" });
}

// === Battles ===
export interface TeamBattleInfo {
  team_id: number;
  name: string;
  score: number;
  member_count: number;
}

export interface BattleResponse {
  id: number;
  guild_id: number;
  goal_type: string;
  duration_days: number;
  start_date: string;
  end_date: string;
  status: string;
  xp_multiplier: number;
  team_a: TeamBattleInfo;
  team_b: TeamBattleInfo;
  winner_team_id: number | null;
}

export interface BattleContribution {
  user_id: number;
  username: string;
  team_id: number;
  contribution: number;
  source: string;
}

export interface BattleDetailResponse extends BattleResponse {
  contributions: BattleContribution[];
}

export function getBattles(guildId: string): Promise<BattleResponse[]> {
  return fetchAPI<BattleResponse[]>(`/api/battles/${guildId}`);
}

export function getBattleDetail(guildId: string, battleId: number): Promise<BattleDetailResponse> {
  return fetchAPI<BattleDetailResponse>(`/api/battles/${guildId}/${battleId}`);
}

// === Rooms ===
export interface StudyRoom {
  id: number;
  guild_id: number;
  name: string;
  description: string;
  theme: string;
  collective_goal_minutes: number;
  collective_progress_minutes: number;
  max_occupants: number;
  member_count: number;
  state: string;
}

export interface RoomMember {
  user_id: number;
  username: string;
  platform: string;
  topic: string;
  joined_at: string;
}

export interface RoomDetail extends StudyRoom {
  members: RoomMember[];
}

export function getRooms(guildId: string): Promise<StudyRoom[]> {
  return fetchAPI<StudyRoom[]>(`/api/rooms/${guildId}`);
}

export function getRoomDetail(guildId: string, roomId: number): Promise<RoomDetail> {
  return fetchAPI<RoomDetail>(`/api/rooms/${guildId}/${roomId}`);
}

export function joinRoom(guildId: string, roomId: number, topic?: string): Promise<{ status: string }> {
  return fetchAPI(`/api/rooms/${guildId}/${roomId}/join`, {
    method: "POST",
    body: JSON.stringify({ topic: topic || "" }),
  });
}

export function leaveRoom(guildId: string, roomId: number): Promise<{ status: string; duration_minutes: number }> {
  return fetchAPI(`/api/rooms/${guildId}/${roomId}/leave`, { method: "POST" });
}

// === Server Analytics ===
export interface EngagementData {
  date: string;
  active_users: number;
  sessions: number;
  total_minutes: number;
}

export interface AtRiskMember {
  user_id: number;
  username: string;
  best_streak: number;
  last_study_date: string | null;
  days_inactive: number;
  risk_score: number;
}

export interface CommunityHealth {
  score: number;
  dau_mau_ratio: number;
  retention_rate: number;
  avg_streak: number;
  churn_rate: number;
}

export interface TopicAnalysis {
  topic: string;
  count: number;
  total_minutes: number;
  this_week: number;
  last_week: number;
}

export interface OptimalTime {
  day_of_week: number;
  hour: number;
  session_count: number;
  total_minutes: number;
}

export function getEngagement(guildId: string, days = 30): Promise<EngagementData[]> {
  return fetchAPI<EngagementData[]>(`/api/server/${guildId}/analytics/engagement?days=${days}`);
}

export function getAtRiskMembers(guildId: string): Promise<AtRiskMember[]> {
  return fetchAPI<AtRiskMember[]>(`/api/server/${guildId}/analytics/at-risk`);
}

export function getCommunityHealth(guildId: string): Promise<CommunityHealth> {
  return fetchAPI<CommunityHealth>(`/api/server/${guildId}/analytics/health`);
}

export function getTopicAnalysis(guildId: string): Promise<TopicAnalysis[]> {
  return fetchAPI<TopicAnalysis[]>(`/api/server/${guildId}/analytics/topics`);
}

export function getOptimalTimes(guildId: string): Promise<OptimalTime[]> {
  return fetchAPI<OptimalTime[]>(`/api/server/${guildId}/analytics/optimal-times`);
}

export function createAction(
  guildId: string,
  actionType: string,
  actionData: Record<string, unknown>,
  scheduledFor?: string
): Promise<{ status: string; id?: number }> {
  return fetchAPI(`/api/server/${guildId}/actions`, {
    method: "POST",
    body: JSON.stringify({
      action_type: actionType,
      action_data: actionData,
      scheduled_for: scheduledFor,
    }),
  });
}
