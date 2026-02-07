"""学習プランのテスト"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from studybot.managers.plan_manager import PlanManager


@pytest.fixture
def plan_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = PlanManager(pool)
    return manager, conn


@pytest.mark.asyncio
async def test_create_plan_with_ai_tasks(plan_manager):
    """AIタスク生成付きプラン作成テスト"""
    manager, conn = plan_manager

    conn.execute.return_value = None
    # create_plan RETURNING *
    conn.fetchrow.side_effect = [
        # create_plan
        {
            "id": 1,
            "user_id": 123,
            "subject": "数学",
            "goal": "微積分をマスター",
            "deadline": None,
            "status": "active",
            "ai_feedback": None,
            "created_at": datetime.now(UTC),
        },
        # add_task (1回目)
        {
            "id": 10,
            "plan_id": 1,
            "title": "基礎の復習",
            "description": "微分の基本を復習する",
            "order_index": 0,
            "status": "pending",
            "completed_at": None,
            "created_at": datetime.now(UTC),
        },
        # add_task (2回目)
        {
            "id": 11,
            "plan_id": 1,
            "title": "演習問題",
            "description": "練習問題を解く",
            "order_index": 1,
            "status": "pending",
            "completed_at": None,
            "created_at": datetime.now(UTC),
        },
        # get_plan_with_tasks: plan
        {
            "id": 1,
            "user_id": 123,
            "subject": "数学",
            "goal": "微積分をマスター",
            "deadline": None,
            "status": "active",
            "ai_feedback": None,
            "created_at": datetime.now(UTC),
        },
    ]
    # get_plan_with_tasks: tasks
    conn.fetch.return_value = [
        {
            "id": 10,
            "plan_id": 1,
            "title": "基礎の復習",
            "description": "微分の基本を復習する",
            "order_index": 0,
            "status": "pending",
            "completed_at": None,
            "created_at": datetime.now(UTC),
        },
        {
            "id": 11,
            "plan_id": 1,
            "title": "演習問題",
            "description": "練習問題を解く",
            "order_index": 1,
            "status": "pending",
            "completed_at": None,
            "created_at": datetime.now(UTC),
        },
    ]

    ai_response = (
        '[{"title": "基礎の復習", '
        '"description": "微分の基本を復習する"}, '
        '{"title": "演習問題", '
        '"description": "練習問題を解く"}]'
    )

    with patch.object(manager, "_call_openai", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = ai_response

        result = await manager.create_plan(
            user_id=123,
            username="Test",
            subject="数学",
            goal="微積分をマスター",
        )

    assert result is not None
    assert result["plan"]["subject"] == "数学"
    assert len(result["tasks"]) == 2


@pytest.mark.asyncio
async def test_create_plan_ai_failure(plan_manager):
    """AI失敗時のプラン作成テスト"""
    manager, conn = plan_manager

    conn.execute.return_value = None
    conn.fetchrow.side_effect = [
        # create_plan
        {
            "id": 1,
            "user_id": 123,
            "subject": "英語",
            "goal": "TOEIC 800",
            "deadline": None,
            "status": "active",
            "ai_feedback": None,
            "created_at": datetime.now(UTC),
        },
        # get_plan_with_tasks: plan
        {
            "id": 1,
            "user_id": 123,
            "subject": "英語",
            "goal": "TOEIC 800",
            "deadline": None,
            "status": "active",
            "ai_feedback": None,
            "created_at": datetime.now(UTC),
        },
    ]
    conn.fetch.return_value = []

    with patch.object(manager, "_call_openai", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = None

        result = await manager.create_plan(
            user_id=123,
            username="Test",
            subject="英語",
            goal="TOEIC 800",
        )

    assert result is not None
    assert result["plan"]["subject"] == "英語"
    assert len(result["tasks"]) == 0


@pytest.mark.asyncio
async def test_get_current_plan(plan_manager):
    """現在プラン取得テスト"""
    manager, conn = plan_manager

    conn.fetchrow.side_effect = [
        # get_active_plan
        {
            "id": 1,
            "user_id": 123,
            "subject": "数学",
            "goal": "微積分をマスター",
            "deadline": None,
            "status": "active",
            "ai_feedback": None,
            "created_at": datetime.now(UTC),
        },
        # get_plan_with_tasks: plan
        {
            "id": 1,
            "user_id": 123,
            "subject": "数学",
            "goal": "微積分をマスター",
            "deadline": None,
            "status": "active",
            "ai_feedback": None,
            "created_at": datetime.now(UTC),
        },
    ]
    conn.fetch.return_value = [
        {
            "id": 10,
            "plan_id": 1,
            "title": "基礎の復習",
            "description": "",
            "order_index": 0,
            "status": "pending",
            "completed_at": None,
            "created_at": datetime.now(UTC),
        },
    ]

    result = await manager.get_current_plan(user_id=123)

    assert result is not None
    assert result["plan"]["subject"] == "数学"
    assert len(result["tasks"]) == 1


@pytest.mark.asyncio
async def test_get_current_plan_none(plan_manager):
    """アクティブプランなしのテスト"""
    manager, conn = plan_manager

    conn.fetchrow.return_value = None

    result = await manager.get_current_plan(user_id=123)

    assert result is None


@pytest.mark.asyncio
async def test_complete_task(plan_manager):
    """タスク完了テスト"""
    manager, conn = plan_manager

    conn.fetchrow.side_effect = [
        # get_active_plan
        {
            "id": 1,
            "user_id": 123,
            "subject": "数学",
            "goal": "微積分をマスター",
            "deadline": None,
            "status": "active",
            "ai_feedback": None,
            "created_at": datetime.now(UTC),
        },
        # complete_task
        {
            "id": 10,
            "plan_id": 1,
            "title": "基礎の復習",
            "description": "",
            "order_index": 0,
            "status": "completed",
            "completed_at": datetime.now(UTC),
            "created_at": datetime.now(UTC),
        },
        # get_plan_progress
        {
            "total": 5,
            "completed": 1,
        },
    ]

    result = await manager.complete_task(user_id=123, task_id=10)

    assert "task" in result
    assert result["task"]["status"] == "completed"
    assert result["progress"]["total"] == 5
    assert result["progress"]["completed"] == 1


@pytest.mark.asyncio
async def test_complete_task_no_active_plan(plan_manager):
    """アクティブプランなしでのタスク完了"""
    manager, conn = plan_manager

    conn.fetchrow.return_value = None

    result = await manager.complete_task(user_id=123, task_id=10)

    assert "error" in result


@pytest.mark.asyncio
async def test_complete_task_not_found(plan_manager):
    """存在しないタスクの完了"""
    manager, conn = plan_manager

    conn.fetchrow.side_effect = [
        # get_active_plan
        {
            "id": 1,
            "user_id": 123,
            "subject": "数学",
            "goal": "微積分をマスター",
            "deadline": None,
            "status": "active",
            "ai_feedback": None,
            "created_at": datetime.now(UTC),
        },
        # complete_task: タスクが見つからない
        None,
    ]

    result = await manager.complete_task(user_id=123, task_id=999)

    assert "error" in result


@pytest.mark.asyncio
async def test_get_progress_with_feedback(plan_manager):
    """進捗取得テスト（フィードバック生成なし）"""
    manager, conn = plan_manager

    conn.fetchrow.side_effect = [
        # get_active_plan
        {
            "id": 1,
            "user_id": 123,
            "subject": "数学",
            "goal": "微積分をマスター",
            "deadline": None,
            "status": "active",
            "ai_feedback": "よく頑張っています！",
            "created_at": datetime.now(UTC),
        },
        # get_plan_progress
        {
            "total": 5,
            "completed": 3,
        },
        # get_plan_with_tasks: plan
        {
            "id": 1,
            "user_id": 123,
            "subject": "数学",
            "goal": "微積分をマスター",
            "deadline": None,
            "status": "active",
            "ai_feedback": "よく頑張っています！",
            "created_at": datetime.now(UTC),
        },
    ]
    conn.fetch.return_value = []

    result = await manager.get_progress_with_feedback(user_id=123)

    assert result["progress"]["percentage"] == 60.0
    assert result["feedback"] == "よく頑張っています！"


@pytest.mark.asyncio
async def test_get_progress_no_plan(plan_manager):
    """アクティブプランなしでの進捗取得"""
    manager, conn = plan_manager

    conn.fetchrow.return_value = None

    result = await manager.get_progress_with_feedback(user_id=123)

    assert "error" in result


@pytest.mark.asyncio
async def test_get_progress_generate_feedback(plan_manager):
    """50%以上でフィードバック自動生成テスト"""
    manager, conn = plan_manager

    conn.fetchrow.side_effect = [
        # get_active_plan
        {
            "id": 1,
            "user_id": 123,
            "subject": "数学",
            "goal": "微積分をマスター",
            "deadline": None,
            "status": "active",
            "ai_feedback": None,
            "created_at": datetime.now(UTC),
        },
        # get_plan_progress
        {
            "total": 4,
            "completed": 3,
        },
        # get_plan_with_tasks: plan
        {
            "id": 1,
            "user_id": 123,
            "subject": "数学",
            "goal": "微積分をマスター",
            "deadline": None,
            "status": "active",
            "ai_feedback": None,
            "created_at": datetime.now(UTC),
        },
    ]
    conn.fetch.return_value = []
    conn.execute.return_value = None

    with patch.object(manager, "_call_openai", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = "素晴らしい進捗です！"

        result = await manager.get_progress_with_feedback(user_id=123)

    assert result["feedback"] == "素晴らしい進捗です！"
