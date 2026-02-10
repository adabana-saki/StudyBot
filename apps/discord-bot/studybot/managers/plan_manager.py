"""学習プラン ビジネスロジック"""

import json
import logging
import re

from studybot.repositories.plan_repository import PlanRepository
from studybot.services.openai_service import call_openai

logger = logging.getLogger(__name__)


class PlanManager:
    """学習プラン管理のビジネスロジック"""

    def __init__(self, db_pool) -> None:
        self.repository = PlanRepository(db_pool)

    async def create_plan(
        self,
        user_id: int,
        username: str,
        subject: str,
        goal: str,
        deadline=None,
    ) -> dict:
        """学習プランを作成（AIでタスクを自動生成）"""
        await self.repository.ensure_user(user_id, username)

        plan = await self.repository.create_plan(user_id, subject, goal, deadline)

        # AIでタスクを生成
        deadline_str = deadline.strftime("%Y-%m-%d") if deadline else "未設定"
        prompt = (
            "以下の学習目標に基づいて、具体的な学習プランを作成してください。\n"
            f"科目: {subject}\n"
            f"目標: {goal}\n"
            f"期限: {deadline_str}\n\n"
            "5-10個のステップに分解して、各ステップにタイトルと簡単な説明をつけてください。\n"
            'JSON形式で回答してください。形式: [{"title": "...", "description": "..."}]'
        )

        tasks_data = await self._generate_tasks(prompt)

        if tasks_data:
            for i, task in enumerate(tasks_data):
                await self.repository.add_task(
                    plan_id=plan["id"],
                    title=task.get("title", f"ステップ {i + 1}"),
                    description=task.get("description", ""),
                    order_index=i,
                )

        # プランとタスクを再取得
        result = await self.repository.get_plan_with_tasks(plan["id"])
        return result

    async def get_current_plan(self, user_id: int) -> dict | None:
        """現在のアクティブなプランをタスク付きで取得"""
        plan = await self.repository.get_active_plan(user_id)
        if not plan:
            return None

        return await self.repository.get_plan_with_tasks(plan["id"])

    async def complete_task(self, user_id: int, task_id: int) -> dict:
        """タスクを完了"""
        # アクティブプランを確認
        plan = await self.repository.get_active_plan(user_id)
        if not plan:
            return {"error": "アクティブな学習プランがありません。"}

        task = await self.repository.complete_task(task_id)
        if not task:
            return {"error": "タスクが見つからないか、既に完了しています。"}

        # 進捗を取得
        progress = await self.repository.get_plan_progress(plan["id"])
        return {"task": task, "progress": progress}

    async def get_progress_with_feedback(self, user_id: int) -> dict:
        """進捗を取得し、条件に応じてAIフィードバックを生成"""
        plan = await self.repository.get_active_plan(user_id)
        if not plan:
            return {"error": "アクティブな学習プランがありません。"}

        progress = await self.repository.get_plan_progress(plan["id"])

        # 50%以上でAIフィードバックがない場合、生成
        feedback = plan.get("ai_feedback")
        if progress["percentage"] >= 50 and not feedback:
            feedback = await self._generate_feedback(plan, progress)
            if feedback:
                await self.repository.update_ai_feedback(plan["id"], feedback)

        plan_with_tasks = await self.repository.get_plan_with_tasks(plan["id"])
        return {
            "plan": plan_with_tasks.get("plan", plan),
            "tasks": plan_with_tasks.get("tasks", []),
            "progress": progress,
            "feedback": feedback,
        }

    async def _generate_tasks(self, prompt: str) -> list[dict] | None:
        """AIでタスクリストを生成"""
        response = await call_openai(prompt, max_tokens=1200)
        if not response:
            return None

        try:
            # マークダウンコードフェンスを除去
            cleaned = re.sub(r"```(?:json)?\s*", "", response)
            cleaned = cleaned.strip().rstrip("`")
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"タスクJSON解析エラー: {e}")
            return None

    async def _generate_feedback(self, plan: dict, progress: dict) -> str | None:
        """AIで進捗フィードバックを生成"""
        prompt = (
            "以下の学習プランの進捗に対してフィードバックを提供してください。\n"
            f"科目: {plan['subject']}\n"
            f"目標: {plan['goal']}\n"
            f"進捗: {progress['completed']}/{progress['total']} "
            f"({progress['percentage']}%)\n\n"
            "励ましと、残りのタスクを効率的に進めるアドバイスを簡潔に述べてください。"
        )
        return await call_openai(prompt, max_tokens=500)
