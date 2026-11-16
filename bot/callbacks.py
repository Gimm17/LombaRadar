"""
bot/callbacks.py — Inline keyboard callback handlers untuk LombaRadar.

Menangani callback dari tombol inline keyboard di pesan notifikasi.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.competition_manager import get_latest_competitions, get_competitions_by_tag
from notifier.formatter import escape_md, format_new_competition
from bot.keyboards import tag_filter_keyboard
from db.database import get_db

logger = logging.getLogger(__name__)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Router utama untuk semua callback query."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    data = query.data

    try:
        if data == "list_all":
            await _handle_list_all(update, context)
        elif data == "show_filter":
            await _handle_show_filter(update, context)
        elif data.startswith("filter_"):
            tag_slug = data.replace("filter_", "", 1)
            await _handle_filter_tag(update, context, tag_slug)
        elif data.startswith("save_"):
            comp_id = data.replace("save_", "", 1)
            await _handle_save(update, context, comp_id)
        elif data.startswith("share_"):
            comp_id = data.replace("share_", "", 1)
            await _handle_share(update, context, comp_id)
        elif data.startswith("detail_"):
            comp_id = data.replace("detail_", "", 1)
            await _handle_detail(update, context, comp_id)
        elif data.startswith("listpage_"):
            page = int(data.replace("listpage_", "", 1))
            await _handle_listpage(update, context, page)
        else:
            logger.warning("Callback tidak dikenal: %s", data)
    except Exception as e:
        logger.error("Error di callback '%s': %s", data, e)


async def _handle_list_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tampilkan 5 lomba terbaru."""
    comps = await get_latest_competitions(limit=5)

    if not comps:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Belum ada lomba baru untuk saat ini\\.\nCoba lagi nanti\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    for comp in comps:
        from core.competition_manager import get_competition_tags
        tags = await get_competition_tags(comp["id"])
        text = format_new_competition(comp, tags)
        from bot.keyboards import new_competition_keyboard
        keyboard = new_competition_keyboard(comp["url"], comp["id"])
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
        )


async def _handle_show_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tampilkan keyboard filter tag."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM tags ORDER BY id")
        rows = await cursor.fetchall()
        tags = [dict(row) for row in rows]

    keyboard = tag_filter_keyboard(tags)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="*Pilih Kategori:*",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=keyboard,
    )


async def _handle_filter_tag(
    update: Update, context: ContextTypes.DEFAULT_TYPE, tag_slug: str
) -> None:
    """Filter lomba berdasarkan tag."""
    comps = await get_competitions_by_tag(tag_slug, limit=5)

    if not comps:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Belum ada lomba baru untuk kategori ini\\.\n"
                 "Coba lagi nanti atau gunakan /lomba untuk semua kategori\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    for comp in comps:
        from core.competition_manager import get_competition_tags
        tags = await get_competition_tags(comp["id"])
        text = format_new_competition(comp, tags)
        from bot.keyboards import new_competition_keyboard
        keyboard = new_competition_keyboard(comp["url"], comp["id"])
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
        )


async def _handle_save(
    update: Update, context: ContextTypes.DEFAULT_TYPE, comp_id: str
) -> None:
    """Simpan lomba (ack saja, fitur bookmark untuk v2)."""
    # NOTE: Fitur bookmark/simpan bisa dikembangkan di v2 dengan tabel tersendiri
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🔖 Lomba disimpan\\! _\\(fitur lengkap segera hadir\\)_",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def _handle_share(
    update: Update, context: ContextTypes.DEFAULT_TYPE, comp_id: str
) -> None:
    """Share lomba via forward."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT title, url FROM competitions WHERE id = ?", (comp_id,)
        )
        row = await cursor.fetchone()

    if row:
        title = escape_md(row["title"])
        url = row["url"]
        text = (
            f"📤 *Bagikan lomba ini:*\n\n"
            f"📌 *{title}*\n"
            f"🔗 {escape_md(url)}\n\n"
            f"_via @LombaRadarBot_"
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
        )


async def _handle_detail(
    update: Update, context: ContextTypes.DEFAULT_TYPE, comp_id: str
) -> None:
    """Tampilkan detail lomba saat user klik dari /list."""
    from core.competition_manager import get_competition_tags
    from bot.keyboards import new_competition_keyboard

    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM competitions WHERE id = ?", (comp_id,)
        )
        row = await cursor.fetchone()

    if not row:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Lomba tidak ditemukan\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    comp = dict(row)
    tags = await get_competition_tags(comp_id)
    text = format_new_competition(comp, tags)
    keyboard = new_competition_keyboard(comp["url"], comp["id"])

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=keyboard,
    )


async def _handle_listpage(
    update: Update, context: ContextTypes.DEFAULT_TYPE, page: int
) -> None:
    """Handle pagination dari /list."""
    from bot.handlers import _build_list_page

    text, keyboard = await _build_list_page(page)

    # Edit pesan yang ada (bukan kirim baru) agar compact
    query = update.callback_query
    try:
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
        )
    except Exception:
        # Fallback: kirim pesan baru jika edit gagal
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
        )

