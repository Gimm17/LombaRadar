"""
core/deduplicator.py — Hash-based dedup dan cek sent_log.

Menyediakan fungsi untuk:
- Generate ID unik dari URL (md5[:12])
- Cek duplikat di tabel competitions
- Cek & catat log pengiriman di tabel sent_log
- Ambil lomba yang belum dikirim ke subscriber tertentu
"""

from __future__ import annotations

import hashlib
import logging
from typing import Optional

import aiosqlite

from db.models import Competition, Tag

logger = logging.getLogger(__name__)


def generate_id(url: str) -> str:
    """Generate ID unik dari URL menggunakan md5[:12]."""
    return hashlib.md5(url.strip().lower().encode()).hexdigest()[:12]


async def is_competition_exists(db: aiosqlite.Connection, competition_id: str) -> bool:
    """Cek apakah competition ID sudah ada di tabel competitions."""
    cursor = await db.execute(
        "SELECT 1 FROM competitions WHERE id = ? LIMIT 1",
        (competition_id,),
    )
    row = await cursor.fetchone()
    return row is not None


async def is_already_sent(
    db: aiosqlite.Connection,
    competition_id: str,
    chat_id: int,
    message_type: str,
) -> bool:
    """Cek apakah pesan sudah pernah dikirim ke chat tertentu."""
    cursor = await db.execute(
        """
        SELECT 1 FROM sent_log
        WHERE competition_id = ? AND telegram_chat_id = ? AND message_type = ?
        LIMIT 1
        """,
        (competition_id, chat_id, message_type),
    )
    row = await cursor.fetchone()
    return row is not None


async def mark_as_sent(
    db: aiosqlite.Connection,
    competition_id: str,
    chat_id: int,
    message_type: str,
) -> None:
    """Catat bahwa pesan sudah dikirim (insert ke sent_log)."""
    await db.execute(
        """
        INSERT OR IGNORE INTO sent_log (competition_id, telegram_chat_id, message_type)
        VALUES (?, ?, ?)
        """,
        (competition_id, chat_id, message_type),
    )
    await db.commit()


async def get_unsent_competitions(
    db: aiosqlite.Connection,
    chat_id: int,
    tag_slugs: Optional[list[str]] = None,
    limit: int = 10,
) -> list[Competition]:
    """
    Ambil lomba yang belum dikirim ke chat_id.

    Args:
        db: Koneksi database.
        chat_id: Telegram chat ID subscriber.
        tag_slugs: Filter berdasarkan tag (None = semua).
        limit: Jumlah maks lomba yang diambil.

    Returns:
        List Competition yang belum dikirim.
    """
    if tag_slugs:
        placeholders = ",".join("?" for _ in tag_slugs)
        query = f"""
            SELECT DISTINCT c.*
            FROM competitions c
            JOIN competition_tags ct ON c.id = ct.competition_id
            JOIN tags t ON ct.tag_id = t.id
            WHERE t.slug IN ({placeholders})
            AND c.status = 'open'
            AND c.id NOT IN (
                SELECT competition_id FROM sent_log
                WHERE telegram_chat_id = ? AND message_type = 'new'
            )
            ORDER BY c.scraped_at DESC
            LIMIT ?
        """
        params = (*tag_slugs, chat_id, limit)
    else:
        query = """
            SELECT c.*
            FROM competitions c
            WHERE c.id NOT IN (
                SELECT competition_id FROM sent_log
                WHERE telegram_chat_id = ? AND message_type = 'new'
            )
            AND c.status = 'open'
            ORDER BY c.scraped_at DESC
            LIMIT ?
        """
        params = (chat_id, limit)

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return [_row_to_competition(row) for row in rows]


def _row_to_competition(row: aiosqlite.Row) -> Competition:
    """Konversi Row SQLite ke dataclass Competition."""
    return Competition(
        id=row["id"],
        title=row["title"],
        source=row["source"],
        url=row["url"],
        description=row["description"],
        deadline=row["deadline"],
        deadline_raw=row["deadline_raw"],
        organizer=row["organizer"],
        prize=row["prize"],
        image_url=row["image_url"],
        eligibility=row["eligibility"],
        location_type=row["location_type"],
        location_detail=row["location_detail"],
        status=row["status"],
        scraped_at=row["scraped_at"],
        updated_at=row["updated_at"],
    )
