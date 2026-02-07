"""学習ログ & 統計 ビジネスロジック"""

import io
import logging
from datetime import date, timedelta

import matplotlib
import matplotlib.pyplot as plt

from studybot.repositories.study_repository import StudyRepository

matplotlib.use("Agg")

logger = logging.getLogger(__name__)

PERIOD_DAYS = {
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
    "all_time": 3650,
}


class StudyManager:
    """学習ログ・統計の管理"""

    def __init__(self, db_pool) -> None:
        self.repository = StudyRepository(db_pool)

    async def log_study(
        self,
        user_id: int,
        username: str,
        guild_id: int,
        duration_minutes: int,
        topic: str = "",
        source: str = "manual",
    ) -> int:
        """学習を記録"""
        await self.repository.ensure_user(user_id, username)

        log_id = await self.repository.add_log(user_id, guild_id, duration_minutes, topic, source)

        # 統計キャッシュを更新
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        for period, start in [
            ("daily", today),
            ("weekly", week_start),
            ("monthly", month_start),
        ]:
            await self.repository.update_stats_cache(
                user_id, guild_id, period, start, duration_minutes
            )

        return log_id

    async def get_stats(self, user_id: int, guild_id: int, period: str = "weekly") -> dict:
        """統計情報を取得"""
        days = PERIOD_DAYS.get(period, 7)
        return await self.repository.get_user_stats(user_id, guild_id, days)

    async def generate_chart(
        self,
        user_id: int,
        guild_id: int,
        chart_type: str = "line",
        days: int = 14,
    ) -> io.BytesIO | None:
        """matplotlibでチャートを生成"""
        data = await self.repository.get_daily_totals(user_id, guild_id, days)
        if not data:
            return None

        dates = [row["study_date"] for row in data]
        minutes = [row["total_minutes"] for row in data]

        plt.rcParams["font.family"] = "sans-serif"
        fig, ax = plt.subplots(figsize=(10, 5))

        if chart_type == "bar":
            ax.bar(dates, minutes, color="#3498DB", alpha=0.8)
        else:
            ax.plot(dates, minutes, marker="o", color="#3498DB", linewidth=2)
            ax.fill_between(dates, minutes, alpha=0.2, color="#3498DB")

        ax.set_xlabel("日付")
        ax.set_ylabel("学習時間（分）")
        ax.set_title(f"過去{days}日間の学習時間")
        ax.grid(True, alpha=0.3)
        fig.autofmt_xdate()
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        buf.seek(0)
        plt.close(fig)

        return buf

    async def generate_topic_chart(
        self, user_id: int, guild_id: int, days: int = 30
    ) -> io.BytesIO | None:
        """トピック別円グラフを生成"""
        data = await self.repository.get_topic_breakdown(user_id, guild_id, days)
        if not data:
            return None

        topics = [row["topic"] for row in data]
        minutes = [row["total_minutes"] for row in data]

        fig, ax = plt.subplots(figsize=(8, 8))
        ax.pie(minutes, labels=topics, autopct="%1.1f%%", startangle=90)
        ax.set_title(f"過去{days}日間のトピック別学習時間")
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        buf.seek(0)
        plt.close(fig)

        return buf
