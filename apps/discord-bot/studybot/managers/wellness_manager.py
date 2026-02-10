"""ウェルネス ビジネスロジック"""

import io
import logging

import matplotlib
import matplotlib.pyplot as plt

from studybot.config.constants import ENERGY_LABELS, MOOD_LABELS, STRESS_LABELS
from studybot.repositories.wellness_repository import WellnessRepository

matplotlib.use("Agg")

logger = logging.getLogger(__name__)


class WellnessManager:
    """ウェルネスチェックの管理"""

    def __init__(self, db_pool) -> None:
        self.repository = WellnessRepository(db_pool)

    async def log_wellness(
        self,
        user_id: int,
        username: str,
        mood: int,
        energy: int,
        stress: int,
        note: str = "",
    ) -> dict:
        """ウェルネスを記録し、分析結果を返す"""
        await self.repository.ensure_user(user_id, username)

        log = await self.repository.log_wellness(user_id, mood, energy, stress, note)

        # 警告メッセージを生成
        warnings = []
        if mood <= 2:
            warnings.append("少し休憩を取りましょう")
        if stress >= 4:
            warnings.append("深呼吸やストレッチをしてみましょう")

        # 7日間の平均値を取得
        averages = await self.repository.get_averages(user_id, days=7)

        return {
            "logged": True,
            "log": log,
            "mood_label": MOOD_LABELS.get(mood, ""),
            "energy_label": ENERGY_LABELS.get(energy, ""),
            "stress_label": STRESS_LABELS.get(stress, ""),
            "warning": "。".join(warnings) if warnings else None,
            "averages": averages,
        }

    async def get_stats(self, user_id: int) -> dict:
        """7日間のウェルネス統計を取得"""
        averages = await self.repository.get_averages(user_id, days=7)
        recent_logs = await self.repository.get_recent_logs(user_id, days=7)

        if not averages:
            return {
                "has_data": False,
                "message": "まだウェルネスデータがありません。/wellness check で記録しましょう！",
            }

        avg_mood = float(averages["avg_mood"])
        avg_energy = float(averages["avg_energy"])
        avg_stress = float(averages["avg_stress"])

        # 最も近いラベルを取得
        mood_label = MOOD_LABELS.get(round(avg_mood), "")
        energy_label = ENERGY_LABELS.get(round(avg_energy), "")
        stress_label = STRESS_LABELS.get(round(avg_stress), "")

        return {
            "has_data": True,
            "avg_mood": avg_mood,
            "avg_energy": avg_energy,
            "avg_stress": avg_stress,
            "mood_label": mood_label,
            "energy_label": energy_label,
            "stress_label": stress_label,
            "log_count": int(averages["log_count"]),
            "recent_logs": recent_logs,
        }

    async def get_recommendation(self, user_id: int) -> dict:
        """ウェルネスデータに基づく学習推奨を生成"""
        today_log = await self.repository.get_today_log(user_id)
        averages = await self.repository.get_averages(user_id, days=7)

        if not averages and not today_log:
            return {
                "has_data": False,
                "message": (
                    "ウェルネスデータがありません。\n`/wellness check` で今の状態を記録しましょう！"
                ),
            }

        # 今日のデータ or 直近平均を使用
        mood = int(today_log["mood"]) if today_log else round(float(averages["avg_mood"]))
        energy = int(today_log["energy"]) if today_log else round(float(averages["avg_energy"]))
        stress = int(today_log["stress"]) if today_log else round(float(averages["avg_stress"]))

        # 推奨セッション時間
        if energy >= 4 and stress <= 2:
            recommended_minutes = 50
            session_type = "deep_focus"
            session_label = "ディープフォーカス（50分）"
            advice = (
                "エネルギーが高く、ストレスも低い最高のコンディションです！"
                "長めのセッションに挑戦しましょう。"
            )
        elif energy >= 3 and stress <= 3:
            recommended_minutes = 25
            session_type = "standard"
            session_label = "スタンダード（25分）"
            advice = "バランスの取れた状態です。通常のポモドーロで学習しましょう。"
        elif energy <= 2 or stress >= 4:
            recommended_minutes = 15
            session_type = "light"
            session_label = "ライトセッション（15分）"
            advice = (
                "少し疲れているようです。短めのセッションで無理なく学習しましょう。休憩も大切に。"
            )
        else:
            recommended_minutes = 20
            session_type = "moderate"
            session_label = "モデレート（20分）"
            advice = "適度なペースで学習しましょう。気分転換にストレッチもおすすめです。"

        # 気分が低い場合の追加アドバイス
        extra_tips = []
        if mood <= 2:
            extra_tips.append("💡 気分が優れない時は、好きな科目から始めるのがおすすめです")
        if stress >= 4:
            extra_tips.append("🧘 学習前に深呼吸を3回してリラックスしましょう")
        if energy <= 2:
            extra_tips.append("☕ 水分補給や軽いストレッチで体を起こしてから始めましょう")

        return {
            "has_data": True,
            "mood": mood,
            "energy": energy,
            "stress": stress,
            "mood_label": MOOD_LABELS.get(mood, ""),
            "energy_label": ENERGY_LABELS.get(energy, ""),
            "stress_label": STRESS_LABELS.get(stress, ""),
            "recommended_minutes": recommended_minutes,
            "session_type": session_type,
            "session_label": session_label,
            "advice": advice,
            "extra_tips": extra_tips,
            "source": "today" if today_log else "average",
        }

    async def generate_trend_chart(self, user_id: int, days: int = 14) -> io.BytesIO | None:
        """ウェルネストレンドチャートを生成"""
        data = await self.repository.get_daily_averages(user_id, days)
        if not data:
            return None

        dates = [row["day"] for row in data]
        moods = [float(row["avg_mood"]) for row in data]
        energies = [float(row["avg_energy"]) for row in data]
        stresses = [float(row["avg_stress"]) for row in data]

        plt.rcParams["font.family"] = "sans-serif"
        fig, ax = plt.subplots(figsize=(10, 5))

        ax.plot(dates, moods, marker="o", color="#3498DB", linewidth=2, label="気分")
        ax.plot(dates, energies, marker="s", color="#2ECC71", linewidth=2, label="エネルギー")
        ax.plot(dates, stresses, marker="^", color="#E74C3C", linewidth=2, label="ストレス")

        ax.set_xlabel("日付")
        ax.set_ylabel("スコア (1-5)")
        ax.set_title(f"過去{days}日間のウェルネストレンド")
        ax.set_ylim(0.5, 5.5)
        ax.legend(loc="upper left")
        ax.grid(True, alpha=0.3)
        fig.autofmt_xdate()
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        buf.seek(0)
        plt.close(fig)

        return buf
