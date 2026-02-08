"""インサイトルート"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import UserInsightResponse, WeeklyReportResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/me", response_model=list[UserInsightResponse])
async def get_my_insights(current_user: dict = Depends(get_current_user)):
    """自分のアクティブなインサイトを取得"""
    user_id = current_user["user_id"]
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM user_insights
            WHERE user_id = $1 AND active = TRUE
            ORDER BY generated_at DESC
            LIMIT 20
            """,
            user_id,
        )

    return [
        UserInsightResponse(
            id=r["id"],
            insight_type=r["insight_type"],
            title=r["title"],
            body=r["body"],
            data=json.loads(r["data"]) if isinstance(r["data"], str) else (r["data"] or {}),
            confidence=r["confidence"],
            generated_at=r["generated_at"],
        )
        for r in rows
    ]


@router.get("/me/reports", response_model=list[WeeklyReportResponse])
async def get_my_reports(current_user: dict = Depends(get_current_user)):
    """自分の週次レポート一覧を取得"""
    user_id = current_user["user_id"]
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, user_id, week_start, week_end, summary,
                   insights, generated_at, sent_via_dm
            FROM weekly_reports WHERE user_id = $1
            ORDER BY week_start DESC LIMIT 12
            """,
            user_id,
        )

    return [
        WeeklyReportResponse(
            id=r["id"],
            week_start=r["week_start"],
            week_end=r["week_end"],
            summary=r["summary"],
            insights=json.loads(r["insights"])
            if isinstance(r["insights"], str)
            else (r["insights"] or []),
            generated_at=r["generated_at"],
        )
        for r in rows
    ]


@router.get("/me/reports/{report_id}", response_model=WeeklyReportResponse)
async def get_report_detail(
    report_id: int,
    current_user: dict = Depends(get_current_user),
):
    """特定の週次レポートを取得"""
    user_id = current_user["user_id"]
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM weekly_reports WHERE id = $1 AND user_id = $2",
            report_id,
            user_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="レポートが見つかりません")

    return WeeklyReportResponse(
        id=row["id"],
        week_start=row["week_start"],
        week_end=row["week_end"],
        summary=row["summary"],
        insights=json.loads(row["insights"])
        if isinstance(row["insights"], str)
        else (row["insights"] or []),
        generated_at=row["generated_at"],
        raw_data=json.loads(row["raw_data"])
        if isinstance(row["raw_data"], str)
        else (row["raw_data"] or {}),
    )
