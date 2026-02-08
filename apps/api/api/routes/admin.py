"""管理者APIルート"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import GrantRequest, ServerMember, ServerSettingsUpdate

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[ServerMember])
async def get_users(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """ユーザー管理一覧"""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT u.user_id, u.username,
                   COALESCE(ul.xp, 0) as xp,
                   COALESCE(ul.level, 1) as level,
                   COALESCE(sl.total_minutes, 0) as total_study_minutes
            FROM users u
            LEFT JOIN user_levels ul ON ul.user_id = u.user_id
            LEFT JOIN (
                SELECT user_id, SUM(duration_minutes) as total_minutes
                FROM study_logs GROUP BY user_id
            ) sl ON sl.user_id = u.user_id
            ORDER BY u.created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )

    return [
        ServerMember(
            user_id=row["user_id"],
            username=row["username"],
            xp=row["xp"],
            level=row["level"],
            total_study_minutes=row["total_study_minutes"],
        )
        for row in rows
    ]


@router.post("/users/{user_id}/grant")
async def grant_to_user(
    user_id: int,
    request: GrantRequest,
    current_user: dict = Depends(get_current_user),
):
    """ユーザーにXP/コインを付与"""
    pool = get_pool()
    async with pool.acquire() as conn:
        if request.type == "xp":
            await conn.execute(
                """
                INSERT INTO user_levels (user_id, xp) VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE SET xp = user_levels.xp + $2
                """,
                user_id,
                request.amount,
            )
            return {"message": f"{request.amount} XP を付与しました"}

        else:  # coins (validated by Literal type)
            await conn.execute(
                """
                INSERT INTO virtual_currency (user_id, balance, total_earned)
                VALUES ($1, $2, $2)
                ON CONFLICT (user_id) DO UPDATE
                    SET balance = virtual_currency.balance + $2,
                        total_earned = virtual_currency.total_earned + $2
                """,
                user_id,
                request.amount,
            )
            return {"message": f"{request.amount} コイン を付与しました"}


_ALLOWED_SETTING_KEYS = frozenset(
    {
        "study_channels",
        "vc_channels",
        "admin_role_id",
        "nudge_enabled",
        "vc_tracking_enabled",
        "min_vc_minutes",
    }
)


@router.put("/settings/{guild_id}")
async def update_server_settings(
    guild_id: int,
    request: ServerSettingsUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """サーバー設定を更新する。

    Pydanticモデルで型が検証済みのフィールドのみ更新する。
    """
    pool = get_pool()
    updates = request.model_dump(exclude_none=True)

    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO server_settings (guild_id) VALUES ($1) ON CONFLICT (guild_id) DO NOTHING",
            guild_id,
        )

        for key, value in updates.items():
            if key not in _ALLOWED_SETTING_KEYS:
                continue
            await conn.execute(
                f"UPDATE server_settings SET {key} = $2,"  # noqa: S608
                " updated_at = $3 WHERE guild_id = $1",
                guild_id,
                value,
                datetime.now(UTC),
            )

    return {"message": "設定を更新しました"}
