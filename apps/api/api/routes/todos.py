"""タスク管理ルート"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import PaginatedResponse, TodoCreateRequest, TodoItem, TodoUpdateRequest

router = APIRouter(prefix="/api/todos", tags=["todos"])

_ALLOWED_TODO_COLUMNS = frozenset(
    {
        "title",
        "priority",
        "deadline",
        "status",
        "completed_at",
    }
)


@router.get("", response_model=PaginatedResponse[TodoItem])
async def get_todos(
    status: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """タスク一覧を取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        if status:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM todos WHERE user_id = $1 AND status = $2",
                user_id,
                status,
            )
            rows = await conn.fetch(
                """
                SELECT * FROM todos
                WHERE user_id = $1 AND status = $2
                ORDER BY priority, created_at DESC
                LIMIT $3 OFFSET $4
                """,
                user_id,
                status,
                limit,
                offset,
            )
        else:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM todos WHERE user_id = $1",
                user_id,
            )
            rows = await conn.fetch(
                """
                SELECT * FROM todos
                WHERE user_id = $1
                ORDER BY status, priority, created_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_id,
                limit,
                offset,
            )

    items = [
        TodoItem(
            id=row["id"],
            title=row["title"],
            priority=row["priority"],
            status=row["status"],
            deadline=row["deadline"],
            completed_at=row["completed_at"],
            created_at=row["created_at"],
        )
        for row in rows
    ]
    return PaginatedResponse(items=items, total=total, offset=offset, limit=limit)


@router.post("", response_model=TodoItem)
async def create_todo(
    request: TodoCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """タスクを作成"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO todos (user_id, guild_id, title, priority, deadline)
            VALUES ($1, 0, $2, $3, $4)
            RETURNING *
            """,
            user_id,
            request.title,
            request.priority,
            request.deadline,
        )

    return TodoItem(
        id=row["id"],
        title=row["title"],
        priority=row["priority"],
        status=row["status"],
        deadline=row["deadline"],
        completed_at=row["completed_at"],
        created_at=row["created_at"],
    )


@router.patch("/{todo_id}", response_model=TodoItem)
async def update_todo(
    todo_id: int,
    request: TodoUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """タスクを更新"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT * FROM todos WHERE id = $1 AND user_id = $2",
            todo_id,
            user_id,
        )
        if not existing:
            raise HTTPException(status_code=404, detail="タスクが見つかりません")

        updates = {}
        if request.title is not None:
            updates["title"] = request.title
        if request.priority is not None:
            updates["priority"] = request.priority
        if request.deadline is not None:
            updates["deadline"] = request.deadline
        if request.status is not None:
            updates["status"] = request.status
            if request.status == "completed":
                updates["completed_at"] = datetime.now(UTC)

        if updates:
            sets = []
            params: list[object] = [todo_id, user_id]
            idx = 3
            for key, value in updates.items():
                if key not in _ALLOWED_TODO_COLUMNS:
                    continue
                sets.append(f"{key} = ${idx}")  # noqa: S608
                params.append(value)
                idx += 1
            query = (
                f"UPDATE todos SET {', '.join(sets)}"  # noqa: S608
                " WHERE id = $1 AND user_id = $2 RETURNING *"
            )
            row = await conn.fetchrow(query, *params)
        else:
            row = existing

    return TodoItem(
        id=row["id"],
        title=row["title"],
        priority=row["priority"],
        status=row["status"],
        deadline=row["deadline"],
        completed_at=row["completed_at"],
        created_at=row["created_at"],
    )


@router.delete("/{todo_id}")
async def delete_todo(
    todo_id: int,
    current_user: dict = Depends(get_current_user),
):
    """タスクを削除"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM todos WHERE id = $1 AND user_id = $2",
            todo_id,
            user_id,
        )

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="タスクが見つかりません")

    return {"message": "削除完了"}


@router.post("/{todo_id}/complete", response_model=TodoItem)
async def complete_todo(
    todo_id: int,
    current_user: dict = Depends(get_current_user),
):
    """タスクを完了にする"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE todos
            SET status = 'completed', completed_at = $3
            WHERE id = $1 AND user_id = $2
            RETURNING *
            """,
            todo_id,
            user_id,
            datetime.now(UTC),
        )

    if not row:
        raise HTTPException(status_code=404, detail="タスクが見つかりません")

    return TodoItem(
        id=row["id"],
        title=row["title"],
        priority=row["priority"],
        status=row["status"],
        deadline=row["deadline"],
        completed_at=row["completed_at"],
        created_at=row["created_at"],
    )
