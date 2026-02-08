"""Pydantic スキーマ定義

StudyBot APIの全リクエスト/レスポンスモデルを定義する。
"""

from datetime import date, datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """ページネーション付きレスポンス"""

    items: list[T]
    total: int
    offset: int
    limit: int


# === Auth ===
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthCodeExchangeRequest(BaseModel):
    code: str = Field(min_length=1, max_length=100, description="認証コード")


# === User / Stats ===
class UserProfile(BaseModel):
    user_id: int
    username: str
    xp: int
    level: int
    streak_days: int
    coins: int
    rank: int


class StudyStats(BaseModel):
    total_minutes: int
    session_count: int
    avg_minutes: float
    period: str


class DailyStudy(BaseModel):
    day: date
    total_minutes: int


# === Leaderboard ===
class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    username: str
    value: int  # XP, minutes, or tasks
    level: int | None = None


class LeaderboardResponse(BaseModel):
    category: str
    period: str
    entries: list[LeaderboardEntry]


# === Achievements ===
class Achievement(BaseModel):
    id: int
    key: str
    name: str
    description: str | None
    emoji: str
    category: str
    target_value: int
    reward_coins: int


class UserAchievement(BaseModel):
    achievement: Achievement
    progress: int
    unlocked: bool
    unlocked_at: datetime | None = None


# === Flashcards ===
class FlashcardDeck(BaseModel):
    id: int
    name: str
    description: str
    card_count: int
    created_at: datetime


class Flashcard(BaseModel):
    id: int
    front: str
    back: str
    easiness: float
    interval: int
    repetitions: int
    next_review: datetime


class ReviewRequest(BaseModel):
    card_id: int
    quality: int = Field(ge=1, le=5, description="復習品質 (1-5)")


class DeckStats(BaseModel):
    deck_id: int
    name: str
    total: int
    mastered: int
    learning: int
    new: int


# === Wellness ===
class WellnessLog(BaseModel):
    id: int
    mood: int
    energy: int
    stress: int
    note: str
    logged_at: datetime


class WellnessAverage(BaseModel):
    avg_mood: float
    avg_energy: float
    avg_stress: float
    days: int


class WellnessLogRequest(BaseModel):
    mood: int = Field(ge=1, le=5, description="気分 (1-5)")
    energy: int = Field(ge=1, le=5, description="エネルギー (1-5)")
    stress: int = Field(ge=1, le=5, description="ストレス (1-5)")
    note: str = Field(default="", max_length=500)


# === Notifications ===
class DeviceTokenRequest(BaseModel):
    device_token: str = Field(min_length=10, max_length=1000)
    platform: Literal["ios", "android", "web"]


class NotificationLog(BaseModel):
    id: int
    type: str
    title: str
    body: str | None
    data: dict | None
    sent_at: datetime
    read_at: datetime | None


# === Shop / Currency ===
class ShopItem(BaseModel):
    id: int
    name: str
    description: str | None
    category: str
    price: int
    rarity: str
    emoji: str


class InventoryItem(BaseModel):
    id: int
    item_id: int
    name: str
    emoji: str
    category: str
    quantity: int
    equipped: bool


class PurchaseRequest(BaseModel):
    item_id: int


class CurrencyBalance(BaseModel):
    balance: int
    total_earned: int
    total_spent: int


# === Todos ===
class TodoItem(BaseModel):
    id: int
    title: str
    priority: int
    status: str
    deadline: datetime | None
    completed_at: datetime | None
    created_at: datetime


class TodoCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200, description="タスクタイトル")
    priority: int = Field(default=2, ge=1, le=3, description="優先度 (1=低, 2=中, 3=高)")
    deadline: datetime | None = None


class TodoUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    priority: int | None = Field(default=None, ge=1, le=3)
    deadline: datetime | None = None
    status: Literal["pending", "completed"] | None = None


# === Plans ===
class PlanTask(BaseModel):
    id: int
    title: str
    description: str
    order_index: int
    status: str
    completed_at: datetime | None


class StudyPlan(BaseModel):
    id: int
    subject: str
    goal: str
    deadline: date | None
    status: str
    ai_feedback: str | None
    created_at: datetime


class StudyPlanDetail(StudyPlan):
    tasks: list[PlanTask] = []


# === Profile ===
class UserPreferences(BaseModel):
    display_name: str | None = None
    bio: str = ""
    timezone: str = "Asia/Tokyo"
    daily_goal_minutes: int = 60
    notifications_enabled: bool = True
    theme: str = "dark"
    custom_title: str | None = None


class ProfileDetail(BaseModel):
    user_id: int
    username: str
    xp: int
    level: int
    streak_days: int
    coins: int
    rank: int
    preferences: UserPreferences | None = None


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    bio: str | None = Field(default=None, max_length=200)
    timezone: str | None = Field(default=None, max_length=50)
    daily_goal_minutes: int | None = Field(default=None, ge=10, le=720)


# === Server ===
class ServerStats(BaseModel):
    member_count: int
    total_minutes: int
    total_sessions: int
    weekly_minutes: int
    weekly_active_members: int
    tasks_completed: int
    raids_completed: int


class ServerMember(BaseModel):
    user_id: int
    username: str
    xp: int
    level: int
    total_study_minutes: int


# === Admin ===
class GrantRequest(BaseModel):
    amount: int = Field(ge=1, le=10000, description="付与量 (1-10000)")
    type: Literal["xp", "coins"] = "xp"


class ServerSettingsUpdate(BaseModel):
    """サーバー設定更新リクエスト"""

    study_channels: list[int] | None = None
    vc_channels: list[int] | None = None
    admin_role_id: int | None = None
    nudge_enabled: bool | None = None
    vc_tracking_enabled: bool | None = None
    min_vc_minutes: int | None = Field(default=None, ge=1, le=120)


# === Focus / Lock ===
class FocusStartRequest(BaseModel):
    """フォーカスセッション開始リクエスト"""

    duration: int = Field(ge=1, le=480, description="ロック時間（分）")
    unlock_level: int = Field(default=1, ge=1, le=5, description="アンロックレベル")
    coins_bet: int = Field(default=0, ge=0, le=100, description="ベットコイン")


class FocusSessionResponse(BaseModel):
    """フォーカスセッション情報"""

    session_id: int
    lock_type: str
    duration_minutes: int
    coins_bet: int
    unlock_level: int
    state: str
    remaining_seconds: int
    remaining_minutes: int
    end_time: datetime | None = None
    started_at: datetime | None = None


class UnlockCodeRequest(BaseModel):
    """アンロックコード入力"""

    code: str = Field(min_length=1, max_length=20)


class UnlockResult(BaseModel):
    """アンロック結果"""

    success: bool
    coins_earned: int = 0
    coins_returned: int = 0
    message: str = ""


class PenaltyUnlockResult(BaseModel):
    """ペナルティ解除結果"""

    success: bool
    coins_lost: int = 0
    penalty_rate: float = 0.0
    message: str = ""


class LockSettingsResponse(BaseModel):
    """ロック設定レスポンス"""

    default_unlock_level: int = 1
    default_duration: int = 60
    default_coin_bet: int = 0
    block_categories: list[str] = []
    custom_blocked_urls: list[str] = []


class LockSettingsUpdateRequest(BaseModel):
    """ロック設定更新リクエスト"""

    default_unlock_level: int | None = Field(default=None, ge=1, le=5)
    default_duration: int | None = Field(default=None, ge=1, le=480)
    default_coin_bet: int | None = Field(default=None, ge=0, le=100)
    block_categories: list[str] | None = None
    custom_blocked_urls: list[str] | None = None


class FocusHistoryEntry(BaseModel):
    """フォーカスセッション履歴"""

    id: int
    lock_type: str
    duration_minutes: int
    coins_bet: int
    unlock_level: int
    state: str
    started_at: datetime
    ended_at: datetime | None = None


# === Activity ===
class ActivityEventResponse(BaseModel):
    id: int
    user_id: int
    username: str
    event_type: str
    event_data: dict
    created_at: datetime


class ActiveStudierResponse(BaseModel):
    user_id: int
    username: str
    event_type: str
    event_data: dict
    started_at: datetime


# === Buddy ===
class BuddyProfileResponse(BaseModel):
    user_id: int
    subjects: list[str] = []
    preferred_times: list[str] = []
    study_style: str = "focused"
    active: bool = True
    username: str | None = None


class BuddyFindRequest(BaseModel):
    subjects: list[str] | None = None
    preferred_times: list[str] | None = None
    study_style: str | None = "focused"


class BuddyMatchResponse(BaseModel):
    id: int
    user_a: int
    user_b: int
    username_a: str
    username_b: str
    guild_id: int
    subject: str | None = None
    compatibility_score: float = 0.0
    status: str = "active"
    matched_at: datetime


# === Challenges ===
class ChallengeCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    goal_type: str = "study_minutes"
    goal_target: int = Field(default=600, ge=1)
    duration_days: int = Field(ge=3, le=90)
    xp_multiplier: float = Field(default=1.5, ge=1.0, le=3.0)


class ChallengeCheckinRequest(BaseModel):
    progress: int = Field(default=0, ge=0)
    note: str = ""


class ChallengeResponse(BaseModel):
    id: int
    creator_id: int
    creator_name: str
    guild_id: int
    name: str
    description: str
    goal_type: str
    goal_target: int
    duration_days: int
    start_date: date
    end_date: date
    xp_multiplier: float
    status: str
    participant_count: int
    created_at: datetime


class ChallengeLeaderboardEntry(BaseModel):
    user_id: int
    username: str
    progress: int
    checkins: int
    completed: bool


class ChallengeDetailResponse(ChallengeResponse):
    participants: list[ChallengeLeaderboardEntry] = []


# === Sessions ===
class SessionStartRequest(BaseModel):
    session_type: str = Field(description="pomodoro, focus, study")
    duration_minutes: int = Field(ge=1, le=480)
    topic: str = ""


class ActiveSessionResponse(BaseModel):
    id: int
    user_id: int
    username: str
    session_type: str
    source_platform: str
    topic: str
    duration_minutes: int
    started_at: datetime
    end_time: datetime
    remaining_seconds: int


# === Insights ===
class UserInsightResponse(BaseModel):
    id: int
    insight_type: str
    title: str
    body: str
    data: dict = {}
    confidence: float = 0.5
    generated_at: datetime


class WeeklyReportResponse(BaseModel):
    id: int
    week_start: date
    week_end: date
    summary: str
    insights: list = []
    generated_at: datetime
    raw_data: dict | None = None
