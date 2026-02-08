"""ラーニングパス ビジネスロジック"""

import logging

from studybot.repositories.learning_path_repository import LearningPathRepository

logger = logging.getLogger(__name__)

# 定義済みラーニングパス
LEARNING_PATHS = {
    "math_basics": {
        "name": "数学基礎マスター",
        "emoji": "\U0001f522",
        "category": "math",
        "milestones": [
            {
                "title": "四則演算の復習",
                "description": "基本計算を30分学習",
                "target_minutes": 30,
            },
            {
                "title": "分数と小数",
                "description": "分数・小数の練習",
                "target_minutes": 60,
            },
            {
                "title": "方程式入門",
                "description": "一次方程式を解く",
                "target_minutes": 90,
            },
            {
                "title": "関数の基礎",
                "description": "関数のグラフを理解",
                "target_minutes": 120,
            },
            {
                "title": "まとめテスト",
                "description": "総復習と確認",
                "target_minutes": 60,
            },
        ],
        "reward_xp": 500,
        "reward_coins": 200,
    },
    "english_beginner": {
        "name": "英語初級コース",
        "emoji": "\U0001f1ec\U0001f1e7",
        "category": "english",
        "milestones": [
            {
                "title": "基本単語100",
                "description": "日常単語を覚える",
                "target_minutes": 45,
            },
            {
                "title": "文法の基礎",
                "description": "基本文法を学ぶ",
                "target_minutes": 60,
            },
            {
                "title": "リーディング練習",
                "description": "短い文章を読む",
                "target_minutes": 60,
            },
            {
                "title": "リスニング入門",
                "description": "音声教材で練習",
                "target_minutes": 45,
            },
            {
                "title": "会話フレーズ",
                "description": "日常会話を練習",
                "target_minutes": 60,
            },
        ],
        "reward_xp": 500,
        "reward_coins": 200,
    },
    "programming_intro": {
        "name": "プログラミング入門",
        "emoji": "\U0001f4bb",
        "category": "programming",
        "milestones": [
            {
                "title": "変数とデータ型",
                "description": "基本概念を学ぶ",
                "target_minutes": 45,
            },
            {
                "title": "条件分岐",
                "description": "if文を理解する",
                "target_minutes": 60,
            },
            {
                "title": "ループ処理",
                "description": "繰り返し処理を学ぶ",
                "target_minutes": 60,
            },
            {
                "title": "関数定義",
                "description": "関数を作る",
                "target_minutes": 90,
            },
            {
                "title": "ミニプロジェクト",
                "description": "簡単なプログラムを作成",
                "target_minutes": 120,
            },
        ],
        "reward_xp": 600,
        "reward_coins": 250,
    },
}


class LearningPathManager:
    """ラーニングパスの管理"""

    def __init__(self, db_pool) -> None:
        self.repository = LearningPathRepository(db_pool)

    def get_paths(self, category: str | None = None) -> list[dict]:
        """定義済みパス一覧を取得"""
        result = []
        for path_id, path_data in LEARNING_PATHS.items():
            if category and path_data["category"] != category:
                continue
            result.append(
                {
                    "path_id": path_id,
                    "name": path_data["name"],
                    "emoji": path_data["emoji"],
                    "category": path_data["category"],
                    "milestone_count": len(path_data["milestones"]),
                    "reward_xp": path_data["reward_xp"],
                    "reward_coins": path_data["reward_coins"],
                }
            )
        return result

    def get_path_definition(self, path_id: str) -> dict | None:
        """パス定義を取得"""
        return LEARNING_PATHS.get(path_id)

    async def enroll(self, user_id: int, username: str, path_id: str) -> dict:
        """ユーザーをパスに登録"""
        path_def = self.get_path_definition(path_id)
        if not path_def:
            return {"error": "指定されたパスが見つかりません"}

        await self.repository.ensure_user(user_id, username)

        existing = await self.repository.get_user_path(user_id, path_id)
        if existing:
            return {"error": "既にこのパスに登録済みです"}

        result = await self.repository.enroll_user(user_id, path_id)
        if "error" in result:
            return result

        return {
            "path_id": path_id,
            "name": path_def["name"],
            "emoji": path_def["emoji"],
            "milestone_count": len(path_def["milestones"]),
        }

    async def get_progress(self, user_id: int, path_id: str) -> dict:
        """パスの進捗を取得"""
        path_def = self.get_path_definition(path_id)
        if not path_def:
            return {"error": "指定されたパスが見つかりません"}

        enrollment = await self.repository.get_user_path(user_id, path_id)
        if not enrollment:
            return {"error": "このパスに登録していません"}

        progress = await self.repository.get_path_progress(user_id, path_id)
        total = len(path_def["milestones"])
        completed = progress["completed"]

        milestones_info = []
        for i, ms in enumerate(path_def["milestones"]):
            milestones_info.append(
                {
                    "index": i,
                    "title": ms["title"],
                    "description": ms["description"],
                    "target_minutes": ms["target_minutes"],
                    "completed": i < completed,
                    "current": i == completed and not enrollment["completed"],
                }
            )

        return {
            "path_id": path_id,
            "name": path_def["name"],
            "emoji": path_def["emoji"],
            "completed_count": completed,
            "total": total,
            "path_completed": enrollment["completed"],
            "milestones": milestones_info,
            "reward_xp": path_def["reward_xp"],
            "reward_coins": path_def["reward_coins"],
        }

    async def get_user_paths_progress(self, user_id: int) -> list[dict]:
        """ユーザーの全パス進捗を取得"""
        enrollments = await self.repository.get_user_paths(user_id)
        results = []
        for enrollment in enrollments:
            path_id = enrollment["path_id"]
            path_def = self.get_path_definition(path_id)
            if not path_def:
                continue

            progress = await self.repository.get_path_progress(user_id, path_id)
            total = len(path_def["milestones"])
            completed = progress["completed"]

            results.append(
                {
                    "path_id": path_id,
                    "name": path_def["name"],
                    "emoji": path_def["emoji"],
                    "completed_count": completed,
                    "total": total,
                    "path_completed": enrollment["completed"],
                }
            )
        return results

    async def complete_current_milestone(self, user_id: int, path_id: str) -> dict:
        """現在のマイルストーンを完了"""
        path_def = self.get_path_definition(path_id)
        if not path_def:
            return {"error": "指定されたパスが見つかりません"}

        enrollment = await self.repository.get_user_path(user_id, path_id)
        if not enrollment:
            return {"error": "このパスに登録していません"}

        if enrollment["completed"]:
            return {"error": "このパスは既に完了しています"}

        current_idx = enrollment["current_milestone"]
        milestones = path_def["milestones"]
        total = len(milestones)

        if current_idx >= total:
            return {"error": "全てのマイルストーンを完了済みです"}

        result = await self.repository.complete_milestone(user_id, path_id, current_idx)
        if "error" in result:
            return result

        milestone = milestones[current_idx]
        is_path_complete = (current_idx + 1) >= total

        if is_path_complete:
            await self.repository.mark_path_completed(user_id, path_id)

        return {
            "path_id": path_id,
            "path_name": path_def["name"],
            "milestone_title": milestone["title"],
            "milestone_index": current_idx,
            "completed_count": current_idx + 1,
            "total": total,
            "path_completed": is_path_complete,
            "reward_xp": path_def["reward_xp"] if is_path_complete else 0,
            "reward_coins": path_def["reward_coins"] if is_path_complete else 0,
        }
