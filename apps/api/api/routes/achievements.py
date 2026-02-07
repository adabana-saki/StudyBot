"""実績ルート"""

from fastapi import APIRouter, Depends

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import Achievement, UserAchievement

router = APIRouter(prefix="/api/achievements", tags=["achievements"])


@router.get("/all", response_model=list[Achievement])
async def get_all_achievements():
    """全実績を取得"""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM achievements ORDER BY category, id")
    return [
        Achievement(
            id=row["id"],
            key=row["key"],
            name=row["name"],
            description=row["description"],
            emoji=row["emoji"],
            category=row["category"],
            target_value=row["target_value"],
            reward_coins=row["reward_coins"],
        )
        for row in rows
    ]


@router.get("/me", response_model=list[UserAchievement])
async def get_my_achievements(current_user: dict = Depends(get_current_user)):
    """自分の実績進捗を取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                a.id, a.key, a.name, a.description, a.emoji, a.category,
                a.target_value, a.reward_coins,
                COALESCE(ua.progress, 0) as progress,
                COALESCE(ua.unlocked, false) as unlocked,
                ua.unlocked_at
            FROM achievements a
            LEFT JOIN user_achievements ua
                ON ua.achievement_id = a.id AND ua.user_id = $1
            ORDER BY a.category, a.id
            """,
            user_id,
        )

    return [
        UserAchievement(
            achievement=Achievement(
                id=row["id"],
                key=row["key"],
                name=row["name"],
                description=row["description"],
                emoji=row["emoji"],
                category=row["category"],
                target_value=row["target_value"],
                reward_coins=row["reward_coins"],
            ),
            progress=row["progress"],
            unlocked=row["unlocked"],
            unlocked_at=row["unlocked_at"],
        )
        for row in rows
    ]
