"""投資市場Cog — /market, /savings, /flea コマンド + タスクループ"""

import logging
from datetime import UTC, time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from studybot.config.constants import COLORS, MARKET_CONFIG, SAVINGS_CONFIG
from studybot.managers.market_manager import MarketManager
from studybot.utils.embed_helper import error_embed

logger = logging.getLogger(__name__)

JST = UTC  # タスクループは UTC で制御


def market_embed(title: str, description: str = "") -> discord.Embed:
    return discord.Embed(title=f"📈 {title}", description=description, color=COLORS["market"])


def savings_embed(title: str, description: str = "") -> discord.Embed:
    return discord.Embed(title=f"🏦 {title}", description=description, color=COLORS["savings"])


def flea_embed(title: str, description: str = "") -> discord.Embed:
    return discord.Embed(title=f"🛒 {title}", description=description, color=COLORS["flea"])


class MarketCog(commands.Cog):
    """投資市場システム"""

    def __init__(self, bot: commands.Bot, manager: MarketManager) -> None:
        self.bot = bot
        self.manager = manager

    async def cog_load(self) -> None:
        self.update_stock_prices.start()
        self.daily_market_tasks.start()

    async def cog_unload(self) -> None:
        self.update_stock_prices.cancel()
        self.daily_market_tasks.cancel()

    # ===== タスクループ =====

    @tasks.loop(hours=1)
    async def update_stock_prices(self):
        """毎時: 株価更新"""
        try:
            results = await self.manager.update_all_prices()
            if results:
                logger.info(f"株価更新完了: {len(results)} 銘柄")
        except Exception as e:
            logger.error(f"株価更新エラー: {e}")

    @update_stock_prices.before_loop
    async def before_price_update(self):
        await self.bot.wait_until_ready()

    @tasks.loop(time=time(15, 0, 0))  # UTC 15:00 = JST 0:00
    async def daily_market_tasks(self):
        """日次: スナップショット保存 + 利息計算 + 期限切れ処理"""
        try:
            await self.manager.save_daily_snapshots()
            logger.info("日次株価スナップショット保存完了")

            results = await self.manager.process_daily_interest()
            logger.info(f"利息付与完了: {len(results)} 口座")

            expired = await self.manager.process_expired_listings()
            if expired:
                logger.info(f"期限切れ出品処理: {expired} 件")

            await self.manager.process_daily_item_prices()
            logger.info("アイテム価格履歴更新完了")
        except Exception as e:
            logger.error(f"日次市場タスクエラー: {e}")

    @daily_market_tasks.before_loop
    async def before_daily_tasks(self):
        await self.bot.wait_until_ready()

    # ===== /market コマンドグループ =====

    market_group = app_commands.Group(name="market", description="📈 学習株式市場")

    @market_group.command(name="stocks", description="全銘柄一覧を表示")
    async def market_stocks(self, interaction: discord.Interaction):
        await interaction.response.defer()
        stocks = await self.manager.get_all_stocks()

        embed = market_embed("学習株式市場", "コミュニティの学習量に連動する仮想株式")
        lines = []
        for s in stocks:
            arrow = "📈" if s["change_pct"] > 0 else "📉" if s["change_pct"] < 0 else "➡️"
            sign = "+" if s["change_pct"] > 0 else ""
            lines.append(
                f"{s['emoji']} **{s['symbol']}** ({s['name']}) — "
                f"**{s['current_price']:,}** 🪙 "
                f"{arrow} {sign}{s['change_pct']}%"
            )

        embed.description = "\n".join(lines) if lines else "銘柄データがありません"
        embed.set_footer(text="💡 /market buy <銘柄> <株数> で購入")
        await interaction.followup.send(embed=embed)

    @market_group.command(name="buy", description="株を購入")
    @app_commands.describe(symbol="銘柄シンボル (例: MATH)", shares="購入株数")
    async def market_buy(self, interaction: discord.Interaction, symbol: str, shares: int):
        await interaction.response.defer(ephemeral=True)
        result = await self.manager.buy_stock(interaction.user.id, symbol.upper(), shares)

        if "error" in result:
            await interaction.followup.send(
                embed=error_embed("購入失敗", result["error"]), ephemeral=True
            )
            return

        embed = market_embed(
            "購入完了！",
            f"{result['emoji']} **{result['symbol']}** ({result['name']})\n"
            f"📊 {result['shares']}株 × {result['price']:,} = **{result['total']:,}** 🪙\n"
            f"💰 残高: **{result['balance']:,}** 🪙",
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @market_group.command(name="sell", description="株を売却")
    @app_commands.describe(symbol="銘柄シンボル", shares="売却株数")
    async def market_sell(self, interaction: discord.Interaction, symbol: str, shares: int):
        await interaction.response.defer(ephemeral=True)
        result = await self.manager.sell_stock(interaction.user.id, symbol.upper(), shares)

        if "error" in result:
            await interaction.followup.send(
                embed=error_embed("売却失敗", result["error"]), ephemeral=True
            )
            return

        profit_str = f"+{result['profit']:,}" if result["profit"] >= 0 else f"{result['profit']:,}"
        embed = market_embed(
            "売却完了！",
            f"{result['emoji']} **{result['symbol']}** ({result['name']})\n"
            f"📊 {result['shares']}株 × {result['price']:,} = **{result['total']:,}** 🪙\n"
            f"💹 損益: **{profit_str}** 🪙\n"
            f"💰 残高: **{result['balance']:,}** 🪙",
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @market_group.command(name="portfolio", description="ポートフォリオを表示")
    async def market_portfolio(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        portfolio = await self.manager.get_portfolio(interaction.user.id)

        if not portfolio["holdings"]:
            await interaction.followup.send(
                embed=market_embed(
                    "ポートフォリオ",
                    "保有株はありません。\n`/market buy` で株を購入しましょう！",
                ),
                ephemeral=True,
            )
            return

        lines = []
        for h in portfolio["holdings"]:
            sign = "+" if h["profit"] >= 0 else ""
            lines.append(
                f"{h['emoji']} **{h['symbol']}** {h['shares']}株\n"
                f"  評価額: {h['market_value']:,} 🪙 | "
                f"損益: {sign}{h['profit']:,} ({sign}{h['profit_pct']}%)"
            )

        total_sign = "+" if portfolio["total_profit"] >= 0 else ""
        embed = market_embed("ポートフォリオ")
        embed.description = "\n".join(lines)
        embed.add_field(
            name="合計",
            value=(
                f"📊 評価額: **{portfolio['total_value']:,}** 🪙\n"
                f"💰 投資額: {portfolio['total_invested']:,} 🪙\n"
                f"💹 損益: {total_sign}{portfolio['total_profit']:,} "
                f"({total_sign}{portfolio['total_profit_pct']}%)"
            ),
            inline=False,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @market_group.command(name="stock_info", description="銘柄詳細を表示")
    @app_commands.describe(symbol="銘柄シンボル")
    async def market_stock_info(self, interaction: discord.Interaction, symbol: str):
        await interaction.response.defer()
        detail = await self.manager.get_stock_detail(symbol.upper())

        if not detail:
            await interaction.followup.send(
                embed=error_embed("銘柄が見つかりません", f"{symbol.upper()} は存在しません")
            )
            return

        sign = "+" if detail["change_pct"] > 0 else ""
        embed = market_embed(
            f"{detail['emoji']} {detail['symbol']} — {detail['name']}",
            detail["description"],
        )
        embed.add_field(name="現在価格", value=f"**{detail['current_price']:,}** 🪙", inline=True)
        embed.add_field(name="前日終値", value=f"{detail['previous_close']:,} 🪙", inline=True)
        embed.add_field(name="変動率", value=f"{sign}{detail['change_pct']}%", inline=True)
        embed.add_field(name="基準価格", value=f"{detail['base_price']:,} 🪙", inline=True)
        circ = f"{detail['circulating_shares']:,} / {detail['total_shares']:,}"
        embed.add_field(name="流通株数", value=circ, inline=True)
        embed.add_field(name="セクター", value=detail["sector"], inline=True)

        # 直近の価格履歴 (簡易テキストチャート)
        if detail["history"]:
            last5 = detail["history"][-5:]
            chart = " → ".join(f"{h['price']:,}" for h in last5)
            embed.add_field(name="直近5日間", value=chart, inline=False)

        await interaction.followup.send(embed=embed)

    @market_group.command(name="history", description="売買履歴を表示")
    async def market_history(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = await self.manager.get_transactions(interaction.user.id, limit=10)

        if not data["items"]:
            await interaction.followup.send(
                embed=market_embed("売買履歴", "取引履歴はありません"),
                ephemeral=True,
            )
            return

        lines = []
        for t in data["items"]:
            action = "🟢 購入" if t["transaction_type"] == "buy" else "🔴 売却"
            lines.append(
                f"{action} {t['emoji']} **{t['symbol']}** "
                f"{t['shares']}株 × {t['price_per_share']:,} = {t['total_amount']:,} 🪙"
            )

        embed = market_embed("売買履歴")
        embed.description = "\n".join(lines)
        embed.set_footer(text=f"直近10件 / 全{data['total']}件")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @market_buy.autocomplete("symbol")
    @market_sell.autocomplete("symbol")
    @market_stock_info.autocomplete("symbol")
    async def symbol_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        stocks = await self.manager.get_all_stocks()
        return [
            app_commands.Choice(
                name=f"{s['emoji']} {s['symbol']} ({s['name']}) - {s['current_price']:,}🪙",
                value=s["symbol"],
            )
            for s in stocks
            if current.upper() in s["symbol"] or current in s["name"]
        ][:25]

    # ===== /savings コマンドグループ =====

    savings_group = app_commands.Group(name="savings", description="🏦 貯金銀行")

    @savings_group.command(name="status", description="口座状況を確認")
    async def savings_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = await self.manager.get_savings_status(interaction.user.id)

        embed = savings_embed("貯金銀行")
        if not data["accounts"]:
            embed.description = (
                "口座はまだありません。\n"
                "`/savings deposit <金額> regular` で普通預金を始めましょう！\n\n"
                f"💰 **普通預金**: 日利 "
                f"{SAVINGS_CONFIG['regular_daily_rate'] * 100}% "
                f"(いつでも引き出し可)\n"
                f"🔒 **定期預金**: 日利 "
                f"{SAVINGS_CONFIG['fixed_daily_rate'] * 100}% "
                f"({SAVINGS_CONFIG['fixed_lock_days']}日ロック)"
            )
        else:
            for acc in data["accounts"]:
                type_label = "💰 普通預金" if acc["account_type"] == "regular" else "🔒 定期預金"
                value = (
                    f"残高: **{acc['balance']:,}** 🪙\n"
                    f"利率: 日利 {acc['interest_rate'] * 100}%\n"
                    f"累計利息: {acc['total_interest_earned']:,} 🪙"
                )
                if acc["account_type"] == "fixed" and acc["maturity_date"]:
                    value += f"\n満期日: {acc['maturity_date'].strftime('%Y-%m-%d')}"
                embed.add_field(name=type_label, value=value, inline=True)

            embed.add_field(
                name="合計",
                value=(
                    f"預金合計: **{data['total_savings']:,}** 🪙\n"
                    f"累計利息: {data['total_interest']:,} 🪙"
                ),
                inline=False,
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @savings_group.command(name="deposit", description="預金する")
    @app_commands.describe(
        amount="預金額",
        account_type="口座タイプ (regular=普通, fixed=定期)",
    )
    @app_commands.choices(
        account_type=[
            app_commands.Choice(name="普通預金 (日利0.1%, いつでも引出可)", value="regular"),
            app_commands.Choice(name="定期預金 (日利0.3%, 7日ロック)", value="fixed"),
        ]
    )
    async def savings_deposit(
        self,
        interaction: discord.Interaction,
        amount: int,
        account_type: app_commands.Choice[str],
    ):
        await interaction.response.defer(ephemeral=True)
        result = await self.manager.deposit(interaction.user.id, amount, account_type.value)

        if "error" in result:
            await interaction.followup.send(
                embed=error_embed("預金失敗", result["error"]), ephemeral=True
            )
            return

        embed = savings_embed(
            "預金完了！",
            f"**{result['type_label']}** に **{result['amount']:,}** 🪙 を預金しました\n"
            f"口座残高: **{result['balance']:,}** 🪙\n"
            f"利率: 日利 {result['interest_rate'] * 100}%",
        )
        if result["lock_days"] > 0:
            embed.description += f"\n🔒 ロック期間: {result['lock_days']}日"
        await interaction.followup.send(embed=embed, ephemeral=True)

    @savings_group.command(name="withdraw", description="引き出す")
    @app_commands.describe(
        amount="引き出し額",
        account_type="口座タイプ (regular=普通, fixed=定期)",
    )
    @app_commands.choices(
        account_type=[
            app_commands.Choice(name="普通預金", value="regular"),
            app_commands.Choice(name="定期預金", value="fixed"),
        ]
    )
    async def savings_withdraw(
        self,
        interaction: discord.Interaction,
        amount: int,
        account_type: app_commands.Choice[str],
    ):
        await interaction.response.defer(ephemeral=True)
        result = await self.manager.withdraw(interaction.user.id, amount, account_type.value)

        if "error" in result:
            await interaction.followup.send(
                embed=error_embed("引き出し失敗", result["error"]), ephemeral=True
            )
            return

        embed = savings_embed(
            "引き出し完了！",
            f"**{result['type_label']}** から **{result['amount']:,}** 🪙 を引き出しました\n"
            f"口座残高: **{result['new_balance']:,}** 🪙",
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @savings_group.command(name="interest_log", description="利息履歴を表示")
    async def savings_interest_log(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        history = await self.manager.get_interest_history(interaction.user.id)

        if not history:
            await interaction.followup.send(
                embed=savings_embed("利息履歴", "利息履歴はありません"),
                ephemeral=True,
            )
            return

        lines = []
        for h in history:
            type_label = "普通" if h["account_type"] == "regular" else "定期"
            lines.append(
                f"[{type_label}] +**{h['amount']:,}** 🪙 → "
                f"残高 {h['balance_after']:,} ({h['calculated_at'].strftime('%m/%d')})"
            )

        embed = savings_embed("利息履歴")
        embed.description = "\n".join(lines[:15])
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ===== /flea コマンドグループ =====

    flea_group = app_commands.Group(name="flea", description="🛒 フリーマーケット")

    @flea_group.command(name="list", description="出品一覧を表示")
    async def flea_list(self, interaction: discord.Interaction):
        await interaction.response.defer()
        data = await self.manager.get_listings()

        if not data["items"]:
            await interaction.followup.send(
                embed=flea_embed(
                    "フリーマーケット",
                    "現在出品はありません。\n`/flea sell` で出品してみましょう！",
                )
            )
            return

        lines = []
        for item in data["items"]:
            lines.append(
                f"**#{item['id']}** {item['emoji']} {item['name']} × {item['quantity']}\n"
                f"  💰 {item['price_per_unit']:,} 🪙/個 | 出品者: {item['seller_name']}"
            )

        embed = flea_embed("フリーマーケット", "\n".join(lines))
        embed.set_footer(
            text=(
                f"全{data['total']}件 | "
                f"手数料{int(MARKET_CONFIG['fee_rate'] * 100)}% | "
                f"/flea buy <ID> で購入"
            )
        )
        await interaction.followup.send(embed=embed)

    @flea_group.command(name="sell", description="アイテムを出品")
    @app_commands.describe(
        item_id="アイテムID",
        quantity="出品数量",
        price="1個あたりの価格",
    )
    async def flea_sell(
        self,
        interaction: discord.Interaction,
        item_id: int,
        quantity: int,
        price: int,
    ):
        await interaction.response.defer(ephemeral=True)
        result = await self.manager.create_listing(interaction.user.id, item_id, quantity, price)

        if "error" in result:
            await interaction.followup.send(
                embed=error_embed("出品失敗", result["error"]), ephemeral=True
            )
            return

        embed = flea_embed(
            "出品完了！",
            f"出品ID: **#{result['listing_id']}**\n"
            f"数量: {result['quantity']}個 × {result['price']:,} 🪙\n"
            f"📅 {MARKET_CONFIG['listing_duration_days']}日間出品されます",
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @flea_group.command(name="buy", description="出品を購入")
    @app_commands.describe(listing_id="出品ID")
    async def flea_buy(self, interaction: discord.Interaction, listing_id: int):
        await interaction.response.defer(ephemeral=True)
        result = await self.manager.buy_listing(interaction.user.id, listing_id)

        if "error" in result:
            await interaction.followup.send(
                embed=error_embed("購入失敗", result["error"]), ephemeral=True
            )
            return

        embed = flea_embed(
            "購入完了！",
            f"{result['item_emoji']} **{result['item_name']}** × {result['quantity']}\n"
            f"💰 価格: {result['total']:,} 🪙 + 手数料: {result['fee']:,} 🪙\n"
            f"💰 残高: **{result['balance']:,}** 🪙",
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @flea_group.command(name="my_listings", description="自分の出品を管理")
    async def flea_my_listings(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        listings = await self.manager.get_my_listings(interaction.user.id)

        if not listings:
            await interaction.followup.send(
                embed=flea_embed("自分の出品", "出品中のアイテムはありません"),
                ephemeral=True,
            )
            return

        lines = []
        for item in listings:
            status_icon = {"active": "🟢", "sold": "✅", "cancelled": "❌", "expired": "⏰"}.get(
                item["status"], "❓"
            )
            lines.append(
                f"{status_icon} **#{item['id']}** "
                f"{item['emoji']} {item['name']} "
                f"× {item['quantity']} — "
                f"{item['price_per_unit']:,} 🪙/個"
            )

        embed = flea_embed("自分の出品")
        embed.description = "\n".join(lines[:15])
        await interaction.followup.send(embed=embed, ephemeral=True)

    @flea_group.command(name="cancel", description="出品をキャンセル")
    @app_commands.describe(listing_id="キャンセルする出品ID")
    async def flea_cancel(self, interaction: discord.Interaction, listing_id: int):
        await interaction.response.defer(ephemeral=True)
        result = await self.manager.cancel_listing(interaction.user.id, listing_id)

        if "error" in result:
            await interaction.followup.send(
                embed=error_embed("キャンセル失敗", result["error"]), ephemeral=True
            )
            return

        embed = flea_embed(
            "出品キャンセル完了",
            f"出品 **#{listing_id}** をキャンセルしました\nアイテムはインベントリに返却されました",
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @flea_group.command(name="price_check", description="アイテムの市場価格を確認")
    @app_commands.describe(item_id="アイテムID")
    async def flea_price_check(self, interaction: discord.Interaction, item_id: int):
        await interaction.response.defer()
        history = await self.manager.get_item_price_history(item_id)
        listings = await self.manager.get_listings(item_id=item_id, limit=5)

        embed = flea_embed(f"市場価格 (アイテムID: {item_id})")

        if listings["items"]:
            current = "\n".join(
                f"  {it['price_per_unit']:,} 🪙 × {it['quantity']} ({it['seller_name']})"
                for it in listings["items"]
            )
            embed.add_field(name="現在の出品", value=current, inline=False)

        if history:
            last5 = history[-5:]
            price_lines = "\n".join(
                f"  {h['recorded_date']}: 平均 {h['avg_price']:,} 🪙 "
                f"(min {h['min_price']:,} / max {h['max_price']:,}) vol: {h['volume']}"
                for h in last5
            )
            embed.add_field(name="価格推移", value=price_lines, inline=False)

        if not listings["items"] and not history:
            embed.description = "このアイテムの取引データはありません"

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = MarketManager(db_pool)
    await bot.add_cog(MarketCog(bot, manager))
