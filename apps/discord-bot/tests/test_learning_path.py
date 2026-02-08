"""ラーニングパスのテスト"""

import pytest

from studybot.managers.learning_path_manager import LEARNING_PATHS, LearningPathManager


@pytest.fixture
def path_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = LearningPathManager(pool)
    return manager, conn


@pytest.mark.asyncio
async def test_list_paths(path_manager):
    """パス一覧テスト"""
    manager, conn = path_manager

    paths = manager.get_paths()
    assert len(paths) == len(LEARNING_PATHS)

    # カテゴリフィルタ
    math_paths = manager.get_paths(category="math")
    assert len(math_paths) == 1
    assert math_paths[0]["path_id"] == "math_basics"
    assert math_paths[0]["name"] == "数学基礎マスター"

    # 存在しないカテゴリ
    empty = manager.get_paths(category="nonexistent")
    assert len(empty) == 0


@pytest.mark.asyncio
async def test_enroll_path(path_manager):
    """パス登録テスト"""
    manager, conn = path_manager

    conn.execute.return_value = None  # ensure_user
    conn.fetchrow.side_effect = [
        # get_user_path (not enrolled yet)
        None,
        # enroll_user INSERT RETURNING
        {
            "id": 1,
            "user_id": 123,
            "path_id": "math_basics",
            "current_milestone": 0,
            "completed": False,
            "enrolled_at": None,
            "completed_at": None,
        },
    ]

    result = await manager.enroll(
        user_id=123,
        username="TestUser",
        path_id="math_basics",
    )

    assert "error" not in result
    assert result["path_id"] == "math_basics"
    assert result["name"] == "数学基礎マスター"
    assert result["milestone_count"] == 5


@pytest.mark.asyncio
async def test_already_enrolled(path_manager):
    """既に登録済みのパスに再登録テスト"""
    manager, conn = path_manager

    conn.execute.return_value = None  # ensure_user
    conn.fetchrow.return_value = {
        "id": 1,
        "user_id": 123,
        "path_id": "math_basics",
        "current_milestone": 2,
        "completed": False,
        "enrolled_at": None,
        "completed_at": None,
    }

    result = await manager.enroll(
        user_id=123,
        username="TestUser",
        path_id="math_basics",
    )

    assert "error" in result
    assert "既に" in result["error"]


@pytest.mark.asyncio
async def test_enroll_invalid_path(path_manager):
    """存在しないパスへの登録テスト"""
    manager, conn = path_manager

    result = await manager.enroll(
        user_id=123,
        username="TestUser",
        path_id="nonexistent_path",
    )

    assert "error" in result
    assert "見つかりません" in result["error"]


@pytest.mark.asyncio
async def test_complete_milestone(path_manager):
    """マイルストーン完了テスト"""
    manager, conn = path_manager

    conn.fetchrow.side_effect = [
        # get_user_path (enrolled, at milestone 0)
        {
            "id": 1,
            "user_id": 123,
            "path_id": "math_basics",
            "current_milestone": 0,
            "completed": False,
            "enrolled_at": None,
            "completed_at": None,
        },
    ]
    conn.execute.return_value = None

    result = await manager.complete_current_milestone(
        user_id=123,
        path_id="math_basics",
    )

    assert "error" not in result
    assert result["milestone_title"] == "四則演算の復習"
    assert result["milestone_index"] == 0
    assert result["completed_count"] == 1
    assert result["total"] == 5
    assert result["path_completed"] is False
    assert result["reward_xp"] == 0  # not completed yet


@pytest.mark.asyncio
async def test_complete_last_milestone(path_manager):
    """最後のマイルストーン完了（パス完了）テスト"""
    manager, conn = path_manager

    conn.fetchrow.side_effect = [
        # get_user_path (enrolled, at last milestone)
        {
            "id": 1,
            "user_id": 123,
            "path_id": "math_basics",
            "current_milestone": 4,
            "completed": False,
            "enrolled_at": None,
            "completed_at": None,
        },
    ]
    conn.execute.return_value = None

    result = await manager.complete_current_milestone(
        user_id=123,
        path_id="math_basics",
    )

    assert "error" not in result
    assert result["milestone_title"] == "まとめテスト"
    assert result["completed_count"] == 5
    assert result["total"] == 5
    assert result["path_completed"] is True
    assert result["reward_xp"] == 500
    assert result["reward_coins"] == 200


@pytest.mark.asyncio
async def test_complete_already_completed_path(path_manager):
    """既に完了したパスでのマイルストーン完了テスト"""
    manager, conn = path_manager

    conn.fetchrow.return_value = {
        "id": 1,
        "user_id": 123,
        "path_id": "math_basics",
        "current_milestone": 5,
        "completed": True,
        "enrolled_at": None,
        "completed_at": None,
    }

    result = await manager.complete_current_milestone(
        user_id=123,
        path_id="math_basics",
    )

    assert "error" in result
    assert "既に完了" in result["error"]


@pytest.mark.asyncio
async def test_get_progress(path_manager):
    """進捗取得テスト"""
    manager, conn = path_manager

    conn.fetchrow.return_value = {
        "id": 1,
        "user_id": 123,
        "path_id": "math_basics",
        "current_milestone": 2,
        "completed": False,
        "enrolled_at": None,
        "completed_at": None,
    }
    conn.fetchval.return_value = 2  # completed milestones count

    result = await manager.get_progress(
        user_id=123,
        path_id="math_basics",
    )

    assert "error" not in result
    assert result["path_id"] == "math_basics"
    assert result["name"] == "数学基礎マスター"
    assert result["completed_count"] == 2
    assert result["total"] == 5
    assert result["path_completed"] is False
    assert len(result["milestones"]) == 5
    # First 2 are completed
    assert result["milestones"][0]["completed"] is True
    assert result["milestones"][1]["completed"] is True
    # Third is current
    assert result["milestones"][2]["current"] is True
    assert result["milestones"][2]["completed"] is False
    # Fourth and fifth are upcoming
    assert result["milestones"][3]["completed"] is False
    assert result["milestones"][3]["current"] is False


@pytest.mark.asyncio
async def test_get_progress_not_enrolled(path_manager):
    """未登録パスの進捗取得テスト"""
    manager, conn = path_manager

    conn.fetchrow.return_value = None  # get_user_path returns None

    result = await manager.get_progress(
        user_id=123,
        path_id="math_basics",
    )

    assert "error" in result
    assert "登録していません" in result["error"]
