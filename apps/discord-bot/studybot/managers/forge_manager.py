"""フォージ（熟練の鍛冶場）ビジネスロジック"""

import logging

from studybot.repositories.forge_repository import ForgeRepository

logger = logging.getLogger(__name__)

# マスタリーレベル定義
MASTERY_LEVELS = [
    {"level": 0, "name": "未着手", "emoji": "⬜", "required_xp": 0},
    {"level": 1, "name": "初心者", "emoji": "🟫", "required_xp": 100},
    {"level": 2, "name": "見習い", "emoji": "🟩", "required_xp": 500},
    {"level": 3, "name": "職人", "emoji": "🟦", "required_xp": 1500},
    {"level": 4, "name": "熟練者", "emoji": "🟪", "required_xp": 4000},
    {"level": 5, "name": "マスター", "emoji": "🟨", "required_xp": 10000},
]

# 難易度スコアマッピング
DIFFICULTY_SCORES = {1: 0.4, 2: 0.7, 3: 1.0, 4: 1.0, 5: 0.8}

# スキルカテゴリ
SKILL_CATEGORIES = {
    "math": {"name": "数学", "emoji": "📐"},
    "english": {"name": "英語", "emoji": "🔤"},
    "science": {"name": "理科", "emoji": "🔬"},
    "history": {"name": "歴史", "emoji": "📜"},
    "programming": {"name": "プログラミング", "emoji": "💻"},
    "japanese": {"name": "国語", "emoji": "📝"},
    "art": {"name": "芸術", "emoji": "🎨"},
    "economics": {"name": "経済", "emoji": "💰"},
    "general": {"name": "その他", "emoji": "📚"},
}

# チャレンジテンプレート
CHALLENGE_TEMPLATES = [
    {
        "title": "基本計算チャレンジ",
        "description": "四則演算の基礎問題",
        "category": "math",
        "rating": 1000,
    },
    {
        "title": "英文法チャレンジ",
        "description": "基本的な英文法問題",
        "category": "english",
        "rating": 1000,
    },
    {
        "title": "歴史年号チャレンジ",
        "description": "重要な歴史年号の暗記",
        "category": "history",
        "rating": 1100,
    },
    {
        "title": "プログラミング基礎",
        "description": "基本的なコーディング問題",
        "category": "programming",
        "rating": 1100,
    },
    {
        "title": "化学式チャレンジ",
        "description": "基本的な化学式の理解",
        "category": "science",
        "rating": 1200,
    },
    {
        "title": "漢字書き取り",
        "description": "常用漢字の書き取り",
        "category": "japanese",
        "rating": 900,
    },
    {
        "title": "統計解析チャレンジ",
        "description": "統計の基本概念と計算",
        "category": "math",
        "rating": 1400,
    },
    {
        "title": "長文読解チャレンジ",
        "description": "英語長文の読解力テスト",
        "category": "english",
        "rating": 1300,
    },
    {
        "title": "アルゴリズム設計",
        "description": "効率的なアルゴリズム設計",
        "category": "programming",
        "rating": 1500,
    },
    {
        "title": "芸術史チャレンジ",
        "description": "芸術作品と時代の対応",
        "category": "art",
        "rating": 1100,
    },
]

# Elo定数
ELO_K = 32
ELO_DEFAULT = 1200


class ForgeManager:
    """品質計算・Elo・スキルツリー"""

    def __init__(self, db_pool) -> None:
        self.repository = ForgeRepository(db_pool)

    def calculate_quality(self, focus: int, difficulty: int, progress: int) -> float:
        """品質スコア計算"""
        focus = max(1, min(5, focus))
        difficulty = max(1, min(5, difficulty))
        progress = max(1, min(5, progress))

        focus_score = focus / 5.0
        difficulty_score = DIFFICULTY_SCORES.get(difficulty, 0.7)
        progress_score = progress / 5.0

        return (focus_score * 0.4 + difficulty_score * 0.3 + progress_score * 0.3) * 100

    def calculate_mastery_xp(self, duration_minutes: int, quality_score: float) -> int:
        """マスタリーXP計算"""
        quality_mult = 0.5 + (quality_score / 100)
        return max(1, int(duration_minutes * quality_mult))

    def get_mastery_level(self, xp: int) -> dict:
        """XPからマスタリーレベルを取得"""
        level = MASTERY_LEVELS[0]
        for ml in MASTERY_LEVELS:
            if xp >= ml["required_xp"]:
                level = ml
        return level

    async def log_practice(
        self,
        user_id: int,
        category: str,
        focus: int,
        difficulty: int,
        progress: int,
        duration_minutes: int,
    ) -> dict:
        """意図的練習をログ"""
        if category not in SKILL_CATEGORIES:
            category = "general"

        quality = self.calculate_quality(focus, difficulty, progress)
        mastery_xp = self.calculate_mastery_xp(duration_minutes, quality)

        # 品質ログ保存
        await self.repository.log_quality(
            user_id,
            category,
            focus,
            difficulty,
            progress,
            quality,
            duration_minutes,
        )

        # マスタリーXP加算
        skill = await self.repository.add_mastery_xp(user_id, category, mastery_xp)

        # レベル判定
        new_level = self.get_mastery_level(skill["mastery_xp"])
        old_level = self.get_mastery_level(skill["mastery_xp"] - mastery_xp)
        leveled_up = new_level["level"] > old_level["level"]

        # 品質平均更新
        avg = await self.repository.get_quality_average(user_id, category)
        await self.repository.upsert_skill(
            user_id,
            category,
            skill["mastery_xp"],
            new_level["level"],
            avg,
        )

        return {
            "quality_score": quality,
            "mastery_xp_gained": mastery_xp,
            "total_mastery_xp": skill["mastery_xp"],
            "mastery_level": new_level,
            "leveled_up": leveled_up,
            "quality_avg": avg,
        }

    async def get_skills(self, user_id: int, category: str = "") -> list[dict]:
        """スキルツリー表示"""
        if category:
            skill = await self.repository.get_skill(user_id, category)
            skills = [skill] if skill else []
        else:
            skills = await self.repository.get_all_skills(user_id)

        for s in skills:
            s["level_info"] = self.get_mastery_level(s.get("mastery_xp", 0))
            cat = s.get("category", "general")
            s["category_info"] = SKILL_CATEGORIES.get(cat, {"name": cat, "emoji": "📚"})
            # 次のレベルまでの進捗
            current = s["level_info"]
            next_levels = [
                ml for ml in MASTERY_LEVELS if ml["required_xp"] > current["required_xp"]
            ]
            if next_levels:
                next_lv = next_levels[0]
                xp = s.get("mastery_xp", 0)
                s["next_level"] = next_lv
                s["progress_to_next"] = min(
                    100,
                    int(
                        (xp - current["required_xp"])
                        / max(1, next_lv["required_xp"] - current["required_xp"])
                        * 100
                    ),
                )
            else:
                s["next_level"] = None
                s["progress_to_next"] = 100

        return skills

    async def get_quality_trend(self, user_id: int, days: int = 7) -> list[dict]:
        """品質トレンド"""
        return await self.repository.get_quality_trend(user_id, days)

    async def record_study_quality(self, user_id: int, category: str, minutes: int) -> int:
        """外部学習からの品質記録（gamificationフック用）: デフォルト品質"""
        if category not in SKILL_CATEGORIES:
            category = "general"
        # デフォルト品質（中程度）
        quality = self.calculate_quality(3, 3, 3)
        mastery_xp = self.calculate_mastery_xp(minutes, quality)
        skill = await self.repository.add_mastery_xp(user_id, category, mastery_xp)
        new_level = self.get_mastery_level(skill["mastery_xp"])
        avg = await self.repository.get_quality_average(user_id, category)
        await self.repository.upsert_skill(
            user_id,
            category,
            skill["mastery_xp"],
            new_level["level"],
            avg,
        )
        return mastery_xp

    # --- Eloレーティング ---

    async def get_rating(self, user_id: int, category: str) -> dict:
        """Eloレーティング取得"""
        rating = await self.repository.get_rating(user_id, category)
        if not rating:
            return {
                "user_id": user_id,
                "category": category,
                "rating": ELO_DEFAULT,
                "wins": 0,
                "losses": 0,
            }
        return rating

    async def update_elo(
        self,
        user_id: int,
        category: str,
        challenge_rating: int,
        won: bool,
    ) -> dict:
        """Eloレーティング更新"""
        current = await self.get_rating(user_id, category)
        user_rating = current["rating"]

        expected = 1 / (1 + 10 ** ((challenge_rating - user_rating) / 400))
        score = 1.0 if won else 0.0
        change = ELO_K * (score - expected)
        new_rating = max(100, int(user_rating + change))

        wins = current["wins"] + (1 if won else 0)
        losses = current["losses"] + (0 if won else 1)

        result = await self.repository.upsert_rating(user_id, category, new_rating, wins, losses)
        result["rating_change"] = new_rating - user_rating
        return result

    async def get_leaderboard(self, category: str, limit: int = 10) -> list[dict]:
        """レーティングリーダーボード"""
        return await self.repository.get_leaderboard(category, limit)

    async def get_profile(self, user_id: int) -> dict:
        """鍛冶プロフィール全体"""
        skills = await self.get_skills(user_id)
        logs = await self.repository.get_quality_logs(user_id, limit=5)
        overall_avg = await self.repository.get_quality_average(user_id)
        return {
            "skills": skills,
            "recent_logs": logs,
            "overall_quality_avg": overall_avg,
            "total_skills": len(skills),
        }

    # --- チャレンジシステム ---

    async def seed_challenges(self) -> int:
        """テンプレートからチャレンジを投入"""
        count = 0
        for tmpl in CHALLENGE_TEMPLATES:
            existing = await self.repository.list_challenges(tmpl["category"], limit=100)
            titles = {c["title"] for c in existing}
            if tmpl["title"] not in titles:
                await self.repository.create_challenge(
                    creator_id=0,
                    title=tmpl["title"],
                    description=tmpl["description"],
                    category=tmpl["category"],
                    difficulty_rating=tmpl["rating"],
                    is_template=True,
                )
                count += 1
        return count

    async def list_challenges(self, category: str = "") -> list[dict]:
        """チャレンジ一覧（成功率付き）"""
        challenges = await self.repository.list_challenges(category)
        for c in challenges:
            cat = c.get("category", "general")
            c["category_info"] = SKILL_CATEGORIES.get(cat, {"name": cat, "emoji": "📚"})
            attempts = c.get("attempt_count", 0)
            successes = c.get("success_count", 0)
            c["success_rate"] = int(successes / attempts * 100) if attempts > 0 else 0
        return challenges

    async def create_challenge(
        self, creator_id: int, title: str, description: str, category: str
    ) -> dict | None:
        """ユーザー作成チャレンジ"""
        if not title.strip():
            return None
        if category not in SKILL_CATEGORIES:
            return None
        return await self.repository.create_challenge(
            creator_id, title.strip(), description.strip(), category
        )

    async def attempt_challenge(self, user_id: int, challenge_id: int, passed: bool) -> dict | None:
        """チャレンジ挑戦処理"""
        challenge = await self.repository.get_challenge(challenge_id)
        if not challenge or not challenge.get("active"):
            return None

        category = challenge["category"]
        challenge_rating = challenge["difficulty_rating"]

        # ユーザーElo更新
        elo_result = await self.update_elo(user_id, category, challenge_rating, passed)
        user_rating_before = elo_result["rating"] - elo_result["rating_change"]

        # チャレンジElo逆方向更新
        ch_expected = 1 / (1 + 10 ** ((user_rating_before - challenge_rating) / 400))
        ch_score = 0.0 if passed else 1.0  # reversed
        ch_change = ELO_K * (ch_score - ch_expected)
        new_ch_rating = max(100, int(challenge_rating + ch_change))

        # DB更新
        await self.repository.update_challenge_stats(
            challenge_id, new_ch_rating, inc_attempts=True, inc_success=passed
        )
        await self.repository.create_challenge_attempt(
            challenge_id,
            user_id,
            passed,
            user_rating_before,
            elo_result["rating"],
            challenge_rating,
            new_ch_rating,
        )

        # マスタリーXP付与
        mastery_xp = 10 if passed else 3
        await self.repository.add_mastery_xp(user_id, category, mastery_xp)

        return {
            "challenge": challenge,
            "passed": passed,
            "user_rating": elo_result["rating"],
            "user_rating_change": elo_result["rating_change"],
            "challenge_rating": new_ch_rating,
            "challenge_rating_change": new_ch_rating - challenge_rating,
            "mastery_xp_gained": mastery_xp,
        }

    # --- ピアレビュー (The Crucible) ---

    async def submit_for_review(
        self, user_id: int, category: str, title: str, description: str
    ) -> dict | None:
        """作品をレビューに提出"""
        if category not in SKILL_CATEGORIES:
            return None
        if not title.strip() or not description.strip():
            return None
        return await self.repository.create_submission(
            user_id, category, title.strip(), description.strip()
        )

    async def claim_review(self, reviewer_id: int, submission_id: int) -> dict | None:
        """レビュー引き受け（自分の作品不可）"""
        submission = await self.repository.get_submission(submission_id)
        if not submission:
            return None
        if submission["user_id"] == reviewer_id:
            return None
        if submission["status"] != "open":
            return None
        claimed = await self.repository.claim_submission(submission_id, reviewer_id)
        if not claimed:
            return None
        return submission

    async def complete_review(
        self,
        reviewer_id: int,
        submission_id: int,
        quality_rating: int,
        feedback: str,
    ) -> dict | None:
        """レビュー完了 → 双方にXP付与"""
        submission = await self.repository.get_submission(submission_id)
        if not submission or submission["status"] != "claimed":
            return None

        review = await self.repository.create_review(
            submission_id, reviewer_id, quality_rating, feedback
        )

        # 提出者XP = quality_rating * 5 (5〜25)
        submitter_xp = quality_rating * 5
        category = submission["category"]
        await self.repository.add_mastery_xp(submission["user_id"], category, submitter_xp)

        # レビュアーXP = 10（固定）
        reviewer_xp = 10
        await self.repository.add_mastery_xp(reviewer_id, category, reviewer_xp)

        return {
            "review": review,
            "submitter_xp": submitter_xp,
            "reviewer_xp": reviewer_xp,
            "submission": submission,
        }

    # --- 相互連携メソッド ---

    def get_recommended_difficulty(self, energy: int, stress: int) -> str:
        """Sanctuary→Forge: ウェルネス状態から推奨難易度"""
        if energy <= 2 or stress >= 4:
            return "easy"
        if energy >= 4 and stress <= 2:
            return "hard"
        return "standard"

    async def get_mastery_level_for_category(self, user_id: int, category: str) -> int:
        """Forge→Expedition: カテゴリのマスタリーレベル取得"""
        skill = await self.repository.get_skill(user_id, category)
        if not skill:
            return 0
        return self.get_mastery_level(skill.get("mastery_xp", 0))["level"]
