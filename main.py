"""
main.py — Entry point LombaRadar Telegram Bot.

Urutan inisialisasi:
1. Load settings dari .env
2. Setup logging (ke file + stdout)
3. Init database (buat tabel jika belum ada, seed tags)
4. Init Telegram bot application (PTB v21)
5. Register semua handlers
6. Register semua callback handlers
7. Init APScheduler
8. Register jobs
9. Start scheduler
10. Start bot polling
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from functools import partial

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)

from config.settings import (
    TELEGRAM_BOT_TOKEN,
    SCRAPE_INTERVAL_HOURS,
    DIGEST_HOUR_UTC,
    LOG_LEVEL,
    LOG_FILE,
)
from db.database import init_db
from bot.handlers import (
    start_handler,
    lomba_handler,
    filter_handler,
    subscribe_handler,
    unsubscribe_handler,
    deadline_handler,
    tags_handler,
    status_handler,
    help_handler,
    scrape_handler,
    list_handler,
)
from bot.callbacks import callback_handler
from scheduler.jobs import scrape_all_sources, send_daily_digest, check_deadlines

# ── Logging Setup ─────────────────────────────────────────────────────────────


def setup_logging() -> None:
    """Konfigurasi logging ke file dan stdout."""
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    # Kurangi noise dari library pihak ketiga
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


# ── Main ──────────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)


def main() -> None:
    """Entry point utama LombaRadar."""
    # 1. Setup logging
    setup_logging()
    logger.info("🚀 Memulai LombaRadar ...")

    # 2. Validasi token
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN tidak di-set di .env!")
        sys.exit(1)

    # 3. Build application
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # 4. Register command handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("lomba", lomba_handler))
    app.add_handler(CommandHandler("filter", filter_handler))
    app.add_handler(CommandHandler("subscribe", subscribe_handler))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_handler))
    app.add_handler(CommandHandler("deadline", deadline_handler))
    app.add_handler(CommandHandler("tags", tags_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("scrape", scrape_handler))  # owner only
    app.add_handler(CommandHandler("list", list_handler))

    # 5. Register callback query handler
    app.add_handler(CallbackQueryHandler(callback_handler))

    # 6. Post-init: init DB & scheduler
    async def post_init(application: Application) -> None:
        """Callback setelah app init — jalankan DB migration & scheduler."""
        # Init database
        await init_db()
        logger.info("Database siap.")

        # Set bot command menu (muncul saat user ketik /)
        from telegram import BotCommand
        await application.bot.set_my_commands([
            BotCommand("start", "Mulai & daftar"),
            BotCommand("lomba", "5 lomba terbaru"),
            BotCommand("list", "Daftar semua lomba"),
            BotCommand("filter", "Filter by kategori"),
            BotCommand("subscribe", "Langganan kategori"),
            BotCommand("unsubscribe", "Berhenti langganan"),
            BotCommand("deadline", "Lomba mendekati deadline"),
            BotCommand("tags", "Daftar semua kategori"),
            BotCommand("status", "Status bot"),
            BotCommand("help", "Bantuan penggunaan"),
            BotCommand("scrape", "Scraping manual (owner)"),
        ])
        logger.info("Bot command menu terdaftar.")

        # Init APScheduler
        scheduler = AsyncIOScheduler(timezone="UTC")

        bot = application.bot

        # Job 1: Scrape semua sumber setiap N jam
        scheduler.add_job(
            scrape_all_sources,
            "interval",
            hours=SCRAPE_INTERVAL_HOURS,
            args=[bot],
            id="scrape_all",
            name="Scrape All Sources",
            misfire_grace_time=3600,
        )

        # Job 2: Daily digest jam 23:00 UTC (= 07:00 WITA)
        scheduler.add_job(
            send_daily_digest,
            "cron",
            hour=DIGEST_HOUR_UTC,
            minute=0,
            args=[bot],
            id="daily_digest",
            name="Daily Digest",
            misfire_grace_time=3600,
        )

        # Job 3: Check deadlines jam 23:00 UTC
        scheduler.add_job(
            check_deadlines,
            "cron",
            hour=DIGEST_HOUR_UTC,
            minute=5,  # 5 menit setelah digest
            args=[bot],
            id="check_deadlines",
            name="Check Deadlines",
            misfire_grace_time=3600,
        )

        scheduler.start()
        logger.info(
            "Scheduler aktif — scrape setiap %d jam, digest jam %d:00 UTC",
            SCRAPE_INTERVAL_HOURS,
            DIGEST_HOUR_UTC,
        )

        # Scraping TIDAK dilakukan otomatis saat startup.
        # Gunakan /scrape untuk trigger manual, atau tunggu jadwal scheduler.

    app.post_init = post_init

    # 7. Start bot polling
    logger.info("Bot mulai polling ...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
