"""Telegram command handlers for /stats, /performance, /history.

Uses python-telegram-bot ApplicationBuilder (polling mode) to handle
user-initiated commands. Runs as a background asyncio task alongside
the AlertManager signal loop.
"""

import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes

from ..config import Settings
from ..data.signal_history import SignalHistoryRepository


class StatsCommandHandler:
    """Handles /stats, /performance, and /history Telegram commands.
    
    Runs its own Application in polling mode as a background task.
    Reads from SignalHistoryRepository for live performance data.
    """

    def __init__(
        self,
        settings: Settings,
        signal_history_repo: SignalHistoryRepository,
    ) -> None:
        self.settings = settings
        self.signal_history_repo = signal_history_repo
        self.logger = logging.getLogger(__name__)
        self._app: Application | None = None

    def _is_authorized(self, update: Update) -> bool:
        """Return True only if the message comes from the configured chat."""
        return str(update.effective_chat.id) == str(self.settings.telegram_chat_id)

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/stats — Quick win/loss/rate summary."""
        if not self._is_authorized(update):
            return
        stats = self.signal_history_repo.get_stats()
        total = stats.get("total", 0)
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        open_count = stats.get("open_count", 0)
        win_rate = stats.get("win_rate_pct") or 0.0
        avg_pnl = stats.get("avg_pnl_pct") or 0.0
        avg_pnl_sign = "+" if avg_pnl >= 0 else ""

        if total == 0:
            text = "📊 <b>Signal Performance</b>\n━━━━━━━━━━━━━━━━━━━━\nNo signals tracked yet."
        else:
            text = (
                "📊 <b>Signal Performance</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"Total signals: {total}\n"
                f"Wins: {wins} | Losses: {losses} | Open: {open_count}\n"
                f"Win rate: {win_rate:.1f}%\n"
                f"Avg P&amp;L: {avg_pnl_sign}{avg_pnl:.2f}% per trade"
            )
        await update.message.reply_text(text, parse_mode="HTML")

    async def cmd_performance(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/performance — Detailed report including per-timeframe breakdown."""
        if not self._is_authorized(update):
            return
        stats = self.signal_history_repo.get_stats()
        tf_stats = self.signal_history_repo.get_stats_by_timeframe()

        total = stats.get("total", 0)
        if total == 0:
            await update.message.reply_text(
                "📈 <b>Full Performance Report</b>\n━━━━━━━━━━━━━━━━━━━━\nNo signals tracked yet.",
                parse_mode="HTML",
            )
            return

        best = stats.get("best_pnl_pct") or 0.0
        worst = stats.get("worst_pnl_pct") or 0.0
        avg = stats.get("avg_pnl_pct") or 0.0
        best_sign = "+" if best >= 0 else ""
        worst_sign = "+" if worst >= 0 else ""
        avg_sign = "+" if avg >= 0 else ""

        tf_lines = "\n".join(
            f"  {row['timeframe']}: {row.get('win_rate_pct') or 0:.0f}% win rate "
            f"({row.get('total', 0)} signals)"
            for row in tf_stats
        ) or "  No data"

        text = (
            "📈 <b>Full Performance Report</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"Best trade: {best_sign}{best:.2f}%\n"
            f"Worst trade: {worst_sign}{worst:.2f}%\n"
            f"Avg P&amp;L: {avg_sign}{avg:.2f}%\n"
            f"\nBy timeframe:\n{tf_lines}"
        )
        await update.message.reply_text(text, parse_mode="HTML")

    async def cmd_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """/history [N] — Last N signals with status icons (default 10)."""
        if not self._is_authorized(update):
            return
        n = 10
        if context.args:
            try:
                n = max(1, min(int(context.args[0]), 50))
            except (ValueError, IndexError):
                pass

        signals = self.signal_history_repo.get_recent(limit=n)
        if not signals:
            await update.message.reply_text(
                f"Last {n} signals:\nNo signals tracked yet."
            )
            return

        STATUS_ICONS = {"WIN": "✅", "LOSS": "❌", "OPEN": "⏳", "EXPIRED": "⌛"}
        lines = [f"<b>Last {len(signals)} signals:</b>"]
        for s in signals:
            icon = STATUS_ICONS.get(s.status, "•")
            tp1_diff = (
                f"{((s.take_profit_1 - s.entry_price) / s.entry_price * 100):+.1f}%"
                if s.direction == "BUY"
                else f"{((s.entry_price - s.take_profit_1) / s.entry_price * 100):+.1f}%"
            )
            pnl_str = ""
            if s.outcome_pnl_pct is not None:
                sign = "+" if s.outcome_pnl_pct >= 0 else ""
                pnl_str = f" ({sign}{s.outcome_pnl_pct * 100:.1f}%)"
            sent_str = s.sent_at.strftime("%b %d") if s.sent_at else ""
            lines.append(
                f"{icon} {s.direction} {s.timeframe} ${s.entry_price:.0f}"
                f" → ${s.take_profit_1:.0f} ({tp1_diff}){pnl_str} {sent_str}"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def start_polling(self) -> None:
        """Build Application and start polling for commands.
        
        Runs indefinitely. Designed to be launched as asyncio.create_task().
        """
        self._app = (
            ApplicationBuilder()
            .token(self.settings.telegram_bot_token)
            .build()
        )
        self._app.add_handler(CommandHandler("stats", self.cmd_stats))
        self._app.add_handler(CommandHandler("performance", self.cmd_performance))
        self._app.add_handler(CommandHandler("history", self.cmd_history))

        self.logger.info("StatsCommandHandler: starting polling for /stats /performance /history")
        async with self._app:
            await self._app.start()
            await self._app.updater.start_polling(drop_pending_updates=True)
            import asyncio
            while True:
                await asyncio.sleep(60)

    async def stop(self) -> None:
        """Gracefully stop the Application."""
        if self._app and self._app.running:
            await self._app.updater.stop()
            await self._app.stop()
