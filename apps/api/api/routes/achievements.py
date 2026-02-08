"""実績ルート"""

from fastapi import APIRouter, Depends, Query

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import Achievement, PaginatedResponse, UserAchievement

router = APIRouter(prefix="/api/achievements", tags=["achievements"])


@router.get("/all", response_model=PaginatedResponse[Achievement])
async def get_all_achievements(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    """全実績を取得"""
    pool = get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM achievements")
        rows = await conn.fetch(
            "SELECT * FROM achievements ORDER BY category, id LIMIT $1 OFFSET $2",
            limit,
            offset,
        )
    items = [
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
    return PaginatedResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/me", response_model=PaginatedResponse[UserAchievement])
async def get_my_achievements(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """自分の実績進捗を取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM achievements",
        )
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
            LIMIT $2 OFFSET $3
            """,
            user_id,
            limit,
            offset,
        )

    items = [
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
    return PaginatedResponse(items=items, total=total, offset=offset, limit=limit)
