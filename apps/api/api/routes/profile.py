"""プロフィールルート"""

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import ProfileDetail, ProfileUpdateRequest, UserPreferences

router = APIRouter(prefix="/api/profile", tags=["profile"])

_ALLOWED_PREFERENCE_COLUMNS = frozenset(
    {
        "display_name",
        "bio",
        "timezone",
        "daily_goal_minutes",
    }
)


async def _get_profile_data(conn, user_id: int) -> dict | None:
    """プロフィールデータを取得（内部ヘルパー）"""
    user = await conn.fetchrow(
        """
        SELECT u.user_id, u.username,
               COALESCE(ul.xp, 0) as xp,
               COALESCE(ul.level, 1) as level,
               COALESCE(ul.streak_days, 0) as streak_days
        FROM users u
        LEFT JOIN user_levels ul ON ul.user_id = u.user_id
        WHERE u.user_id = $1
        """,
        user_id,
    )
    if not user:
        return None

    coins = await conn.fetchval(
        "SELECT COALESCE(balance, 0) FROM virtual_currency WHERE user_id = $1",
        user_id,
    )

    rank = await conn.fetchval(
        """
        SELECT COUNT(*) + 1 FROM user_levels
        WHERE xp > COALESCE((SELECT xp FROM user_levels WHERE user_id = $1), 0)
        """,
        user_id,
    )

    prefs = await conn.fetchrow(
        "SELECT * FROM user_preferences WHERE user_id = $1",
        user_id,
    )

    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "xp": user["xp"],
        "level": user["level"],
        "streak_days": user["streak_days"],
        "coins": coins or 0,
        "rank": rank or 1,
        "preferences": prefs,
    }


@router.get("/me", response_model=ProfileDetail)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """自分のプロフィールを取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        data = await _get_profile_data(conn, user_id)

    if not data:
        raise HTTPException(status_code=404, detail="プロフィールが見つかりません")

    prefs = None
    if data["preferences"]:
        p = data["preferences"]
        prefs = UserPreferences(
            display_name=p.get("display_name"),
            bio=p.get("bio", ""),
            timezone=p.get("timezone", "Asia/Tokyo"),
            daily_goal_minutes=p.get("daily_goal_minutes", 60),
            notifications_enabled=p.get("notifications_enabled", True),
            theme=p.get("theme", "dark"),
            custom_title=p.get("custom_title"),
        )

    return ProfileDetail(
        user_id=data["user_id"],
        username=data["username"],
        xp=data["xp"],
        level=data["level"],
        streak_days=data["streak_days"],
        coins=data["coins"],
        rank=data["rank"],
        preferences=prefs,
    )


@router.put("/me", response_model=ProfileDetail)
async def update_my_profile(
    request: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """プロフィールを更新"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        # user_preferences を確保
        await conn.execute(
            """
            INSERT INTO user_preferences (user_id)
            VALUES ($1)
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id,
        )

        updates = {}
        if request.display_name is not None:
            updates["display_name"] = request.display_name
        if request.bio is not None:
            updates["bio"] = request.bio
        if request.timezone is not None:
            updates["timezone"] = request.timezone
        if request.daily_goal_minutes is not None:
            updates["daily_goal_minutes"] = request.daily_goal_minutes

        if updates:
            sets = []
            params: list[object] = [user_id]
            idx = 2
            for key, value in updates.items():
                if key not in _ALLOWED_PREFERENCE_COLUMNS:
                    continue
                sets.append(f"{key} = ${idx}")  # noqa: S608
                params.append(value)
                idx += 1
            if sets:
                set_clause = ", ".join(sets)
                query = (
                    f"UPDATE user_preferences SET {set_clause}"  # noqa: S608
                    " WHERE user_id = $1"
                )
                await conn.execute(query, *params)

        data = await _get_profile_data(conn, user_id)

    if not data:
        raise HTTPException(status_code=404, detail="プロフィールが見つかりません")

    prefs = None
    if data["preferences"]:
        p = data["preferences"]
        prefs = UserPreferences(
            display_name=p.get("display_name"),
            bio=p.get("bio", ""),
            timezone=p.get("timezone", "Asia/Tokyo"),
            daily_goal_minutes=p.get("daily_goal_minutes", 60),
            notifications_enabled=p.get("notifications_enabled", True),
            theme=p.get("theme", "dark"),
            custom_title=p.get("custom_title"),
        )

    return ProfileDetail(
        user_id=data["user_id"],
        username=data["username"],
        xp=data["xp"],
        level=data["level"],
        streak_days=data["streak_days"],
        coins=data["coins"],
        rank=data["rank"],
        preferences=prefs,
    )


@router.get("/{user_id}", response_model=ProfileDetail)
async def get_user_profile(
    user_id: int,
    current_user: dict = Depends(get_current_user),
):
    """他ユーザーのプロフィールを取得（公開情報のみ）"""
    pool = get_pool()

    async with pool.acquire() as conn:
        data = await _get_profile_data(conn, user_id)

    if not data:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    # 公開情報のみ返す（通知設定やテーマは除外）
    prefs = None
    if data["preferences"]:
        p = data["preferences"]
        prefs = UserPreferences(
            display_name=p.get("display_name"),
            bio=p.get("bio", ""),
            timezone=p.get("timezone", "Asia/Tokyo"),
            daily_goal_minutes=p.get("daily_goal_minutes", 60),
            custom_title=p.get("custom_title"),
        )

    return ProfileDetail(
        user_id=data["user_id"],
        username=data["username"],
        xp=data["xp"],
        level=data["level"],
        streak_days=data["streak_days"],
        coins=data["coins"],
        rank=data["rank"],
        preferences=prefs,
    )
