"""ウェルネスのテスト"""

from datetime import date

import pytest

from studybot.managers.wellness_manager import WellnessManager


@pytest.fixture
def wellness_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = WellnessManager(pool)
    return manager, conn


@pytest.mark.asyncio
async def test_log_wellness_normal(wellness_manager):
    """通常のウェルネス記録テスト"""
    manager, conn = wellness_manager

    conn.execute.return_value = None  # ensure_user
    conn.fetchrow.side_effect = [
        # log_wellness RETURNING *
        {
            "id": 1,
            "user_id": 123,
            "mood": 4,
            "energy": 3,
            "stress": 2,
            "note": "良い感じ",
            "logged_at": None,
        },
        # get_averages
        {
            "avg_mood": 3.5,
            "avg_energy": 3.0,
            "avg_stress": 2.5,
            "log_count": 5,
        },
    ]

    result = await manager.log_wellness(
        user_id=123,
        username="TestUser",
        mood=4,
        energy=3,
        stress=2,
        note="良い感じ",
    )

    assert result["logged"] is True
    assert result["warning"] is None
    assert "良い" in result["mood_label"]


@pytest.mark.asyncio
async def test_log_wellness_with_warning_low_mood(wellness_manager):
    """気分が低い場合の警告テスト"""
    manager, conn = wellness_manager

    conn.execute.return_value = None
    conn.fetchrow.side_effect = [
        # log_wellness RETURNING *
        {
            "id": 2,
            "user_id": 123,
            "mood": 1,
            "energy": 2,
            "stress": 3,
            "note": "",
            "logged_at": None,
        },
        # get_averages
        {
            "avg_mood": 2.0,
            "avg_energy": 2.5,
            "avg_stress": 3.0,
            "log_count": 3,
        },
    ]

    result = await manager.log_wellness(
        user_id=123,
        username="TestUser",
        mood=1,
        energy=2,
        stress=3,
    )

    assert result["logged"] is True
    assert result["warning"] is not None
    assert "休憩" in result["warning"]


@pytest.mark.asyncio
async def test_log_wellness_with_warning_high_stress(wellness_manager):
    """ストレスが高い場合の警告テスト"""
    manager, conn = wellness_manager

    conn.execute.return_value = None
    conn.fetchrow.side_effect = [
        # log_wellness RETURNING *
        {
            "id": 3,
            "user_id": 123,
            "mood": 3,
            "energy": 3,
            "stress": 5,
            "note": "",
            "logged_at": None,
        },
        # get_averages
        {
            "avg_mood": 3.0,
            "avg_energy": 3.0,
            "avg_stress": 4.5,
            "log_count": 4,
        },
    ]

    result = await manager.log_wellness(
        user_id=123,
        username="TestUser",
        mood=3,
        energy=3,
        stress=5,
    )

    assert result["logged"] is True
    assert result["warning"] is not None
    assert "深呼吸" in result["warning"]


@pytest.mark.asyncio
async def test_log_wellness_with_both_warnings(wellness_manager):
    """気分が低くストレスも高い場合のテスト"""
    manager, conn = wellness_manager

    conn.execute.return_value = None
    conn.fetchrow.side_effect = [
        {
            "id": 4,
            "user_id": 123,
            "mood": 2,
            "energy": 1,
            "stress": 4,
            "note": "",
            "logged_at": None,
        },
        {
            "avg_mood": 2.0,
            "avg_energy": 1.5,
            "avg_stress": 4.0,
            "log_count": 2,
        },
    ]

    result = await manager.log_wellness(
        user_id=123,
        username="TestUser",
        mood=2,
        energy=1,
        stress=4,
    )

    assert result["logged"] is True
    assert result["warning"] is not None
    assert "休憩" in result["warning"]
    assert "深呼吸" in result["warning"]


@pytest.mark.asyncio
async def test_get_stats_with_data(wellness_manager):
    """統計データありのテスト"""
    manager, conn = wellness_manager

    conn.fetchrow.return_value = {
        "avg_mood": 3.8,
        "avg_energy": 3.2,
        "avg_stress": 2.4,
        "log_count": 7,
    }
    conn.fetch.return_value = [
        {
            "id": 1,
            "user_id": 123,
            "mood": 4,
            "energy": 3,
            "stress": 2,
            "note": "",
            "logged_at": None,
        },
    ]

    result = await manager.get_stats(user_id=123)

    assert result["has_data"] is True
    assert result["avg_mood"] == 3.8
    assert result["avg_energy"] == 3.2
    assert result["avg_stress"] == 2.4
    assert result["log_count"] == 7


@pytest.mark.asyncio
async def test_get_stats_no_data(wellness_manager):
    """統計データなしのテスト"""
    manager, conn = wellness_manager

    conn.fetchrow.return_value = None  # get_averages returns None
    conn.fetch.return_value = []  # get_recent_logs returns empty

    result = await manager.get_stats(user_id=123)

    assert result["has_data"] is False
    assert "message" in result


@pytest.mark.asyncio
async def test_generate_trend_chart_no_data(wellness_manager):
    """トレンドチャート生成（データなし）"""
    manager, conn = wellness_manager

    conn.fetch.return_value = []  # no daily averages

    result = await manager.generate_trend_chart(user_id=123)

    assert result is None


@pytest.mark.asyncio
async def test_generate_trend_chart_with_data(wellness_manager):
    """トレンドチャート生成（データあり）"""
    manager, conn = wellness_manager

    today = date.today()
    conn.fetch.return_value = [
        {
            "day": today,
            "avg_mood": 3.5,
            "avg_energy": 3.0,
            "avg_stress": 2.5,
        },
        {
            "day": today,
            "avg_mood": 4.0,
            "avg_energy": 3.5,
            "avg_stress": 2.0,
        },
    ]

    result = await manager.generate_trend_chart(user_id=123)

    assert result is not None
    # BytesIOオブジェクトであることを確認
    assert hasattr(result, "read")
    # PNGデータであることを確認
    data = result.read()
    assert len(data) > 0
    assert data[:4] == b"\x89PNG"
