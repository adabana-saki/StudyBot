"""デイリークエストのテスト"""

from datetime import date

import pytest

from studybot.managers.quest_manager import QuestManager, _generate_random_quests


@pytest.fixture
def quest_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = QuestManager(pool)
    return manager, conn


@pytest.mark.asyncio
async def test_get_daily_quests_generates_new(quest_manager):
    """クエストが存在しない場合、自動生成されるテスト"""
    manager, conn = quest_manager

    conn.execute.return_value = None  # ensure_user
    conn.fetch.return_value = []  # get_user_quests -> empty
    conn.fetchval.side_effect = [1, 2, 3]  # create_quest returns IDs

    quests = await manager.get_daily_quests(user_id=123, username="TestUser")

    assert len(quests) == 3
    assert quests[0]["id"] == 1
    assert quests[1]["id"] == 2
    assert quests[2]["id"] == 3
    for q in quests:
        assert q["progress"] == 0
        assert q["completed"] is False
        assert q["claimed"] is False


@pytest.mark.asyncio
async def test_get_daily_quests_returns_existing(quest_manager):
    """既存のクエストがある場合、そのまま返すテスト"""
    manager, conn = quest_manager

    conn.execute.return_value = None  # ensure_user
    existing_quests = [
        {
            "id": 10,
            "user_id": 123,
            "quest_type": "complete_pomodoro",
            "target": 3,
            "progress": 1,
            "reward_xp": 45,
            "reward_coins": 30,
            "completed": False,
            "claimed": False,
            "quest_date": date.today(),
        },
        {
            "id": 11,
            "user_id": 123,
            "quest_type": "study_minutes",
            "target": 60,
            "progress": 30,
            "reward_xp": 30,
            "reward_coins": 18,
            "completed": False,
            "claimed": False,
            "quest_date": date.today(),
        },
        {
            "id": 12,
            "user_id": 123,
            "quest_type": "log_study",
            "target": 2,
            "progress": 2,
            "reward_xp": 40,
            "reward_coins": 24,
            "completed": True,
            "claimed": False,
            "quest_date": date.today(),
        },
    ]
    conn.fetch.return_value = existing_quests

    quests = await manager.get_daily_quests(user_id=123, username="TestUser")

    assert len(quests) == 3
    assert quests[0]["id"] == 10
    assert quests[2]["completed"] is True
    # fetchval should NOT have been called (no quest creation)
    conn.fetchval.assert_not_called()


@pytest.mark.asyncio
async def test_claim_quest_success(quest_manager):
    """クエスト報酬受取成功テスト"""
    manager, conn = quest_manager

    conn.fetchrow.side_effect = [
        # get_quest_by_id
        {
            "id": 10,
            "user_id": 123,
            "quest_type": "complete_pomodoro",
            "target": 3,
            "progress": 3,
            "reward_xp": 45,
            "reward_coins": 30,
            "completed": True,
            "claimed": False,
            "quest_date": date.today(),
        },
        # claim_quest UPDATE RETURNING
        {
            "id": 10,
            "user_id": 123,
            "quest_type": "complete_pomodoro",
            "target": 3,
            "progress": 3,
            "reward_xp": 45,
            "reward_coins": 30,
            "completed": True,
            "claimed": True,
            "quest_date": date.today(),
        },
    ]

    result = await manager.claim_quest(user_id=123, quest_id=10)

    assert "error" not in result
    assert result["quest_id"] == 10
    assert result["reward_xp"] == 45
    assert result["reward_coins"] == 30


@pytest.mark.asyncio
async def test_claim_quest_not_completed(quest_manager):
    """未完了クエストの報酬受取テスト"""
    manager, conn = quest_manager

    conn.fetchrow.return_value = {
        "id": 10,
        "user_id": 123,
        "quest_type": "complete_pomodoro",
        "target": 3,
        "progress": 1,
        "reward_xp": 45,
        "reward_coins": 30,
        "completed": False,
        "claimed": False,
        "quest_date": date.today(),
    }

    result = await manager.claim_quest(user_id=123, quest_id=10)

    assert "error" in result
    assert "完了していません" in result["error"]


@pytest.mark.asyncio
async def test_claim_quest_already_claimed(quest_manager):
    """既に受取済みクエストの報酬受取テスト"""
    manager, conn = quest_manager

    conn.fetchrow.return_value = {
        "id": 10,
        "user_id": 123,
        "quest_type": "complete_pomodoro",
        "target": 3,
        "progress": 3,
        "reward_xp": 45,
        "reward_coins": 30,
        "completed": True,
        "claimed": True,
        "quest_date": date.today(),
    }

    result = await manager.claim_quest(user_id=123, quest_id=10)

    assert "error" in result
    assert "受け取り済み" in result["error"]


@pytest.mark.asyncio
async def test_claim_quest_not_found(quest_manager):
    """存在しないクエストの報酬受取テスト"""
    manager, conn = quest_manager

    conn.fetchrow.return_value = None  # get_quest_by_id returns None

    result = await manager.claim_quest(user_id=123, quest_id=999)

    assert "error" in result
    assert "見つかりません" in result["error"]


@pytest.mark.asyncio
async def test_update_progress(quest_manager):
    """クエスト進捗更新テスト"""
    manager, conn = quest_manager

    updated_quests = [
        {
            "id": 10,
            "user_id": 123,
            "quest_type": "complete_pomodoro",
            "target": 3,
            "progress": 2,
            "reward_xp": 45,
            "reward_coins": 30,
            "completed": False,
            "claimed": False,
            "quest_date": date.today(),
        },
    ]
    conn.execute.return_value = None
    conn.fetch.return_value = updated_quests

    result = await manager.update_progress(user_id=123, quest_type="complete_pomodoro", delta=1)

    assert len(result) == 1
    assert result[0]["progress"] == 2


def test_generate_quests_produces_three():
    """クエスト生成が3つ生成するテスト"""
    quests = _generate_random_quests(user_id=123, quest_date=date.today())

    assert len(quests) == 3
    quest_types = [q["quest_type"] for q in quests]
    # 3つとも異なるタイプであること
    assert len(set(quest_types)) == 3
    for q in quests:
        assert q["user_id"] == 123
        assert q["target"] > 0
        assert q["reward_xp"] >= 10
        assert q["reward_coins"] >= 5


def test_get_quest_label():
    """クエストラベル取得テスト"""
    manager = QuestManager.__new__(QuestManager)
    assert manager.get_quest_label("complete_pomodoro") == "ポモドーロ完了"
    assert manager.get_quest_label("study_minutes") == "学習時間"
    assert manager.get_quest_label("complete_tasks") == "タスク完了"
    assert manager.get_quest_label("log_study") == "学習ログ記録"
    assert manager.get_quest_label("unknown") == "unknown"


def test_get_quest_unit():
    """クエスト単位取得テスト"""
    manager = QuestManager.__new__(QuestManager)
    assert manager.get_quest_unit("complete_pomodoro") == "回"
    assert manager.get_quest_unit("study_minutes") == "分"
    assert manager.get_quest_unit("complete_tasks") == "件"
    assert manager.get_quest_unit("log_study") == "回"
    assert manager.get_quest_unit("unknown") == ""
