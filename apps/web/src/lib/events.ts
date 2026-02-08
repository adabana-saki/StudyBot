// リアルタイムイベント型定義

export const EVENT_TYPES = {
  STUDY_START: "study_start",
  STUDY_END: "study_end",
  POMODORO_COMPLETE: "pomodoro_complete",
  STUDY_LOG: "study_log",
  XP_GAIN: "xp_gain",
  LEVEL_UP: "level_up",
  ACHIEVEMENT_UNLOCK: "achievement_unlock",
  TODO_COMPLETE: "todo_complete",
  FOCUS_START: "focus_start",
  FOCUS_END: "focus_end",
  LOCK_START: "lock_start",
  LOCK_END: "lock_end",
  RAID_JOIN: "raid_join",
  RAID_COMPLETE: "raid_complete",
  FLASHCARD_REVIEW: "flashcard_review",
  BUDDY_MATCH: "buddy_match",
  CHALLENGE_JOIN: "challenge_join",
  CHALLENGE_CHECKIN: "challenge_checkin",
  SESSION_SYNC: "session_sync",
  INSIGHTS_READY: "insights_ready",
} as const;

export type EventType = (typeof EVENT_TYPES)[keyof typeof EVENT_TYPES];

export interface BaseEvent {
  type: EventType;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface StudyEvent extends BaseEvent {
  type: "study_start" | "study_end";
  data: {
    user_id: number;
    guild_id: number;
    topic: string;
    username: string;
    duration_minutes?: number;
  };
}

export interface XPEvent extends BaseEvent {
  type: "xp_gain" | "level_up";
  data: {
    user_id: number;
    guild_id: number;
    username: string;
    amount?: number;
    reason?: string;
    new_level?: number;
  };
}

export interface AchievementEvent extends BaseEvent {
  type: "achievement_unlock";
  data: {
    user_id: number;
    guild_id: number;
    username: string;
    achievement_name: string;
    achievement_emoji: string;
  };
}

export interface SessionSyncEvent extends BaseEvent {
  type: "session_sync";
  data: {
    user_id: number;
    session_type: string;
    source: string;
    action: string;
    topic: string;
  };
}

export type StudyBotEvent =
  | StudyEvent
  | XPEvent
  | AchievementEvent
  | SessionSyncEvent
  | BaseEvent;

// イベント表示用ラベル
export const EVENT_LABELS: Record<string, { label: string; icon: string; color: string }> = {
  study_start: { label: "学習開始", icon: "📖", color: "text-blue-400" },
  study_end: { label: "学習完了", icon: "✅", color: "text-green-400" },
  pomodoro_complete: { label: "ポモドーロ完了", icon: "🍅", color: "text-red-400" },
  study_log: { label: "学習記録", icon: "📝", color: "text-blue-300" },
  xp_gain: { label: "XP獲得", icon: "⭐", color: "text-yellow-400" },
  level_up: { label: "レベルアップ", icon: "🎉", color: "text-purple-400" },
  achievement_unlock: { label: "実績解除", icon: "🏆", color: "text-orange-400" },
  todo_complete: { label: "タスク完了", icon: "✔️", color: "text-green-300" },
  focus_start: { label: "フォーカス開始", icon: "🎯", color: "text-cyan-400" },
  focus_end: { label: "フォーカス終了", icon: "🎯", color: "text-cyan-300" },
  lock_start: { label: "ロック開始", icon: "🔒", color: "text-red-300" },
  lock_end: { label: "ロック解除", icon: "🔓", color: "text-green-300" },
  raid_join: { label: "レイド参加", icon: "⚔️", color: "text-purple-300" },
  raid_complete: { label: "レイド完了", icon: "🛡️", color: "text-purple-400" },
  flashcard_review: { label: "カード復習", icon: "🃏", color: "text-indigo-400" },
  buddy_match: { label: "バディマッチ", icon: "🤝", color: "text-pink-400" },
  challenge_join: { label: "チャレンジ参加", icon: "🏁", color: "text-amber-400" },
  challenge_checkin: { label: "チェックイン", icon: "📋", color: "text-amber-300" },
  session_sync: { label: "セッション同期", icon: "🔄", color: "text-teal-400" },
  insights_ready: { label: "インサイト完成", icon: "🧠", color: "text-violet-400" },
};
