"""スタディルーム Cog"""

import logging
from datetime import timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from studybot.config.constants import COLORS
from studybot.managers.room_manager import RoomManager
from studybot.utils.embed_helper import error_embed, info_embed, success_embed

JST = timezone(timedelta(hours=9))

logger = logging.getLogger(__name__)

THEME_EMOJIS = {
    "general": "📚",
    "math": "🔢",
    "english": "🔤",
    "science": "🔬",
    "programming": "💻",
    "art": "🎨",
    "music": "🎵",
}


class StudyRoomCog(commands.Cog):
    """スタディルーム機能"""

    def __init__(self, bot: commands.Bot, manager: RoomManager) -> None:
        self.bot = bot
        self.manager = manager

    async def cog_load(self) -> None:
        self.room_check.start()

    async def cog_unload(self) -> None:
        self.room_check.cancel()

    room_group = app_commands.Group(name="room", description="スタディルーム")

    @room_group.command(name="create", description="ルームを作成")
    @app_commands.describe(
        name="ルーム名",
        theme="テーマ（general/math/english/science/programming/art/music）",
        goal_minutes="集合目標（分）",
    )
    async def room_create(
        self,
        interaction: discord.Interaction,
        name: str,
        theme: str = "general",
        goal_minutes: int = 0,
    ):
        await interaction.response.defer()
        result = await self.manager.create_room(
            guild_id=interaction.guild_id or 0,
            name=name,
            theme=theme,
            goal_minutes=goal_minutes,
            created_by=interaction.user.id,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("ルーム作成失敗", result["error"]))
            return

        emoji = THEME_EMOJIS.get(theme, "📚")
        embed = discord.Embed(
            title=f"{emoji} ルーム作成完了！",
            description=f"**{name}**",
            color=COLORS.get("success", 0x22C55E),
        )
        embed.add_field(name="ルームID", value=f"#{result['id']}", inline=True)
        embed.add_field(name="テーマ", value=theme, inline=True)
        if goal_minutes > 0:
            embed.add_field(name="集合目標", value=f"{goal_minutes}分", inline=True)
        embed.set_footer(text="/room join でルームに参加しよう！")
        await interaction.followup.send(embed=embed)

    @room_group.command(name="list", description="ルーム一覧")
    async def room_list(self, interaction: discord.Interaction):
        await interaction.response.defer()
        rooms = await self.manager.get_campus(interaction.guild_id or 0)

        if not rooms:
            await interaction.followup.send(
                embed=info_embed(
                    "スタディルーム", "ルームがありません。/room create で作成しましょう！"
                )
            )
            return

        embed = discord.Embed(
            title="🏫 スタディキャンパス",
            color=COLORS.get("primary", 0x5865F2),
        )
        for r in rooms[:15]:
            emoji = THEME_EMOJIS.get(r.get("theme", "general"), "📚")
            count = r.get("member_count", 0)
            max_occ = r.get("max_occupants", 20)
            goal_text = ""
            if r.get("collective_goal_minutes", 0) > 0:
                progress = r.get("collective_progress_minutes", 0)
                goal = r["collective_goal_minutes"]
                goal_text = f" | 目標: {progress}/{goal}分"
            embed.add_field(
                name=f"{emoji} #{r['id']} {r['name']}",
                value=f"👥 {count}/{max_occ}{goal_text}",
                inline=True,
            )
        await interaction.followup.send(embed=embed)

    @room_group.command(name="join", description="ルームに参加")
    @app_commands.describe(
        room_id="ルームID",
        topic="学習トピック",
    )
    async def room_join(
        self,
        interaction: discord.Interaction,
        room_id: int,
        topic: str = "",
    ):
        await interaction.response.defer()
        result = await self.manager.join_room(
            room_id=room_id,
            user_id=interaction.user.id,
            platform="discord",
            topic=topic,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("参加失敗", result["error"]))
            return

        await interaction.followup.send(
            embed=success_embed("ルーム参加完了", f"ルーム #{room_id} に参加しました！")
        )

    @room_group.command(name="leave", description="ルームを退出")
    async def room_leave(self, interaction: discord.Interaction):
        await interaction.response.defer()

        current = await self.manager.room_repo.get_user_room(interaction.user.id)
        if not current:
            await interaction.followup.send(
                embed=error_embed("退出失敗", "ルームに参加していません")
            )
            return

        result = await self.manager.leave_room(current["room_id"], interaction.user.id)
        duration = result.get("duration_minutes", 0)
        await interaction.followup.send(
            embed=success_embed(
                "ルーム退出完了",
                f"ルームを退出しました（{duration}分間在室）",
            )
        )

    @room_group.command(name="link", description="VCチャンネルとルームを紐付け")
    @app_commands.describe(
        room_id="ルームID",
        vc_channel="VCチャンネル",
    )
    async def room_link(
        self,
        interaction: discord.Interaction,
        room_id: int,
        vc_channel: discord.VoiceChannel,
    ):
        await interaction.response.defer()
        room = await self.manager.room_repo.get_room(room_id)
        if not room:
            await interaction.followup.send(embed=error_embed("エラー", "ルームが見つかりません"))
            return

        async with self.manager.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE study_rooms SET vc_channel_id = $2 WHERE id = $1",
                room_id,
                vc_channel.id,
            )

        await interaction.followup.send(
            embed=success_embed(
                "VC連携完了",
                f"ルーム #{room_id} と {vc_channel.mention} を連携しました",
            )
        )

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        """VC入退室をルーム参加/退出に自動連携"""
        try:
            # Left a VC
            if before.channel and (not after.channel or after.channel != before.channel):
                room = await self.manager.room_repo.get_room_by_vc_channel(before.channel.id)
                if room:
                    await self.manager.leave_room(room["id"], member.id)

            # Joined a VC
            if after.channel and (not before.channel or before.channel != after.channel):
                room = await self.manager.room_repo.get_room_by_vc_channel(after.channel.id)
                if room:
                    await self.manager.join_room(room["id"], member.id, "discord")
        except Exception:
            logger.debug("VC連携処理失敗", exc_info=True)

    @tasks.loop(minutes=1)
    async def room_check(self) -> None:
        """毎分: 集合目標チェック"""
        pass  # Goal checking is handled in leave_room

    @room_check.before_loop
    async def before_room_check(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    db_pool = getattr(bot, "db_pool", None)
    if db_pool is None:
        logger.error("db_pool が未初期化のため StudyRoomCog をロードできません")
        return
    event_publisher = getattr(bot, "event_publisher", None)
    manager = RoomManager(db_pool, event_publisher)
    await bot.add_cog(StudyRoomCog(bot, manager))
