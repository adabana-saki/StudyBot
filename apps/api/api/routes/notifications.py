"""通知ルート"""

from fastapi import APIRouter, Depends, HTTPException, status

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import DeviceTokenRequest, NotificationLog

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_device_token(
    request: DeviceTokenRequest,
    current_user: dict = Depends(get_current_user),
):
    """デバイストークンを登録"""
    user_id = current_user["user_id"]

    if request.platform not in ("ios", "android", "web"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="platformはios, android, webのいずれかです",
        )

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO device_tokens (user_id, device_token, platform)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, device_token)
            DO UPDATE SET
                platform = EXCLUDED.platform,
                is_active = TRUE,
                updated_at = NOW()
            """,
            user_id,
            request.device_token,
            request.platform,
        )

    return {"detail": "デバイストークンを登録しました"}


@router.delete("/unregister")
async def unregister_device_token(
    request: DeviceTokenRequest,
    current_user: dict = Depends(get_current_user),
):
    """デバイストークンを削除"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE device_tokens
            SET is_active = FALSE, updated_at = NOW()
            WHERE user_id = $1 AND device_token = $2
            """,
            user_id,
            request.device_token,
        )

    if result == "UPDATE 0":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="デバイストークンが見つかりません",
        )

    return {"detail": "デバイストークンを無効化しました"}


@router.get("/me", response_model=list[NotificationLog])
async def get_my_notifications(
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    """自分の通知履歴を取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, type, title, body, data, sent_at, read_at
            FROM notification_logs
            WHERE user_id = $1
            ORDER BY sent_at DESC
            LIMIT $2
            """,
            user_id,
            limit,
        )

    return [
        NotificationLog(
            id=row["id"],
            type=row["type"],
            title=row["title"],
            body=row["body"],
            data=row["data"],
            sent_at=row["sent_at"],
            read_at=row["read_at"],
        )
        for row in rows
    ]


@router.post("/read/{notification_id}")
async def mark_notification_read(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
):
    """通知を既読にする"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE notification_logs
            SET read_at = NOW()
            WHERE id = $1 AND user_id = $2 AND read_at IS NULL
            """,
            notification_id,
            user_id,
        )

    if result == "UPDATE 0":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知が見つからないか、既に既読です",
        )

    return {"detail": "既読にしました"}
