"""
bot/keyboards.py — InlineKeyboardMarkup builders untuk LombaRadar.

Semua keyboard layout yang digunakan di pesan notifikasi dan command.
"""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def new_competition_keyboard(url: str, competition_id: str) -> InlineKeyboardMarkup:
    """Keyboard untuk pesan lomba baru."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Daftar Sekarang 🔗", url=url)],
        [
            InlineKeyboardButton("Simpan 🔖", callback_data=f"save_{competition_id}"),
            InlineKeyboardButton("Bagikan 📤", callback_data=f"share_{competition_id}"),
        ],
    ])


def reminder_7d_keyboard(url: str) -> InlineKeyboardMarkup:
    """Keyboard untuk reminder 7 hari."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Lihat Detail 👀", url=url)],
        [InlineKeyboardButton("Submit Sekarang ✅", url=url)],
    ])


def reminder_1d_keyboard(url: str) -> InlineKeyboardMarkup:
    """Keyboard untuk reminder 1 hari (besok)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Daftar Sekarang ⚡", url=url)],
    ])


def digest_keyboard() -> InlineKeyboardMarkup:
    """Keyboard untuk daily digest."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Lihat Semua 📋", callback_data="list_all"),
            InlineKeyboardButton("Filter Kategori 🏷", callback_data="show_filter"),
        ],
    ])


def tag_filter_keyboard(tags: list[dict]) -> InlineKeyboardMarkup:
    """Keyboard untuk memilih filter tag."""
    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []

    for tag in tags:
        emoji = tag.get("emoji", "🏷")
        name = tag.get("name", "")
        slug = tag.get("slug", "")
        btn = InlineKeyboardButton(f"{emoji} {name}", callback_data=f"filter_{slug}")
        row.append(btn)
        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    return InlineKeyboardMarkup(buttons)
