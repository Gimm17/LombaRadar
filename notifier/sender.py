"""
notifier/sender.py — Kirim pesan Telegram ke subscriber.

Menangani pengiriman pesan ke private chat, group, dan channel
dengan retry 1x jika gagal.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from telegram import Bot, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


async def send_message(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> bool:
    """
    Kirim pesan ke satu chat dengan retry 1x.

    Args:
        bot: Instance Bot Telegram.
        chat_id: Target chat ID.
        text: Pesan dalam format MarkdownV2.
        reply_markup: Inline keyboard (opsional).

    Returns:
        True jika berhasil, False jika gagal setelah retry.
    """
    for attempt in range(2):  # max 2 attempt (initial + 1 retry)
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
            return True
        except TelegramError as e:
            if attempt == 0:
                logger.warning(
                    "Gagal kirim pesan ke %s (attempt 1), retry dalam 5 detik: %s",
                    chat_id, e,
                )
                await asyncio.sleep(5)
            else:
                logger.error(
                    "Gagal kirim pesan ke %s setelah retry: %s",
                    chat_id, e,
                )
                return False
        except Exception as e:
            logger.error("Error tidak terduga saat kirim ke %s: %s", chat_id, e)
            return False

    return False


async def broadcast_message(
    bot: Bot,
    chat_ids: list[int],
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> tuple[int, int]:
    """
    Kirim pesan ke banyak chat secara sequential.

    Args:
        bot: Instance Bot Telegram.
        chat_ids: List target chat IDs.
        text: Pesan dalam format MarkdownV2.
        reply_markup: Inline keyboard (opsional).

    Returns:
        Tuple (sukses_count, gagal_count).
    """
    success = 0
    failed = 0

    for chat_id in chat_ids:
        result = await send_message(bot, chat_id, text, reply_markup)
        if result:
            success += 1
        else:
            failed += 1
        # Rate limiting: 1 pesan per 0.1 detik (max ~30 pesan/detik sesuai Telegram limit)
        await asyncio.sleep(0.1)

    logger.info(
        "Broadcast selesai: %d berhasil, %d gagal dari %d target",
        success, failed, len(chat_ids),
    )
    return success, failed
