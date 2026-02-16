"""スマホ通知のテスト"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from studybot.managers.nudge_manager import NudgeManager


@pytest.fixture
def nudge_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = NudgeManager(pool)
    return manager, conn


@pytest.mark.asyncio
@patch("studybot.managers.nudge_manager._is_safe_url", return_value=True)
async def test_setup_webhook(_mock_safe, nudge_manager):
    """Webhook設定テスト"""
    manager, conn = nudge_manager

    conn.execute.return_value = None

    result = await manager.setup_webhook(123, "Test", "https://example.com/webhook")

    assert result.get("success") is True


@pytest.mark.asyncio
async def test_setup_webhook_invalid_url(nudge_manager):
    """無効なURLのエラー"""
    manager, conn = nudge_manager

    result = await manager.setup_webhook(123, "Test", "not-a-url")
    assert "error" in result


@pytest.mark.asyncio
@patch("studybot.managers.nudge_manager._is_safe_url", return_value=False)
async def test_setup_webhook_ssrf_blocked(_mock_safe, nudge_manager):
    """プライベートIPへのWebhookがブロックされる"""
    manager, conn = nudge_manager

    result = await manager.setup_webhook(123, "Test", "http://192.168.1.1/webhook")
    assert "error" in result
    assert "プライベートIP" in result["error"]


@pytest.mark.asyncio
async def test_send_nudge_no_config(nudge_manager):
    """設定なしでの通知送信"""
    manager, conn = nudge_manager

    conn.fetchrow.return_value = None  # no config

    result = await manager.send_nudge(123, "test", "テスト")
    assert result is False


@pytest.mark.asyncio
async def test_send_nudge_disabled(nudge_manager):
    """無効化された通知"""
    manager, conn = nudge_manager

    conn.fetchrow.return_value = {
        "user_id": 123,
        "webhook_url": "https://example.com/webhook",
        "enabled": False,
    }

    result = await manager.send_nudge(123, "test", "テスト")
    assert result is False


@pytest.mark.asyncio
async def test_toggle(nudge_manager):
    """通知ON/OFF切り替え"""
    manager, conn = nudge_manager

    conn.execute.return_value = "UPDATE 1"

    result = await manager.toggle(123, False)
    assert result is True


@pytest.mark.asyncio
async def test_get_config(nudge_manager):
    """設定取得テスト"""
    manager, conn = nudge_manager

    conn.fetchrow.return_value = {
        "user_id": 123,
        "webhook_url": "https://example.com/webhook",
        "enabled": True,
    }

    config = await manager.get_config(123)
    assert config is not None
    assert config["enabled"] is True


# === Lock/Shield テスト ===


@pytest.mark.asyncio
async def test_start_lock(nudge_manager):
    """ロック作成テスト"""
    manager, conn = nudge_manager

    # アクティブロックなし
    conn.fetchrow.return_value = None
    conn.execute.return_value = None

    # create_lock_session の返り値を設定（2回目のfetchrow呼び出し）
    lock_row = {
        "id": 1,
        "user_id": 123,
        "lock_type": "lock",
        "duration_minutes": 30,
        "coins_bet": 20,
        "state": "active",
        "started_at": datetime.now(UTC),
        "ended_at": None,
    }
    # get_active_lock -> None, create_lock_session -> lock_row
    conn.fetchrow.side_effect = [None, lock_row]

    result = await manager.start_lock(123, "Test", 30, coins_bet=20)

    assert "error" not in result
    assert result["session_id"] == 1
    assert result["duration"] == 30
    assert result["coins_bet"] == 20
    assert 123 in manager.active_locks


@pytest.mark.asyncio
async def test_start_lock_already_active(nudge_manager):
    """既存ロックありでのエラー"""
    manager, conn = nudge_manager

    # メモリ上にアクティブロックを設定
    manager.active_locks[123] = {
        "session_id": 1,
        "end_time": datetime.now(UTC) + timedelta(minutes=30),
        "coins_bet": 0,
        "lock_type": "lock",
    }

    result = await manager.start_lock(123, "Test", 30)

    assert "error" in result
    assert "既にアクティブなロック" in result["error"]

    # クリーンアップ
    manager.active_locks.pop(123, None)


@pytest.mark.asyncio
async def test_break_lock(nudge_manager):
    """ロック中断テスト"""
    manager, conn = nudge_manager

    # メモリ上にアクティブロックを設定
    manager.active_locks[123] = {
        "session_id": 1,
        "end_time": datetime.now(UTC) + timedelta(minutes=30),
        "coins_bet": 50,
        "lock_type": "lock",
    }

    broken_row = {
        "id": 1,
        "user_id": 123,
        "lock_type": "lock",
        "duration_minutes": 30,
        "coins_bet": 50,
        "state": "broken",
        "started_at": datetime.now(UTC),
        "ended_at": datetime.now(UTC),
    }
    conn.fetchrow.return_value = broken_row

    result = await manager.break_lock(123)

    assert result["broken"] is True
    assert result["coins_lost"] == 50
    assert 123 not in manager.active_locks


@pytest.mark.asyncio
async def test_complete_lock(nudge_manager):
    """ロック完了テスト"""
    manager, conn = nudge_manager

    # メモリ上にアクティブロックを設定
    manager.active_locks[123] = {
        "session_id": 1,
        "end_time": datetime.now(UTC) + timedelta(minutes=30),
        "coins_bet": 20,
        "lock_type": "lock",
    }

    completed_row = {
        "id": 1,
        "user_id": 123,
        "lock_type": "lock",
        "duration_minutes": 30,
        "coins_bet": 20,
        "state": "completed",
        "started_at": datetime.now(UTC),
        "ended_at": datetime.now(UTC),
    }
    conn.fetchrow.return_value = completed_row

    result = await manager.complete_lock(123)

    assert result["completed"] is True
    assert result["coins_earned"] == 15  # COIN_REWARDS["lock_complete"]
    assert result["coins_returned"] == 20
    assert 123 not in manager.active_locks


@pytest.mark.asyncio
async def test_start_shield(nudge_manager):
    """シールド作成テスト"""
    manager, conn = nudge_manager

    # アクティブロックなし
    conn.fetchrow.return_value = None
    conn.execute.return_value = None

    shield_row = {
        "id": 2,
        "user_id": 123,
        "lock_type": "shield",
        "duration_minutes": 60,
        "coins_bet": 0,
        "state": "active",
        "started_at": datetime.now(UTC),
        "ended_at": None,
    }
    # get_active_lock -> None, create_lock_session -> shield_row
    conn.fetchrow.side_effect = [None, shield_row]

    result = await manager.start_shield(123, "Test", 60)

    assert "error" not in result
    assert result["session_id"] == 2
    assert result["duration"] == 60
    assert 123 in manager.active_locks
    assert manager.active_locks[123]["lock_type"] == "shield"

    # クリーンアップ
    manager.active_locks.pop(123, None)


@pytest.mark.asyncio
async def test_get_lock_status(nudge_manager):
    """ロックステータス取得テスト"""
    manager, conn = nudge_manager

    end_time = datetime.now(UTC) + timedelta(minutes=15)
    manager.active_locks[123] = {
        "session_id": 1,
        "end_time": end_time,
        "coins_bet": 30,
        "lock_type": "lock",
    }

    status = await manager.get_lock_status(123)

    assert status is not None
    assert status["session_id"] == 1
    assert status["lock_type"] == "lock"
    assert status["coins_bet"] == 30
    assert status["remaining_minutes"] > 0

    # クリーンアップ
    manager.active_locks.pop(123, None)


@pytest.mark.asyncio
async def test_check_locks_expired(nudge_manager):
    """期限切れロックの完了チェック（レベル1のみ自動完了）"""
    manager, conn = nudge_manager

    # 期限切れのロックを設定（レベル1）
    manager.active_locks[123] = {
        "session_id": 1,
        "end_time": datetime.now(UTC) - timedelta(minutes=5),
        "coins_bet": 10,
        "lock_type": "lock",
        "unlock_level": 1,
    }

    completed_row = {
        "id": 1,
        "user_id": 123,
        "lock_type": "lock",
        "duration_minutes": 30,
        "coins_bet": 10,
        "state": "completed",
        "started_at": datetime.now(UTC) - timedelta(minutes=35),
        "ended_at": datetime.now(UTC),
    }
    conn.fetchrow.return_value = completed_row

    completed = await manager.check_locks()

    assert len(completed) == 1
    assert completed[0]["completed"] is True
    assert completed[0]["user_id"] == 123
    assert completed[0]["coins_earned"] == 15
    assert 123 not in manager.active_locks


@pytest.mark.asyncio
async def test_check_locks_level2_not_auto_complete(nudge_manager):
    """レベル2以上は自動完了しない"""
    manager, conn = nudge_manager

    manager.active_locks[456] = {
        "session_id": 2,
        "end_time": datetime.now(UTC) - timedelta(minutes=5),
        "coins_bet": 20,
        "lock_type": "lock",
        "unlock_level": 2,
    }

    completed = await manager.check_locks()

    assert len(completed) == 0
    assert 456 in manager.active_locks

    # クリーンアップ
    manager.active_locks.pop(456, None)


@pytest.mark.asyncio
async def test_start_lock_with_unlock_level(nudge_manager):
    """アンロックレベル付きロック作成テスト"""
    manager, conn = nudge_manager

    conn.fetchrow.return_value = None
    conn.execute.return_value = None

    lock_row = {
        "id": 3,
        "user_id": 789,
        "lock_type": "lock",
        "duration_minutes": 60,
        "coins_bet": 50,
        "unlock_level": 3,
        "state": "active",
        "started_at": datetime.now(UTC),
        "ended_at": None,
    }
    conn.fetchrow.side_effect = [None, lock_row]

    result = await manager.start_lock(789, "Test", 60, coins_bet=50, unlock_level=3)

    assert "error" not in result
    assert result["unlock_level"] == 3
    assert result["session_id"] == 3
    assert manager.active_locks[789]["unlock_level"] == 3

    # クリーンアップ
    manager.active_locks.pop(789, None)


@pytest.mark.asyncio
async def test_start_lock_invalid_unlock_level(nudge_manager):
    """無効なアンロックレベルでのエラー"""
    manager, conn = nudge_manager

    conn.fetchrow.return_value = None  # no active lock

    result = await manager.start_lock(123, "Test", 30, unlock_level=6)
    assert "error" in result


@pytest.mark.asyncio
async def test_penalty_unlock(nudge_manager):
    """ペナルティ解除テスト"""
    manager, conn = nudge_manager

    manager.active_locks[123] = {
        "session_id": 5,
        "end_time": datetime.now(UTC) + timedelta(minutes=30),
        "coins_bet": 50,
        "lock_type": "lock",
        "unlock_level": 5,
    }

    broken_row = {
        "id": 5,
        "user_id": 123,
        "state": "broken",
        "started_at": datetime.now(UTC),
        "ended_at": datetime.now(UTC),
    }
    conn.fetchrow.return_value = broken_row

    result = await manager.penalty_unlock(123)

    assert result.get("penalty_unlocked") is True
    assert result["coins_lost"] == 50
    assert result["penalty_rate"] == 0.20
    assert 123 not in manager.active_locks


@pytest.mark.asyncio
async def test_penalty_unlock_wrong_level(nudge_manager):
    """レベル5以外でのペナルティ解除エラー"""
    manager, conn = nudge_manager

    manager.active_locks[123] = {
        "session_id": 6,
        "end_time": datetime.now(UTC) + timedelta(minutes=30),
        "coins_bet": 20,
        "lock_type": "lock",
        "unlock_level": 2,
    }

    result = await manager.penalty_unlock(123)
    assert "error" in result

    # クリーンアップ
    manager.active_locks.pop(123, None)


@pytest.mark.asyncio
async def test_get_lock_status_with_unlock_level(nudge_manager):
    """アンロックレベル付きステータス取得"""
    manager, conn = nudge_manager

    end_time = datetime.now(UTC) + timedelta(minutes=15)
    manager.active_locks[123] = {
        "session_id": 1,
        "end_time": end_time,
        "coins_bet": 30,
        "lock_type": "lock",
        "unlock_level": 3,
    }

    status = await manager.get_lock_status(123)

    assert status is not None
    assert status["unlock_level"] == 3

    # クリーンアップ
    manager.active_locks.pop(123, None)


@pytest.mark.asyncio
async def test_on_study_completed_no_lock(nudge_manager):
    """ロックなしでの学習完了フック"""
    manager, conn = nudge_manager
    conn.fetchrow.return_value = None

    code = await manager.on_study_completed(999)
    assert code is None


@pytest.mark.asyncio
async def test_on_study_completed_wrong_level(nudge_manager):
    """レベル4以外での学習完了フック"""
    manager, conn = nudge_manager

    manager.active_locks[123] = {
        "session_id": 1,
        "end_time": datetime.now(UTC) + timedelta(minutes=30),
        "coins_bet": 0,
        "lock_type": "lock",
        "unlock_level": 2,
    }

    code = await manager.on_study_completed(123)
    assert code is None

    # クリーンアップ
    manager.active_locks.pop(123, None)


# === チャレンジ生成・検証テスト ===


@pytest.mark.asyncio
async def test_generate_math_challenge(nudge_manager):
    """計算チャレンジ生成テスト"""
    manager, conn = nudge_manager

    problems = manager.generate_math_challenge(difficulty=1)
    assert len(problems) == 3  # difficulty 1 = 3 problems
    for p in problems:
        assert "expression" in p
        assert "answer" in p
        assert isinstance(p["answer"], int)


@pytest.mark.asyncio
async def test_generate_math_challenge_high_difficulty(nudge_manager):
    """高難易度の計算チャレンジ生成"""
    manager, conn = nudge_manager

    problems = manager.generate_math_challenge(difficulty=5)
    assert len(problems) == 8  # difficulty 5 = 8 problems


@pytest.mark.asyncio
async def test_verify_math_challenge_correct(nudge_manager):
    """計算チャレンジの正解検証"""
    manager, conn = nudge_manager

    problems = [
        {"expression": "5 + 3", "answer": 8},
        {"expression": "10 - 4", "answer": 6},
        {"expression": "3 * 7", "answer": 21},
    ]
    answers = [8, 6, 21]

    result = manager.verify_math_challenge(problems, answers)
    assert result["correct"] is True
    assert result["score"] == 3
    assert result["total"] == 3


@pytest.mark.asyncio
async def test_verify_math_challenge_wrong(nudge_manager):
    """計算チャレンジの不正解検証"""
    manager, conn = nudge_manager

    problems = [
        {"expression": "5 + 3", "answer": 8},
        {"expression": "10 - 4", "answer": 6},
    ]
    answers = [8, 5]  # 2問目が不正解

    result = manager.verify_math_challenge(problems, answers)
    assert result["correct"] is False
    assert result["score"] == 1
    assert result["total"] == 2


@pytest.mark.asyncio
async def test_verify_math_challenge_wrong_count(nudge_manager):
    """回答数が問題数と一致しない場合"""
    manager, conn = nudge_manager

    problems = [{"expression": "5 + 3", "answer": 8}]
    answers = [8, 6]  # 余分な回答

    result = manager.verify_math_challenge(problems, answers)
    assert result["correct"] is False


@pytest.mark.asyncio
async def test_generate_typing_challenge(nudge_manager):
    """タイピングチャレンジ生成テスト"""
    manager, conn = nudge_manager

    phrases = manager.generate_typing_challenge(difficulty=2)
    assert len(phrases) == 2
    for p in phrases:
        assert isinstance(p, str)
        assert len(p) > 0


@pytest.mark.asyncio
async def test_verify_typing_challenge_correct(nudge_manager):
    """タイピングチャレンジの正解検証"""
    manager, conn = nudge_manager

    originals = ["集中して学習に取り組みましょう"]
    typed = ["集中して学習に取り組みましょう"]

    result = manager.verify_typing_challenge(originals, typed)
    assert result["correct"] is True
    assert result["accuracy"] == 100.0


@pytest.mark.asyncio
async def test_verify_typing_challenge_wrong(nudge_manager):
    """タイピングチャレンジの不正解検証"""
    manager, conn = nudge_manager

    originals = ["集中して学習に取り組みましょう", "今やるべきことに全力を注ごう"]
    typed = ["集中して学習に取り組みましょう", "間違ったテキスト"]

    result = manager.verify_typing_challenge(originals, typed)
    assert result["correct"] is False
    assert result["accuracy"] == 50.0
    assert result["matched"] == 1


@pytest.mark.asyncio
async def test_start_lock_with_challenge_mode(nudge_manager):
    """チャレンジモード付きロック作成テスト"""
    manager, conn = nudge_manager

    conn.fetchrow.return_value = None
    conn.execute.return_value = None

    lock_row = {
        "id": 10,
        "user_id": 123,
        "lock_type": "lock",
        "duration_minutes": 30,
        "coins_bet": 0,
        "unlock_level": 1,
        "challenge_mode": "math",
        "state": "active",
        "started_at": datetime.now(UTC),
        "ended_at": None,
    }
    conn.fetchrow.side_effect = [None, lock_row]

    result = await manager.start_lock(123, "Test", 30, challenge_mode="math")

    assert "error" not in result
    assert result["challenge_mode"] == "math"
    assert manager.active_locks[123]["challenge_mode"] == "math"

    # クリーンアップ
    manager.active_locks.pop(123, None)


@pytest.mark.asyncio
async def test_math_challenge_division_exact(nudge_manager):
    """整数除算が割り切れることを確認"""
    manager, conn = nudge_manager

    # difficulty 4+ includes // operator
    problems = manager.generate_math_challenge(difficulty=4)
    for p in problems:
        if "//" in p["expression"]:
            parts = p["expression"].split(" // ")
            a, b = int(parts[0]), int(parts[1])
            assert a % b == 0, f"{a} is not divisible by {b}"
