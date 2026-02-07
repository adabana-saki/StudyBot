"""定数定義"""

# Embed カラー
COLORS = {
    "primary": 0x5865F2,
    "success": 0x57F287,
    "warning": 0xFEE75C,
    "error": 0xED4245,
    "study": 0x3498DB,
    "xp": 0xF1C40F,
    "pomodoro": 0xE74C3C,
}

# XP報酬
XP_REWARDS = {
    "pomodoro_complete": 10,  # ポモドーロ1セッション完了
    "task_complete_low": 10,  # 低優先度タスク完了
    "task_complete_medium": 20,  # 中優先度タスク完了
    "task_complete_high": 30,  # 高優先度タスク完了
    "study_log": 5,  # 学習ログ記録
    "streak_bonus": 50,  # 連続学習ボーナス
}


def level_required_xp(level: int) -> int:
    """レベルアップに必要なXPを計算: level² × 100"""
    return level * level * 100


LEVEL_FORMULA = level_required_xp

# ポモドーロデフォルト設定
POMODORO_DEFAULTS = {
    "work_minutes": 25,
    "break_minutes": 5,
}

# 優先度ラベル
PRIORITY_LABELS = {
    1: "🔴 高",
    2: "🟡 中",
    3: "🟢 低",
}

# 期間ラベル
PERIOD_LABELS = {
    "daily": "今日",
    "weekly": "今週",
    "monthly": "今月",
    "all_time": "全期間",
}

# メダル絵文字
MEDAL_EMOJIS = ["🥇", "🥈", "🥉"]
