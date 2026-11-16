"""
bot/handlers.py — Command handlers Telegram bot LombaRadar.

Semua command /start, /lomba, /filter, /subscribe, /unsubscribe,
/deadline, /tags, /status, /help didefinisikan di sini.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from db.database import get_db
from core.competition_manager import (
    get_latest_competitions,
    get_competitions_by_tag,
    get_deadline_competitions,
    get_competition_tags,
    get_competition_count,
)
from notifier.formatter import escape_md, format_new_competition
from bot.keyboards import new_competition_keyboard

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk /start — registrasi subscriber dan tampilkan welcome."""
    chat = update.effective_chat
    if not chat:
        return

    chat_id = chat.id
    chat_type = chat.type  # 'private', 'group', 'supergroup', 'channel'
    chat_title = chat.title or chat.full_name or None

    # Normalisasi chat_type
    db_chat_type = "private"
    if chat_type in ("group", "supergroup"):
        db_chat_type = "group"
    elif chat_type == "channel":
        db_chat_type = "channel"

    try:
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO subscribers (telegram_chat_id, chat_type, chat_title)
                VALUES (?, ?, ?)
                ON CONFLICT(telegram_chat_id)
                DO UPDATE SET
                    is_active = 1,
                    last_active_at = CURRENT_TIMESTAMP,
                    chat_title = ?
                """,
                (chat_id, db_chat_type, chat_title, chat_title),
            )
            await db.commit()
    except Exception as e:
        logger.error("Gagal registrasi subscriber %s: %s", chat_id, e)

    welcome = (
        "Halo\\! 👋 Selamat datang di *LombaRadar*\\!\n"
        "\n"
        "Saya akan membantu kamu menemukan lomba, hackathon, "
        "datathon, dan call for paper terbaru\\.\n"
        "\n"
        "*Command yang tersedia:*\n"
        "/lomba — 5 lomba terbaru\n"
        "/filter \\[tag\\] — filter by kategori\n"
        "/subscribe \\[tag\\] — langganan kategori\n"
        "/unsubscribe \\[tag\\] — berhenti langganan\n"
        "/deadline — lomba mendekati deadline\n"
        "/tags — daftar semua kategori\n"
        "/help — bantuan lengkap"
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=welcome,
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def lomba_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk /lomba — list 5 lomba terbaru."""
    chat_id = update.effective_chat.id

    # Update last_active_at
    await _touch_subscriber(chat_id)

    comps = await get_latest_competitions(limit=5)

    if not comps:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Belum ada lomba baru untuk saat ini\\.\nCoba lagi nanti\\! 🔍",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    for comp in comps:
        tags = await get_competition_tags(comp["id"])
        text = format_new_competition(comp, tags)
        keyboard = new_competition_keyboard(comp["url"], comp["id"])
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
        )


async def filter_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk /filter [tag] — filter lomba by tag."""
    chat_id = update.effective_chat.id
    await _touch_subscriber(chat_id)

    if not context.args:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Gunakan: /filter \\[tag\\]\nContoh: `/filter ai_ml`\n\n"
                 "Gunakan /tags untuk melihat daftar kategori\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    tag_slug = context.args[0].lower()
    comps = await get_competitions_by_tag(tag_slug, limit=5)

    if not comps:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Belum ada lomba baru untuk kategori ini\\.\n"
                 "Coba lagi nanti atau gunakan /lomba untuk semua kategori\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    for comp in comps:
        tags = await get_competition_tags(comp["id"])
        text = format_new_competition(comp, tags)
        keyboard = new_competition_keyboard(comp["url"], comp["id"])
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
        )


async def subscribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk /subscribe [tag] — subscribe ke tag tertentu."""
    chat_id = update.effective_chat.id
    await _touch_subscriber(chat_id)

    if not context.args:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Gunakan: /subscribe \\[tag\\]\nContoh: `/subscribe ai_ml`\n\n"
                 "Gunakan /tags untuk melihat daftar kategori\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    tag_slug = context.args[0].lower()

    try:
        async with get_db() as db:
            # Cek tag valid
            cursor = await db.execute("SELECT id, name FROM tags WHERE slug = ?", (tag_slug,))
            tag_row = await cursor.fetchone()
            if not tag_row:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Tag `{escape_md(tag_slug)}` tidak ditemukan\\.\n"
                         f"Gunakan /tags untuk melihat daftar kategori\\.",
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                return

            # Ambil subscriber id
            cursor = await db.execute(
                "SELECT id FROM subscribers WHERE telegram_chat_id = ?", (chat_id,)
            )
            sub_row = await cursor.fetchone()
            if not sub_row:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Silakan /start dulu untuk mendaftar\\.",
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                return

            await db.execute(
                "INSERT OR IGNORE INTO subscriber_tags (subscriber_id, tag_id) VALUES (?, ?)",
                (sub_row["id"], tag_row["id"]),
            )
            await db.commit()

        tag_name = escape_md(tag_row["name"])
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Berhasil subscribe ke kategori *{tag_name}*\\!",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except Exception as e:
        logger.error("Gagal subscribe: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text="Terjadi error saat subscribe\\. Coba lagi nanti\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )


async def unsubscribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk /unsubscribe [tag] — unsubscribe dari tag."""
    chat_id = update.effective_chat.id
    await _touch_subscriber(chat_id)

    if not context.args:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Gunakan: /unsubscribe \\[tag\\]\nContoh: `/unsubscribe ai_ml`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    tag_slug = context.args[0].lower()

    try:
        async with get_db() as db:
            cursor = await db.execute("SELECT id, name FROM tags WHERE slug = ?", (tag_slug,))
            tag_row = await cursor.fetchone()
            if not tag_row:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Tag `{escape_md(tag_slug)}` tidak ditemukan\\.",
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                return

            cursor = await db.execute(
                "SELECT id FROM subscribers WHERE telegram_chat_id = ?", (chat_id,)
            )
            sub_row = await cursor.fetchone()
            if sub_row:
                await db.execute(
                    "DELETE FROM subscriber_tags WHERE subscriber_id = ? AND tag_id = ?",
                    (sub_row["id"], tag_row["id"]),
                )
                await db.commit()

        tag_name = escape_md(tag_row["name"])
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Berhasil unsubscribe dari kategori *{tag_name}*\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except Exception as e:
        logger.error("Gagal unsubscribe: %s", e)


async def deadline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk /deadline — list lomba deadline < 7 hari."""
    chat_id = update.effective_chat.id
    await _touch_subscriber(chat_id)

    comps = await get_deadline_competitions(days=7)

    if not comps:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Tidak ada lomba dengan deadline dalam 7 hari ke depan\\. 🎉",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    for comp in comps:
        tags = await get_competition_tags(comp["id"])
        text = format_new_competition(comp, tags)
        keyboard = new_competition_keyboard(comp["url"], comp["id"])
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
        )


async def tags_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk /tags — list semua tag tersedia."""
    chat_id = update.effective_chat.id
    await _touch_subscriber(chat_id)

    text = (
        "*Kategori Lomba Tersedia:*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🤖 AI/ML → /filter ai\\_ml\n"
        "🌐 Web Dev → /filter web\\_dev\n"
        "📊 Datathon → /filter datathon\n"
        "📄 Paper/Jurnal → /filter paper\n"
        "🗺️ GIS → /filter gis\n"
        "📱 Mobile Dev → /filter mobile\n"
        "🔐 Cybersecurity → /filter cyber\n"
        "🏆 Umum → /filter umum\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "_Gunakan /subscribe \\[tag\\] untuk langganan kategori tertentu_"
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk /status — status bot dan jumlah lomba di DB."""
    chat_id = update.effective_chat.id

    try:
        comp_count = await get_competition_count()
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT COUNT(*) as cnt FROM subscribers WHERE is_active = 1"
            )
            sub_row = await cursor.fetchone()
            sub_count = sub_row["cnt"] if sub_row else 0

        text = (
            f"📊 *Status LombaRadar*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📋 Total lomba  : {comp_count}\n"
            f"👥 Subscriber   : {sub_count}\n"
            f"🟢 Status       : Aktif\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except Exception as e:
        logger.error("Error status: %s", e)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk /help — bantuan penggunaan bot."""
    chat_id = update.effective_chat.id

    text = (
        "📖 *Bantuan LombaRadar*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "*Command:*\n"
        "/start — Mulai \& daftar\n"
        "/lomba — 5 lomba terbaru\n"
        "/list — Daftar semua lomba \\(compact\\)\n"
        "/filter \\[tag\\] — Filter berdasarkan kategori\n"
        "/subscribe \\[tag\\] — Langganan kategori\n"
        "/unsubscribe \\[tag\\] — Berhenti langganan\n"
        "/deadline — Lomba mendekati deadline\n"
        "/tags — Daftar semua kategori\n"
        "/status — Status bot\n"
        "/help — Tampilkan bantuan ini\n"
        "\n"
        "*Contoh:*\n"
        "`/filter ai_ml` — Cari lomba AI/ML\n"
        "`/subscribe datathon` — Langganan Datathon\n"
        "\n"
        "_Bot ini mengagregasi lomba dari MLH, Devfolio, "
        "LabLab, Sumatranomics, EJAVEC, dan sumber lainnya\\._"
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk /list — tampilkan daftar judul lomba compact, klik untuk detail."""
    chat_id = update.effective_chat.id
    await _touch_subscriber(chat_id)

    page = 0
    text, keyboard = await _build_list_page(page)

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=keyboard,
    )


async def _build_list_page(page: int = 0, page_size: int = 10):
    """Build halaman list lomba — return (text, keyboard)."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    async with get_db() as db:
        # Hitung total
        cursor = await db.execute(
            "SELECT COUNT(*) FROM competitions WHERE status IN ('open', 'closing_soon')"
        )
        total = (await cursor.fetchone())[0]

        # Ambil page
        offset = page * page_size
        cursor = await db.execute(
            """
            SELECT id, title, source, deadline
            FROM competitions
            WHERE status IN ('open', 'closing_soon')
            ORDER BY scraped_at DESC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        )
        comps = [dict(row) for row in await cursor.fetchall()]

    if not comps:
        from telegram import InlineKeyboardMarkup
        return (
            "📋 *Belum ada lomba tersedia\\.*\n_Gunakan /scrape untuk mengambil data\\._",
            None,
        )

    # Build text: numbered list
    from notifier.formatter import SOURCE_LABELS, escape_md, format_deadline_short
    lines = [
        f"📋 *Daftar Lomba* \\(hal {page + 1}\\)\n"
        f"━━━━━━━━━━━━━━━━━━"
    ]
    for i, comp in enumerate(comps, start=offset + 1):
        title = escape_md(comp["title"][:50])
        src = SOURCE_LABELS.get(comp["source"], comp["source"])
        dl = escape_md(format_deadline_short(comp.get("deadline")))
        lines.append(f"{i}\\. {title}\n   _📌 {escape_md(src)} · ⏰ {dl}_")

    lines.append(f"\n_Total: {total} lomba aktif_")
    lines.append("_Klik judul di bawah untuk detail ↓_")
    text = "\n".join(lines)

    # Build inline buttons — satu per lomba
    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for i, comp in enumerate(comps, start=offset + 1):
        short_title = comp["title"][:30]
        if len(comp["title"]) > 30:
            short_title += "…"
        btn = InlineKeyboardButton(
            f"{i}. {short_title}",
            callback_data=f"detail_{comp['id']}",
        )
        row.append(btn)
        if len(row) == 1:  # 1 button per row for readability
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # Pagination buttons
    total_pages = (total + page_size - 1) // page_size
    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"listpage_{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"listpage_{page + 1}"))
    if nav_row:
        buttons.append(nav_row)

    return text, InlineKeyboardMarkup(buttons)


async def scrape_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk /scrape — trigger scraping manual (owner only)."""
    chat_id = update.effective_chat.id

    if not _is_owner(chat_id):
        await context.bot.send_message(
            chat_id=chat_id,
            text="⛔ Command ini hanya bisa digunakan oleh owner bot\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text="🔄 *Memulai scraping manual\\.\\.\\.*\nMohon tunggu, ini bisa memakan waktu beberapa menit\\.",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    try:
        from core.competition_manager import run_all_scrapers, process_and_save, update_competition_statuses

        # Scrape
        raw_competitions = await run_all_scrapers()

        # Process & save
        new_ids = await process_and_save(raw_competitions)

        # Update statuses
        await update_competition_statuses()

        # Report
        total_scraped = len(raw_competitions)
        total_new = len(new_ids)
        total_db = await get_competition_count()

        text = (
            f"✅ *Scraping Manual Selesai\\!*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔍 Total di\\-scrape  : {total_scraped}\n"
            f"🆕 Lomba baru       : {total_new}\n"
            f"📋 Total di DB      : {total_db}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except Exception as e:
        logger.error("Error scrape manual: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Scraping gagal: {escape_md(str(e))}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )


def _is_owner(chat_id: int) -> bool:
    """Cek apakah chat_id adalah owner bot."""
    from config.settings import OWNER_CHAT_ID
    if not OWNER_CHAT_ID:
        return False
    return chat_id == OWNER_CHAT_ID


async def _touch_subscriber(chat_id: int) -> None:
    """Update last_active_at subscriber."""
    try:
        async with get_db() as db:
            await db.execute(
                "UPDATE subscribers SET last_active_at = CURRENT_TIMESTAMP WHERE telegram_chat_id = ?",
                (chat_id,),
            )
            await db.commit()
    except Exception:
        pass  # Non-critical

