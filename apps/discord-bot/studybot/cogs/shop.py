"""ショップ・通貨 Cog"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from studybot.config.constants import RARITY_LABELS, SHOP_CATEGORIES
from studybot.managers.currency_manager import CurrencyManager
from studybot.utils.embed_helper import coin_embed, error_embed, success_embed

logger = logging.getLogger(__name__)


class ShopView(discord.ui.View):
    """ショップページネーションビュー"""

    def __init__(self, cog: "ShopCog", category, page: int, data: dict) -> None:
        super().__init__(timeout=120)
        self.cog = cog
        self.category = category
        self.page = page
        self.data = data
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.prev_button.disabled = self.page <= 0
        self.next_button.disabled = self.page >= self.data["total_pages"] - 1

    def _build_embed(self) -> discord.Embed:
        cat_label = (
            SHOP_CATEGORIES.get(self.category, "全カテゴリ") if self.category else "全カテゴリ"
        )
        embed = coin_embed(
            f"ショップ - {cat_label}",
            "",
        )

        if not self.data["items"]:
            embed.description = "アイテムがありません。"
            return embed

        lines = []
        for item in self.data["items"]:
            rarity = RARITY_LABELS.get(item["rarity"], item["rarity"])
            lines.append(
                f"{item['emoji']} **{item['name']}** — {item['price']:,} 🪙\n"
                f"　{rarity} | ID: `{item['id']}`\n"
                f"　_{item['description']}_"
            )

        embed.description = "\n\n".join(lines)
        pages = self.data["total_pages"]
        total = self.data["total_items"]
        embed.set_footer(text=f"ページ {self.page + 1}/{pages} | 全{total}件")
        return embed

    @discord.ui.button(label="◀ 前へ", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self.data = await self.cog.manager.get_shop_page(category=self.category, page=self.page)
        self._update_buttons()
        await interaction.response.edit_message(embed=self._build_embed(), view=self)

    @discord.ui.button(label="▶ 次へ", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self.data = await self.cog.manager.get_shop_page(category=self.category, page=self.page)
        self._update_buttons()
        await interaction.response.edit_message(embed=self._build_embed(), view=self)


class ConfirmPurchaseView(discord.ui.View):
    """購入確認ビュー"""

    def __init__(self, cog: "ShopCog", user_id: int, item: dict) -> None:
        super().__init__(timeout=60)
        self.cog = cog
        self.user_id = user_id
        self.item = item

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "この操作はあなたのものではありません。", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="購入する", style=discord.ButtonStyle.success, emoji="🪙")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = await self.cog.manager.purchase(self.user_id, self.item["id"])

        if "error" in result:
            await interaction.response.edit_message(
                embed=error_embed("購入失敗", result["error"]),
                view=None,
            )
        else:
            embed = success_embed(
                "購入完了！",
                f"{self.item['emoji']} **{self.item['name']}** を購入しました！\n"
                f"残高: {result['balance']:,} 🪙",
            )
            await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=coin_embed("キャンセル", "購入をキャンセルしました。"),
            view=None,
        )
        self.stop()


class ShopCog(commands.Cog):
    """ショップ & 通貨機能"""

    def __init__(self, bot: commands.Bot, manager: CurrencyManager) -> None:
        self.bot = bot
        self.manager = manager

    shop_group = app_commands.Group(name="shop", description="ショップ")

    @shop_group.command(name="list", description="ショップのアイテム一覧を表示")
    @app_commands.describe(category="カテゴリでフィルタ")
    @app_commands.choices(
        category=[
            app_commands.Choice(name="タイトル", value="title"),
            app_commands.Choice(name="コスメティック", value="cosmetic"),
            app_commands.Choice(name="ブースト", value="boost"),
            app_commands.Choice(name="テーマ", value="theme"),
        ]
    )
    async def shop_list(
        self,
        interaction: discord.Interaction,
        category: str | None = None,
    ):
        await interaction.response.defer()

        data = await self.manager.get_shop_page(category=category, page=0)
        view = ShopView(self, category, 0, data)
        await interaction.followup.send(embed=view._build_embed(), view=view)

    @shop_group.command(name="buy", description="アイテムを購入")
    @app_commands.describe(item_id="購入するアイテムのID")
    async def shop_buy(self, interaction: discord.Interaction, item_id: int):
        await interaction.response.defer(ephemeral=True)

        # アイテム情報を取得
        item = await self.manager.repository.get_item(item_id)
        if not item:
            await interaction.followup.send(
                embed=error_embed("エラー", "アイテムが見つかりません。"),
                ephemeral=True,
            )
            return

        # 残高チェック
        await self.manager.repository.ensure_user(
            interaction.user.id, interaction.user.display_name
        )
        await self.manager.repository.ensure_currency(interaction.user.id)
        balance = await self.manager.get_balance(interaction.user.id)

        rarity = RARITY_LABELS.get(item["rarity"], item["rarity"])
        embed = coin_embed(
            "購入確認",
            f"{item['emoji']} **{item['name']}**\n"
            f"{rarity}\n"
            f"_{item['description']}_\n\n"
            f"価格: **{item['price']:,}** 🪙\n"
            f"残高: **{balance:,}** 🪙",
        )

        view = ConfirmPurchaseView(self, interaction.user.id, item)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @shop_group.command(name="inventory", description="所持アイテムを表示")
    async def shop_inventory(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        items = await self.manager.get_inventory(interaction.user.id)

        if not items:
            await interaction.followup.send(
                embed=coin_embed("インベントリ", "アイテムを持っていません。"),
                ephemeral=True,
            )
            return

        lines = []
        for item in items:
            equipped = " 【装備中】" if item["equipped"] else ""
            lines.append(f"{item['emoji']} **{item['name']}** x{item['quantity']}{equipped}")

        embed = coin_embed("インベントリ", "\n".join(lines))
        embed.set_footer(text=f"{len(items)}種類のアイテム")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="coins", description="StudyCoinの残高を表示")
    async def coins_command(self, interaction: discord.Interaction):
        await self.manager.repository.ensure_user(
            interaction.user.id, interaction.user.display_name
        )
        currency = await self.manager.repository.ensure_currency(interaction.user.id)

        embed = coin_embed(
            f"{interaction.user.display_name} のStudyCoin",
            f"💰 残高: **{currency['balance']:,}** 🪙\n"
            f"📈 累計獲得: {currency['total_earned']:,} 🪙\n"
            f"📉 累計消費: {currency['total_spent']:,} 🪙",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @shop_group.command(name="equip", description="アイテムを装備/使用")
    @app_commands.describe(item_id="装備するアイテムのID")
    async def shop_equip(self, interaction: discord.Interaction, item_id: int):
        await interaction.response.defer(ephemeral=True)

        result = await self.manager.equip_item(interaction.user.id, item_id)
        if "error" in result:
            await interaction.followup.send(
                embed=error_embed("装備失敗", result["error"]),
                ephemeral=True,
            )
            return

        item = result["item"]

        # ロールアイテムの場合、Discord ロールを付与
        if item.get("category") == "role" and interaction.guild:
            role_name = item["name"].replace(" ロール", "")
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if not role:
                # ロールを作成
                try:
                    role = await interaction.guild.create_role(
                        name=role_name,
                        color=discord.Color.gold(),
                        reason=f"StudyBot ショップアイテム: {item['name']}",
                    )
                except discord.Forbidden:
                    pass
            if role:
                try:
                    await interaction.user.add_roles(role, reason="ショップアイテム使用")
                except discord.Forbidden:
                    await interaction.followup.send(
                        embed=error_embed("ロール付与失敗", "Botにロール管理権限がありません。"),
                        ephemeral=True,
                    )
                    return

        embed = success_embed(
            "装備完了",
            f"{item['emoji']} **{item['name']}** を装備しました！",
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @shop_group.command(name="roles", description="取得可能な特別ロール一覧")
    async def shop_roles(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        items = await self.manager.repository.get_shop_items(category="role")

        if not items:
            await interaction.followup.send(
                embed=coin_embed("特別ロール", "取得可能なロールアイテムはありません。"),
                ephemeral=True,
            )
            return

        lines = []
        for item in items:
            rarity = RARITY_LABELS.get(item["rarity"], item["rarity"])
            lines.append(
                f"{item['emoji']} **{item['name']}** — {item['price']:,} 🪙\n"
                f"　{rarity} | ID: `{item['id']}`\n"
                f"　_{item['description']}_"
            )

        embed = coin_embed("特別ロール一覧", "\n\n".join(lines))
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def award_coins(self, user_id: int, username: str, amount: int, reason: str) -> dict:
        """他Cogからのコイン付与（外部API）"""
        return await self.manager.award_coins(user_id, username, amount, reason)


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = CurrencyManager(db_pool)
    await bot.add_cog(ShopCog(bot, manager))
