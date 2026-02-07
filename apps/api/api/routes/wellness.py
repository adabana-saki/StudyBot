"""ウェルネスルート"""

from fastapi import APIRouter, Depends, HTTPException, status

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import WellnessAverage, WellnessLog, WellnessLogRequest

router = APIRouter(prefix="/api/wellness", tags=["wellness"])


@router.get("/me", response_model=list[WellnessLog])
async def get_my_wellness(
    days: int = 14,
    current_user: dict = Depends(get_current_user),
):
    """自分のウェルネスログを取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM wellness_logs
            WHERE user_id = $1
              AND logged_at >= CURRENT_TIMESTAMP - make_interval(days => $2)
            ORDER BY logged_at DESC
            """,
            user_id,
            days,
        )

    return [
        WellnessLog(
            id=row["id"],
            mood=row["mood"],
            energy=row["energy"],
            stress=row["stress"],
            note=row["note"],
            logged_at=row["logged_at"],
        )
        for row in rows
    ]


@router.get("/me/averages", response_model=WellnessAverage)
async def get_my_averages(
    days: int = 7,
    current_user: dict = Depends(get_current_user),
):
    """自分のウェルネス平均値を取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                COALESCE(AVG(mood), 0) as avg_mood,
                COALESCE(AVG(energy), 0) as avg_energy,
                COALESCE(AVG(stress), 0) as avg_stress
            FROM wellness_logs
            WHERE user_id = $1
              AND logged_at >= CURRENT_TIMESTAMP - make_interval(days => $2)
            """,
            user_id,
            days,
        )

    return WellnessAverage(
        avg_mood=float(row["avg_mood"]),
        avg_energy=float(row["avg_energy"]),
        avg_stress=float(row["avg_stress"]),
        days=days,
    )


@router.post("/me", response_model=WellnessLog)
async def log_wellness(
    request: WellnessLogRequest,
    current_user: dict = Depends(get_current_user),
):
    """ウェルネスを記録"""
    user_id = current_user["user_id"]

    for field, value in [
        ("mood", request.mood),
        ("energy", request.energy),
        ("stress", request.stress),
    ]:
        if not 1 <= value <= 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field}は1-5の範囲で指定してください",
            )

    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO wellness_logs (user_id, mood, energy, stress, note)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            user_id,
            request.mood,
            request.energy,
            request.stress,
            request.note,
        )

    return WellnessLog(
        id=row["id"],
        mood=row["mood"],
        energy=row["energy"],
        stress=row["stress"],
        note=row["note"],
        logged_at=row["logged_at"],
    )
