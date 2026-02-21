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
    # Phase 5
    "buddy": 0xE91E63,
    "insights": 0x9B59B6,
    "challenge": 0xFFD700,
    # Phase 6
    "quest": 0xE67E22,
    "team": 0x00BCD4,
    "learning_path": 0x8E24AA,
    # Phase 9
    "market": 0x00C853,
    "savings": 0x2196F3,
    "flea": 0xFF9800,
    # Phase 10: Transformative Concepts
    "sanctuary": 0x4CAF50,
    "expedition": 0xFF6F00,
    "forge": 0x795548,
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

# 5段階アンロックレベル
UNLOCK_LEVELS = {
    1: {
        "name": "タイマー完了",
        "description": "タイマー満了で自動解除",
        "code_length": 0,
    },
    2: {
        "name": "確認コード",
        "description": "開始時にDMで6桁コードを受け取り、入力して解除",
        "code_length": 6,
        "code_type": "confirmation",
    },
    3: {
        "name": "DMコード",
        "description": "リクエスト後にDMで8文字コードを受け取り、入力して解除",
        "code_length": 8,
        "code_type": "dm",
    },
    4: {
        "name": "学習完了コード",
        "description": "学習セッション完了後にDMで12文字コードを受け取り、入力して解除",
        "code_length": 12,
        "code_type": "study",
    },
    5: {
        "name": "ペナルティ解除",
        "description": "全ベット+残高20%没収で即時解除",
        "code_length": 0,
    },
}

# ペナルティ解除レート（残高の何%を没収するか）
PENALTY_UNLOCK_RATE = 0.20

# ブロックカテゴリ
BLOCK_CATEGORIES = {
    "sns": "SNS (Twitter, Instagram, TikTok等)",
    "games": "ゲーム",
    "entertainment": "エンタメ (YouTube, Netflix等)",
    "news": "ニュース",
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

# VC勉強追跡設定
VC_DEFAULTS = {
    "min_duration_minutes": 5,
    "check_interval_seconds": 60,
}

# 管理者権限
ADMIN_PERMISSIONS = {
    "max_xp_grant": 10000,
    "max_coin_grant": 10000,
}

# ヘルプカテゴリ
HELP_CATEGORIES = {
    "study": "📚 学習",
    "gamification": "🎮 ゲーミフィケーション",
    "social": "👥 ソーシャル",
    "ai": "🤖 AI・学習支援",
    "wellness": "🧘 ウェルネス・通知",
    "market": "📈 投資市場",
    "settings": "⚙️ 設定・管理",
}

# XP報酬（追加）
XP_REWARDS["vc_study"] = 5  # VC勉強30分あたり

# コイン報酬（追加）
COIN_REWARDS["vc_study"] = 3  # VC勉強30分あたり

# ショップカテゴリ（追加）
SHOP_CATEGORIES["role"] = "👑 ロール"

# バディマッチング設定
BUDDY_DEFAULTS = {
    "queue_ttl_minutes": 30,
    "max_subjects": 10,
    "max_preferred_times": 5,
}

COMPATIBILITY_WEIGHTS = {
    "subject_overlap": 0.4,
    "timezone_compat": 0.2,
    "pattern_similarity": 0.2,
    "style_compat": 0.2,
}

# チャレンジ設定
CHALLENGE_DEFAULTS = {
    "max_duration_days": 90,
    "min_duration_days": 3,
    "max_participants": 50,
    "xp_multiplier": 1.5,
}

# インサイト設定
INSIGHTS_DEFAULTS = {
    "min_data_points": 3,
    "max_insights": 5,
    "report_day": "monday",
    "report_hour_jst": 9,
}

# === 投資市場システム ===

# 学習株式市場設定
STOCK_CONFIG = {
    "base_price": 100,
    "min_price": 10,
    "max_price": 10000,
    "total_shares": 10000,
    "ema_weight": 0.3,  # activity_price の重み (1-ema = 前回価格の重み)
    "buy_pressure_factor": 0.05,  # 売買圧力係数
    "circuit_breaker_pct": 0.15,  # サーキットブレーカー (±15%)
    "price_update_hours": 1,  # 株価更新間隔 (時間)
    "max_shares_per_trade": 100,  # 1回の売買上限
}

# 株式銘柄定義
STOCK_SYMBOLS = [
    {
        "symbol": "MATH",
        "name": "数学株",
        "topic_keyword": "数学",
        "emoji": "📐",
        "sector": "理系",
        "description": "数学の学習量に連動",
    },
    {
        "symbol": "ENG",
        "name": "英語株",
        "topic_keyword": "英語",
        "emoji": "🔤",
        "sector": "語学",
        "description": "英語の学習量に連動",
    },
    {
        "symbol": "SCI",
        "name": "理科株",
        "topic_keyword": "理科",
        "emoji": "🔬",
        "sector": "理系",
        "description": "理科の学習量に連動",
    },
    {
        "symbol": "HIST",
        "name": "歴史株",
        "topic_keyword": "歴史",
        "emoji": "📜",
        "sector": "文系",
        "description": "歴史の学習量に連動",
    },
    {
        "symbol": "CODE",
        "name": "プログラミング株",
        "topic_keyword": "プログラミング",
        "emoji": "💻",
        "sector": "技術",
        "description": "プログラミングの学習量に連動",
    },
    {
        "symbol": "JPN",
        "name": "国語株",
        "topic_keyword": "国語",
        "emoji": "📝",
        "sector": "文系",
        "description": "国語の学習量に連動",
    },
    {
        "symbol": "ART",
        "name": "芸術株",
        "topic_keyword": "芸術",
        "emoji": "🎨",
        "sector": "芸術",
        "description": "芸術の学習量に連動",
    },
    {
        "symbol": "ECON",
        "name": "経済株",
        "topic_keyword": "経済",
        "emoji": "💰",
        "sector": "社会",
        "description": "経済の学習量に連動",
    },
]

# 貯金銀行設定
SAVINGS_CONFIG = {
    "regular_daily_rate": 0.001,  # 普通預金日利 0.1%
    "fixed_daily_rate": 0.003,  # 定期預金日利 0.3%
    "fixed_lock_days": 7,  # 定期預金ロック日数
    "min_deposit": 10,  # 最低預金額
    "min_interest_balance": 100,  # 利息付与に必要な最低残高
    "min_interest_amount": 1,  # 最低利息額
}

# === チャレンジモード設定 ===

# チャレンジモード種別
CHALLENGE_MODES = {
    "none": "チャレンジなし",
    "math": "計算チャレンジ",
    "typing": "タイピングチャレンジ",
}

# チャレンジ難易度設定
# difficulty: 問題数, 桁数レンジ, 演算子
CHALLENGE_DIFFICULTY = {
    1: {"problems": 3, "min_digits": 1, "max_digits": 2, "ops": ["+", "-"]},
    2: {"problems": 4, "min_digits": 1, "max_digits": 2, "ops": ["+", "-", "*"]},
    3: {"problems": 5, "min_digits": 2, "max_digits": 3, "ops": ["+", "-", "*"]},
    4: {"problems": 6, "min_digits": 2, "max_digits": 3, "ops": ["+", "-", "*", "//"]},
    5: {"problems": 8, "min_digits": 2, "max_digits": 4, "ops": ["+", "-", "*", "//"]},
}

# タイピングチャレンジ用フレーズ
TYPING_PHRASES = [
    "集中して学習に取り組みましょう",
    "今やるべきことに全力を注ごう",
    "スマホを置いて目標に向かって進もう",
    "一歩一歩の積み重ねが大きな成果になる",
    "今この瞬間の努力が未来を変える",
    "諦めずに続ける人だけが目標を達成できる",
    "集中力こそが最強のスキルである",
    "自分との約束を守ることが成長の鍵",
    "目の前の課題に集中すれば結果はついてくる",
    "限られた時間を最大限に活用しよう",
]

# ブロックページ用モチベーションメッセージ
BLOCK_MOTIVATION_MESSAGES = [
    "今は集中タイムです。目標に向かって頑張りましょう！",
    "このアプリは今ブロック中です。学習に戻りましょう！",
    "誘惑に負けない強い意志を持ちましょう！",
    "あなたの目標は何ですか？今はそれに集中する時間です。",
    "ブロック解除まであと少し。最後まで頑張りましょう！",
    "未来の自分に感謝されるような選択をしましょう。",
    "集中を続けることで、素晴らしい成果が待っています。",
]

# チャレンジ一時解除のクールダウン（秒）
CHALLENGE_DISMISS_COOLDOWN = 300

# フリーマーケット設定
MARKET_CONFIG = {
    "fee_rate": 0.05,  # 取引手数料 5%
    "listing_duration_days": 7,  # 出品期限 7日
    "max_listings_per_user": 10,  # ユーザーあたり最大出品数
    "min_price": 1,  # 最低出品価格
    "max_price": 100000,  # 最高出品価格
}
