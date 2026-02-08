"""バディルート"""

import logging

from fastapi import APIRouter, Depends

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import BuddyFindRequest, BuddyMatchResponse, BuddyProfileResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/buddy", tags=["buddy"])


@router.get("/profile", response_model=BuddyProfileResponse | None)
async def get_buddy_profile(current_user: dict = Depends(get_current_user)):
    """バディプロフィールを取得"""
    user_id = current_user["user_id"]
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM buddy_profiles WHERE user_id = $1", user_id)
    if not row:
        return None
    return BuddyProfileResponse(
        user_id=row["user_id"],
        subjects=row["subjects"] or [],
        preferred_times=row["preferred_times"] or [],
        study_style=row["study_style"],
        active=row["active"],
    )


@router.put("/profile", response_model=BuddyProfileResponse)
async def update_buddy_profile(
    data: BuddyFindRequest,
    current_user: dict = Depends(get_current_user),
):
    """バディプロフィールを更新"""
    user_id = current_user["user_id"]
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO buddy_profiles (user_id, subjects, preferred_times, study_style)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id) DO UPDATE SET
                subjects = $2, preferred_times = $3, study_style = $4, updated_at = NOW()
            """,
            user_id,
            data.subjects or [],
            data.preferred_times or [],
            data.study_style or "focused",
        )
    return BuddyProfileResponse(
        user_id=user_id,
        subjects=data.subjects or [],
        preferred_times=data.preferred_times or [],
        study_style=data.study_style or "focused",
        active=True,
    )


@router.get("/matches", response_model=list[BuddyMatchResponse])
async def get_buddy_matches(current_user: dict = Depends(get_current_user)):
    """自分のバディマッチを取得"""
    user_id = current_user["user_id"]
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT bm.*, u_a.username AS username_a, u_b.username AS username_b
            FROM buddy_matches bm
            JOIN users u_a ON u_a.user_id = bm.user_a
            JOIN users u_b ON u_b.user_id = bm.user_b
            WHERE (bm.user_a = $1 OR bm.user_b = $1)
            ORDER BY bm.matched_at DESC
            LIMIT 50
            """,
            user_id,
        )
    return [
        BuddyMatchResponse(
            id=r["id"],
            user_a=r["user_a"],
            user_b=r["user_b"],
            username_a=r["username_a"],
            username_b=r["username_b"],
            guild_id=r["guild_id"],
            subject=r["subject"],
            compatibility_score=r["compatibility_score"],
            status=r["status"],
            matched_at=r["matched_at"],
        )
        for r in rows
    ]


@router.get("/available", response_model=list[BuddyProfileResponse])
async def get_available_buddies(current_user: dict = Depends(get_current_user)):
    """利用可能なバディ一覧"""
    user_id = current_user["user_id"]
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT bp.*, u.username FROM buddy_profiles bp
            JOIN users u ON u.user_id = bp.user_id
            WHERE bp.user_id != $1 AND bp.active = TRUE
            ORDER BY bp.updated_at DESC
            LIMIT 50
            """,
            user_id,
        )
    return [
        BuddyProfileResponse(
            user_id=r["user_id"],
            subjects=r["subjects"] or [],
            preferred_times=r["preferred_times"] or [],
            study_style=r["study_style"],
            active=r["active"],
            username=r["username"],
        )
        for r in rows
    ]
