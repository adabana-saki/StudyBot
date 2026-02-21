"""エクスペディション Cog - 知識探検冒険"""

import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from studybot.config.constants import COLORS
from studybot.managers.expedition_manager import (
    EXPLORER_RANKS,
    REGION_CATEGORY_MAP,
    REGIONS,
    TERRITORY_PLANT_MAP,
    ExpeditionManager,
)
from studybot.utils.embed_helper import error_embed, success_embed

logger = logging.getLogger(__name__)


class JournalWriteModal(discord.ui.Modal, title="探検日誌エントリ"):
    """探検日誌の記入"""

    entry_title = discord.ui.TextInput(
        label="タイトル",
        placeholder="今日の探検で発見したこと",
        max_length=100,
        required=True,
    )
    content = discord.ui.TextInput(
        label="内容",
        style=discord.TextStyle.paragraph,
        placeholder="学んだこと、気づいたことを記録しましょう",
        max_length=1000,
        required=True,
    )

    def __init__(self, cog: "ExpeditionCog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        # DB保存
        await self.cog.manager.save_journal_entry(
            interaction.user.id,
            self.entry_title.value,
            self.content.value,
        )

        embed = discord.Embed(
            title=f"📔 {self.entry_title.value}",
            description=self.content.value,
            color=COLORS["expedition"],
        )
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url,
        )
        embed.set_footer(text="探検日誌エントリ（保存済み）")
        await interaction.response.send_message(embed=embed)


class ExpeditionCog(commands.Cog):
    """エクスペディション - 知識探検冒険"""

    def __init__(self, bot: commands.Bot, manager: ExpeditionManager) -> None:
        self.bot = bot
        self.manager = manager

    async def cog_load(self) -> None:
        self.discovery_event_generator.start()
        self.party_progress_check.start()

    async def cog_unload(self) -> None:
        self.discovery_event_generator.cancel()
        self.party_progress_check.cancel()

    @tasks.loop(hours=168)  # 週1回
    async def discovery_event_generator(self) -> None:
        """毎週の発見イベント生成"""
        try:
            for guild in self.bot.guilds:
                await self.manager.generate_discovery(guild.id)
            logger.info("週次発見イベント生成完了")
        except Exception:
            logger.error("発見イベント生成失敗", exc_info=True)

    @discovery_event_generator.before_loop
    async def before_discovery(self) -> None:
        await self.bot.wait_until_ready()

    @tasks.loop(hours=1)
    async def party_progress_check(self) -> None:
        """パーティ目標達成チェック"""
        try:
            for guild in self.bot.guilds:
                completed = await self.manager.check_parties(guild.id)
                for party in completed:
                    logger.info(
                        "パーティ目標達成: %s (guild=%d)",
                        party["name"],
                        guild.id,
                    )
        except Exception:
            logger.error("パーティチェック失敗", exc_info=True)

    @party_progress_check.before_loop
    async def before_party_check(self) -> None:
        await self.bot.wait_until_ready()

    # --- 外部連携メソッド ---

    async def record_study(self, user_id: int, topic: str, minutes: int) -> None:
        """gamificationフック: 学習をマップ進捗に反映"""
        try:
            result = await self.manager.record_study(user_id, topic, minutes)

            # 領域完了時の報酬処理
            if result and result.get("completed_now") and result.get("rewards"):
                rewards = result["rewards"]
                territory = result["territory"]

                # XP付与
                gamification_cog = self.bot.get_cog("GamificationCog")
                if gamification_cog:
                    try:
                        await gamification_cog.manager.add_xp(
                            user_id, rewards["xp"], "領域探索完了"
                        )
                    except Exception:
                        logger.debug("領域完了XP付与失敗", exc_info=True)

                # コイン付与
                shop_cog = self.bot.get_cog("ShopCog")
                if shop_cog:
                    try:
                        await shop_cog.award_coins(user_id, "", rewards["coins"], "領域探索完了")
                    except Exception:
                        logger.debug("領域完了コイン付与失敗", exc_info=True)

                # サンクチュアリ記念植物
                region = territory.get("region", "")
                plant_type = TERRITORY_PLANT_MAP.get(region)
                if plant_type:
                    sanctuary_cog = self.bot.get_cog("SanctuaryCog")
                    if sanctuary_cog:
                        try:
                            await sanctuary_cog.manager.plant(
                                user_id, plant_type, f"{territory['name']}の記念"
                            )
                        except Exception:
                            logger.debug("記念植物の植え付け失敗", exc_info=True)

        except Exception:
            logger.debug("探索進捗更新失敗 (user=%d)", user_id, exc_info=True)

    # --- コマンド ---

    expedition_group = app_commands.Group(
        name="expedition", description="エクスペディション - 知識探検冒険"
    )

    @expedition_group.command(name="map", description="ワールドマップ表示")
    @app_commands.describe(region="地域フィルター")
    @app_commands.choices(
        region=[
            app_commands.Choice(name=f"{v['emoji']} {v['name']}", value=k)
            for k, v in REGIONS.items()
        ]
    )
    async def map_cmd(self, interaction: discord.Interaction, region: str = "") -> None:
        await interaction.response.defer()

        map_data = await self.manager.get_map(interaction.user.id, region)
        if not map_data:
            await interaction.followup.send(
                embed=error_embed(
                    "マップエラー",
                    "領域データがありません。サーバー管理者に連絡してください。",
                )
            )
            return

        embed = discord.Embed(
            title="🗺️ ワールドマップ",
            description="知識の領域を探索しよう！",
            color=COLORS["expedition"],
        )

        for _region_key, data in map_data.items():
            territories_text = ""
            for t in data["territories"][:5]:  # Max 5 per region
                if t["completed"]:
                    status = "✅"
                elif t["progress_pct"] > 0:
                    bar_filled = t["progress_pct"] // 20
                    bar = "🟧" * bar_filled + "⬜" * (5 - bar_filled)
                    status = f"{bar} {t['progress_pct']}%"
                else:
                    status = "🔲 未探索"
                territories_text += f"{t['emoji']} **{t['name']}** {status}\n"

            if len(data["territories"]) > 5:
                territories_text += f"... 他{len(data['territories']) - 5}領域\n"

            embed.add_field(
                name=f"{data['emoji']} {data['name']} ({data['completed']}/{data['total']})",
                value=territories_text or "データなし",
                inline=False,
            )

        await interaction.followup.send(embed=embed)

    @expedition_group.command(name="explore", description="領域探索開始")
    @app_commands.describe(topic="探索トピック（学習科目）")
    async def explore(self, interaction: discord.Interaction, topic: str) -> None:
        await interaction.response.defer()

        from studybot.repositories.expedition_repository import ExpeditionRepository

        repo = ExpeditionRepository(self.bot.db_pool)
        territory = await repo.get_territory_by_keyword(topic)

        if not territory:
            await interaction.followup.send(
                embed=error_embed(
                    "領域が見つかりません",
                    f"「{topic}」に対応する領域がありません。\n"
                    "マップを確認してみてください: `/expedition map`",
                ),
                ephemeral=True,
            )
            return

        # 難易度4+の領域: Forge mastery Lv3チェック
        if territory["difficulty"] >= 4:
            region = territory["region"]
            category = REGION_CATEGORY_MAP.get(region, "general")
            forge_cog = self.bot.get_cog("ForgeCog")
            if forge_cog:
                try:
                    mastery_level = await forge_cog.manager.get_mastery_level_for_category(
                        interaction.user.id, category
                    )
                    if mastery_level < 3:
                        await interaction.followup.send(
                            embed=error_embed(
                                "スキル不足",
                                f"この領域は難易度{territory['difficulty']}です。\n"
                                f"**{category}** のマスタリーLv3が必要です "
                                f"(現在: Lv{mastery_level})\n\n"
                                "`/forge practice` でスキルを鍛えましょう！",
                            ),
                            ephemeral=True,
                        )
                        return
                except Exception:
                    logger.debug("Forge mastery check failed", exc_info=True)

        progress = await repo.get_progress(interaction.user.id, territory["id"])
        spent = progress.get("minutes_spent", 0) if progress else 0
        req = territory["required_minutes"]
        pct = min(100, int(spent / req * 100)) if req > 0 else 0

        embed = discord.Embed(
            title=f"{territory['emoji']} {territory['name']}の探索",
            description=(
                f"地域: {REGIONS.get(territory['region'], {}).get('name', territory['region'])}\n"
                f"難易度: {'⭐' * territory['difficulty']}\n"
                f"必要時間: {territory['required_minutes']}分\n\n"
                f"進捗: {spent}/{territory['required_minutes']}分 ({pct}%)\n"
                f"{'🟧' * (pct // 20)}{'⬜' * (5 - pct // 20)}"
            ),
            color=COLORS["expedition"],
        )
        embed.set_footer(text="学習ログを記録すると自動的に進捗が反映されます")
        await interaction.followup.send(embed=embed)

    @expedition_group.command(name="profile", description="探検家プロフィール")
    async def profile(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        data = await self.manager.get_explorer_profile(interaction.user.id)
        rank = data["rank"]

        embed = discord.Embed(
            title=f"{rank['emoji']} {interaction.user.display_name}",
            description=f"ランク: **{rank['name']}**",
            color=COLORS["expedition"],
        )
        embed.add_field(
            name="探索実績",
            value=(
                f"完了領域: {data['completed_territories']}\n"
                f"ポイント: {data['explorer'].get('total_points', 0)}"
            ),
            inline=True,
        )

        # 次のランク
        current_idx = next(
            (i for i, r in enumerate(EXPLORER_RANKS) if r["name"] == rank["name"]),
            0,
        )
        if current_idx < len(EXPLORER_RANKS) - 1:
            next_rank = EXPLORER_RANKS[current_idx + 1]
            embed.add_field(
                name="次のランク",
                value=(
                    f"{next_rank['emoji']} {next_rank['name']}\n"
                    f"必要領域: {next_rank['min_territories']}"
                ),
                inline=True,
            )

        await interaction.followup.send(embed=embed)

    # --- パーティ ---

    party_group = app_commands.Group(
        name="party",
        description="エクスペディションパーティ",
        parent=expedition_group,
    )

    @party_group.command(name="create", description="パーティ作成")
    @app_commands.describe(
        name="パーティ名",
        region="探索地域",
        goal_minutes="目標学習時間（分）",
    )
    @app_commands.choices(
        region=[
            app_commands.Choice(name=f"{v['emoji']} {v['name']}", value=k)
            for k, v in REGIONS.items()
        ]
    )
    async def party_create(
        self,
        interaction: discord.Interaction,
        name: str,
        region: str,
        goal_minutes: int,
    ) -> None:
        party = await self.manager.create_party(
            interaction.user.id,
            interaction.guild_id,
            name,
            region,
            goal_minutes,
        )
        if not party:
            await interaction.response.send_message(
                embed=error_embed(
                    "パーティ作成失敗",
                    "既にパーティに参加中か、入力が不正です",
                ),
                ephemeral=True,
            )
            return

        region_info = REGIONS.get(region, {})
        embed = discord.Embed(
            title=f"🎪 パーティ「{name}」結成！",
            description=(
                f"地域: {region_info.get('emoji', '')} {region_info.get('name', region)}\n"
                f"目標: {goal_minutes}分\n"
                f"ID: `{party['id']}`\n\n"
                f"仲間を集めよう！ `/expedition party join {party['id']}`"
            ),
            color=COLORS["expedition"],
        )
        await interaction.response.send_message(embed=embed)

    @party_group.command(name="join", description="パーティ参加")
    @app_commands.describe(party_id="パーティID")
    async def party_join(self, interaction: discord.Interaction, party_id: int) -> None:
        joined = await self.manager.join_party(interaction.user.id, party_id)
        if not joined:
            await interaction.response.send_message(
                embed=error_embed(
                    "参加失敗",
                    "パーティが存在しない、満員、または既にパーティに参加中です",
                ),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success_embed("パーティ参加完了！", "一緒に探検しましょう！")
        )

    @party_group.command(name="status", description="パーティ進捗表示")
    async def party_status(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        status = await self.manager.get_party_status(interaction.user.id)
        if not status:
            await interaction.followup.send(
                embed=error_embed("パーティなし", "パーティに参加していません"),
                ephemeral=True,
            )
            return

        party = status["party"]
        members = status["members"]
        pct = status["progress_pct"]
        bar_filled = pct // 10
        bar = "🟧" * bar_filled + "⬜" * (10 - bar_filled)

        embed = discord.Embed(
            title=f"🎪 {party['name']}",
            description=(
                f"地域: {REGIONS.get(party['region'], {}).get('name', party['region'])}\n"
                f"進捗: {bar} {pct}%\n"
                f"**{party['progress_minutes']}** / {party['goal_minutes']}分"
            ),
            color=COLORS["expedition"],
        )

        member_text = ""
        for m in members:
            member_text += f"<@{m['user_id']}> - {m.get('contribution_minutes', 0)}分\n"
        embed.add_field(
            name=f"メンバー ({len(members)}/5)",
            value=member_text or "なし",
            inline=False,
        )

        await interaction.followup.send(embed=embed)

    # --- 発見イベント ---

    @expedition_group.command(name="discovery", description="今週の発見イベント")
    async def discovery(self, interaction: discord.Interaction) -> None:
        event = await self.manager.get_discovery(interaction.guild_id)
        if not event:
            await interaction.response.send_message(
                embed=error_embed("イベントなし", "今週の発見イベントはまだありません"),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"🔍 {event['title']}",
            description=event["description"],
            color=COLORS["expedition"],
        )
        embed.add_field(name="報酬", value=f"⭐ {event['reward_points']}ポイント", inline=True)
        embed.set_footer(text="学習を通じてイベントに参加しよう")
        await interaction.response.send_message(embed=embed)

    # --- 日誌サブグループ ---

    journal_group = app_commands.Group(
        name="journal",
        description="探検日誌",
        parent=expedition_group,
    )

    @journal_group.command(name="write", description="探検日誌を記入")
    async def journal_write(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(JournalWriteModal(self))

    @journal_group.command(name="list", description="探検日誌一覧")
    async def journal_list(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        entries = await self.manager.get_journal_entries(interaction.user.id, limit=5)
        if not entries:
            await interaction.followup.send(
                embed=error_embed(
                    "日誌なし",
                    "まだ日誌がありません。`/expedition journal write` で記入しましょう！",
                ),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="📔 探検日誌",
            description=f"{interaction.user.display_name}の最近の記録",
            color=COLORS["expedition"],
        )

        for entry in entries:
            content_preview = entry["content"][:80]
            if len(entry["content"]) > 80:
                content_preview += "..."
            embed.add_field(
                name=f"📝 {entry['title']}",
                value=f"{content_preview}\n`{entry['created_at']}`",
                inline=False,
            )

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    manager = ExpeditionManager(bot.db_pool)
    # 初期領域データ投入
    try:
        await manager.seed_territories()
    except Exception:
        logger.warning("領域データ投入失敗（既存データがある場合は正常）", exc_info=True)
    await bot.add_cog(ExpeditionCog(bot, manager))
