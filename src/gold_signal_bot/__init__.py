"""Gold Signal Bot - XAU/USD trading signals with technical analysis.

This package provides real-time gold trading signals by combining
technical indicators (RSI, MACD, EMA, Bollinger Bands) with
support/resistance detection, delivered via Telegram.

To run the bot:
    python -m gold_signal_bot

Required environment variables:
    - TELEGRAM_BOT_TOKEN: Your Telegram bot API token
    - TELEGRAM_CHAT_ID: Target chat/channel ID
    - ALPHA_VANTAGE_API_KEY: API key for price data (optional for testing)
"""

import asyncio
import logging

__version__ = "0.1.0"


async def _run_health_server(port: int) -> None:
    """Minimal aiohttp health check server for Railway/Fly.io liveness probes."""
    from aiohttp import web

    async def health(_request: web.Request) -> web.Response:
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def main() -> None:
    """Run the gold signal bot.
    
    Initializes all components and starts the alert manager
    for continuous signal monitoring and delivery.
    """
    from gold_signal_bot.analysis.signals import SignalGenerator
    from gold_signal_bot.config import get_settings
    from gold_signal_bot.data.repository import OHLCRepository
    from gold_signal_bot.telegram import AlertManager, TelegramBot
    
    # Load configuration
    settings = get_settings()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Optional health check server (for Railway/Fly.io liveness probes)
    if settings.health_check_port > 0:
        asyncio.create_task(_run_health_server(settings.health_check_port))
        logger.info(f"Health check server started on port {settings.health_check_port}")

    logger.info(f"Database: {settings.db_path}")

    # Setup data layer
    ohlc_repo = OHLCRepository(db_path=settings.db_path)
    
    # Setup analysis engine
    signal_gen = SignalGenerator(ohlc_repo)
    
    # Setup Telegram bot
    bot = TelegramBot(settings)
    
    # Setup and run alert manager
    alert_manager = AlertManager(bot, signal_gen)
    
    logger.info("Gold Signal Bot starting...")
    logger.info(f"Monitoring timeframes: {[tf.value for tf in alert_manager.timeframes]}")
    logger.info(f"Telegram chat: {settings.telegram_chat_id}")
    
    await alert_manager.run_continuous()


if __name__ == "__main__":
    asyncio.run(main())
