"""学習プランルート"""

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import PlanTask, StudyPlan, StudyPlanDetail

router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.get("", response_model=list[StudyPlan])
async def get_plans(current_user: dict = Depends(get_current_user)):
    """学習プラン一覧を取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM study_plans
            WHERE user_id = $1
            ORDER BY created_at DESC
            """,
            user_id,
        )

    return [
        StudyPlan(
            id=row["id"],
            subject=row["subject"],
            goal=row["goal"],
            deadline=row["deadline"],
            status=row["status"],
            ai_feedback=row["ai_feedback"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


@router.get("/{plan_id}", response_model=StudyPlanDetail)
async def get_plan_detail(
    plan_id: int,
    current_user: dict = Depends(get_current_user),
):
    """学習プラン詳細を取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        plan = await conn.fetchrow(
            "SELECT * FROM study_plans WHERE id = $1 AND user_id = $2",
            plan_id,
            user_id,
        )
        if not plan:
            raise HTTPException(status_code=404, detail="プランが見つかりません")

        tasks = await conn.fetch(
            """
            SELECT * FROM plan_tasks
            WHERE plan_id = $1
            ORDER BY order_index
            """,
            plan_id,
        )

    return StudyPlanDetail(
        id=plan["id"],
        subject=plan["subject"],
        goal=plan["goal"],
        deadline=plan["deadline"],
        status=plan["status"],
        ai_feedback=plan["ai_feedback"],
        created_at=plan["created_at"],
        tasks=[
            PlanTask(
                id=t["id"],
                title=t["title"],
                description=t["description"],
                order_index=t["order_index"],
                status=t["status"],
                completed_at=t["completed_at"],
            )
            for t in tasks
        ],
    )
