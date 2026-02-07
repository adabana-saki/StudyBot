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
    # Phase 2
    "coins": 0xFFD700,
    "raid": 0x9B59B6,
    "wellness": 0x2ECC71,
    "achievement": 0xE67E22,
    "focus": 0x1ABC9C,
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

# StudyCoin報酬テーブル
COIN_REWARDS = {
    "pomodoro_complete": 5,
    "task_complete_low": 5,
    "task_complete_medium": 10,
    "task_complete_high": 15,
    "study_log": 3,
    "streak_bonus_7": 30,
    "streak_bonus_30": 100,
    "raid_complete": 20,
    "raid_host": 30,
    "achievement_unlock": 0,  # 実績ごとに個別設定
    "focus_complete": 10,
    "lock_complete": 15,
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

# スタディレイド設定
RAID_DEFAULTS = {
    "max_participants": 10,
    "xp_multiplier": 1.5,
    "min_duration": 15,
    "max_duration": 180,
}

# ショップカテゴリ
SHOP_CATEGORIES = {
    "title": "📝 タイトル",
    "cosmetic": "🎨 コスメティック",
    "boost": "⚡ ブースト",
    "theme": "🎭 テーマ",
}

# レアリティラベル
RARITY_LABELS = {
    "common": "⬜ コモン",
    "uncommon": "🟩 アンコモン",
    "rare": "🟦 レア",
    "epic": "🟪 エピック",
    "legendary": "🟨 レジェンダリー",
}

# ウェルネスラベル
MOOD_LABELS = {
    1: "😢 とても悪い",
    2: "😟 悪い",
    3: "😐 普通",
    4: "😊 良い",
    5: "😄 とても良い",
}

ENERGY_LABELS = {
    1: "🔋 とても低い",
    2: "🪫 低い",
    3: "⚡ 普通",
    4: "⚡⚡ 高い",
    5: "⚡⚡⚡ とても高い",
}

STRESS_LABELS = {
    1: "😌 とても低い",
    2: "🙂 低い",
    3: "😐 普通",
    4: "😰 高い",
    5: "😫 とても高い",
}

# SM-2 間隔反復アルゴリズム デフォルト
SM2_DEFAULTS = {
    "initial_easiness": 2.5,
    "min_easiness": 1.3,
    "initial_interval": 0,
    "initial_repetitions": 0,
}

# フォーカスモード設定
FOCUS_DEFAULTS = {
    "min_duration": 10,
    "max_duration": 480,
    "default_duration": 60,
}

# ナッジレベル設定
NUDGE_LEVELS = {
    "lock": {
        "name": "フォーカスロック",
        "coin_bet_min": 10,
        "coin_bet_max": 100,
    },
    "shield": {
        "name": "フォーカスシールド",
        "min_duration": 30,
        "max_duration": 240,
        "nudge_interval_minutes": 15,
    },
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
