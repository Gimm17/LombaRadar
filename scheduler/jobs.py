"""
scheduler/jobs.py — APScheduler job definitions untuk LombaRadar.

Berisi 3 job utama:
1. scrape_all_sources() — scrape & proses lomba baru
2. send_daily_digest() — kirim ringkasan harian
3. check_deadlines() — kirim reminder deadline
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from telegram import Bot

from core.competition_manager import (
    run_all_scrapers,
    process_and_save,
    update_competition_statuses,
    get_competition_tags,
)
from core.deduplicator import is_already_sent, mark_as_sent
from db.database import get_db
from notifier.formatter import (
    format_new_competition,
    format_reminder_7d,
    format_reminder_1d,
    format_digest,
)
from notifier.sender import send_message
from bot.keyboards import (
    new_competition_keyboard,
    reminder_7d_keyboard,
    reminder_1d_keyboard,
    digest_keyboard,
)

logger = logging.getLogger(__name__)


async def scrape_all_sources(bot: Bot) -> None:
    """
    Job 1: Scrape semua sumber, proses, simpan, dan kirim notifikasi.
    Interval: setiap SCRAPE_INTERVAL_HOURS jam.
    """
    logger.info("=== Mulai job scraping ===")
    try:
        # 1. Jalankan semua scraper
        raw_competitions = await run_all_scrapers()
        logger.info("Total lomba di-scrape: %d", len(raw_competitions))

        # 2. Proses dan simpan ke DB
        new_ids = await process_and_save(raw_competitions)
        logger.info("Lomba baru disimpan: %d", len(new_ids))

        # 3. Update status (closing_soon, closed)
        await update_competition_statuses()

        # 4. Kirim notifikasi lomba baru ke subscriber
        if new_ids:
            await _notify_new_competitions(bot, new_ids)

    except Exception as e:
        logger.error("Error di job scraping: %s", e)

    logger.info("=== Job scraping selesai ===")


async def send_daily_digest(bot: Bot) -> None:
    """
    Job 2: Kirim daily digest ke semua subscriber aktif.
    Waktu: 23:00 UTC (= 07:00 WITA).
    """
    logger.info("=== Mulai job daily digest ===")
    try:
        async with get_db() as db:
            # Ambil semua subscriber aktif
            cursor = await db.execute(
                "SELECT * FROM subscribers WHERE is_active = 1"
            )
            subscribers = await cursor.fetchall()

            for sub in subscribers:
                try:
                    chat_id = sub["telegram_chat_id"]

                    # Ambil lomba baru (belum di-digest)
                    cursor = await db.execute(
                        """
                        SELECT c.* FROM competitions c
                        WHERE c.status IN ('open', 'closing_soon')
                        AND c.id NOT IN (
                            SELECT competition_id FROM sent_log
                            WHERE telegram_chat_id = ? AND message_type = 'digest'
                        )
                        ORDER BY c.scraped_at DESC
                        LIMIT 5
                        """,
                        (chat_id,),
                    )
                    new_comps = [dict(row) for row in await cursor.fetchall()]

                    # Ambil lomba deadline minggu ini
                    cursor = await db.execute(
                        """
                        SELECT c.* FROM competitions c
                        WHERE c.deadline IS NOT NULL
                        AND c.deadline BETWEEN date('now') AND date('now', '+7 days')
                        AND c.status IN ('open', 'closing_soon')
                        ORDER BY c.deadline ASC
                        LIMIT 3
                        """,
                    )
                    deadline_comps = [dict(row) for row in await cursor.fetchall()]

                    if not new_comps:
                        continue  # Skip jika tidak ada lomba baru

                    # Ambil tags untuk setiap lomba baru
                    tags_map: dict[str, list[dict]] = {}
                    for comp in new_comps:
                        tags_map[comp["id"]] = await get_competition_tags(comp["id"])

                    # Format & kirim digest
                    text = format_digest(new_comps, deadline_comps, tags_map)
                    if text:
                        result = await send_message(
                            bot, chat_id, text, digest_keyboard()
                        )
                        if result:
                            # Catat semua lomba di digest ke sent_log
                            for comp in new_comps:
                                await mark_as_sent(db, comp["id"], chat_id, "digest")

                except Exception as e:
                    logger.warning("Gagal kirim digest ke %s: %s", sub["telegram_chat_id"], e)
                    continue

    except Exception as e:
        logger.error("Error di job digest: %s", e)

    logger.info("=== Job daily digest selesai ===")


async def check_deadlines(bot: Bot) -> None:
    """
    Job 3: Kirim reminder deadline (7 hari dan 1 hari).
    Waktu: 23:00 UTC (= 07:00 WITA).
    """
    logger.info("=== Mulai job check deadlines ===")
    try:
        async with get_db() as db:
            # Ambil subscriber aktif
            cursor = await db.execute(
                "SELECT * FROM subscribers WHERE is_active = 1"
            )
            subscribers = await cursor.fetchall()

            # Reminder 7 hari
            cursor = await db.execute(
                """
                SELECT c.* FROM competitions c
                WHERE c.deadline = date('now', '+7 days')
                AND c.status IN ('open', 'closing_soon')
                """
            )
            comps_7d = [dict(row) for row in await cursor.fetchall()]

            # Reminder 1 hari
            cursor = await db.execute(
                """
                SELECT c.* FROM competitions c
                WHERE c.deadline = date('now', '+1 day')
                AND c.status IN ('open', 'closing_soon')
                """
            )
            comps_1d = [dict(row) for row in await cursor.fetchall()]

            for sub in subscribers:
                chat_id = sub["telegram_chat_id"]

                # Kirim reminder 7 hari
                for comp in comps_7d:
                    try:
                        if await is_already_sent(db, comp["id"], chat_id, "reminder_7d"):
                            continue
                        tags = await get_competition_tags(comp["id"])
                        text = format_reminder_7d(comp, tags)
                        keyboard = reminder_7d_keyboard(comp["url"])
                        result = await send_message(bot, chat_id, text, keyboard)
                        if result:
                            await mark_as_sent(db, comp["id"], chat_id, "reminder_7d")
                    except Exception as e:
                        logger.warning("Gagal kirim reminder_7d: %s", e)

                # Kirim reminder 1 hari
                for comp in comps_1d:
                    try:
                        if await is_already_sent(db, comp["id"], chat_id, "reminder_1d"):
                            continue
                        tags = await get_competition_tags(comp["id"])
                        text = format_reminder_1d(comp, tags)
                        keyboard = reminder_1d_keyboard(comp["url"])
                        result = await send_message(bot, chat_id, text, keyboard)
                        if result:
                            await mark_as_sent(db, comp["id"], chat_id, "reminder_1d")
                    except Exception as e:
                        logger.warning("Gagal kirim reminder_1d: %s", e)

    except Exception as e:
        logger.error("Error di job deadlines: %s", e)

    logger.info("=== Job check deadlines selesai ===")


async def _notify_new_competitions(bot: Bot, competition_ids: list[str]) -> None:
    """Kirim notifikasi lomba baru ke semua subscriber yang relevan."""
    async with get_db() as db:
        # Ambil subscriber aktif
        cursor = await db.execute(
            "SELECT * FROM subscribers WHERE is_active = 1"
        )
        subscribers = await cursor.fetchall()

        for comp_id in competition_ids:
            # Ambil data lomba
            cursor = await db.execute(
                "SELECT * FROM competitions WHERE id = ?", (comp_id,)
            )
            comp_row = await cursor.fetchone()
            if not comp_row:
                continue

            comp = dict(comp_row)
            tags = await get_competition_tags(comp_id)
            comp_tag_slugs = {t["slug"] for t in tags}

            text = format_new_competition(comp, tags)
            keyboard = new_competition_keyboard(comp["url"], comp_id)

            for sub in subscribers:
                try:
                    chat_id = sub["telegram_chat_id"]

                    # Cek apakah sudah dikirim
                    if await is_already_sent(db, comp_id, chat_id, "new"):
                        continue

                    # Cek preferensi tag subscriber
                    cursor = await db.execute(
                        """
                        SELECT t.slug FROM subscriber_tags st
                        JOIN tags t ON st.tag_id = t.id
                        WHERE st.subscriber_id = ?
                        """,
                        (sub["id"],),
                    )
                    sub_tag_rows = await cursor.fetchall()

                    # Jika subscriber punya preferensi tag, cek apakah cocok
                    if sub_tag_rows:
                        sub_tag_slugs = {row["slug"] for row in sub_tag_rows}
                        if not comp_tag_slugs.intersection(sub_tag_slugs):
                            continue  # Tag tidak cocok, skip

                    # Kirim notifikasi
                    result = await send_message(bot, chat_id, text, keyboard)
                    if result:
                        await mark_as_sent(db, comp_id, chat_id, "new")

                except Exception as e:
                    logger.warning(
                        "Gagal kirim notif lomba baru ke %s: %s",
                        sub["telegram_chat_id"], e,
                    )
