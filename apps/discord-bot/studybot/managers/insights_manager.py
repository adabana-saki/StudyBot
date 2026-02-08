"""AI インサイト ビジネスロジック"""

import json
import logging
from datetime import date, timedelta

from studybot.config.settings import settings
from studybot.repositories.insights_repository import InsightsRepository
from studybot.services.openai_service import call_openai

logger = logging.getLogger(__name__)


class InsightsManager:
    """AI週次インサイトの管理"""

    def __init__(self, db_pool) -> None:
        self.repository = InsightsRepository(db_pool)

    async def generate_insights(self, user_id: int) -> dict:
        """ユーザーの週次インサイトを生成"""
        raw_data = await self.repository.get_weekly_study_data(user_id, days=7)

        # データが不十分な場合
        total_logs = len(raw_data.get("study_logs", [])) + len(
            raw_data.get("pomodoro_sessions", [])
        )
        if total_logs == 0:
            return {"error": "この週の学習データが不足しています"}

        # 統計を計算
        stats = self._compute_stats(raw_data)

        # OpenAI でインサイト生成
        insights = await self._generate_with_ai(stats)
        if not insights:
            insights = self._generate_fallback(stats)

        summary = self._build_summary(stats, insights)

        # 保存
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_end = week_start + timedelta(days=6)

        report_id = await self.repository.save_report(
            user_id,
            week_start,
            week_end,
            stats,
            insights,
            summary,
        )
        await self.repository.save_insights(user_id, insights)

        return {
            "report_id": report_id,
            "summary": summary,
            "insights": insights,
            "stats": stats,
        }

    def _compute_stats(self, raw_data: dict) -> dict:
        """生データから統計を計算"""
        study_logs = raw_data.get("study_logs", [])
        pomodoro = raw_data.get("pomodoro_sessions", [])
        wellness = raw_data.get("wellness_logs", [])
        todos = raw_data.get("todos", [])
        flashcards = raw_data.get("flashcard_reviews", [])
        focus = raw_data.get("focus_sessions", [])

        total_study_minutes = sum(entry.get("duration_minutes", 0) for entry in study_logs)
        total_pomodoro_minutes = sum((s.get("total_work_seconds", 0) // 60) for s in pomodoro)

        # 時間帯分布
        hour_dist = [0] * 24
        for entry in study_logs:
            if entry.get("logged_at"):
                h = entry["logged_at"].hour if hasattr(entry["logged_at"], "hour") else 0
                hour_dist[h] += entry.get("duration_minutes", 0)

        # ウェルネス平均
        avg_mood = sum(w.get("mood", 3) for w in wellness) / max(len(wellness), 1)
        avg_energy = sum(w.get("energy", 3) for w in wellness) / max(len(wellness), 1)
        avg_stress = sum(w.get("stress", 3) for w in wellness) / max(len(wellness), 1)

        # タスク完了率
        completed_todos = sum(1 for t in todos if t.get("status") == "completed")
        total_todos = len(todos)

        # フラッシュカード正答率
        correct_reviews = sum(1 for f in flashcards if f.get("quality", 0) >= 3)
        total_reviews = len(flashcards)

        # フォーカス完了率
        completed_focus = sum(1 for f in focus if f.get("state") == "completed")
        total_focus = len(focus)

        return {
            "total_study_minutes": total_study_minutes,
            "total_pomodoro_minutes": total_pomodoro_minutes,
            "total_combined_minutes": total_study_minutes + total_pomodoro_minutes,
            "study_sessions": len(study_logs),
            "pomodoro_sessions": len(pomodoro),
            "hour_distribution": hour_dist,
            "avg_mood": round(avg_mood, 1),
            "avg_energy": round(avg_energy, 1),
            "avg_stress": round(avg_stress, 1),
            "wellness_entries": len(wellness),
            "todo_completed": completed_todos,
            "todo_total": total_todos,
            "todo_completion_rate": round(completed_todos / max(total_todos, 1) * 100),
            "flashcard_correct": correct_reviews,
            "flashcard_total": total_reviews,
            "flashcard_accuracy": round(correct_reviews / max(total_reviews, 1) * 100),
            "focus_completed": completed_focus,
            "focus_total": total_focus,
            "focus_completion_rate": round(completed_focus / max(total_focus, 1) * 100),
        }

    async def _generate_with_ai(self, stats: dict) -> list[dict]:
        """OpenAI でインサイトを生成"""
        if not settings.OPENAI_API_KEY:
            return []

        try:
            insight_format = (
                '{"type": "pattern|improvement|achievement|warning",'
                ' "title": "短いタイトル",'
                ' "body": "1-2文の説明",'
                ' "confidence": 0.0-1.0}'
            )
            mood = stats["avg_mood"]
            energy = stats["avg_energy"]
            stress = stats["avg_stress"]
            fc_acc = stats["flashcard_accuracy"]
            fc_correct = stats["flashcard_correct"]
            fc_total = stats["flashcard_total"]
            prompt = (
                "以下の学習データから3〜5個のインサイトを"
                "JSON配列で返してください。\n"
                f"各インサイトは {insight_format} の形式です。\n\n"
                "学習データ:\n"
                f"- 総学習時間: {stats['total_combined_minutes']}分\n"
                f"- ポモドーロ: {stats['pomodoro_sessions']}セッション\n"
                f"- 気分平均: {mood}/5,"
                f" エネルギー: {energy}/5,"
                f" ストレス: {stress}/5\n"
                f"- タスク完了率: {stats['todo_completion_rate']}%"
                f" ({stats['todo_completed']}/{stats['todo_total']})\n"
                f"- フラッシュカード正答率: {fc_acc}%"
                f" ({fc_correct}/{fc_total})\n"
                f"- フォーカス完了率: {stats['focus_completion_rate']}%\n"
                f"- 時間帯分布(0-23h): {stats['hour_distribution']}\n\n"
                "JSONのみを返してください。"
            )

            content = await call_openai(
                prompt,
                system_prompt="あなたは学習データ分析の専門家です。",
                max_tokens=800,
                temperature=0.7,
            )
            if not content:
                return []

            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(content)

        except Exception as e:
            logger.warning(f"OpenAI インサイト生成失敗: {e}")
            return []

    def _generate_fallback(self, stats: dict) -> list[dict]:
        """AI使用不可時のフォールバックインサイト"""
        insights = []

        total = stats["total_combined_minutes"]
        if total > 300:
            insights.append(
                {
                    "type": "achievement",
                    "title": "素晴らしい学習量！",
                    "body": f"今週{total}分（{total // 60}時間）学習しました。",
                    "confidence": 0.9,
                }
            )
        elif total > 0:
            insights.append(
                {
                    "type": "improvement",
                    "title": "学習習慣を構築中",
                    "body": f"今週{total}分学習しました。少しずつ増やしていきましょう。",
                    "confidence": 0.7,
                }
            )

        if stats["avg_stress"] > 3.5:
            insights.append(
                {
                    "type": "warning",
                    "title": "ストレスレベルに注意",
                    "body": "ストレスが高めです。休憩を取ることも大切です。",
                    "confidence": 0.6,
                }
            )

        if stats["todo_completion_rate"] >= 80:
            insights.append(
                {
                    "type": "achievement",
                    "title": "タスク管理が優秀",
                    "body": f"タスク完了率{stats['todo_completion_rate']}%！素晴らしいです。",
                    "confidence": 0.85,
                }
            )

        # 時間帯分析
        hour_dist = stats.get("hour_distribution", [0] * 24)
        morning = sum(hour_dist[6:12])
        afternoon = sum(hour_dist[12:18])
        evening = sum(hour_dist[18:24])
        if morning > afternoon and morning > evening:
            insights.append(
                {
                    "type": "pattern",
                    "title": "朝型学習パターン",
                    "body": "午前中に最も多く学習しています。この時間帯を活用しましょう。",
                    "confidence": 0.7,
                }
            )
        elif evening > morning and evening > afternoon:
            insights.append(
                {
                    "type": "pattern",
                    "title": "夜型学習パターン",
                    "body": "夕方〜夜に集中して学習しています。",
                    "confidence": 0.7,
                }
            )

        return insights[:5]

    def _build_summary(self, stats: dict, insights: list[dict]) -> str:
        total = stats["total_combined_minutes"]
        hours = total // 60
        mins = total % 60
        lines = [f"今週の学習時間: {hours}時間{mins}分"]
        for ins in insights[:3]:
            lines.append(f"- {ins.get('title', '')}")
        return "\n".join(lines)

    async def get_insights(self, user_id: int) -> list[dict]:
        return await self.repository.get_user_insights(user_id)

    async def get_reports(self, user_id: int, limit: int = 10) -> list[dict]:
        return await self.repository.get_reports(user_id, limit)

    async def get_report(self, report_id: int) -> dict | None:
        return await self.repository.get_report(report_id)

    async def get_active_user_ids(self) -> list[int]:
        return await self.repository.get_active_user_ids()

    async def mark_dm_sent(self, report_id: int) -> None:
        await self.repository.mark_dm_sent(report_id)
