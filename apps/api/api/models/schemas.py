"""Pydantic スキーマ定義"""

from datetime import date, datetime

from pydantic import BaseModel


# === Auth ===
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


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
    quality: int  # 1-5


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
    mood: int  # 1-5
    energy: int  # 1-5
    stress: int  # 1-5
    note: str = ""
