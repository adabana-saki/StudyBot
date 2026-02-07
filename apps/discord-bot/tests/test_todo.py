"""To-Do管理のテスト"""

from datetime import UTC, datetime

import pytest

from studybot.managers.todo_manager import TodoManager


@pytest.fixture
def todo_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = TodoManager(pool)
    return manager, conn


@pytest.mark.asyncio
async def test_add_todo(todo_manager):
    """タスク追加テスト"""
    manager, conn = todo_manager

    conn.execute.return_value = None
    conn.fetchval.return_value = 1

    todo_id = await manager.add_todo(
        user_id=123,
        username="Test",
        guild_id=456,
        title="宿題を終わらせる",
        priority=1,
    )

    assert todo_id == 1


@pytest.mark.asyncio
async def test_list_todos(todo_manager):
    """タスク一覧テスト"""
    manager, conn = todo_manager

    conn.fetch.return_value = [
        {"id": 1, "title": "タスク1", "priority": 1, "status": "pending", "deadline": None},
        {"id": 2, "title": "タスク2", "priority": 2, "status": "pending", "deadline": None},
    ]

    todos = await manager.list_todos(123, 456, "pending")
    assert len(todos) == 2
    assert todos[0]["title"] == "タスク1"


@pytest.mark.asyncio
async def test_complete_todo(todo_manager):
    """タスク完了テスト"""
    manager, conn = todo_manager

    conn.fetchrow.return_value = {
        "id": 1,
        "title": "宿題",
        "priority": 2,
        "status": "completed",
        "completed_at": datetime.now(UTC),
        "user_id": 123,
        "guild_id": 456,
        "deadline": None,
        "created_at": None,
    }

    result = await manager.complete_todo(1, 123)
    assert result is not None
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_complete_nonexistent_todo(todo_manager):
    """存在しないタスクの完了"""
    manager, conn = todo_manager

    conn.fetchrow.return_value = None

    result = await manager.complete_todo(999, 123)
    assert result is None


@pytest.mark.asyncio
async def test_delete_todo(todo_manager):
    """タスク削除テスト"""
    manager, conn = todo_manager

    conn.execute.return_value = "DELETE 1"

    result = await manager.delete_todo(1, 123)
    assert result is True


@pytest.mark.asyncio
async def test_delete_nonexistent_todo(todo_manager):
    """存在しないタスクの削除"""
    manager, conn = todo_manager

    conn.execute.return_value = "DELETE 0"

    result = await manager.delete_todo(999, 123)
    assert result is False
