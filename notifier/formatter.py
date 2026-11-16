"""
notifier/formatter.py — Format pesan Telegram (MarkdownV2) untuk LombaRadar.

Semua template pesan dan helper formatting ada di sini.
Seluruh output sudah siap untuk ParseMode.MARKDOWN_V2.
"""

from __future__ import annotations

import re
import logging
from datetime import date, datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ── Escape MarkdownV2 ────────────────────────────────────────────────────────

_MD_ESCAPE_CHARS = r"\_*[]()~`>#+-=|{}.!"


def escape_md(text: str) -> str:
    """Escape semua karakter spesial MarkdownV2 Telegram."""
    if not text:
        return ""
    return re.sub(f"([{re.escape(_MD_ESCAPE_CHARS)}])", r"\\\1", str(text))


# ── Bulan Indonesia ───────────────────────────────────────────────────────────

MONTH_ID: dict[int, str] = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember",
}

DAY_ID: dict[int, str] = {
    0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis",
    4: "Jumat", 5: "Sabtu", 6: "Minggu",
}

# ── Source Label ──────────────────────────────────────────────────────────────

SOURCE_LABELS: dict[str, str] = {
    "devpost": "Devpost",
    "kaggle": "Kaggle",
    "sinta": "SINTA Dikti",
    "dicoding": "Dicoding Events",
    "lomba_info": "Lomba\\.info",
    "info_lomba": "Info Lomba",
    "twitter_x":  "X \\(Twitter\\)",
    "devfolio": "Devfolio",
    "mlh": "MLH",
    "hackerearth": "HackerEarth",
    "unstop": "Unstop",
    "lablab": "LabLab\\.ai",
    "sumatranomics": "Sumatranomics",
    "ejavec": "EJAVEC Forum",
}


# ── Helper Functions ──────────────────────────────────────────────────────────


def format_deadline_display(deadline: Optional[str]) -> str:
    """Format deadline YYYY-MM-DD ke '15 Juni 2026' atau 'Tidak diketahui'."""
    if not deadline:
        return "Tidak diketahui"
    try:
        d = date.fromisoformat(deadline)
        return f"{d.day} {MONTH_ID[d.month]} {d.year}"
    except Exception:
        return deadline


def format_deadline_short(deadline: Optional[str]) -> str:
    """Format deadline pendek: '15 Jun'."""
    if not deadline:
        return "TBD"
    try:
        d = date.fromisoformat(deadline)
        short_month = MONTH_ID[d.month][:3]
        return f"{d.day} {short_month}"
    except Exception:
        return deadline or "TBD"


def format_location(location_type: str, location_detail: str = "") -> str:
    """Return string lokasi yang sudah siap untuk MarkdownV2."""
    if location_type == "online":
        return "🌐 Online"
    elif location_type == "onsite":
        detail = f" — {escape_md(location_detail)}" if location_detail else ""
        return f"📍 Onsite{detail}"
    elif location_type == "hybrid":
        detail = f" — {escape_md(location_detail)}" if location_detail else ""
        return f"🔀 Hybrid{detail}"
    return "🌐 Online"


def format_tag_line(tags: list[dict]) -> str:
    """Format baris tag: '🤖 AI/ML  📊 Datathon'. Max 3 tag."""
    return "  ".join(
        f"{t.get('emoji', '🏷')} {escape_md(t.get('name', ''))}"
        for t in tags[:3]
    )


def format_today() -> str:
    """Format tanggal hari ini: 'Rabu, 29 Apr 2026'."""
    today = datetime.utcnow() + timedelta(hours=8)  # WITA = UTC+8
    day_name = DAY_ID[today.weekday()]
    short_month = MONTH_ID[today.month][:3]
    return f"{day_name}, {today.day} {short_month} {today.year}"


# ── Template Pesan ────────────────────────────────────────────────────────────


def format_new_competition(comp: dict, tags: list[dict]) -> str:
    """Format pesan tipe 'new' — lomba baru terdeteksi."""
    title = escape_md(comp.get("title") or "Tanpa Judul")
    organizer = escape_md(comp.get("organizer") or "Tidak diketahui")
    source_label = SOURCE_LABELS.get(comp.get("source", ""), escape_md(comp.get("source", "")))
    tag_line = format_tag_line(tags)
    prize = escape_md(comp.get("prize") or "Tidak disebutkan")
    deadline = escape_md(format_deadline_display(comp.get("deadline")))
    eligibility = escape_md(comp.get("eligibility") or "Umum")
    location = format_location(
        comp.get("location_type") or "online",
        comp.get("location_detail") or "",
    )
    url = comp.get("url", "")

    return (
        f"🏆 *Lomba Baru Terdeteksi\\!*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 *{title}*\n"
        f"🏢 _{organizer}_ · {source_label}\n"
        f"\n"
        f"🏷 {tag_line}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 Hadiah   : {prize}\n"
        f"📅 Deadline : {deadline}\n"
        f"👥 Peserta  : {eligibility}\n"
        f"📍 Lokasi   : {location}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )


def format_reminder_7d(comp: dict, tags: list[dict]) -> str:
    """Format pesan tipe 'reminder_7d' — deadline 7 hari lagi."""
    title = escape_md(comp.get("title") or "Tanpa Judul")
    organizer = escape_md(comp.get("organizer") or "Tidak diketahui")
    tag_line = format_tag_line(tags)
    deadline = escape_md(format_deadline_display(comp.get("deadline")))
    location = format_location(
        comp.get("location_type") or "online",
        comp.get("location_detail") or "",
    )

    return (
        f"⚠️ *Deadline 7 Hari Lagi\\!*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 *{title}*\n"
        f"🏢 _{organizer}_\n"
        f"\n"
        f"🏷 {tag_line}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📅 Deadline : *{deadline}* \\(7 hari lagi\\)\n"
        f"📍 Lokasi   : {location}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )


def format_reminder_1d(comp: dict, tags: list[dict]) -> str:
    """Format pesan tipe 'reminder_1d' — deadline besok."""
    title = escape_md(comp.get("title") or "Tanpa Judul")
    organizer = escape_md(comp.get("organizer") or "Tidak diketahui")
    tag_line = format_tag_line(tags)
    deadline = escape_md(format_deadline_display(comp.get("deadline")))
    location = format_location(
        comp.get("location_type", "online"),
        comp.get("location_detail", ""),
    )

    return (
        f"🚨 *Deadline Besok\\!*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 *{title}*\n"
        f"🏢 _{organizer}_\n"
        f"\n"
        f"🏷 {tag_line}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📅 Deadline : *{deadline}* \\(BESOK\\!\\)\n"
        f"📍 Lokasi   : {location}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )


def format_digest(
    new_comps: list[dict],
    deadline_comps: list[dict],
    new_tags_map: dict[str, list[dict]],
) -> Optional[str]:
    """
    Format pesan tipe 'digest' — ringkasan harian.

    Returns:
        String pesan atau None jika tidak ada lomba baru.
    """
    if not new_comps:
        return None

    tanggal = escape_md(format_today())
    n = len(new_comps)

    # Bagian lomba baru (max 5)
    lines_new: list[str] = []
    for i, comp in enumerate(new_comps[:5], start=1):
        title = escape_md(comp.get("title", ""))
        tags = new_tags_map.get(comp.get("id", ""), [])
        tag_short = tags[0].get("name", "Umum") if tags else "Umum"
        dl = format_deadline_short(comp.get("deadline"))
        lines_new.append(
            f"{i}\\. *{title}* — {escape_md(tag_short)} · {escape_md(dl)}"
        )

    msg = (
        f"📋 *Ringkasan Lomba — {tanggal}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✨ *{n} Lomba Baru:*\n"
        f"\n"
        + "\n".join(lines_new)
    )

    # Bagian deadline minggu ini (max 3)
    if deadline_comps:
        lines_dl: list[str] = []
        today = (datetime.utcnow() + timedelta(hours=8)).date()
        for comp in deadline_comps[:3]:
            title = escape_md(comp.get("title", ""))
            dl_str = comp.get("deadline")
            if dl_str:
                try:
                    dl_date = date.fromisoformat(dl_str)
                    days_left = (dl_date - today).days
                    lines_dl.append(f"‼️ {title} — {days_left} hari lagi")
                except Exception:
                    lines_dl.append(f"‼️ {title}")
            else:
                lines_dl.append(f"‼️ {title}")

        msg += (
            f"\n\n"
            f"⏰ *Deadline Minggu Ini:*\n"
            f"\n"
            + "\n".join(lines_dl)
        )

    msg += f"\n\n_Gunakan /lomba untuk daftar lengkap_"
    return msg
