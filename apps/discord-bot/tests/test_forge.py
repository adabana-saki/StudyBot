"""フォージ（熟練の鍛冶場）のテスト"""

import pytest

from studybot.managers.forge_manager import (
    CHALLENGE_TEMPLATES,
    DIFFICULTY_SCORES,
    ELO_DEFAULT,
    ELO_K,
    MASTERY_LEVELS,
    SKILL_CATEGORIES,
    ForgeManager,
)


@pytest.fixture
def forge_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = ForgeManager(pool)
    return manager, conn


# --- 品質スコア計算テスト ---


class TestQualityCalculation:
    def test_perfect_scores(self, forge_manager):
        manager, _ = forge_manager
        quality = manager.calculate_quality(5, 3, 5)
        # focus=1.0*0.4 + diff=1.0*0.3 + progress=1.0*0.3 = 1.0 * 100
        assert quality == 100.0

    def test_minimum_scores(self, forge_manager):
        manager, _ = forge_manager
        quality = manager.calculate_quality(1, 1, 1)
        # focus=0.2*0.4 + diff=0.4*0.3 + progress=0.2*0.3
        expected = (0.2 * 0.4 + 0.4 * 0.3 + 0.2 * 0.3) * 100
        assert quality == pytest.approx(expected)

    def test_optimal_difficulty(self, forge_manager):
        manager, _ = forge_manager
        q3 = manager.calculate_quality(3, 3, 3)
        q4 = manager.calculate_quality(3, 4, 3)
        # difficulty 3 and 4 both map to 1.0
        assert q3 == q4

    def test_too_high_difficulty_penalty(self, forge_manager):
        manager, _ = forge_manager
        q4 = manager.calculate_quality(3, 4, 3)
        q5 = manager.calculate_quality(3, 5, 3)
        # difficulty 5 maps to 0.8 (penalty)
        assert q5 < q4

    def test_clamping(self, forge_manager):
        manager, _ = forge_manager
        quality = manager.calculate_quality(0, 0, 0)  # Below min
        # Should clamp to 1
        expected = (1 / 5.0 * 0.4 + DIFFICULTY_SCORES[1] * 0.3 + 1 / 5.0 * 0.3) * 100
        assert quality == pytest.approx(expected)

    def test_clamping_above_max(self, forge_manager):
        manager, _ = forge_manager
        quality = manager.calculate_quality(10, 10, 10)  # Above max
        # Should clamp to 5
        expected = (5 / 5.0 * 0.4 + DIFFICULTY_SCORES[5] * 0.3 + 5 / 5.0 * 0.3) * 100
        assert quality == pytest.approx(expected)


# --- マスタリーXP計算テスト ---


class TestMasteryXP:
    def test_basic_mastery_xp(self, forge_manager):
        manager, _ = forge_manager
        xp = manager.calculate_mastery_xp(30, 100)
        # 30 * (0.5 + 100/100) = 30 * 1.5 = 45
        assert xp == 45

    def test_low_quality_mastery_xp(self, forge_manager):
        manager, _ = forge_manager
        xp = manager.calculate_mastery_xp(30, 0)
        # 30 * (0.5 + 0/100) = 30 * 0.5 = 15
        assert xp == 15

    def test_minimum_xp(self, forge_manager):
        manager, _ = forge_manager
        xp = manager.calculate_mastery_xp(1, 0)
        # max(1, 1 * 0.5) = 1
        assert xp >= 1

    def test_long_session_high_quality(self, forge_manager):
        manager, _ = forge_manager
        xp = manager.calculate_mastery_xp(60, 100)
        # 60 * 1.5 = 90
        assert xp == 90


# --- マスタリーレベルテスト ---


class TestMasteryLevel:
    def test_level_zero(self, forge_manager):
        manager, _ = forge_manager
        level = manager.get_mastery_level(0)
        assert level["level"] == 0
        assert level["name"] == "未着手"

    def test_level_beginner(self, forge_manager):
        manager, _ = forge_manager
        level = manager.get_mastery_level(100)
        assert level["level"] == 1
        assert level["name"] == "初心者"

    def test_level_apprentice(self, forge_manager):
        manager, _ = forge_manager
        level = manager.get_mastery_level(500)
        assert level["level"] == 2
        assert level["name"] == "見習い"

    def test_level_craftsman(self, forge_manager):
        manager, _ = forge_manager
        level = manager.get_mastery_level(1500)
        assert level["level"] == 3
        assert level["name"] == "職人"

    def test_level_expert(self, forge_manager):
        manager, _ = forge_manager
        level = manager.get_mastery_level(4000)
        assert level["level"] == 4
        assert level["name"] == "熟練者"

    def test_level_master(self, forge_manager):
        manager, _ = forge_manager
        level = manager.get_mastery_level(10000)
        assert level["level"] == 5
        assert level["name"] == "マスター"

    def test_level_between(self, forge_manager):
        manager, _ = forge_manager
        level = manager.get_mastery_level(300)
        assert level["level"] == 1  # 100-499 = beginner


# --- 練習ログテスト ---


class TestPracticeLogging:
    @pytest.mark.asyncio
    async def test_log_practice_success(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.side_effect = [
            # log_quality
            {"id": 1, "user_id": 123, "category": "math", "quality_score": 80},
            # add_mastery_xp
            {
                "id": 1,
                "user_id": 123,
                "category": "math",
                "mastery_xp": 45,
                "mastery_level": 0,
                "quality_avg": 0,
            },
            # upsert_skill
            {
                "id": 1,
                "user_id": 123,
                "category": "math",
                "mastery_xp": 45,
                "mastery_level": 0,
                "quality_avg": 80,
            },
        ]
        conn.fetchval.return_value = 80.0  # quality average

        result = await manager.log_practice(123, "math", 4, 3, 4, 30)
        assert result["quality_score"] > 0
        assert result["mastery_xp_gained"] > 0

    @pytest.mark.asyncio
    async def test_log_practice_unknown_category(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.side_effect = [
            {"id": 1, "user_id": 123, "category": "general", "quality_score": 60},
            {
                "id": 1,
                "user_id": 123,
                "category": "general",
                "mastery_xp": 20,
                "mastery_level": 0,
                "quality_avg": 0,
            },
            {
                "id": 1,
                "user_id": 123,
                "category": "general",
                "mastery_xp": 20,
                "mastery_level": 0,
                "quality_avg": 60,
            },
        ]
        conn.fetchval.return_value = 60.0

        result = await manager.log_practice(123, "unknown", 3, 3, 3, 30)
        assert result is not None  # defaults to "general"

    @pytest.mark.asyncio
    async def test_log_practice_level_up(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.side_effect = [
            {"id": 1, "user_id": 123, "category": "math", "quality_score": 90},
            # add_mastery_xp -> now at 100+ (level 1 threshold)
            {
                "id": 1,
                "user_id": 123,
                "category": "math",
                "mastery_xp": 120,
                "mastery_level": 0,
                "quality_avg": 0,
            },
            {
                "id": 1,
                "user_id": 123,
                "category": "math",
                "mastery_xp": 120,
                "mastery_level": 1,
                "quality_avg": 90,
            },
        ]
        conn.fetchval.return_value = 90.0

        result = await manager.log_practice(123, "math", 5, 3, 5, 60)
        assert result["leveled_up"] is True
        assert result["mastery_level"]["level"] == 1


# --- スキル表示テスト ---


class TestSkillDisplay:
    @pytest.mark.asyncio
    async def test_get_skills_empty(self, forge_manager):
        manager, conn = forge_manager
        conn.fetch.return_value = []

        skills = await manager.get_skills(123)
        assert skills == []

    @pytest.mark.asyncio
    async def test_get_skills_with_data(self, forge_manager):
        manager, conn = forge_manager
        conn.fetch.return_value = [
            {
                "user_id": 123,
                "category": "math",
                "mastery_xp": 500,
                "mastery_level": 2,
                "quality_avg": 75.0,
            },
        ]

        skills = await manager.get_skills(123)
        assert len(skills) == 1
        assert skills[0]["level_info"]["name"] == "見習い"
        assert skills[0]["category_info"]["name"] == "数学"

    @pytest.mark.asyncio
    async def test_get_skills_progress_to_next(self, forge_manager):
        manager, conn = forge_manager
        conn.fetch.return_value = [
            {
                "user_id": 123,
                "category": "math",
                "mastery_xp": 300,
                "mastery_level": 1,
                "quality_avg": 70.0,
            },
        ]

        skills = await manager.get_skills(123)
        assert skills[0]["next_level"] is not None
        assert 0 <= skills[0]["progress_to_next"] <= 100

    @pytest.mark.asyncio
    async def test_get_skills_by_category(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.return_value = {
            "user_id": 123,
            "category": "math",
            "mastery_xp": 200,
            "mastery_level": 1,
            "quality_avg": 65.0,
        }

        skills = await manager.get_skills(123, "math")
        assert len(skills) == 1


# --- Eloレーティングテスト ---


class TestEloRating:
    @pytest.mark.asyncio
    async def test_get_default_rating(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.return_value = None

        rating = await manager.get_rating(123, "math")
        assert rating["rating"] == ELO_DEFAULT
        assert rating["wins"] == 0

    @pytest.mark.asyncio
    async def test_update_elo_win(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.side_effect = [
            None,  # get_rating (default)
            {
                "user_id": 123,
                "category": "math",
                "rating": 1216,
                "wins": 1,
                "losses": 0,
            },  # upsert_rating
        ]

        result = await manager.update_elo(123, "math", 1200, won=True)
        assert result["rating_change"] > 0
        assert result["wins"] == 1

    @pytest.mark.asyncio
    async def test_update_elo_loss(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.side_effect = [
            None,  # get_rating (default)
            {
                "user_id": 123,
                "category": "math",
                "rating": 1184,
                "wins": 0,
                "losses": 1,
            },  # upsert_rating
        ]

        result = await manager.update_elo(123, "math", 1200, won=False)
        assert result["rating_change"] < 0
        assert result["losses"] == 1

    @pytest.mark.asyncio
    async def test_update_elo_upset_win(self, forge_manager):
        """弱い側が強い相手に勝つと大きなレーティング変動"""
        manager, conn = forge_manager
        conn.fetchrow.side_effect = [
            {
                "user_id": 123,
                "category": "math",
                "rating": 1000,
                "wins": 0,
                "losses": 0,
            },  # get_rating
            {
                "user_id": 123,
                "category": "math",
                "rating": 1028,
                "wins": 1,
                "losses": 0,
            },  # upsert_rating
        ]

        result = await manager.update_elo(123, "math", 1400, won=True)
        assert result["rating_change"] > 16  # More than K/2


# --- 品質トレンドテスト ---


class TestQualityTrend:
    @pytest.mark.asyncio
    async def test_get_quality_trend_empty(self, forge_manager):
        manager, conn = forge_manager
        conn.fetch.return_value = []

        trend = await manager.get_quality_trend(123)
        assert trend == []

    @pytest.mark.asyncio
    async def test_get_quality_trend_with_data(self, forge_manager):
        manager, conn = forge_manager
        conn.fetch.return_value = [
            {"day": "2026-02-20", "avg_quality": 75.0, "sessions": 3},
            {"day": "2026-02-21", "avg_quality": 80.0, "sessions": 2},
        ]

        trend = await manager.get_quality_trend(123, 7)
        assert len(trend) == 2


# --- プロフィールテスト ---


class TestProfile:
    @pytest.mark.asyncio
    async def test_get_profile(self, forge_manager):
        manager, conn = forge_manager
        conn.fetch.side_effect = [
            # get_all_skills
            [
                {
                    "user_id": 123,
                    "category": "math",
                    "mastery_xp": 500,
                    "mastery_level": 2,
                    "quality_avg": 75.0,
                },
            ],
            # get_quality_logs
            [
                {
                    "id": 1,
                    "category": "math",
                    "focus": 4,
                    "difficulty": 3,
                    "progress": 4,
                    "quality_score": 80.0,
                    "duration_minutes": 30,
                    "logged_at": "2026-02-21",
                },
            ],
        ]
        conn.fetchval.return_value = 77.5  # overall quality avg

        profile = await manager.get_profile(123)
        assert profile["total_skills"] == 1
        assert len(profile["recent_logs"]) == 1
        assert profile["overall_quality_avg"] == pytest.approx(77.5)


# --- 外部連携テスト ---


class TestExternalIntegration:
    @pytest.mark.asyncio
    async def test_record_study_quality(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.side_effect = [
            # add_mastery_xp
            {
                "id": 1,
                "user_id": 123,
                "category": "math",
                "mastery_xp": 20,
                "mastery_level": 0,
                "quality_avg": 0,
            },
            # upsert_skill
            {
                "id": 1,
                "user_id": 123,
                "category": "math",
                "mastery_xp": 20,
                "mastery_level": 0,
                "quality_avg": 63.0,
            },
        ]
        conn.fetchval.return_value = 63.0

        xp = await manager.record_study_quality(123, "math", 30)
        assert xp > 0

    @pytest.mark.asyncio
    async def test_record_study_quality_unknown_category(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.side_effect = [
            {
                "id": 1,
                "user_id": 123,
                "category": "general",
                "mastery_xp": 20,
                "mastery_level": 0,
                "quality_avg": 0,
            },
            {
                "id": 1,
                "user_id": 123,
                "category": "general",
                "mastery_xp": 20,
                "mastery_level": 0,
                "quality_avg": 63.0,
            },
        ]
        conn.fetchval.return_value = 63.0

        xp = await manager.record_study_quality(123, "unknown_category", 30)
        assert xp > 0  # Should default to "general"


# --- 定数テスト ---


class TestConstants:
    def test_mastery_levels_ordered(self):
        prev_xp = -1
        for ml in MASTERY_LEVELS:
            assert ml["required_xp"] > prev_xp
            prev_xp = ml["required_xp"]

    def test_skill_categories_defined(self):
        assert len(SKILL_CATEGORIES) >= 8
        for _key, val in SKILL_CATEGORIES.items():
            assert "name" in val
            assert "emoji" in val

    def test_difficulty_scores_defined(self):
        for i in range(1, 6):
            assert i in DIFFICULTY_SCORES

    def test_elo_constants(self):
        assert ELO_K == 32
        assert ELO_DEFAULT == 1200

    def test_challenge_templates_defined(self):
        assert len(CHALLENGE_TEMPLATES) >= 10
        for tmpl in CHALLENGE_TEMPLATES:
            assert "title" in tmpl
            assert "description" in tmpl
            assert "category" in tmpl
            assert "rating" in tmpl
            assert tmpl["category"] in SKILL_CATEGORIES


# --- チャレンジシステムテスト ---


class TestChallengeSystem:
    @pytest.mark.asyncio
    async def test_list_challenges_empty(self, forge_manager):
        manager, conn = forge_manager
        conn.fetch.return_value = []

        challenges = await manager.list_challenges()
        assert challenges == []

    @pytest.mark.asyncio
    async def test_list_challenges_with_data(self, forge_manager):
        manager, conn = forge_manager
        conn.fetch.return_value = [
            {
                "id": 1,
                "title": "基本計算",
                "description": "四則演算",
                "category": "math",
                "difficulty_rating": 1000,
                "attempt_count": 10,
                "success_count": 7,
                "active": True,
            },
        ]

        challenges = await manager.list_challenges()
        assert len(challenges) == 1
        assert challenges[0]["success_rate"] == 70
        assert challenges[0]["category_info"]["name"] == "数学"

    @pytest.mark.asyncio
    async def test_list_challenges_by_category(self, forge_manager):
        manager, conn = forge_manager
        conn.fetch.return_value = [
            {
                "id": 1,
                "title": "英文法",
                "description": "文法問題",
                "category": "english",
                "difficulty_rating": 1000,
                "attempt_count": 0,
                "success_count": 0,
                "active": True,
            },
        ]

        challenges = await manager.list_challenges("english")
        assert len(challenges) == 1

    @pytest.mark.asyncio
    async def test_attempt_challenge_pass(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.side_effect = [
            # get_challenge
            {
                "id": 1,
                "title": "テスト",
                "category": "math",
                "difficulty_rating": 1200,
                "active": True,
            },
            # update_elo -> get_rating (None = default)
            None,
            # update_elo -> upsert_rating
            {"user_id": 123, "category": "math", "rating": 1216, "wins": 1, "losses": 0},
            # create_challenge_attempt
            {"id": 1, "challenge_id": 1, "user_id": 123, "passed": True},
            # add_mastery_xp
            {"user_id": 123, "category": "math", "mastery_xp": 10},
        ]
        conn.execute.return_value = None

        result = await manager.attempt_challenge(123, 1, True)
        assert result is not None
        assert result["passed"] is True
        assert result["mastery_xp_gained"] == 10
        assert result["user_rating_change"] > 0

    @pytest.mark.asyncio
    async def test_attempt_challenge_fail(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.side_effect = [
            # get_challenge
            {
                "id": 1,
                "title": "テスト",
                "category": "math",
                "difficulty_rating": 1200,
                "active": True,
            },
            # update_elo -> get_rating
            None,
            # update_elo -> upsert_rating
            {"user_id": 123, "category": "math", "rating": 1184, "wins": 0, "losses": 1},
            # create_challenge_attempt
            {"id": 1, "challenge_id": 1, "user_id": 123, "passed": False},
            # add_mastery_xp
            {"user_id": 123, "category": "math", "mastery_xp": 3},
        ]
        conn.execute.return_value = None

        result = await manager.attempt_challenge(123, 1, False)
        assert result is not None
        assert result["passed"] is False
        assert result["mastery_xp_gained"] == 3
        assert result["user_rating_change"] < 0

    @pytest.mark.asyncio
    async def test_attempt_nonexistent_challenge(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.return_value = None

        result = await manager.attempt_challenge(123, 999, True)
        assert result is None

    @pytest.mark.asyncio
    async def test_attempt_inactive_challenge(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.return_value = {
            "id": 1,
            "title": "テスト",
            "category": "math",
            "difficulty_rating": 1200,
            "active": False,
        }

        result = await manager.attempt_challenge(123, 1, True)
        assert result is None

    @pytest.mark.asyncio
    async def test_create_challenge_valid(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.return_value = {
            "id": 1,
            "creator_id": 123,
            "title": "新チャレンジ",
            "description": "説明",
            "category": "math",
        }

        result = await manager.create_challenge(123, "新チャレンジ", "説明", "math")
        assert result is not None
        assert result["title"] == "新チャレンジ"

    def test_create_challenge_invalid_category(self, forge_manager):
        import asyncio

        manager, conn = forge_manager
        result = asyncio.get_event_loop().run_until_complete(
            manager.create_challenge(123, "テスト", "説明", "invalid_cat")
        )
        assert result is None

    def test_create_challenge_empty_title(self, forge_manager):
        import asyncio

        manager, conn = forge_manager
        result = asyncio.get_event_loop().run_until_complete(
            manager.create_challenge(123, "", "説明", "math")
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_seed_challenges(self, forge_manager):
        manager, conn = forge_manager
        conn.fetch.return_value = []  # list_challenges returns empty each time
        conn.fetchrow.return_value = {"id": 1}  # create_challenge

        count = await manager.seed_challenges()
        assert count == len(CHALLENGE_TEMPLATES)


# --- ピアレビュー (The Crucible) テスト ---


class TestCrucible:
    @pytest.mark.asyncio
    async def test_submit_for_review(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.return_value = {
            "id": 1,
            "user_id": 123,
            "category": "math",
            "title": "数学レポート",
            "description": "証明問題",
            "status": "open",
        }

        result = await manager.submit_for_review(123, "math", "数学レポート", "証明問題")
        assert result is not None
        assert result["title"] == "数学レポート"

    @pytest.mark.asyncio
    async def test_submit_invalid_category(self, forge_manager):
        manager, conn = forge_manager
        result = await manager.submit_for_review(123, "invalid", "テスト", "説明")
        assert result is None

    @pytest.mark.asyncio
    async def test_claim_success(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.return_value = {
            "id": 1,
            "user_id": 111,
            "category": "math",
            "title": "テスト",
            "status": "open",
        }
        conn.execute.return_value = "UPDATE 1"

        result = await manager.claim_review(222, 1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_claim_own_submission(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.return_value = {
            "id": 1,
            "user_id": 123,
            "category": "math",
            "title": "テスト",
            "status": "open",
        }

        result = await manager.claim_review(123, 1)
        assert result is None

    @pytest.mark.asyncio
    async def test_claim_already_claimed(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.return_value = {
            "id": 1,
            "user_id": 111,
            "category": "math",
            "title": "テスト",
            "status": "claimed",
        }

        result = await manager.claim_review(222, 1)
        assert result is None

    @pytest.mark.asyncio
    async def test_complete_review_success(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.side_effect = [
            # get_submission
            {
                "id": 1,
                "user_id": 111,
                "category": "math",
                "title": "テスト",
                "status": "claimed",
            },
            # create_review
            {"id": 1, "submission_id": 1, "reviewer_id": 222, "quality_rating": 4},
            # add_mastery_xp (submitter)
            {"user_id": 111, "category": "math", "mastery_xp": 20},
            # add_mastery_xp (reviewer)
            {"user_id": 222, "category": "math", "mastery_xp": 10},
        ]
        conn.execute.return_value = None

        result = await manager.complete_review(222, 1, 4, "よくできました")
        assert result is not None
        assert result["submitter_xp"] == 20  # 4 * 5
        assert result["reviewer_xp"] == 10

    @pytest.mark.asyncio
    async def test_complete_review_unclaimed(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.return_value = {
            "id": 1,
            "user_id": 111,
            "category": "math",
            "title": "テスト",
            "status": "open",
        }

        result = await manager.complete_review(222, 1, 3, "フィードバック")
        assert result is None

    @pytest.mark.asyncio
    async def test_submitter_xp_scales_with_rating(self, forge_manager):
        """提出者XPはquality_ratingに比例 (rating * 5)"""
        manager, conn = forge_manager

        for rating in [1, 3, 5]:
            conn.fetchrow.side_effect = [
                {
                    "id": 1,
                    "user_id": 111,
                    "category": "math",
                    "title": "テスト",
                    "status": "claimed",
                },
                {"id": 1, "submission_id": 1, "reviewer_id": 222, "quality_rating": rating},
                {"user_id": 111, "category": "math", "mastery_xp": rating * 5},
                {"user_id": 222, "category": "math", "mastery_xp": 10},
            ]
            conn.execute.return_value = None

            result = await manager.complete_review(222, 1, rating, "FB")
            assert result["submitter_xp"] == rating * 5

    @pytest.mark.asyncio
    async def test_reviewer_flat_xp(self, forge_manager):
        """レビュアーXPは常に10固定"""
        manager, conn = forge_manager
        conn.fetchrow.side_effect = [
            {
                "id": 1,
                "user_id": 111,
                "category": "math",
                "title": "テスト",
                "status": "claimed",
            },
            {"id": 1, "submission_id": 1, "reviewer_id": 222, "quality_rating": 5},
            {"user_id": 111, "category": "math", "mastery_xp": 25},
            {"user_id": 222, "category": "math", "mastery_xp": 10},
        ]
        conn.execute.return_value = None

        result = await manager.complete_review(222, 1, 5, "素晴らしい")
        assert result["reviewer_xp"] == 10


# --- 相互連携テスト ---


class TestCrossConcept:
    def test_recommended_difficulty_high_energy(self, forge_manager):
        manager, _ = forge_manager
        assert manager.get_recommended_difficulty(5, 1) == "hard"

    def test_recommended_difficulty_standard(self, forge_manager):
        manager, _ = forge_manager
        assert manager.get_recommended_difficulty(3, 3) == "standard"

    def test_recommended_difficulty_tired(self, forge_manager):
        manager, _ = forge_manager
        assert manager.get_recommended_difficulty(2, 4) == "easy"

    def test_recommended_difficulty_low_energy(self, forge_manager):
        manager, _ = forge_manager
        assert manager.get_recommended_difficulty(1, 2) == "easy"

    def test_recommended_difficulty_high_stress(self, forge_manager):
        manager, _ = forge_manager
        assert manager.get_recommended_difficulty(3, 5) == "easy"

    @pytest.mark.asyncio
    async def test_mastery_level_no_data(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.return_value = None

        level = await manager.get_mastery_level_for_category(123, "math")
        assert level == 0

    @pytest.mark.asyncio
    async def test_mastery_level_with_data(self, forge_manager):
        manager, conn = forge_manager
        conn.fetchrow.return_value = {
            "user_id": 123,
            "category": "math",
            "mastery_xp": 1500,
            "mastery_level": 3,
            "quality_avg": 80.0,
        }

        level = await manager.get_mastery_level_for_category(123, "math")
        assert level == 3
