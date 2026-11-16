"""
db/models.py — Dataclass untuk setiap tabel di database LombaRadar.

Digunakan sebagai type-safe wrapper atas row SQLite.
Semua modul lain import model dari sini, bukan menggunakan dict mentah.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Competition:
    """Representasi satu baris di tabel `competitions`."""

    id: str                                  # md5(url)[:12]
    title: str
    source: str                              # 'devpost', 'kaggle', dll
    url: str
    description: Optional[str] = None
    deadline: Optional[str] = None           # YYYY-MM-DD
    deadline_raw: Optional[str] = None       # teks asli dari sumber
    organizer: Optional[str] = None
    prize: Optional[str] = None
    image_url: Optional[str] = None
    eligibility: Optional[str] = None
    location_type: str = "online"            # 'online' | 'onsite' | 'hybrid'
    location_detail: Optional[str] = None
    status: str = "open"                     # 'open' | 'closing_soon' | 'closed'
    scraped_at: Optional[str] = None
    updated_at: Optional[str] = None
    # Relasi virtual — diisi oleh query JOIN, bukan kolom di tabel
    tags: list[Tag] = field(default_factory=list)


@dataclass
class Tag:
    """Representasi satu baris di tabel `tags`."""

    id: int
    name: str           # 'AI/ML', 'Web Dev', dll
    slug: str           # 'ai_ml', 'web_dev', dll
    color_hex: str      # '#7F77DD'
    emoji: str = ""     # opsional


@dataclass
class Subscriber:
    """Representasi satu baris di tabel `subscribers`."""

    id: int
    telegram_chat_id: int
    chat_type: str          # 'private' | 'group' | 'channel'
    chat_title: Optional[str] = None
    is_active: int = 1      # 1=aktif, 0=unsubscribe
    joined_at: Optional[str] = None
    last_active_at: Optional[str] = None


@dataclass
class SentLog:
    """Representasi satu baris di tabel `sent_log`."""

    id: int
    competition_id: str
    telegram_chat_id: int
    message_type: str       # 'new' | 'reminder_7d' | 'reminder_1d' | 'digest'
    sent_at: Optional[str] = None
